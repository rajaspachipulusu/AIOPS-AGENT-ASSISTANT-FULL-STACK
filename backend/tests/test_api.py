"""
API-level tests that don't require the LLM to be running (health checks,
auth protection, login flow). Uses FastAPI's TestClient.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

settings = get_settings()
client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoint_requires_auth():
    response = client.post("/api/ask", json={"question": "anything"})
    assert response.status_code == 403 or response.status_code == 401


def test_login_with_wrong_password_rejected():
    response = client.post(
        "/api/login", json={"username": settings.demo_username, "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_with_correct_credentials_returns_token():
    response = client.post(
        "/api/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_authenticated_request_passes_auth_layer():
    login_response = client.post(
        "/api/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    token = login_response.json()["access_token"]
    # We only assert it's not rejected by the AUTH layer (401/403). The
    # request may still fail later if Ollama isn't running, which is a
    # separate concern from authentication.
    response = client.post(
        "/api/ask",
        json={"question": "How many employees are there?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code not in (401, 403)
