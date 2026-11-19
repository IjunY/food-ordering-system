from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.auth.states import UserRole

Headers = Callable[..., dict[str, str]]


def vendor_body(zh: str = "測試便當", en: str = "Test Bento", **extra: object) -> dict:
    return {
        "name_zh": zh,
        "name_en": en,
        "location_zh": "綜二館 1F",
        "location_en": "General Building II 1F",
        **extra,
    }


@pytest.fixture
def staff(auth_headers: Headers) -> dict[str, str]:
    """A staff account that has not registered a vendor yet."""
    return auth_headers("staff01", UserRole.STAFF)


def test_staff_registers_their_vendor(
    client: TestClient, staff: dict[str, str]
) -> None:
    # Before registering, there is no vendor to show
    assert client.get("/api/vendors/me", headers=staff).status_code == 404

    created = client.post("/api/vendors", json=vendor_body(), headers=staff)
    assert created.status_code == 201, created.text
    vendor = created.json()
    assert vendor == {
        "id": vendor["id"],
        "name": {"zh": "測試便當", "en": "Test Bento"},
        "description": {"zh": "", "en": ""},
        "opening_hours": {"zh": "", "en": ""},
        "location": {"zh": "綜二館 1F", "en": "General Building II 1F"},
        "area": "other",
        "is_accepting_orders": True,
        "image_url": None,
        "cover_image_url": None,
        "queue_count": 0,
    }

    # The account is now linked to it
    assert client.get("/api/auth/me", headers=staff).json()["vendor_id"] == vendor["id"]
    assert client.get("/api/vendors/me", headers=staff).json() == vendor
    # ... and it shows up publicly
    assert client.get(f"/api/vendors/{vendor['id']}").json() == vendor

    # One vendor per staff account
    again = client.post(
        "/api/vendors", json=vendor_body("第二家", "Second"), headers=staff
    )
    assert again.status_code == 409


def test_staff_can_then_build_their_menu(
    client: TestClient, staff: dict[str, str]
) -> None:
    item = {
        "item_name_zh": "雞腿便當",
        "item_name_en": "Chicken Leg Bento",
        "category_zh": "便當",
        "category_en": "Bento",
        "price": 100,
        "prep_minutes": 8,
    }
    # No vendor yet: nothing to add items to
    assert (
        client.post(
            "/api/menu-items", json={**item, "vendor_id": 1}, headers=staff
        ).status_code
        == 403
    )

    vendor_id = client.post("/api/vendors", json=vendor_body(), headers=staff).json()[
        "id"
    ]
    created = client.post(
        "/api/menu-items", json={**item, "vendor_id": vendor_id}, headers=staff
    )
    assert created.status_code == 201, created.text


def test_staff_update_their_own_vendor(
    client: TestClient, auth_headers: Headers, staff: dict[str, str]
) -> None:
    vendor = client.post("/api/vendors", json=vendor_body(), headers=staff).json()

    # PATCH changes only what is sent (null is ignored, like menu items)
    paused = client.patch(
        f"/api/vendors/{vendor['id']}",
        json={
            "is_accepting_orders": False,
            "name_en": "Test Bento House",
            "name_zh": None,
        },
        headers=staff,
    )
    assert paused.status_code == 200, paused.text
    assert paused.json() == {
        **vendor,
        "name": {"zh": "測試便當", "en": "Test Bento House"},
        "is_accepting_orders": False,
    }

    # Another vendor's staff cannot touch it
    other = auth_headers("staff02", UserRole.STAFF)
    client.post("/api/vendors", json=vendor_body("別家", "Other"), headers=other)
    assert (
        client.patch(
            f"/api/vendors/{vendor['id']}", json={"name_en": "Hijacked"}, headers=other
        ).status_code
        == 403
    )
    assert client.patch(
        "/api/vendors/999999", json={"name_en": "x"}, headers=staff
    ).status_code == (404)
    assert client.get(f"/api/vendors/{vendor['id']}").json()["name"]["en"] == (
        "Test Bento House"
    )


