from app.utils.security import create_access_token, decode_token, hash_password, verify_password
from tests.conftest import register_and_login

VALID = {"name": "Sara Ali", "email": "sara@example.com", "password": "secret123", "confirm_password": "secret123"}


# ---- pure logic (no web server needed)
def test_password_hash_is_salted_and_verifiable():
    first, second = hash_password("secret123"), hash_password("secret123")
    assert first != second and "secret123" not in first
    assert verify_password("secret123", first)
    assert not verify_password("wrong-password", first)


def test_jwt_roundtrip_and_tampering():
    token = create_access_token(7)
    assert decode_token(token)["sub"] == "7"
    assert decode_token(token[:-2] + "xx") is None
    assert decode_token(create_access_token(7, expires_minutes=-1)) is None


# ---- API
def test_register_success(client):
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 201
    assert response.json()["email"] == "sara@example.com"
    assert "password" not in response.text


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json=VALID)
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists."


def test_register_invalid_email(client):
    response = client.post("/api/auth/register", json={**VALID, "email": "not-an-email"})
    assert response.status_code == 422
    assert "Please enter a valid email address." in response.json()["detail"]


def test_register_short_password_and_mismatch(client):
    short = client.post("/api/auth/register", json={**VALID, "password": "123", "confirm_password": "123"})
    assert short.status_code == 422 and "at least 8" in short.json()["detail"]
    mismatch = client.post("/api/auth/register", json={**VALID, "confirm_password": "different1"})
    assert mismatch.status_code == 422 and "do not match" in mismatch.json()["detail"]


def test_register_missing_field(client):
    response = client.post("/api/auth/register", json={"email": "a@b.com"})
    assert response.status_code == 422 and "required" in response.json()["detail"]


def test_login_success_and_invalid_login(client):
    client.post("/api/auth/register", json=VALID)
    ok = client.post("/api/auth/login", json={"email": VALID["email"], "password": VALID["password"]})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": VALID["email"], "password": "wrongpass1"})
    assert bad.status_code == 401 and bad.json()["detail"] == "Invalid email or password."
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert unknown.status_code == 401


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/resumes").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_logout_invalidates_token(client):
    headers = register_and_login(client)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
