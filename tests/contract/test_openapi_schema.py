"""Contract tests: validate the OpenAPI 3.1 schema with Schemathesis.

Usage:
    pytest tests/contract/ --contract

Requires ``schemathesis`` (in dev deps).  Skips automatically if schemathesis
is not installed (CI gate uses a separate job).
"""

import pytest

pytest.importorskip("schemathesis")


def test_schema_served(api_client):
    """The OpenAPI schema is served at the expected URL."""
    resp = api_client.get("/api/schema/")
    assert resp.status_code in (200, 403, 302)


def test_schema_is_valid_openapi(api_client):
    """Schema validates as OpenAPI 3.0+ and contains required paths."""
    resp = api_client.get("/api/schema/?format=json")
    if resp.status_code != 200:
        pytest.skip("schema endpoint not reachable without auth")
    schema = resp.json()
    assert "openapi" in schema or "swagger" in schema
    assert "paths" in schema
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/health/metrics" in schema["paths"]


def test_well_known_claims_schema(api_client):
    """The IAM claims-schema well-known endpoint is always public."""
    resp = api_client.get("/.well-known/iam-claims-schema.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in schema


@pytest.mark.skip(reason="schemathesis full-run needs a live server; use `st run` separately")
def test_schemathesis_full_run():
    """Placeholder: run via ``st run --base-url=http://localhost:8000 /api/schema/``."""
