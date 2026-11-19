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
        "is_accepting_orders": True,
        "image_url": None,
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
