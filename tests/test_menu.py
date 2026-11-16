from collections.abc import Callable

from fastapi.testclient import TestClient

from app.auth.states import UserRole

Headers = Callable[..., dict[str, str]]

BEEF_NOODLES = {
    "vendor": "Test Noodle House",
    "item_name": "Beef Noodles",
    "price": 120,
}


def test_anyone_can_browse_the_menu(client: TestClient, auth_headers: Headers) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    client.post("/api/menu-items", json=BEEF_NOODLES, headers=staff)
    client.post(
        "/api/menu-items",
        json={"vendor": "Test Tea Shop", "item_name": "Milk Tea", "price": 45},
        headers=staff,
    )
    client.post(
        "/api/menu-items",
        json={
            "vendor": "Test Tea Shop",
            "item_name": "Seasonal Special",
            "price": 60,
            "is_available": False,
        },
        headers=staff,
    )

    # No Authorization header on any of these
    everything = client.get("/api/menu-items")
    assert everything.status_code == 200
    assert {i["item_name"] for i in everything.json()} >= {
        "Beef Noodles",
        "Milk Tea",
        "Seasonal Special",
    }

    tea_shop = client.get("/api/menu-items", params={"vendor": "Test Tea Shop"}).json()
    assert {i["item_name"] for i in tea_shop} == {"Milk Tea", "Seasonal Special"}

    on_sale = client.get(
        "/api/menu-items", params={"vendor": "Test Tea Shop", "available_only": True}
    ).json()
    assert [i["item_name"] for i in on_sale] == ["Milk Tea"]

    vendors = client.get("/api/vendors").json()
    assert {"Test Noodle House", "Test Tea Shop"} <= set(vendors)


def test_staff_can_create_update_and_delete(
    client: TestClient, auth_headers: Headers
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)

    created = client.post("/api/menu-items", json=BEEF_NOODLES, headers=staff)
    assert created.status_code == 201
    item = created.json()
    assert item == {**BEEF_NOODLES, "id": item["id"], "is_available": True}

    # PATCH changes only what is sent
    updated = client.patch(
        f"/api/menu-items/{item['id']}",
        json={"price": 130, "is_available": False},
        headers=staff,
    )
    assert updated.status_code == 200
    assert updated.json() == {**item, "price": 130, "is_available": False}
    assert client.get(f"/api/menu-items/{item['id']}").json()["price"] == 130

    deleted = client.delete(f"/api/menu-items/{item['id']}", headers=staff)
    assert deleted.status_code == 204
    assert client.get(f"/api/menu-items/{item['id']}").status_code == 404


def test_customers_and_guests_cannot_change_the_menu(
    client: TestClient, auth_headers: Headers
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    customer = auth_headers("990000001")
    item_id = client.post("/api/menu-items", json=BEEF_NOODLES, headers=staff).json()[
        "id"
    ]

    assert client.post("/api/menu-items", json=BEEF_NOODLES).status_code == 401
    for headers in (customer,):
        assert (
            client.post("/api/menu-items", json=BEEF_NOODLES, headers=headers)
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


def test_menu_item_validation(client: TestClient, auth_headers: Headers) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)

    for bad in ({"price": -1}, {"item_name": "   "}, {"vendor": "x" * 101}):
        response = client.post(
            "/api/menu-items", json={**BEEF_NOODLES, **bad}, headers=staff
        )
        assert response.status_code == 422, bad

    missing = client.patch("/api/menu-items/999999", json={"price": 1}, headers=staff)
    assert missing.status_code == 404


def test_item_used_in_an_order_cannot_be_deleted(
    client: TestClient, auth_headers: Headers
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    customer = auth_headers("990000001")
    item_id = client.post("/api/menu-items", json=BEEF_NOODLES, headers=staff).json()[
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
