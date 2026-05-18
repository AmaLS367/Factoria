from fastapi.testclient import TestClient

from backend.api.app import app
from backend.utils.templates import BUILTIN_TEMPLATES

client = TestClient(app)


def test_list_templates() -> None:
    response = client.get("/templates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= len(BUILTIN_TEMPLATES)
    slugs = [t["slug"] for t in data]
    for builtin in BUILTIN_TEMPLATES:
        assert builtin.slug in slugs


def test_create_and_get_and_delete_template() -> None:
    payload = {
        "slug": "api-test-template",
        "name": "API Test Template",
        "description": "desc",
        "item_label": "api test",
        "column_name": "API ID",
        "target_fields": ["Field A", "Field B"],
    }

    response = client.post("/templates", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "api-test-template"
    assert data["is_builtin"] is False

    response = client.get("/templates/api-test-template")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Test Template"

    response = client.delete("/templates/api-test-template")
    assert response.status_code == 204

    response = client.get("/templates/api-test-template")
    assert response.status_code == 404


def test_create_template_validations() -> None:
    # empty target fields
    payload = {
        "slug": "bad-template",
        "name": "Bad",
        "description": "",
        "item_label": "bad",
        "column_name": "ID",
        "target_fields": [],
    }
    res = client.post("/templates", json=payload)
    assert res.status_code == 400

    # invalid slug
    payload["target_fields"] = ["Valid"]
    payload["slug"] = "INVALID SLUG"
    res = client.post("/templates", json=payload)
    assert res.status_code == 400

    # > 50 fields
    payload["slug"] = "valid-slug"
    payload["target_fields"] = [f"Field {i}" for i in range(51)]
    res = client.post("/templates", json=payload)
    assert res.status_code == 400
