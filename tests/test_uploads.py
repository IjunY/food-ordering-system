from collections.abc import Callable

from fastapi.testclient import TestClient

from app.auth.states import UserRole
from app.uploads.router import MAX_BYTES

Headers = Callable[..., dict[str, str]]

# The smallest valid 1x1 PNG
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


def upload(client: TestClient, headers: dict[str, str], data: bytes, kind: str):
    return client.post(
        "/api/uploads", content=data, headers={**headers, "Content-Type": kind}
    )


def test_staff_upload_a_photo_and_it_is_served(
    client: TestClient, auth_headers: Headers
) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    response = upload(client, staff, PNG, "image/png")
    assert response.status_code == 201, response.text
    url = response.json()["url"]
    assert url.startswith("/uploads/") and url.endswith(".png")

    served = client.get(url)
    assert served.status_code == 200
    assert served.content == PNG
    assert served.headers["content-type"] == "image/png"

    # Admins can upload too (photos for a new vendor); each upload gets its own name
    admin = auth_headers("admin01", UserRole.ADMIN)
    again = upload(client, admin, PNG, "image/png")
    assert again.status_code == 201
    assert again.json()["url"] != url


def test_only_images_are_accepted(client: TestClient, auth_headers: Headers) -> None:
    staff = auth_headers("staff01", UserRole.STAFF)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    # What counts is the file itself, not the type the client claims
    for data, kind in (
        (svg, "image/svg+xml"),
        (b"hello", "image/png"),
        (b"", "image/jpeg"),
    ):
        assert upload(client, staff, data, kind).status_code == 400, data

    too_big = PNG + b"\0" * MAX_BYTES
    assert upload(client, staff, too_big, "image/png").status_code == 413


def test_customers_and_guests_cannot_upload(
    client: TestClient, auth_headers: Headers
) -> None:
    assert upload(client, {}, PNG, "image/png").status_code == 401
    customer = auth_headers("990000001")
    assert upload(client, customer, PNG, "image/png").status_code == 403
