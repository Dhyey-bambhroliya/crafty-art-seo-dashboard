import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings
from backend.app.core.database import get_normalized_database_url, get_masked_db_url
from backend.app.services.settings_service import get_system_setting, set_system_setting

def test_database_url_normalization():
    """Verify PostgreSQL connection strings are mapped to psycopg 3 driver."""
    assert get_normalized_database_url("sqlite:///./test.db") == "sqlite:///./test.db"
    assert get_normalized_database_url("postgres://user:pass@host:5432/db") == "postgresql+psycopg://user:pass@host:5432/db"
    assert get_normalized_database_url("postgresql://user:pass@host:5432/db") == "postgresql+psycopg://user:pass@host:5432/db"
    assert get_normalized_database_url("postgresql+psycopg2://user:pass@host:5432/db") == "postgresql+psycopg://user:pass@host:5432/db"
    assert get_normalized_database_url("") == "sqlite:///./crafty_art_seo.db"

def test_database_url_masking():
    """Verify passwords are masked safely without leaking credentials."""
    raw = "postgresql://myuser:superSecretPassword123@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
    norm = get_normalized_database_url(raw)
    masked = get_masked_db_url(norm)
    assert "superSecretPassword123" not in masked
    assert "***" in masked
    assert "myuser" in masked

def test_cors_origins_configuration():
    """Verify production and local origins are present in CORS configuration."""
    origins = settings.cors_origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "https://crafty-art-seo-dashboard.vercel.app" in origins
    assert "https://crafty-art-seo-dashboard-e5q96gbo8-new-journy.vercel.app" in origins

def test_cors_preflight_options_login(client: TestClient):
    """Verify OPTIONS preflight request succeeds for login from production Vercel origins."""
    allowed_origins = [
        "https://crafty-art-seo-dashboard-e5q96gbo8-new-journy.vercel.app",
        "https://crafty-art-seo-dashboard.vercel.app",
        "http://localhost:5173",
        "https://crafty-art-seo-dashboard-anypreview.vercel.app",
    ]
    for origin in allowed_origins:
        res = client.options(
            "/api/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type, authorization",
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
        assert res.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in res.headers.get("access-control-allow-methods", "")

    # Unauthorized domain must be rejected
    rejected_res = client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://unauthorized-attacker.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
    )
    assert rejected_res.status_code == 400
    assert "Disallowed CORS origin" in rejected_res.text

def test_health_endpoints(client: TestClient):
    """Verify health check responds on both /health and /api/health."""
    res1 = client.get("/api/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/health")
    assert res2.status_code == 200
    assert res2.json()["status"] == "healthy"

def test_system_settings_persistence(db_session):
    """Verify database-backed system settings can be set and retrieved."""
    set_system_setting(db_session, "TEST_KEY", "test_value_123")
    val = get_system_setting(db_session, "TEST_KEY")
    assert val == "test_value_123"

    # Update setting
    set_system_setting(db_session, "TEST_KEY", "updated_value")
    assert get_system_setting(db_session, "TEST_KEY") == "updated_value"

def test_auth_and_gsc_config_flow(client: TestClient):
    """Verify complete authentication and database-persisted GSC configuration flow."""
    # 1. Setup Status
    res = client.get("/api/auth/setup-status")
    assert res.status_code == 200
    assert res.json()["manager_exists"] is False

    # 2. Setup initial manager
    setup_payload = {
        "email": "manager@craftyartapp.com",
        "full_name": "Crafty Art Manager",
        "password": "SecurePassword123!"
    }
    setup_res = client.post("/api/auth/setup-manager", json=setup_payload)
    assert setup_res.status_code == 200
    token = setup_res.json()["access_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Setup status now shows initialized
    status_res = client.get("/api/auth/setup-status")
    assert status_res.status_code == 200
    assert status_res.json()["manager_exists"] is True

    # 4. Second setup attempt must be rejected (cannot overwrite manager)
    second_setup = client.post("/api/auth/setup-manager", json=setup_payload)
    assert second_setup.status_code == 400

    # 5. Login
    login_res = client.post("/api/auth/login", json={
        "email": "manager@craftyartapp.com",
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    assert login_res.json()["role"] == "MANAGER"

    # 6. Current user /auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "manager@craftyartapp.com"

    # 7. Check GSC config status
    gsc_status = client.get("/api/gsc/config-status", headers=headers)
    assert gsc_status.status_code == 200

    # 8. Update GSC config via manager endpoint (persists in db)
    update_res = client.post("/api/gsc/config", headers=headers, json={
        "client_id": "123456789-abc.apps.googleusercontent.com",
        "client_secret": "my-secret-token",
        "redirect_uri": "https://crafty-art-seo-dashboard.vercel.app/gsc-connection"
    })
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["is_configured"] is True
    assert data["client_id"] == "123456789-abc.apps.googleusercontent.com"
    # Notice secret is never returned in response
    assert "client_secret" not in data or data.get("client_secret") is None

    # 9. Verify get_gsc_auth_url generates URL with newly configured client_id
    auth_url_res = client.get("/api/gsc/auth-url", headers=headers)
    assert auth_url_res.status_code == 200
    assert "accounts.google.com" in auth_url_res.json()["auth_url"]
    assert "123456789-abc.apps.googleusercontent.com" in auth_url_res.json()["auth_url"]

def test_team_leaders_seeding_and_login(client: TestClient, db_session):
    """Verify all 6 authorized Team Leaders are seeded and can login with password '12345678'."""
    from backend.app.services.user_service import seed_team_leaders, INITIAL_TEAM_LEADERS
    seed_team_leaders(db_session)

    for leader in INITIAL_TEAM_LEADERS:
        email = leader["email"]
        login_res = client.post("/api/auth/login", json={
            "email": email,
            "password": "12345678"
        })
        assert login_res.status_code == 200, f"Failed login for {email}: {login_res.text}"
        data = login_res.json()
        assert data["role"] == "TEAM_LEADER"
        assert data["email"] == email.lower()
        assert data["access_token"]

def test_cron_sync_endpoint(client: TestClient):
    """Verify automated webhook cron-sync endpoint triggers successfully."""
    res = client.get("/api/gsc/cron-sync")
    assert res.status_code == 200
    assert res.json()["status"] == "triggered"
