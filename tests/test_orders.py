from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.states import UserRole
from app.core.errors import BadRequestError
from app.orders.pickup import check_pickup_time

Headers = Callable[..., dict[str, str]]
TAIWAN = timezone(timedelta(hours=8))


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


def test_cannot_order_from_a_vendor_that_is_not_taking_orders(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    vendors: dict[str, int],
    menu: dict[str, int],
) -> None:
    def switch(on: bool) -> None:
        response = client.patch(
            f"/api/vendors/{vendors['noodles']}",
            json={"is_accepting_orders": on},
            headers=staff,
        )
        assert response.status_code == 200, response.text

    switch(False)
    response = client.post(
        "/api/orders",
        json={"items": [{"item_id": menu["noodles"], "quantity": 1}]},
        headers=customer,
    )
    assert response.status_code == 409
    assert client.get("/api/orders", headers=customer).json() == []
    # other vendors are not affected
    place(client, customer, (menu["tea"], 1))

    switch(True)
    place(client, customer, (menu["noodles"], 1))


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


# ---------- add-ons and notes ----------
@pytest.fixture
def bento(client: TestClient, staff: dict[str, str], vendors: dict[str, int]) -> int:
    """A noodle-house item with a required rice choice and optional paid extras."""
    body = {
        "vendor_id": vendors["noodles"],
        "item_name_zh": "排骨飯",
        "item_name_en": "Pork Chop Rice",
        "category_zh": "主餐",
        "category_en": "Mains",
        "price": 100,
        "prep_minutes": 8,
        "option_groups": [
            {
                "id": "rice",
                "name": {"zh": "飯量", "en": "Rice"},
                "required": True,
                "choices": [
                    {"id": "normal", "label": {"zh": "正常", "en": "Regular"}},
                    {"id": "less", "label": {"zh": "少飯", "en": "Less rice"}},
                ],
            },
            {
                "id": "extra",
                "name": {"zh": "加點", "en": "Extras"},
                "max_select": 2,
                "choices": [
                    {
                        "id": "egg",
                        "label": {"zh": "加蛋", "en": "Egg"},
                        "price_delta": 15,
                    },
                    {
                        "id": "tofu",
                        "label": {"zh": "加豆干", "en": "Tofu"},
                        "price_delta": 10,
                    },
                    {
                        "id": "veg",
                        "label": {"zh": "加青菜", "en": "Greens"},
                        "price_delta": 20,
                    },
                ],
            },
        ],
    }
    response = client.post("/api/menu-items", json=body, headers=staff)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def order_lines(client: TestClient, headers: dict[str, str], *lines: dict):
    return client.post("/api/orders", json={"items": list(lines)}, headers=headers)


def test_add_ons_are_priced_and_kept_with_the_order(
    client: TestClient, customer: dict[str, str], staff: dict[str, str], bento: int
) -> None:
    response = order_lines(
        client,
        customer,
        {
            "item_id": bento,
            "quantity": 2,
            "option_ids": ["extra:tofu", "rice:less", "extra:egg"],
            "note": "  不要辣  ",
        },
        {"item_id": bento, "quantity": 1, "option_ids": ["rice:normal"]},
    )
    assert response.status_code == 201, response.text
    order = response.json()
    first, second = order["items"]
    # menu order, not the order they were sent in
    assert first["option_ids"] == ["rice:less", "extra:egg", "extra:tofu"]
    assert first["options_label"] == {
        "zh": "少飯、加蛋、加豆干",
        "en": "Less rice, Egg, Tofu",
    }
    assert first["note"] == "不要辣"
    assert (first["unit_price"], first["subtotal"]) == (125, 250)
    assert second["options_label"] == {"zh": "正常", "en": "Regular"}
    assert (second["unit_price"], second["note"]) == (100, "")
    assert order["total"] == 350

    # Later menu changes do not touch the order
    client.patch(f"/api/menu-items/{bento}", json={"option_groups": []}, headers=staff)
    again = client.get(f"/api/orders/{order['id']}", headers=customer).json()
    assert again["items"] == order["items"]


def test_same_add_ons_and_note_are_merged(
    client: TestClient, customer: dict[str, str], bento: int
) -> None:
    line = {"item_id": bento, "quantity": 1, "option_ids": ["rice:less"], "note": "x"}
    order = order_lines(client, customer, line, line, {**line, "note": "y"}).json()
    assert [(i["quantity"], i["note"]) for i in order["items"]] == [(2, "x"), (1, "y")]


