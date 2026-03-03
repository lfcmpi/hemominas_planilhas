"""Tests para rotas de consulta e sincronizacao."""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.auth import init_users_table, seed_default_user
from src.history_store import get_db, init_db


@pytest.fixture
def app_client(monkeypatch):
    """Create a test client with a temporary database."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    import src.config
    monkeypatch.setattr(src.config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(src.config, "SCHEDULER_ENABLED", False)

    init_db(db_path)
    init_users_table(db_path)
    seed_default_user(db_path)

    import src.app as app_mod
    monkeypatch.setattr(app_mod, "SQLITE_DB_PATH", db_path)

    app_mod.app.config["TESTING"] = True
    app_mod.app.config["WTF_CSRF_ENABLED"] = False

    with app_mod.app.test_client() as client:
        yield client, db_path

    os.unlink(db_path)


def _login(client):
    client.post("/login", data={
        "email": "anavcunha@gmail.com",
        "password": "hemominas2024",
    })


def _populate_data(db_path):
    """Insert test data into planilha_data."""
    with get_db(db_path) as conn:
        rows = [
            ("25051087", "5", "VENCE EM 5 DIAS", "01/03/2026", "06/03/2026", "", "", "", "CHD", "O/POS", 292, "Ana", "", 11, "2026-03-02T10:00:00"),
            ("25009258", "-2", "VENCIDO", "15/02/2026", "27/02/2026", "", "UTI", "", "PFC", "A/NEG", 180, "Maria", "", 12, "2026-03-02T10:00:00"),
        ]
        for r in rows:
            conn.execute(
                "INSERT INTO planilha_data (num_bolsa, dias_antes_vencimento, status_vencimento, "
                "data_entrada, data_validade, data_transfusao, destino, nome_paciente, "
                "tipo_hemocomponente, gs_rh, volume, responsavel_recepcao, setor_transfusao, "
                "sheet_row, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r
            )


def test_consulta_page_authenticated(app_client):
    client, _ = app_client
    _login(client)  # admin user has access to consulta
    resp = client.get("/consulta")
    assert resp.status_code == 200
    assert "Consulta de Dados" in resp.data.decode("utf-8")


def test_consulta_page_redirects_unauthenticated(app_client):
    client, _ = app_client
    resp = client.get("/consulta", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_consulta_returns_json(app_client):
    client, db_path = app_client
    _login(client)
    _populate_data(db_path)
    resp = client.get("/api/consulta")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "rows" in data
    assert "total" in data
    assert "page" in data
    assert data["total"] == 2


def test_api_consulta_search(app_client):
    client, db_path = app_client
    _login(client)
    _populate_data(db_path)
    resp = client.get("/api/consulta?search=O/POS")
    data = resp.get_json()
    assert data["total"] == 1
    assert data["rows"][0]["gs_rh"] == "O/POS"


@patch("src.app.executar_sync")
def test_api_sync_triggers_sync(mock_sync, app_client):
    client, _ = app_client
    _login(client)
    mock_sync.return_value = {"status": "sucesso", "rows_synced": 5, "timestamp": "2026-03-02T10:00:00"}
    resp = client.post("/api/sync")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "sucesso"
    mock_sync.assert_called_once()


def test_api_sync_status(app_client):
    client, _ = app_client
    _login(client)
    resp = client.get("/api/sync/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "last_sync_at" in data
    assert "last_sync_status" in data


def test_api_consulta_dias_vencimento_max_filter(app_client):
    """Filter by dias_vencimento_max returns only bags within range."""
    client, db_path = app_client
    _login(client)
    _populate_data(db_path)
    # dias_antes_vencimento: "5" (bolsa 25051087), "-2" (bolsa 25009258)
    # With dias_max=7: only bolsa with 5 days should match (>=0 AND <=7)
    resp = client.get("/api/consulta?dias_vencimento_max=7")
    data = resp.get_json()
    assert data["total"] == 1
    assert data["rows"][0]["num_bolsa"] == "25051087"


def test_api_consulta_dias_vencimento_max_excludes_expired(app_client):
    """Expired bags (negative dias_antes_vencimento) are excluded."""
    client, db_path = app_client
    _login(client)
    _populate_data(db_path)
    # dias_max=14 should still exclude the "-2" (expired) bag
    resp = client.get("/api/consulta?dias_vencimento_max=14")
    data = resp.get_json()
    assert data["total"] == 1
    assert data["rows"][0]["num_bolsa"] == "25051087"