def test_vendor_validation(client: TestClient, staff: dict[str, str]) -> None:
    for bad in (
        {"name_zh": "   "},
        {"name_en": ""},
        {"location_en": "x" * 101},
    ):
        response = client.post("/api/vendors", json=vendor_body(**bad), headers=staff)
        assert response.status_code == 422, bad

    # Both names are required
    for name in ("name_zh", "name_en"):
        without = {k: v for k, v in vendor_body().items() if k != name}
        assert client.post("/api/vendors", json=without, headers=staff).status_code == (
            422
        )

    vendor_id = client.post("/api/vendors", json=vendor_body(), headers=staff).json()[
        "id"
    ]
    assert (
        client.patch(
            f"/api/vendors/{vendor_id}", json={"name_zh": "  "}, headers=staff
        ).status_code
        == 422
    )


def test_admins_customers_and_guests_can_only_read(
    client: TestClient,
    auth_headers: Headers,
    make_vendor: Callable[..., int],
) -> None:
    vendor_id = make_vendor("Test Noodle House", "測試麵館")
    admin = auth_headers("admin01", UserRole.ADMIN)
    customer = auth_headers("990000001")

    # Guests: not signed in
    assert client.post("/api/vendors", json=vendor_body()).status_code == 401
    assert (
        client.patch(f"/api/vendors/{vendor_id}", json={"name_en": "x"}).status_code
        == 401
    )

    # Admins monitor only, customers do not run vendors
    for headers in (admin, customer):
        assert (
            client.post("/api/vendors", json=vendor_body(), headers=headers).status_code
            == 403
        )
        assert (
            client.patch(
                f"/api/vendors/{vendor_id}", json={"name_en": "x"}, headers=headers
            ).status_code
            == 403
        )
        assert client.get("/api/vendors/me", headers=headers).status_code == 403
        # ... but reading works for everyone
        assert client.get("/api/vendors", headers=headers).status_code == 200
        assert client.get(f"/api/vendors/{vendor_id}", headers=headers).json()[
            "name"
        ] == {"zh": "測試麵館", "en": "Test Noodle House"}


def test_area_and_cover_photo(client: TestClient, staff: dict[str, str]) -> None:
    created = client.post(
        "/api/vendors",
        json=vendor_body(area="shuimu", cover_image_url="img/vendors/r4-cover.svg"),
        headers=staff,
    ).json()
    assert created["area"] == "shuimu"
    assert created["cover_image_url"] == "img/vendors/r4-cover.svg"

    # Unknown areas are refused
    moved = client.patch(
        f"/api/vendors/{created['id']}", json={"area": "moon"}, headers=staff
    )
    assert moved.status_code == 422
    # null removes the cover photo but leaves the area alone
    updated = client.patch(
        f"/api/vendors/{created['id']}",
        json={"cover_image_url": None, "area": None},
        headers=staff,
    ).json()
    assert updated["cover_image_url"] is None
    assert updated["area"] == "shuimu"


def test_queue_count_shows_orders_waiting(
    client: TestClient, auth_headers: Headers, staff: dict[str, str]
) -> None:
    vendor = client.post("/api/vendors", json=vendor_body(), headers=staff).json()
    item = client.post(
        "/api/menu-items",
        json={
            "vendor_id": vendor["id"],
            "item_name_zh": "便當",
            "item_name_en": "Bento",
            "category_zh": "主餐",
            "category_en": "Mains",
            "price": 80,
            "prep_minutes": 5,
        },
        headers=staff,
    ).json()
    customer = auth_headers("990000001")

    def queue() -> int:
        return client.get(f"/api/vendors/{vendor['id']}").json()["queue_count"]

    ids = [
        client.post(
            "/api/orders",
            json={"items": [{"item_id": item["id"], "quantity": 1}]},
            headers=customer,
        ).json()["id"]
        for _ in range(3)
    ]
    assert queue() == 3
    # Ready and cancelled orders are no longer waiting
    client.patch(
        f"/api/orders/{ids[0]}/status", json={"status": "preparing"}, headers=staff
    )
    assert queue() == 3
    client.patch(
        f"/api/orders/{ids[0]}/status", json={"status": "ready"}, headers=staff
    )
    client.post(f"/api/orders/{ids[1]}/cancel", headers=customer)
    assert queue() == 1
    listed = {v["id"]: v for v in client.get("/api/vendors").json()}
    assert listed[vendor["id"]]["queue_count"] == 1
