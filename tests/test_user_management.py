"""Tests for user management CRUD functions and API endpoints."""

import os
import sqlite3
import tempfile

import bcrypt
import pytest

from src.auth import (
    atualizar_usuario,
    criar_usuario,
    excluir_usuario,
    init_users_table,
    listar_usuarios,
    seed_default_user,
)
from src.history_store import init_db


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_users_table(path)
    yield path
    os.unlink(path)


# === CRUD function tests ===

class TestCriarUsuario:
    def test_create_user(self, db_path):
        uid = criar_usuario(db_path, "new@test.com", "New User", "pass123", "consulta")
        assert uid > 0

    def test_create_user_invalid_role(self, db_path):
        with pytest.raises(ValueError, match="Role invalido"):
            criar_usuario(db_path, "x@test.com", "X", "pass123", "superadmin")

    def test_create_user_missing_fields(self, db_path):
        with pytest.raises(ValueError, match="obrigatorios"):
            criar_usuario(db_path, "", "Name", "pass123", "admin")

    def test_create_user_duplicate_email(self, db_path):
        criar_usuario(db_path, "dup@test.com", "Dup", "pass123", "admin")
        with pytest.raises(ValueError, match="ja esta cadastrado"):
            criar_usuario(db_path, "dup@test.com", "Dup2", "pass456", "admin")

    def test_password_is_hashed(self, db_path):
        criar_usuario(db_path, "hash@test.com", "Hash", "mypassword", "admin")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT password_hash FROM users WHERE email = 'hash@test.com'").fetchone()
        conn.close()
        assert row[0] != "mypassword"
        assert row[0].startswith("$2")


class TestListarUsuarios:
    def test_list_empty(self, db_path):
        users = listar_usuarios(db_path)
        assert users == []

    def test_list_users(self, db_path):
        criar_usuario(db_path, "a@t.com", "A", "p1", "admin")
        criar_usuario(db_path, "b@t.com", "B", "p2", "consulta")
        users = listar_usuarios(db_path)
        assert len(users) == 2
        assert users[0]["email"] == "a@t.com"
        assert users[0]["role"] == "admin"
        # Should not include password_hash
        assert "password_hash" not in users[0]


class TestAtualizarUsuario:
    def test_update_name(self, db_path):
        uid = criar_usuario(db_path, "u@t.com", "Old", "p1", "admin")
        atualizar_usuario(db_path, uid, name="New Name")
        users = listar_usuarios(db_path)
        assert users[0]["name"] == "New Name"

    def test_update_role(self, db_path):
        uid = criar_usuario(db_path, "u@t.com", "U", "p1", "admin")
        atualizar_usuario(db_path, uid, role="manager")
        users = listar_usuarios(db_path)
        assert users[0]["role"] == "manager"

    def test_update_password(self, db_path):
        uid = criar_usuario(db_path, "u@t.com", "U", "oldpass", "admin")
        atualizar_usuario(db_path, uid, password="newpass")
        from src.auth import authenticate
        user = authenticate(db_path, "u@t.com", "newpass")
        assert user is not None

    def test_update_invalid_role(self, db_path):
        uid = criar_usuario(db_path, "u@t.com", "U", "p1", "admin")
        with pytest.raises(ValueError, match="Role invalido"):
            atualizar_usuario(db_path, uid, role="bogus")

    def test_update_nonexistent_user(self, db_path):
        with pytest.raises(ValueError, match="nao encontrado"):
            atualizar_usuario(db_path, 9999, name="Ghost")


class TestExcluirUsuario:
    def test_delete_user(self, db_path):
        uid = criar_usuario(db_path, "del@t.com", "Del", "p1", "admin")
        excluir_usuario(db_path, uid)
        users = listar_usuarios(db_path)
        assert len(users) == 0

    def test_delete_nonexistent(self, db_path):
        with pytest.raises(ValueError, match="nao encontrado"):
            excluir_usuario(db_path, 9999)


# === API endpoint tests ===

@pytest.fixture
def app_client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    init_db(path)
    init_users_table(path)
    seed_default_user(path)

    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", path)
    app_mod.app.config["TESTING"] = True

    with app_mod.app.test_client() as client:
        yield client, path

    os.unlink(path)


def _login_admin(client):
    client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })


class TestUsuariosAPI:
    def test_list_usuarios(self, app_client):
        client, _ = app_client
        _login_admin(client)
        resp = client.get("/api/usuarios")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "usuarios" in data
        assert len(data["usuarios"]) == 1  # default user

    def test_create_usuario(self, app_client):
        client, _ = app_client
        _login_admin(client)
        resp = client.post("/api/usuarios", json={
            "email": "new@test.com",
            "name": "New",
            "password": "test123",
            "role": "consulta",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "id" in data

    def test_update_usuario(self, app_client):
        client, _ = app_client
        _login_admin(client)
        # Create first
        resp = client.post("/api/usuarios", json={
            "email": "upd@test.com",
            "name": "Old",
            "password": "test123",
            "role": "consulta",
        })
        uid = resp.get_json()["id"]
        # Update
        resp = client.put(f"/api/usuarios/{uid}", json={
            "name": "Updated",
            "role": "manager",
        })
        assert resp.status_code == 200

    def test_delete_usuario(self, app_client):
        client, _ = app_client
        _login_admin(client)
        resp = client.post("/api/usuarios", json={
            "email": "del@test.com",
            "name": "Del",
            "password": "test123",
            "role": "consulta",
        })
        uid = resp.get_json()["id"]
        resp = client.delete(f"/api/usuarios/{uid}")
        assert resp.status_code == 200

    def test_cannot_delete_self(self, app_client):
        client, _ = app_client
        _login_admin(client)
        # Admin user is id=1
        resp = client.delete("/api/usuarios/1")
        assert resp.status_code == 400
        assert "proprio" in resp.get_json()["error"]

    def test_usuarios_page_requires_admin(self, app_client):
        client, db_path = app_client
        # Create a non-admin user
        pw_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
            ("viewer@test.com", "Viewer", pw_hash, "consulta"),
        )
        conn.commit()
        conn.close()

        client.post("/login", data={
            "email": "viewer@test.com",
            "password": "test123",
        })
        resp = client.get("/usuarios")
        assert resp.status_code == 403

    def test_api_me(self, app_client):
        client, _ = app_client
        _login_admin(client)
        resp = client.get("/api/me")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["role"] == "admin"
        assert data["can_edit"] is True
        assert data["email"] == "anavcunha@gmail.com"
