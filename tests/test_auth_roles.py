"""Tests for RBAC: User.has_role, User.can_edit, role_required decorator."""

import os
import tempfile

import pytest

from src.auth import (
    User,
    authenticate,
    get_user_by_id,
    init_users_table,
    role_required,
    seed_default_user,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


# === User model tests ===

def test_user_has_role_single():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="admin")
    assert user.has_role("admin")
    assert not user.has_role("manager")


def test_user_has_role_multiple():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="manager")
    assert user.has_role("admin", "manager")
    assert not user.has_role("uploader", "consulta")


def test_user_can_edit_admin():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="admin")
    assert user.can_edit


def test_user_can_edit_manager():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="manager")
    assert user.can_edit


def test_user_cannot_edit_uploader():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="uploader")
    assert not user.can_edit


def test_user_cannot_edit_consulta():
    user = User(id=1, email="a@b.com", name="T", password_hash="x", role="consulta")
    assert not user.can_edit


def test_user_default_role_is_admin():
    user = User(id=1, email="a@b.com", name="T", password_hash="x")
    assert user.role == "admin"


# === DB integration tests ===

def test_seed_default_user_has_admin_role(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = authenticate(db_path, "anavcunha@gmail.com", "hemominas2024")
    assert user is not None
    assert user.role == "admin"


def test_get_user_by_id_returns_role(db_path):
    init_users_table(db_path)
    seed_default_user(db_path)
    user = get_user_by_id(db_path, 1)
    assert user is not None
    assert user.role == "admin"


def test_init_users_table_migration_adds_role_column(db_path):
    """If users table exists without role column, migration should add it."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
        ("test@test.com", "Test", "hash"),
    )
    conn.commit()
    conn.close()

    # Running init should add role column with default 'admin'
    init_users_table(db_path)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT role FROM users WHERE email = 'test@test.com'").fetchone()
    conn.close()
    assert row[0] == "admin"


# === role_required decorator tests (via Flask app) ===

def test_role_required_allows_authorized_role(db_path, monkeypatch):
    """Admin user can access admin-only route."""
    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    from src.history_store import init_db
    init_db(db_path)
    init_users_table(db_path)
    seed_default_user(db_path)

    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", db_path)
    app_mod.app.config["TESTING"] = True

    with app_mod.app.test_client() as client:
        # Login as admin
        client.post("/login", data={
            "email": "anavcunha@gmail.com",
            "password": "hemominas2024",
        })
        resp = client.get("/configuracoes")
        assert resp.status_code == 200


def test_role_required_blocks_unauthorized_role(db_path, monkeypatch):
    """Consulta user cannot access admin-only route."""
    import sqlite3
    import bcrypt
    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    from src.history_store import init_db
    init_db(db_path)
    init_users_table(db_path)

    # Create a consulta user
    pw_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("viewer@test.com", "Viewer", pw_hash, "consulta"),
    )
    conn.commit()
    conn.close()

    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", db_path)
    app_mod.app.config["TESTING"] = True

    with app_mod.app.test_client() as client:
        client.post("/login", data={
            "email": "viewer@test.com",
            "password": "test123",
        })
        resp = client.get("/configuracoes")
        assert resp.status_code == 403


def test_role_required_api_returns_403_json(db_path, monkeypatch):
    """API routes return JSON 403 for unauthorized roles."""
    import sqlite3
    import bcrypt
    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    from src.history_store import init_db
    init_db(db_path)
    init_users_table(db_path)

    pw_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
        ("uploader@test.com", "Uploader", pw_hash, "uploader"),
    )
    conn.commit()
    conn.close()

    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", db_path)
    app_mod.app.config["TESTING"] = True

    with app_mod.app.test_client() as client:
        client.post("/login", data={
            "email": "uploader@test.com",
            "password": "test123",
        })
        # Uploader cannot access consulta API
        resp = client.get("/api/consulta")
        assert resp.status_code == 403
        data = resp.get_json()
        assert "error" in data
