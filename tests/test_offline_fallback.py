"""Tests para funcionalidade de fallback offline (pending_sync, local fallback, sincronizacao)."""

import os
import tempfile
from datetime import date
from unittest.mock import patch

import pytest

from src.field_mapper import LinhaPlanilha
from src.history_store import get_db, init_db
from src.sheets_reader import ler_bolsas_existentes_local, ler_valores_base_local
from src.sync_service import contar_pendentes, salvar_linhas_local, sincronizar_pendentes


@pytest.fixture
def db_path():
    """Cria banco temporario para cada teste."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


def _make_linha(num_bolsa="25051087", tipo="CHD", gs_rh="O/POS", volume=292):
    return LinhaPlanilha(
        dias_antes_vencimento="",
        status="",
        data_entrada=date(2026, 3, 1),
        data_validade=date(2026, 3, 8),
        tipo_hemocomponente=tipo,
        gs_rh=gs_rh,
        volume=volume,
        responsavel_recepcao="Ana",
        num_bolsa=num_bolsa,
    )


def _populate_planilha_data(db_path, rows=None):
    """Insert sample rows into planilha_data."""
    if rows is None:
        rows = [
            ("25051087", "01/03/2026", "06/03/2026", "CHD", "O/POS", 292, "Ana", 11, 0, "2026-03-02T10:00:00"),
            ("25009258", "15/02/2026", "27/02/2026", "PFC", "A/NEG", 180, "Maria", 12, 0, "2026-03-02T10:00:00"),
        ]
    with get_db(db_path) as conn:
        for r in rows:
            conn.execute(
                "INSERT INTO planilha_data (num_bolsa, data_entrada, data_validade, "
                "tipo_hemocomponente, gs_rh, volume, responsavel_recepcao, "
                "sheet_row, pending_sync, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", r
            )


class TestPendingSyncColumn:
    def test_coluna_existe_no_schema(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(planilha_data)").fetchall()]
        assert "pending_sync" in cols
        conn.close()

    def test_default_e_zero(self, db_path):
        with get_db(db_path) as conn:
            conn.execute(
                "INSERT INTO planilha_data (num_bolsa, updated_at) VALUES ('TEST123', '2026-03-02')"
            )
            row = conn.execute(
                "SELECT pending_sync FROM planilha_data WHERE num_bolsa = 'TEST123'"
            ).fetchone()
            assert row["pending_sync"] == 0

    def test_index_existe(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='planilha_data'"
        ).fetchall()
        index_names = [i[0] for i in indexes]
        assert "idx_planilha_pending_sync" in index_names
        conn.close()


class TestLerValoresBaseLocal:
    def test_retorna_tipos_e_gs_rh_do_banco(self, db_path):
        _populate_planilha_data(db_path)
        base = ler_valores_base_local(db_path)
        assert "CHD" in base.tipos_hemocomponente
        assert "PFC" in base.tipos_hemocomponente
        assert "O/POS" in base.gs_rh
        assert "A/NEG" in base.gs_rh

    def test_inclui_dados_de_import_bolsas(self, db_path):
        from src.history_store import registrar_importacao
        from dataclasses import dataclass

        @dataclass
        class BolsaMock:
            num_bolsa: str = "99999"
            tipo_hemocomponente: str = "CRIO"
            gs_rh: str = "AB/POS"
            volume: int = 100
            data_validade: date = date(2026, 4, 1)

        registrar_importacao(db_path, "test.pdf", "123", 1, "sucesso", None, [BolsaMock()])
        base = ler_valores_base_local(db_path)
        assert "CRIO" in base.tipos_hemocomponente
        assert "AB/POS" in base.gs_rh

    def test_banco_vazio_retorna_listas_vazias(self, db_path):
        base = ler_valores_base_local(db_path)
        assert base.tipos_hemocomponente == []
        assert base.gs_rh == []
        assert base.responsaveis == []

    def test_retorna_responsaveis(self, db_path):
        _populate_planilha_data(db_path)
        base = ler_valores_base_local(db_path)
        assert "Ana" in base.responsaveis
        assert "Maria" in base.responsaveis


class TestLerBolsasExistentesLocal:
    def test_retorna_set_de_bolsas(self, db_path):
        _populate_planilha_data(db_path)
        bolsas = ler_bolsas_existentes_local(db_path)
        assert isinstance(bolsas, set)
        assert "25051087" in bolsas
        assert "25009258" in bolsas

    def test_banco_vazio_retorna_set_vazio(self, db_path):
        bolsas = ler_bolsas_existentes_local(db_path)
        assert bolsas == set()


class TestSalvarLinhasLocal:
    def test_salva_com_pending_sync_1(self, db_path):
        linhas = [_make_linha(), _make_linha(num_bolsa="25009258", gs_rh="A/NEG")]
        result = salvar_linhas_local(db_path, linhas)
        assert result["salvas_localmente"] == 2

        with get_db(db_path) as conn:
            rows = conn.execute("SELECT * FROM planilha_data WHERE pending_sync = 1").fetchall()
            assert len(rows) == 2
            nums = {r["num_bolsa"] for r in rows}
            assert nums == {"25051087", "25009258"}

    def test_upsert_atualiza_existente(self, db_path):
        _populate_planilha_data(db_path)
        # Update existing row - should set pending_sync=1
        linhas = [_make_linha(num_bolsa="25051087", volume=500)]
        salvar_linhas_local(db_path, linhas)

        with get_db(db_path) as conn:
            row = conn.execute(
                "SELECT volume, pending_sync FROM planilha_data WHERE num_bolsa = '25051087'"
            ).fetchone()
            assert row["volume"] == 500
            assert row["pending_sync"] == 1

    def test_salva_zero_linhas(self, db_path):
        result = salvar_linhas_local(db_path, [])
        assert result["salvas_localmente"] == 0


class TestContarPendentes:
    def test_zero_quando_vazio(self, db_path):
        assert contar_pendentes(db_path) == 0

    def test_conta_pendentes(self, db_path):
        linhas = [_make_linha(), _make_linha(num_bolsa="25009258")]
        salvar_linhas_local(db_path, linhas)
        assert contar_pendentes(db_path) == 2

    def test_nao_conta_sincronizados(self, db_path):
        _populate_planilha_data(db_path)  # pending_sync=0
        assert contar_pendentes(db_path) == 0


class TestSincronizarPendentes:
    def test_nenhum_pendente(self, db_path):
        result = sincronizar_pendentes(db_path)
        assert result["status"] == "nenhum_pendente"
        assert result["total"] == 0

    @patch("src.sheets_writer.escrever_linhas")
    def test_sincroniza_com_sucesso(self, mock_escrever, db_path):
        mock_escrever.return_value = {"linhas_inseridas": 2, "mensagem": "OK"}
        linhas = [_make_linha(), _make_linha(num_bolsa="25009258")]
        salvar_linhas_local(db_path, linhas)

        result = sincronizar_pendentes(db_path)
        assert result["status"] == "sucesso"
        assert result["total"] == 2
        mock_escrever.assert_called_once()

        # Verify pending_sync is now 0
        with get_db(db_path) as conn:
            pending = conn.execute(
                "SELECT COUNT(*) as c FROM planilha_data WHERE pending_sync = 1"
            ).fetchone()["c"]
            assert pending == 0

    @patch("src.sheets_writer.escrever_linhas")
    def test_mantem_pendente_em_caso_de_erro(self, mock_escrever, db_path):
        mock_escrever.side_effect = Exception("API error")
        salvar_linhas_local(db_path, [_make_linha()])

        result = sincronizar_pendentes(db_path)
        assert result["status"] == "erro"
        assert "API error" in result["error"]

        # Verify still pending
        assert contar_pendentes(db_path) == 1

    @patch("src.sheets_writer.escrever_linhas")
    def test_converte_datas_corretamente(self, mock_escrever, db_path):
        mock_escrever.return_value = {"linhas_inseridas": 1, "mensagem": "OK"}
        salvar_linhas_local(db_path, [_make_linha()])
        sincronizar_pendentes(db_path)

        # Verify the LinhaPlanilha passed to escrever_linhas has proper date objects
        call_args = mock_escrever.call_args[0][0]  # first positional arg (list of linhas)
        assert len(call_args) == 1
        assert hasattr(call_args[0].data_entrada, 'strftime')
        assert hasattr(call_args[0].data_validade, 'strftime')
