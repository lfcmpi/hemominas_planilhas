"""Tests para rotas de /configuracoes."""

import json
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


def _login(client):
    """Helper para autenticar no test client."""
    client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })


class TestConfiguracoesPagina:
    def test_get_configuracoes_retorna_200_autenticado(self, app_client):
        _login(app_client)
        resp = app_client.get("/configuracoes")
        assert resp.status_code == 200
        assert "Configuracoes" in resp.data.decode("utf-8")

    def test_get_configuracoes_redireciona_sem_login(self, app_client):
        resp = app_client.get("/configuracoes", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


class TestApiConfiguracoes:
    def test_get_api_retorna_json_com_chaves(self, app_client):
        _login(app_client)
        resp = app_client.get("/api/configuracoes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "google_sheets_id" in data
        assert "smtp_host" in data
        assert "cache_ttl_seconds" in data
        assert "credentials_file_exists" in data

    def test_get_api_mascara_smtp_password(self, app_client, monkeypatch):
        import src.config
        monkeypatch.setattr(src.config, "SMTP_PASSWORD", "secret123")
        _login(app_client)
        resp = app_client.get("/api/configuracoes")
        data = resp.get_json()
        assert data["smtp_password"] == "\u2022\u2022\u2022\u2022\u2022\u2022"

    def test_put_api_salva_e_retorna_sucesso(self, app_client):
        _login(app_client)
        resp = app_client.put("/api/configuracoes",
            data=json.dumps({"google_sheets_id": "NEW_ID", "smtp_port": 465}),
            content_type="application/json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sucesso" in data["mensagem"].lower() or "salva" in data["mensagem"].lower()


class TestUploadCredentials:
    def test_upload_aceita_json_valido(self, app_client, monkeypatch, tmp_path):
        import src.config
        creds_path = str(tmp_path / "credentials" / "service-account.json")
        monkeypatch.setattr(src.config, "GOOGLE_CREDENTIALS_PATH", creds_path)

        _login(app_client)
        valid_json = json.dumps({"type": "service_account", "project_id": "test"})
        from io import BytesIO
        data = {
            "file": (BytesIO(valid_json.encode()), "credentials.json"),
        }
        resp = app_client.post("/api/configuracoes/upload-credentials",
            data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        assert "sucesso" in resp.get_json()["mensagem"].lower() or "salva" in resp.get_json()["mensagem"].lower()

    def test_upload_rejeita_json_invalido(self, app_client):
        _login(app_client)
        from io import BytesIO
        data = {
            "file": (BytesIO(b"not json content"), "bad.json"),
        }
        resp = app_client.post("/api/configuracoes/upload-credentials",
            data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
