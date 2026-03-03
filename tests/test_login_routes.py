"""Tests for login/logout routes and authentication protection."""

import os
import tempfile

import pytest

from src.auth import init_users_table, seed_default_user
from src.history_store import init_db


@pytest.fixture
def app_client(monkeypatch):
    """Create a test client with a temporary database."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Patch config before importing app
    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    # Initialize DB
    init_db(db_path)
    init_users_table(db_path)
    seed_default_user(db_path)

    # Import app and patch its local SQLITE_DB_PATH reference
    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", db_path)

    app_mod.app.config["TESTING"] = True
    app_mod.app.config["WTF_CSRF_ENABLED"] = False

    with app_mod.app.test_client() as client:
        yield client

    os.unlink(db_path)


def test_get_login_returns_200(app_client):
    resp = app_client.get("/login")
    assert resp.status_code == 200
    assert b"Entrar" in resp.data


def test_post_login_valid_credentials_redirects(app_client):
    resp = app_client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/" == resp.headers["Location"] or resp.headers["Location"].endswith("/")


def test_post_login_invalid_credentials_shows_error(app_client):
    resp = app_client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "wrong",
    })
    assert resp.status_code == 200
    assert "incorretos" in resp.data.decode("utf-8")


def test_protected_page_redirects_to_login(app_client):
    resp = app_client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_returns_401_when_not_authenticated(app_client):
    resp = app_client.get("/api/historico")
    assert resp.status_code == 401
    data = resp.get_json()
    assert "error" in data


def test_logout_clears_session(app_client):
    # Login first
    app_client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })
    # Access protected page should work
    resp = app_client.get("/", follow_redirects=False)
    assert resp.status_code == 200

    # Logout
    resp = app_client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302

    # Now protected page should redirect
    resp = app_client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_authenticated_user_can_access_protected_pages(app_client):
    app_client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })
    for path in ["/", "/historico", "/dashboard", "/alertas/config"]:
        resp = app_client.get(path)
        assert resp.status_code == 200, f"Failed to access {path}"


def test_login_page_redirects_when_already_authenticated(app_client):
    app_client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })
    resp = app_client.get("/login", follow_redirects=False)
    assert resp.status_code == 302
