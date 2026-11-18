from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.auth.states import UserRole

Headers = Callable[..., dict[str, str]]


@pytest.fixture
def vendors(make_vendor: Callable[..., int]) -> dict[str, int]:
    return {
        "noodles": make_vendor("Test Noodle House", "測試麵館"),
        "tea": make_vendor("Test Tea Shop", "測試茶飲"),
    }


@pytest.fixture
def staff(auth_headers: Headers, vendors: dict[str, int]) -> dict[str, str]:
    """Staff of the noodle house."""
    return auth_headers("staff01", UserRole.STAFF, vendor_id=vendors["noodles"])


@pytest.fixture
def tea_staff(auth_headers: Headers, vendors: dict[str, int]) -> dict[str, str]:
    return auth_headers("staff02", UserRole.STAFF, vendor_id=vendors["tea"])


@pytest.fixture
def admin(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("admin01", UserRole.ADMIN)


@pytest.fixture
def customer(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("990000001")


@pytest.fixture
def menu(
    client: TestClient,
    staff: dict[str, str],
    tea_staff: dict[str, str],
    vendors: dict[str, int],
) -> dict[str, int]:
    """A small menu; maps a short name to the menu item id."""

    def row(vendor: str, zh: str, en: str, price: int, **extra: object) -> dict:
        return {
            "vendor_id": vendors[vendor],
            "item_name_zh": zh,
            "item_name_en": en,
            "category_zh": "主餐",
            "category_en": "Mains",
            "price": price,
            "prep_minutes": 5,
            **extra,
        }

    rows = {
        "noodles": row("noodles", "牛肉麵", "Beef Noodles", 120),
        "dumplings": row("noodles", "水餃", "Dumplings", 60),
        "sold_out": row("noodles", "餛飩", "Wontons", 70, is_available=False),
        "tea": row("tea", "奶茶", "Milk Tea", 45),
    }
    ids = {}
    for key, body in rows.items():
        # each vendor's own staff adds its items
        headers = tea_staff if body["vendor_id"] == vendors["tea"] else staff
        response = client.post("/api/menu-items", json=body, headers=headers)
        assert response.status_code == 201, response.text
        ids[key] = response.json()["id"]
    return ids


def place(client: TestClient, headers: dict[str, str], *lines: tuple[int, int]) -> dict:
    response = client.post(
        "/api/orders",
        json={"items": [{"item_id": i, "quantity": q} for i, q in lines]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_status(client: TestClient, headers: dict[str, str], order_id: int, status: str):
    return client.patch(
        f"/api/orders/{order_id}/status", json={"status": status}, headers=headers
    )


# ---------- placing an order ----------
def test_customer_places_an_order(
    client: TestClient,
    customer: dict[str, str],
    vendors: dict[str, int],
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 2), (menu["dumplings"], 1))

    assert order["status"] == "confirming"
    assert order["created_by"] == "990000001"
    assert order["vendor_id"] == vendors["noodles"]
    assert order["vendor_name"] == {"zh": "測試麵館", "en": "Test Noodle House"}
    assert order["total"] == 2 * 120 + 60
    assert [
        (i["item_name"], i["quantity"], i["unit_price"], i["subtotal"])
        for i in order["items"]
    ] == [
        ({"zh": "牛肉麵", "en": "Beef Noodles"}, 2, 120, 240),
        ({"zh": "水餃", "en": "Dumplings"}, 1, 60, 60),
    ]
    assert order["created_at"]


def test_same_item_listed_twice_is_merged(
    client: TestClient, customer: dict[str, str], menu: dict[str, int]
) -> None:
    order = place(client, customer, (menu["noodles"], 1), (menu["noodles"], 2))

    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 3
    assert order["total"] == 360


def test_order_keeps_the_price_it_was_placed_at(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 1))

    client.patch(
        f"/api/menu-items/{menu['noodles']}", json={"price": 999}, headers=staff
    )

    again = client.get(f"/api/orders/{order['id']}", headers=customer).json()
    assert again["items"][0]["unit_price"] == 120
    assert again["total"] == 120


def test_order_rules(
    client: TestClient, customer: dict[str, str], menu: dict[str, int]
) -> None:
    def post(items: list[dict]) -> int:
        return client.post(
            "/api/orders", json={"items": items}, headers=customer
        ).status_code

    # must be signed in
    assert (
        client.post(
            "/api/orders", json={"items": [{"item_id": menu["tea"], "quantity": 1}]}
        ).status_code
        == 401
    )
    # empty order, zero quantity
    assert post([]) == 422
    assert post([{"item_id": menu["tea"], "quantity": 0}]) == 422
    # item that does not exist / is off the menu
    assert post([{"item_id": 999999, "quantity": 1}]) == 404
    assert post([{"item_id": menu["sold_out"], "quantity": 1}]) == 409
    # one order = one vendor
    assert (
        post(
            [
                {"item_id": menu["noodles"], "quantity": 1},
                {"item_id": menu["tea"], "quantity": 1},
            ]
        )
        == 400
    )
    # none of the rejected attempts left an order behind
    assert client.get("/api/orders", headers=customer).json() == []


def test_client_cannot_set_the_price(
    client: TestClient, customer: dict[str, str], menu: dict[str, int]
) -> None:
    response = client.post(
        "/api/orders",
        json={"items": [{"item_id": menu["noodles"], "quantity": 1, "unit_price": 1}]},
        headers=customer,
    )
    assert response.status_code == 201
    assert response.json()["total"] == 120


# ---------- reading orders ----------
def test_who_sees_which_orders(
    client: TestClient,
    auth_headers: Headers,
    customer: dict[str, str],
    staff: dict[str, str],
    tea_staff: dict[str, str],
    admin: dict[str, str],
    menu: dict[str, int],
) -> None:
    other = auth_headers("990000002")
    mine = place(client, customer, (menu["noodles"], 1))
    theirs = place(client, other, (menu["tea"], 1))

    listed = client.get("/api/orders", headers=customer).json()
    assert [o["id"] for o in listed] == [mine["id"]]

    # someone else's order looks like it does not exist
    assert (
        client.get(f"/api/orders/{theirs['id']}", headers=customer).status_code == 404
    )
    assert (
        client.post(f"/api/orders/{theirs['id']}/cancel", headers=customer).status_code
        == 404
    )
    assert client.get("/api/orders").status_code == 401

    # staff see their own vendor's orders only (mine is noodles, theirs is tea)
    noodle_ids = [o["id"] for o in client.get("/api/orders", headers=staff).json()]
    assert mine["id"] in noodle_ids
    assert theirs["id"] not in noodle_ids
    assert client.get(f"/api/orders/{mine['id']}", headers=staff).status_code == 200
    assert client.get(f"/api/orders/{theirs['id']}", headers=staff).status_code == 404
    tea_ids = [o["id"] for o in client.get("/api/orders", headers=tea_staff).json()]
    assert theirs["id"] in tea_ids
    assert mine["id"] not in tea_ids
    # ... and only the ones they placed themselves if they ask for mine=true
    assert client.get("/api/orders", params={"mine": True}, headers=staff).json() == []

    # admins monitor every vendor, newest first
    admin_ids = [o["id"] for o in client.get("/api/orders", headers=admin).json()]
    assert admin_ids.index(theirs["id"]) < admin_ids.index(mine["id"])
    assert client.get(f"/api/orders/{theirs['id']}", headers=admin).status_code == 200


def test_staff_without_a_vendor_only_see_their_own_orders(
    client: TestClient, auth_headers: Headers, menu: dict[str, int]
) -> None:
    newcomer = auth_headers("staff03", UserRole.STAFF)
    other = auth_headers("990000002")
    theirs = place(client, other, (menu["tea"], 1))
    own = place(client, newcomer, (menu["noodles"], 1))

    assert [o["id"] for o in client.get("/api/orders", headers=newcomer).json()] == [
        own["id"]
    ]
    assert (
        client.get(f"/api/orders/{theirs['id']}", headers=newcomer).status_code == 404
    )
    # Placing an order does not make them its vendor's staff
    assert set_status(client, newcomer, own["id"], "preparing").status_code == 403


def test_list_can_filter_by_status(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    first = place(client, customer, (menu["noodles"], 1))
    second = place(client, customer, (menu["tea"], 1))
    assert set_status(client, staff, first["id"], "preparing").status_code == 200

    preparing = client.get(
        "/api/orders", params={"status": "preparing"}, headers=customer
    ).json()
    confirming = client.get(
        "/api/orders", params={"status": "confirming"}, headers=customer
    ).json()
    assert [o["id"] for o in preparing] == [first["id"]]
    assert [o["id"] for o in confirming] == [second["id"]]


# ---------- status changes ----------
def test_staff_moves_an_order_through_to_pick_up(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 1))

    for status in ("preparing", "ready", "picked up"):
        response = set_status(client, staff, order["id"], status)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status

    # finished orders cannot change any more
    assert set_status(client, staff, order["id"], "cancelled").status_code == 409
    assert set_status(client, staff, order["id"], "preparing").status_code == 409


def test_status_cannot_skip_or_go_backwards(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 1))

    assert set_status(client, staff, order["id"], "ready").status_code == 409
    assert set_status(client, staff, order["id"], "picked up").status_code == 409
    assert set_status(client, staff, order["id"], "preparing").status_code == 200
    assert set_status(client, staff, order["id"], "confirming").status_code == 409
    assert set_status(client, staff, order["id"], "not-a-status").status_code == 422
    assert set_status(client, staff, 999999, "preparing").status_code == 404


def test_only_the_vendors_staff_can_change_status(
    client: TestClient,
    customer: dict[str, str],
    tea_staff: dict[str, str],
    admin: dict[str, str],
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 1))

    assert set_status(client, customer, order["id"], "preparing").status_code == 403
    # admins monitor only
    assert set_status(client, admin, order["id"], "preparing").status_code == 403
    assert (
        client.post(f"/api/orders/{order['id']}/cancel", headers=admin).status_code
        == 403
    )
    # another vendor's staff cannot even see it
    assert set_status(client, tea_staff, order["id"], "preparing").status_code == 404
    assert (
        client.get(f"/api/orders/{order['id']}", headers=customer).json()["status"]
        == "confirming"
    )


def test_cancelling(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    # A customer can cancel while the order is still waiting for confirmation
    waiting = place(client, customer, (menu["noodles"], 1))
    cancelled = client.post(f"/api/orders/{waiting['id']}/cancel", headers=customer)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    # ... but not twice
    assert (
        client.post(f"/api/orders/{waiting['id']}/cancel", headers=customer).status_code
        == 409
    )

    # Once the kitchen has started, only staff can cancel
    started = place(client, customer, (menu["noodles"], 1))
    assert set_status(client, staff, started["id"], "preparing").status_code == 200
    assert (
        client.post(f"/api/orders/{started['id']}/cancel", headers=customer).status_code
        == 403
    )
    by_staff = client.post(f"/api/orders/{started['id']}/cancel", headers=staff)
    assert by_staff.status_code == 200
    assert by_staff.json()["status"] == "cancelled"
