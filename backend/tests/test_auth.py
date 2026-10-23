"""
Unit tests for JWT auth (app.auth). Deterministic, no network/LLM calls.
"""
import pytest
from jose import jwt

from app.auth import authenticate, create_access_token, ALGORITHM
from app.config import get_settings

settings = get_settings()


def test_authenticate_correct_credentials():
    assert authenticate(settings.demo_username, settings.demo_password) is True


def test_authenticate_wrong_password():
    assert authenticate(settings.demo_username, "wrong-password") is False


def test_authenticate_wrong_username():
    assert authenticate("not-a-real-user", settings.demo_password) is False


def test_create_access_token_contains_username():
    token = create_access_token("admin")
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert "exp" in payload
