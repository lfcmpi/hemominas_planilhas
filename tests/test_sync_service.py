"""Tests para sync_service.py — sincronizacao Google Sheets -> SQLite."""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.history_store import get_db, init_db
from src.sync_service import consultar_planilha, executar_sync, obter_sync_status


@pytest.fixture
def db_path():
    """Cria banco temporario para cada teste."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


# Header row matching the MAPA DE TRANSFUSAO (columns A-S)
MOCK_HEADER = [
    "DIAS ANTES DO VENCIMENTO", "STATUS", "DATA ENTRADA", "DATA VALIDADE.",
    "DATA TRANSFUSAO/DESTINO", "DESTINO", "NOME COMPLETO DO PACIENTE",
    "TIPO DE HEMOCOMPONENTE", "GS/RH", "VOLUME (ML)",
    "RESPONS\u00c1VEL RECEP\u00c7AO", "SETOR DA TRANSFUSAO",
    "N\u00ba DA BOLSA", "N\u00ba PRONTU\u00c1RIO SALUS", "N\u00b0 PRONTUARIO MV",
    "SUS (*)N\u00ba LAUDO / N\u00ba AIH / N\u00ba APAC / BPAI", "2",
    "REA\u00c7AO TRANSFUSIONAL", "N\u00ba BOLSA SBS",
]

MOCK_ROWS = [
    ["5", "VENCE EM 5 DIAS", "01/03/2026", "06/03/2026", "", "", "Paciente A", "CHD", "O/POS", "292", "Ana", "", "25051087", "12345", "", "", "", "", ""],
    ["-2", "VENCIDO", "15/02/2026", "27/02/2026", "28/02/2026", "UTI", "Paciente B", "PFC", "A/NEG", "180", "Maria", "Enf.", "25009258", "", "67890", "", "", "Nenhuma", ""],
    ["30", "", "20/02/2026", "02/04/2026", "", "", "Paciente C", "CHD", "B/POS", "350", "Joao", "CC", "25012345", "", "", "LAUDO123", "", "", "SBS001"],
]


class TestInitDbTables:
    def test_cria_planilha_data_e_sync_metadata(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "planilha_data" in table_names
        assert "sync_metadata" in table_names
        conn.close()


class TestExecutarSync:
    @patch("src.sync_service.ler_planilha_completa")
    def test_popula_planilha_data(self, mock_ler, db_path):
        mock_ler.return_value = (MOCK_HEADER, MOCK_ROWS)
        result = executar_sync(db_path)
        assert result["status"] == "sucesso"
        assert result["rows_synced"] == 3

        with get_db(db_path) as conn:
            rows = conn.execute("SELECT * FROM planilha_data ORDER BY num_bolsa").fetchall()
            assert len(rows) == 3
            r = dict(rows[0])
            assert r["num_bolsa"] == "25009258"
            assert r["gs_rh"] == "A/NEG"
            assert r["destino"] == "UTI"
            assert r["nome_paciente"] == "Paciente B"
            assert r["setor_transfusao"] == "Enf."
            assert r["reacao_transfusional"] == "Nenhuma"

    @patch("src.sync_service.ler_planilha_completa")
    def test_upsert_atualiza_existente(self, mock_ler, db_path):
        mock_ler.return_value = (MOCK_HEADER, MOCK_ROWS)
        executar_sync(db_path)

        # Update destination for row 2
        updated_rows = [list(r) for r in MOCK_ROWS]
        updated_rows[1][5] = "Enfermaria"
        mock_ler.return_value = (MOCK_HEADER, updated_rows)
        result = executar_sync(db_path)
        assert result["rows_synced"] == 3

        with get_db(db_path) as conn:
            row = conn.execute(
                "SELECT destino FROM planilha_data WHERE num_bolsa = '25009258'"
            ).fetchone()
            assert row["destino"] == "Enfermaria"

    @patch("src.sync_service.ler_planilha_completa")
    def test_planilha_vazia(self, mock_ler, db_path):
        mock_ler.return_value = ([], [])
        result = executar_sync(db_path)
        assert result["status"] == "sucesso"
        assert result["rows_synced"] == 0

    @patch("src.sync_service.ler_planilha_completa")
    def test_atualiza_sync_metadata_sucesso(self, mock_ler, db_path):
        mock_ler.return_value = (MOCK_HEADER, MOCK_ROWS)
        executar_sync(db_path)

        with get_db(db_path) as conn:
            meta = conn.execute("SELECT * FROM sync_metadata WHERE id = 1").fetchone()
            assert meta["last_sync_status"] == "sucesso"
            assert meta["last_sync_rows"] == 3
            assert meta["last_sync_error"] is None

    @patch("src.sync_service.ler_planilha_completa")
    def test_registra_erro_no_metadata(self, mock_ler, db_path):
        mock_ler.side_effect = Exception("API error")
        result = executar_sync(db_path)
        assert result["status"] == "erro"
        assert "API error" in result["error"]

        with get_db(db_path) as conn:
            meta = conn.execute("SELECT * FROM sync_metadata WHERE id = 1").fetchone()
            assert meta["last_sync_status"] == "erro"
            assert "API error" in meta["last_sync_error"]

    @patch("src.sync_service.ler_planilha_completa")
    def test_ignora_linhas_sem_num_bolsa(self, mock_ler, db_path):
        rows_with_empty = [
            MOCK_ROWS[0],
            ["", "", "", "", "", "", "", "", "", "", "", "", ""],  # empty row
            MOCK_ROWS[2],
        ]
        mock_ler.return_value = (MOCK_HEADER, rows_with_empty)
        result = executar_sync(db_path)
        assert result["rows_synced"] == 2


class TestObterSyncStatus:
    def test_sem_sync_anterior(self, db_path):
        status = obter_sync_status(db_path)
        assert status["last_sync_at"] is None
        assert status["last_sync_status"] is None
        assert status["last_sync_rows"] == 0

    @patch("src.sync_service.ler_planilha_completa")
    def test_retorna_ultimo_sync(self, mock_ler, db_path):
        mock_ler.return_value = (MOCK_HEADER, MOCK_ROWS)
        executar_sync(db_path)

        status = obter_sync_status(db_path)
        assert status["last_sync_at"] is not None
        assert status["last_sync_status"] == "sucesso"
        assert status["last_sync_rows"] == 3


class TestConsultarPlanilha:
    @pytest.fixture(autouse=True)
    def _populate(self, db_path):
        """Populate test data directly into planilha_data."""
        with get_db(db_path) as conn:
            rows = [
                ("25051087", "5", "VENCE EM 5 DIAS", "01/03/2026", "06/03/2026", "", "", "Paciente A", "CHD", "O/POS", 292, "Ana", "", 11, "2026-03-02T10:00:00"),
                ("25009258", "-2", "VENCIDO", "15/02/2026", "27/02/2026", "28/02/2026", "UTI", "Paciente B", "PFC", "A/NEG", 180, "Maria", "Enf.", 12, "2026-03-02T10:00:00"),
                ("25012345", "30", "", "20/02/2026", "02/04/2026", "", "", "Paciente C", "CHD", "B/POS", 350, "Joao", "CC", 13, "2026-03-02T10:00:00"),
            ]
            for r in rows:
                conn.execute(
                    "INSERT INTO planilha_data (num_bolsa, dias_antes_vencimento, status_vencimento, "
                    "data_entrada, data_validade, data_transfusao, destino, nome_paciente, "
                    "tipo_hemocomponente, gs_rh, volume, responsavel_recepcao, setor_transfusao, "
                    "sheet_row, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r
                )
        self.db = db_path

    def test_paginacao(self):
        result = consultar_planilha(self.db, page=1, per_page=2)
        assert result["total"] == 3
        assert len(result["rows"]) == 2
        assert result["page"] == 1

    def test_busca_por_num_bolsa(self):
        result = consultar_planilha(self.db, search="25051087")
        assert result["total"] == 1
        assert result["rows"][0]["num_bolsa"] == "25051087"

    def test_busca_por_gs_rh(self):
        result = consultar_planilha(self.db, search="O/POS")
        assert result["total"] == 1

    def test_sort_por_coluna(self):
        result = consultar_planilha(self.db, sort_by="volume", sort_dir="asc")
        volumes = [r["volume"] for r in result["rows"]]
        assert volumes == [180, 292, 350]

    def test_filtro_gs_rh(self):
        result = consultar_planilha(self.db, filters={"gs_rh": "A/NEG"})
        assert result["total"] == 1
        assert result["rows"][0]["gs_rh"] == "A/NEG"

    def test_filtro_tipo_hemocomponente(self):
        result = consultar_planilha(self.db, filters={"tipo_hemocomponente": "CHD"})
        assert result["total"] == 2
