def test_openapi_schema_is_served(client) -> None:
    assert client.get("/openapi.json").status_code == 200
