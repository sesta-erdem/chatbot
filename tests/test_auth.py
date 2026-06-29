from tests.conftest import ADMIN_TOKEN, USER_TOKEN


# --- register ---

def test_register_returns_token(client):
    resp = client.post("/auth/register", json={"email": "new@test.com", "password": "password123"})
    assert resp.status_code == 201
    assert "access_token" in resp.json()


def test_register_duplicate_email_conflicts(client):
    # me@test.com conftest'te seeded
    resp = client.post("/auth/register", json={"email": "me@test.com", "password": "password123"})
    assert resp.status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post("/auth/register", json={"email": "x@test.com", "password": "kısa"})
    assert resp.status_code == 422  # Pydantic doğrulama hatası


# --- login ---

def test_login_success_after_register(client):
    client.post("/auth/register", json={"email": "login@test.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "login@test.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "login2@test.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "login2@test.com", "password": "yanlisparola"})
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post("/auth/login", json={"email": "yok@test.com", "password": "password123"})
    assert resp.status_code == 401


# --- RBAC (rol kapısı) ---

def test_admin_endpoint_forbidden_for_user(client):
    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {USER_TOKEN}"})
    assert resp.status_code == 403


def test_admin_endpoint_allowed_for_admin(client):
    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    assert "active_connections" in resp.json()


def test_admin_endpoint_requires_auth(client):
    resp = client.get("/admin/stats")
    assert resp.status_code == 401  # HTTPBearer: başlık yoksa kimlik yok