def test_add_on_rules(client: TestClient, customer: dict[str, str], bento: int) -> None:
    for option_ids in (
        [],  # the rice choice is required
        ["rice:normal", "rice:less"],  # ... and takes one
        ["rice:normal", "extra:egg", "extra:tofu", "extra:veg"],  # at most two extras
        ["rice:normal", "extra:bacon"],  # not on the menu
        ["rice:normal", "sauce:hot"],
    ):
        response = order_lines(
            client,
            customer,
            {"item_id": bento, "quantity": 1, "option_ids": option_ids},
        )
        assert response.status_code == 400, option_ids
    too_long = {
        "item_id": bento,
        "quantity": 1,
        "option_ids": ["rice:normal"],
        "note": "x" * 61,
    }
    assert order_lines(client, customer, too_long).status_code == 422


# ---------- paying at the counter ----------
def test_customer_chooses_to_pay_at_pickup(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    auth_headers: Headers,
    menu: dict[str, int],
) -> None:
    order = place(client, customer, (menu["noodles"], 1))
    assert (order["payment_status"], order["pay_at_pickup"]) == ("unpaid", False)

    # Only the customer who placed it decides how to pay
    other = auth_headers("990000002")
    assert (
        client.post(
            f"/api/orders/{order['id']}/pay-at-pickup", headers=other
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/orders/{order['id']}/pay-at-pickup", headers=staff
        ).status_code
        == 403
    )

    chosen = client.post(f"/api/orders/{order['id']}/pay-at-pickup", headers=customer)
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["pay_at_pickup"] is True
    # The vendor sees it too
    seen = client.get(f"/api/orders/{order['id']}", headers=staff).json()
    assert (seen["pay_at_pickup"], seen["payment_status"]) == (True, "unpaid")

    # Once the vendor has started, it is too late to change how to pay
    later = place(client, customer, (menu["dumplings"], 1))
    set_status(client, staff, later["id"], "preparing")
    assert (
        client.post(
            f"/api/orders/{later['id']}/pay-at-pickup", headers=customer
        ).status_code
        == 409
    )


# ---------- booking a pickup time ----------
def _slot(minutes_from_now: int) -> datetime:
    """The first 15-minute mark at least this many minutes from now, in Taiwan time."""
    at = datetime.now(TAIWAN) + timedelta(minutes=minutes_from_now)
    mark = at.replace(minute=at.minute - at.minute % 15, second=0, microsecond=0)
    return mark if mark == at else mark + timedelta(minutes=15)


def book(
    client: TestClient, headers: dict[str, str], item_id: int, pickup_time: object
):
    return client.post(
        "/api/orders",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "pickup_time": pickup_time,
        },
        headers=headers,
    )


def test_order_without_a_time_is_as_soon_as_possible(
    client: TestClient, customer: dict[str, str], menu: dict[str, int]
) -> None:
    assert place(client, customer, (menu["noodles"], 1))["pickup_time"] is None
    assert book(client, customer, menu["noodles"], None).json()["pickup_time"] is None


def test_customer_books_a_pickup_time_and_the_vendor_sees_it(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    menu: dict[str, int],
) -> None:
    at = _slot(45)
    response = book(client, customer, menu["noodles"], at.isoformat())
    assert response.status_code == 201, response.text
    order = response.json()
    assert datetime.fromisoformat(order["pickup_time"]) == at

    for_vendor = client.get("/api/orders", headers=staff).json()
    assert [datetime.fromisoformat(o["pickup_time"]) for o in for_vendor] == [at]


def test_pickup_time_rules(
    client: TestClient, customer: dict[str, str], menu: dict[str, int]
) -> None:
    item = menu["noodles"]
    # Within 30 minutes of now: too soon (this mark is 10 to 25 minutes away)
    assert book(client, customer, item, _slot(10).isoformat()).status_code == 400
    # In the past
    assert book(client, customer, item, _slot(-60).isoformat()).status_code == 400
    # Not on a 15-minute mark
    off_mark = _slot(60) + timedelta(minutes=7)
    assert book(client, customer, item, off_mark.isoformat()).status_code == 400
    assert (
        book(client, customer, item, (_slot(60) + timedelta(seconds=1)).isoformat())
    ).status_code == 400
    # More than a day ahead
    assert book(client, customer, item, _slot(25 * 60).isoformat()).status_code == 400
    # Without a timezone the time is ambiguous
    naive = _slot(60).replace(tzinfo=None)
    assert book(client, customer, item, naive.isoformat()).status_code == 422
    assert book(client, customer, item, "soon").status_code == 422

    # The first allowed slot (31 to 46 minutes away) and one almost a day ahead are fine
    assert book(client, customer, item, _slot(31).isoformat()).status_code == 201
    assert book(client, customer, item, _slot(23 * 60).isoformat()).status_code == 201


