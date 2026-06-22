"""
Tests for auth middleware. /health always accessible. Protected endpoints reject bad keys.
"""

import pytest
from httpx import AsyncClient
from core.config import settings

@pytest.fixture
def enforce_auth():
    orig_env = settings.APP_ENV
    settings.APP_ENV = "production"
    yield
    settings.APP_ENV = orig_env

@pytest.mark.anyio
async def test_health_no_key(client: AsyncClient, enforce_auth) -> None:
    # /health is always accessible even under production mode without an API key
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.anyio
async def test_protected_no_key_in_prod(client: AsyncClient, enforce_auth) -> None:
    # Protected endpoint should reject request with 401 status when in production and no key is provided
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "decision",
        "content": "Verify auth is active."
    }
    response = await client.post("/knowledge/store", json=payload)
    assert response.status_code == 401

@pytest.mark.anyio
async def test_valid_key_passes(client: AsyncClient, enforce_auth) -> None:
    # Protected endpoint should not return 401 when valid X-API-Key is provided
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "decision",
        "content": "Verify valid key passes."
    }
    headers = {settings.api_key_header: settings.secret_key}
    response = await client.post("/knowledge/store", json=payload, headers=headers)
    assert response.status_code != 401

@pytest.mark.anyio
async def test_profile_get_and_patch(client: AsyncClient) -> None:
    # Under development environment (or any), get profile of test_user
    # 1. GET non-existent profile should return defaults
    get_res = await client.get("/profile/user_profile_test")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["user_id"] == "user_profile_test"
    assert data["profile_data"]["context_size"] == 10
    assert data["profile_data"]["preferred_language"] is None

    # 2. PATCH profile to set context_size
    patch_payload = {
        "context_size": 15,
        "preferred_language": "fr",
        "tone": "formal"
    }
    patch_res = await client.patch("/profile/user_profile_test", json=patch_payload)
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["user_id"] == "user_profile_test"
    assert patch_data["profile_data"]["context_size"] == 15
    assert patch_data["profile_data"]["preferred_language"] == "fr"
    assert patch_data["profile_data"]["tone"] == "formal"

    # 3. GET profile again to verify it persisted
    get_res2 = await client.get("/profile/user_profile_test")
    assert get_res2.status_code == 200
    data2 = get_res2.json()
    assert data2["profile_data"]["context_size"] == 15
    assert data2["profile_data"]["preferred_language"] == "fr"
    assert data2["profile_data"]["tone"] == "formal"
