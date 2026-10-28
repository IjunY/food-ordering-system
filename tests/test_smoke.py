from fastapi.testclient import TestClient

from app.main import app


def test_openapi_schema_is_served() -> None:
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 200
