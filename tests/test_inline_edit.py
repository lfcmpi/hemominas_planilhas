"""Tests for inline editing: PUT /api/planilha_data/<num_bolsa>."""

import os
import sqlite3
import tempfile

import bcrypt
import pytest

from src.auth import init_users_table, seed_default_user
from src.history_store import get_db, init_db
from src.sync_service import atualizar_campo_planilha


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


def _populate_data(db_path):
    """Insert test data into planilha_data."""
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO planilha_data (num_bolsa, tipo_hemocomponente, gs_rh, volume, "
            "destino, nome_paciente, responsavel_recepcao, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("25051087", "CHD", "O/POS", 292, "", "", "Ana", "2026-03-02T10:00:00"),
        )


# === Unit tests for atualizar_campo_planilha ===

class TestAtualizarCampoPlanilha:
    def test_update_editable_field(self, db_path):
        _populate_data(db_path)
        result = atualizar_campo_planilha(db_path, "25051087", "destino", "UTI", "admin@test.com")
        assert result["status"] == "sucesso"
        assert result["campo"] == "destino"

        # Verify in DB
        with get_db(db_path) as conn:
            row = conn.execute("SELECT destino, edited_by, edited_at FROM planilha_data WHERE num_bolsa = '25051087'").fetchone()
        assert row["destino"] == "UTI"
        assert row["edited_by"] == "admin@test.com"
        assert row["edited_at"] != ""

    def test_reject_non_editable_field(self, db_path):
        _populate_data(db_path)
        with pytest.raises(ValueError, match="nao pode ser editado"):
            atualizar_campo_planilha(db_path, "25051087", "status_vencimento", "OK", "admin@test.com")

    def test_reject_num_bolsa_edit(self, db_path):
        _populate_data(db_path)
        with pytest.raises(ValueError, match="nao pode ser editado"):
            atualizar_campo_planilha(db_path, "25051087", "num_bolsa", "99999", "admin@test.com")

    def test_reject_nonexistent_bolsa(self, db_path):
        _populate_data(db_path)
        with pytest.raises(ValueError, match="nao encontrada"):
            atualizar_campo_planilha(db_path, "99999999", "destino", "UTI", "admin@test.com")

    def test_update_multiple_fields_sequentially(self, db_path):
        _populate_data(db_path)
        atualizar_campo_planilha(db_path, "25051087", "destino", "UTI", "admin@test.com")
        atualizar_campo_planilha(db_path, "25051087", "nome_paciente", "Joao", "admin@test.com")

        with get_db(db_path) as conn:
            row = conn.execute("SELECT destino, nome_paciente FROM planilha_data WHERE num_bolsa = '25051087'").fetchone()
        assert row["destino"] == "UTI"
        assert row["nome_paciente"] == "Joao"


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


class TestInlineEditAPI:
    def test_edit_field_as_admin(self, app_client):
        client, db_path = app_client
        _login_admin(client)
        _populate_data(db_path)

        resp = client.put("/api/planilha_data/25051087", json={
            "campo": "destino",
            "valor": "UTI",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "sucesso"

    def test_edit_rejected_for_consulta_user(self, app_client):
        client, db_path = app_client
        _populate_data(db_path)

        # Create a consulta user
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

        resp = client.put("/api/planilha_data/25051087", json={
            "campo": "destino",
            "valor": "UTI",
        })
        assert resp.status_code == 403

    def test_edit_non_editable_field_returns_400(self, app_client):
        client, db_path = app_client
        _login_admin(client)
        _populate_data(db_path)

        resp = client.put("/api/planilha_data/25051087", json={
            "campo": "status_vencimento",
            "valor": "OK",
        })
        assert resp.status_code == 400

    def test_edit_missing_fields_returns_400(self, app_client):
        client, db_path = app_client
        _login_admin(client)

        resp = client.put("/api/planilha_data/25051087", json={})
        assert resp.status_code == 400

    def test_edit_nonexistent_bolsa_returns_400(self, app_client):
        client, db_path = app_client
        _login_admin(client)

        resp = client.put("/api/planilha_data/99999999", json={
            "campo": "destino",
            "valor": "UTI",
        })
        assert resp.status_code == 400
