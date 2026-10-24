import pytest

def test_initial_manager_setup(client):
    # Setup status before setup
    r = client.get("/api/auth/setup-status")
    assert r.status_code == 200
    assert r.json()["is_initialized"] is False

    # Setup first manager
    setup_payload = {
        "email": "manager@craftyartapp.com",
        "full_name": "Crafty Art Admin",
        "password": "SuperSecretPassword123"
    }
    r = client.post("/api/auth/setup-manager", json=setup_payload)
    assert r.status_code == 200
    token_data = r.json()
    assert token_data["role"] == "MANAGER"
    assert "access_token" in token_data

    # Attempting second manager setup must be rejected
    r_dup = client.post("/api/auth/setup-manager", json=setup_payload)
    assert r_dup.status_code == 400

    # Login with manager credentials
    login_payload = {
        "email": "manager@craftyartapp.com",
        "password": "SuperSecretPassword123"
    }
    r_login = client.post("/api/auth/login", json=login_payload)
    assert r_login.status_code == 200
    assert r_login.json()["role"] == "MANAGER"

def test_invalid_login(client):
    r = client.post("/api/auth/login", json={"email": "nobody@craftyart.com", "password": "wrong"})
    assert r.status_code == 401
