from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.auth.states import UserRole

Headers = Callable[..., dict[str, str]]
MakeVendor = Callable[..., int]


# Requests send each text field once per language (item_name_zh / item_name_en);
# responses return each pair as one {"zh": ..., "en": ...} object, so the frontend
# can show whichever language the user picked.
def menu_item(vendor_id: int, zh: str, en: str, price: int, **extra: object) -> dict:
    return {
        "vendor_id": vendor_id,
        "item_name_zh": zh,
        "item_name_en": en,
        "category_zh": "主餐",
        "category_en": "Mains",
        "price": price,
        "prep_minutes": 5,
        **extra,
    }


@pytest.fixture
def noodle_house(make_vendor: MakeVendor) -> int:
    return make_vendor("Test Noodle House", "測試麵館")


@pytest.fixture
def beef_noodles(noodle_house: int) -> dict:
    return menu_item(noodle_house, "牛肉麵", "Beef Noodles", 120)


def test_anyone_can_browse_vendors_and_the_menu(
    client: TestClient, auth_headers: Headers, make_vendor: MakeVendor
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    noodles = make_vendor("Test Noodle House", "測試麵館")
    tea = make_vendor("Test Tea Shop", "測試茶飲", location_en="Building 1")

    client.post(
        "/api/menu-items",
        json=menu_item(noodles, "牛肉麵", "Beef Noodles", 120),
        headers=staff,
    )
    client.post(
        "/api/menu-items", json=menu_item(tea, "奶茶", "Milk Tea", 45), headers=staff
    )
    client.post(
        "/api/menu-items",
        json=menu_item(tea, "季節限定", "Seasonal Special", 60, is_available=False),
        headers=staff,
    )

    # No Authorization header on any of these
    vendors = client.get("/api/vendors")
    assert vendors.status_code == 200
    names = [v["name"] for v in vendors.json()]
    assert {"zh": "測試麵館", "en": "Test Noodle House"} in names
    assert {"zh": "測試茶飲", "en": "Test Tea Shop"} in names

    one = client.get(f"/api/vendors/{tea}")
    assert one.status_code == 200
    assert one.json()["location"] == {"zh": "", "en": "Building 1"}
    assert one.json()["is_accepting_orders"] is True
    assert client.get("/api/vendors/999999").status_code == 404

    everything = client.get("/api/menu-items")
    assert everything.status_code == 200
    assert {i["item_name"]["en"] for i in everything.json()} >= {
        "Beef Noodles",
        "Milk Tea",
        "Seasonal Special",
    }

    tea_shop = client.get("/api/menu-items", params={"vendor_id": tea}).json()
    assert [i["item_name"] for i in tea_shop] == [
        {"zh": "奶茶", "en": "Milk Tea"},
        {"zh": "季節限定", "en": "Seasonal Special"},
    ]

    on_sale = client.get(
        "/api/menu-items", params={"vendor_id": tea, "available_only": True}
    ).json()
    assert [i["item_name"]["en"] for i in on_sale] == ["Milk Tea"]


def test_staff_can_create_update_and_delete(
    client: TestClient, auth_headers: Headers, noodle_house: int, beef_noodles: dict
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)

    created = client.post("/api/menu-items", json=beef_noodles, headers=staff)
    assert created.status_code == 201
    item = created.json()
    assert item == {
        "id": item["id"],
        "vendor_id": noodle_house,
        "item_name": {"zh": "牛肉麵", "en": "Beef Noodles"},
        "category": {"zh": "主餐", "en": "Mains"},
        "price": 120,
        "prep_minutes": 5,
        "is_available": True,
    }

    # PATCH changes only what is sent
    updated = client.patch(
        f"/api/menu-items/{item['id']}",
        json={"price": 130, "is_available": False},
        headers=staff,
    )
    assert updated.status_code == 200
    assert updated.json() == {**item, "price": 130, "is_available": False}
    assert client.get(f"/api/menu-items/{item['id']}").json()["price"] == 130

    # ... including just one of the two names
    renamed = client.patch(
        f"/api/menu-items/{item['id']}",
        json={"item_name_en": "Beef Noodle Soup"},
        headers=staff,
    )
    assert renamed.status_code == 200
    assert renamed.json()["item_name"] == {"zh": "牛肉麵", "en": "Beef Noodle Soup"}

    deleted = client.delete(f"/api/menu-items/{item['id']}", headers=staff)
    assert deleted.status_code == 204
    assert client.get(f"/api/menu-items/{item['id']}").status_code == 404


def test_customers_and_guests_cannot_change_the_menu(
    client: TestClient, auth_headers: Headers, beef_noodles: dict
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    customer = auth_headers("990000001")
    item_id = client.post("/api/menu-items", json=beef_noodles, headers=staff).json()[
        "id"
    ]

    assert client.post("/api/menu-items", json=beef_noodles).status_code == 401
    for headers in (customer,):
        assert (
            client.post("/api/menu-items", json=beef_noodles, headers=headers)
        ).status_code == 403
        assert (
            client.patch(
                f"/api/menu-items/{item_id}", json={"price": 1}, headers=headers
            )
        ).status_code == 403
        assert (
            client.delete(f"/api/menu-items/{item_id}", headers=headers)
        ).status_code == 403

    assert client.get(f"/api/menu-items/{item_id}").json()["price"] == 120


def test_menu_item_validation(
    client: TestClient, auth_headers: Headers, beef_noodles: dict
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)

    for bad in (
        {"price": -1},
        {"prep_minutes": -1},
        {"item_name_zh": "   "},
        {"item_name_en": "   "},
        {"category_en": "x" * 101},
    ):
        response = client.post(
            "/api/menu-items", json={**beef_noodles, **bad}, headers=staff
        )
        assert response.status_code == 422, bad

    # Both languages are required when creating an item
    for name in ("item_name_zh", "item_name_en"):
        without = {k: v for k, v in beef_noodles.items() if k != name}
        response = client.post("/api/menu-items", json=without, headers=staff)
        assert response.status_code == 422, name

    # The vendor has to exist, when creating and when moving an item
    no_vendor = {**beef_noodles, "vendor_id": 999999}
    assert (
        client.post("/api/menu-items", json=no_vendor, headers=staff).status_code == 404
    )
    item_id = client.post("/api/menu-items", json=beef_noodles, headers=staff).json()[
        "id"
    ]
    moved = client.patch(
        f"/api/menu-items/{item_id}", json={"vendor_id": 999999}, headers=staff
    )
    assert moved.status_code == 404

    missing = client.patch("/api/menu-items/999999", json={"price": 1}, headers=staff)
    assert missing.status_code == 404


def test_item_used_in_an_order_cannot_be_deleted(
    client: TestClient, auth_headers: Headers, beef_noodles: dict
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    customer = auth_headers("990000001")
    item_id = client.post("/api/menu-items", json=beef_noodles, headers=staff).json()[
        "id"
    ]
    order = client.post(
        "/api/orders",
        json={"items": [{"item_id": item_id, "quantity": 1}]},
        headers=customer,
    )
    assert order.status_code == 201

    response = client.delete(f"/api/menu-items/{item_id}", headers=staff)
    assert response.status_code == 409
    # Still there, and the order still reads fine
    assert client.get(f"/api/menu-items/{item_id}").status_code == 200
    assert (
        client.get(f"/api/orders/{order.json()['id']}", headers=customer).status_code
        == 200
    )
