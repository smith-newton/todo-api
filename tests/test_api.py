from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import JWT_SECRET_KEY
from app.core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# Module-level client for fast, non-database unit tests
client = TestClient(app)


def test_welcome_endpoint():
    response = client.get("/welcome")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to Todo API"


def test_todos_requires_login():
    response = client.get("/todos")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_todos_rejects_invalid_token():
    response = client.get(
        "/todos",
        headers={"Authorization": "Bearer invalid-test-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


def test_jwt_token_round_trip():
    token = create_access_token(user_id=123)
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_password_is_hashed_and_verifiable():
    password = "DemoPass123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPass123!", hashed)


def test_invalid_jwt_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("not-a-valid-jwt")


def test_expired_jwt_is_rejected():
    # Create an expired token manually
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired_token = jwt.encode(
        {"sub": "999", "exp": expired_time},
        JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


def test_password_hash_uniqueness():
    # Even with same password, bcrypt/argon2 should produce unique salts
    password = "IdenticalPassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