def test_pickup_rule_edges() -> None:
    now = datetime(2026, 11, 23, 4, 0, tzinfo=UTC)  # 12:00 in Taiwan
    assert check_pickup_time(now + timedelta(minutes=30), now) == now + timedelta(
        minutes=30
    )
    with pytest.raises(BadRequestError):
        check_pickup_time(now + timedelta(minutes=15), now)
    # 24 hours ahead is the last slot allowed
    assert check_pickup_time(now + timedelta(hours=24), now)
    with pytest.raises(BadRequestError):
        check_pickup_time(now + timedelta(hours=24, minutes=15), now)
    # Stored in UTC whatever timezone it came in
    taiwan = (now + timedelta(hours=1)).astimezone(TAIWAN)
    assert check_pickup_time(taiwan, now).tzinfo is UTC


def test_pickup_hours_rule() -> None:
    now = datetime(2026, 11, 23, 0, 0, tzinfo=UTC)  # 08:00 in Taiwan
    lunch = [{"open": "11:00", "close": "13:30"}, {"open": "17:00", "close": "19:30"}]
    at = datetime(2026, 11, 23, 11, 0, tzinfo=TAIWAN)
    # Both ends of a period can be booked, the minutes outside cannot
    for hhmm in ("11:00", "12:15", "13:30", "17:00", "19:30"):
        h, m = map(int, hhmm.split(":"))
        assert check_pickup_time(at.replace(hour=h, minute=m), now, lunch), hhmm
    for hhmm in ("10:45", "13:45", "16:45", "19:45", "23:00"):
        h, m = map(int, hhmm.split(":"))
        with pytest.raises(BadRequestError):
            check_pickup_time(at.replace(hour=h, minute=m), now, lunch)
    # Checked in Taiwan time whatever timezone the time came in (03:00 UTC = 11:00)
    assert check_pickup_time(datetime(2026, 11, 23, 3, 0, tzinfo=UTC), now, lunch)
    # No pickup hours: any slot
    assert check_pickup_time(at.replace(hour=23), now, [])


def _set_pickup(client: TestClient, staff: dict[str, str], vendor_id: int, **body):
    response = client.patch(f"/api/vendors/{vendor_id}", json=body, headers=staff)
    assert response.status_code == 200, response.text
    return response.json()


def test_booking_follows_the_vendors_pickup_hours(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    vendors: dict[str, int],
    menu: dict[str, int],
) -> None:
    at = _slot(60)
    if at.hour == 0 and at.minute == 0:  # keep the period below inside one day
        at = _slot(90)
    period = {
        "open": (at - timedelta(minutes=15)).strftime("%H:%M"),
        "close": at.strftime("%H:%M"),
    }
    vendor = _set_pickup(client, staff, vendors["noodles"], pickup_hours=[period])
    assert vendor["pickup_hours"] == [period]
    assert vendor["allow_scheduled_pickup"] is True
    shown = client.get(f"/api/vendors/{vendors['noodles']}").json()
    assert shown["pickup_hours"] == [period]

    item = menu["noodles"]
    after = book(client, customer, item, (at + timedelta(minutes=15)).isoformat())
    assert after.status_code == 400
    assert book(client, customer, item, at.isoformat()).status_code == 201
    # "As soon as possible" is not limited by the pickup hours
    assert book(client, customer, item, None).status_code == 201

    # An empty list removes the limit again
    _set_pickup(client, staff, vendors["noodles"], pickup_hours=[])
    later = (at + timedelta(minutes=15)).isoformat()
    assert book(client, customer, item, later).status_code == 201


def test_vendor_can_turn_booking_off(
    client: TestClient,
    customer: dict[str, str],
    staff: dict[str, str],
    vendors: dict[str, int],
    menu: dict[str, int],
) -> None:
    vendor = _set_pickup(
        client, staff, vendors["noodles"], allow_scheduled_pickup=False
    )
    assert vendor["allow_scheduled_pickup"] is False
    item = menu["noodles"]
    assert book(client, customer, item, _slot(60).isoformat()).status_code == 409
    assert book(client, customer, item, None).status_code == 201
    # The other vendor still takes bookings
    tea = book(client, customer, menu["tea"], _slot(60).isoformat())
    assert tea.status_code == 201


def test_pickup_hours_validation(
    client: TestClient, staff: dict[str, str], vendors: dict[str, int]
) -> None:
    for bad in (
        [{"open": "13:00", "close": "11:00"}],  # closes before it opens
        [{"open": "11:00", "close": "11:00"}],
        [{"open": "11:10", "close": "13:00"}],  # not a 15-minute mark
        [{"open": "24:00", "close": "24:15"}],
        [{"open": "11:00"}],
        [{"open": "08:00", "close": "09:00"}] * 7,  # at most 6 periods
    ):
        response = client.patch(
            f"/api/vendors/{vendors['noodles']}",
            json={"pickup_hours": bad},
            headers=staff,
        )
        assert response.status_code == 422, bad
