"""Tests para history_store.py — CRUD SQLite de historico e alertas."""

import os
import tempfile
from dataclasses import dataclass
from datetime import date

import pytest

from src.history_store import (
    init_db,
    listar_importacoes,
    obter_alert_config,
    obter_distribuicao_bolsas,
    obter_estatisticas_importacoes,
    obter_evolucao_diaria,
    obter_evolucao_por_tipo,
    obter_importacao,
    obter_top_bolsas_recentes,
    registrar_importacao,
    salvar_alert_config,
)


@dataclass
class BolsaMock:
    num_bolsa: str = "25051087"
    tipo_hemocomponente: str = "CHD"
    gs_rh: str = "O/POS"
    volume: int = 292
    data_validade: date = None

    def __post_init__(self):
        if self.data_validade is None:
            self.data_validade = date(2026, 3, 8)


@pytest.fixture
def db_path():
    """Cria banco temporario para cada teste."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestInitDb:
    def test_cria_tabelas(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "import_records" in table_names
        assert "import_bolsas" in table_names
        assert "alert_config" in table_names
        conn.close()

    def test_idempotente(self, db_path):
        # Chamar init_db novamente nao deve falhar
        init_db(db_path)
        init_db(db_path)


class TestRegistrarImportacao:
    def test_registra_com_bolsas(self, db_path):
        bolsas = [BolsaMock(), BolsaMock(num_bolsa="25009258", gs_rh="A/POS")]
        import_id = registrar_importacao(
            db_path, "test.pdf", "1292305", 2, "sucesso", None, bolsas
        )
        assert import_id > 0

    def test_registra_sem_bolsas(self, db_path):
        import_id = registrar_importacao(
            db_path, "empty.pdf", "", 0, "erro", "Nenhum comprovante", []
        )
        assert import_id > 0

    def test_registra_multiplas(self, db_path):
        id1 = registrar_importacao(db_path, "a.pdf", "100", 3, "sucesso", None, [BolsaMock()])
        id2 = registrar_importacao(db_path, "b.pdf", "200", 2, "sucesso", None, [BolsaMock()])
        assert id2 > id1


class TestListarImportacoes:
    def test_lista_vazia(self, db_path):
        imports, total = listar_importacoes(db_path)
        assert total == 0
        assert imports == []

    def test_lista_com_registros(self, db_path):
        registrar_importacao(db_path, "a.pdf", "100", 3, "sucesso", None, [BolsaMock()])
        registrar_importacao(db_path, "b.pdf", "200", 2, "sucesso", None, [BolsaMock()])
        imports, total = listar_importacoes(db_path)
        assert total == 2
        assert len(imports) == 2
        # Ordem cronologica reversa
        assert imports[0]["filename"] == "b.pdf"
        assert imports[1]["filename"] == "a.pdf"

    def test_paginacao(self, db_path):
        for i in range(5):
            registrar_importacao(db_path, f"f{i}.pdf", str(i), 1, "sucesso", None, [])
        page1, total = listar_importacoes(db_path, page=1, per_page=2)
        assert total == 5
        assert len(page1) == 2
        page3, _ = listar_importacoes(db_path, page=3, per_page=2)
        assert len(page3) == 1

    def test_filtro_por_data(self, db_path):
        registrar_importacao(db_path, "a.pdf", "100", 1, "sucesso", None, [])
        # Filtro que inclui tudo (data de hoje)
        from datetime import datetime
        hoje = datetime.now().strftime("%Y-%m-%d")
        imports, total = listar_importacoes(db_path, data_inicio=hoje, data_fim=hoje)
        assert total == 1


class TestObterImportacao:
    def test_obter_existente(self, db_path):
        bolsas = [BolsaMock(), BolsaMock(num_bolsa="25009258")]
        import_id = registrar_importacao(
            db_path, "test.pdf", "1292305", 2, "sucesso", None, bolsas
        )
        result = obter_importacao(db_path, import_id)
        assert result is not None
        assert result["importacao"]["filename"] == "test.pdf"
        assert len(result["bolsas"]) == 2
        assert result["bolsas"][0]["num_bolsa"] == "25051087"

    def test_obter_inexistente(self, db_path):
        result = obter_importacao(db_path, 9999)
        assert result is None


class TestAlertConfig:
    def test_config_padrao(self, db_path):
        config = obter_alert_config(db_path)
        assert config["threshold_urgente"] == 7
        assert config["threshold_atencao"] == 14
        assert config["email_enabled"] is False
        assert config["inapp_enabled"] is True

    def test_salvar_e_obter(self, db_path):
        salvar_alert_config(db_path, {
            "threshold_urgente": 5,
            "threshold_atencao": 10,
            "email_enabled": True,
            "email_to": "ana@hmob.mg.gov.br",
            "inapp_enabled": True,
        })
        config = obter_alert_config(db_path)
        assert config["threshold_urgente"] == 5
        assert config["threshold_atencao"] == 10
        assert config["email_enabled"] is True
        assert config["email_to"] == "ana@hmob.mg.gov.br"

    def test_atualizar_config(self, db_path):
        obter_alert_config(db_path)  # Cria padrao
        salvar_alert_config(db_path, {
            "threshold_urgente": 3,
            "threshold_atencao": 7,
            "email_enabled": False,
            "email_to": None,
            "inapp_enabled": False,
        })
        config = obter_alert_config(db_path)
        assert config["threshold_urgente"] == 3
        assert config["inapp_enabled"] is False


class TestEstatisticasImportacoes:
    def test_vazio(self, db_path):
        stats = obter_estatisticas_importacoes(db_path)
        assert stats["total_importacoes"] == 0
        assert stats["total_bolsas"] == 0
        assert stats["media_bolsas_por_importacao"] == 0

    def test_com_dados(self, db_path):
        bolsas1 = [BolsaMock(), BolsaMock(num_bolsa="111")]
        bolsas2 = [BolsaMock(num_bolsa="222", volume=350)]
        registrar_importacao(db_path, "a.pdf", "1", 2, "sucesso", None, bolsas1)
        registrar_importacao(db_path, "b.pdf", "2", 1, "sucesso", None, bolsas2)
        stats = obter_estatisticas_importacoes(db_path)
        assert stats["total_importacoes"] == 2
        assert stats["total_bolsas"] == 3
        assert stats["media_bolsas_por_importacao"] == 1.5
        assert stats["bolsas_7d"] == 3
        assert stats["bolsas_30d"] == 3
        assert stats["ultima_importacao"] is not None

    def test_ignora_erros(self, db_path):
        registrar_importacao(db_path, "a.pdf", "1", 2, "sucesso", None, [BolsaMock()])
        registrar_importacao(db_path, "b.pdf", "2", 0, "erro", "falhou", [])
        stats = obter_estatisticas_importacoes(db_path)
        assert stats["total_importacoes"] == 1


class TestEvolucaoDiaria:
    def test_vazio(self, db_path):
        result = obter_evolucao_diaria(db_path, dias=7)
        assert result == []

    def test_com_dados(self, db_path):
        registrar_importacao(db_path, "a.pdf", "1", 5, "sucesso", None, [])
        result = obter_evolucao_diaria(db_path, dias=7)
        assert len(result) == 1
        assert result[0]["total"] == 5


class TestDistribuicaoBolsas:
    def test_vazio(self, db_path):
        dist = obter_distribuicao_bolsas(db_path)
        assert dist["por_gs_rh"] == []
        assert dist["por_hemocomponente"] == []

    def test_com_dados(self, db_path):
        bolsas = [
            BolsaMock(gs_rh="O/POS", tipo_hemocomponente="CHD"),
            BolsaMock(num_bolsa="111", gs_rh="O/POS", tipo_hemocomponente="CHD"),
            BolsaMock(num_bolsa="222", gs_rh="A/NEG", tipo_hemocomponente="PFC"),
        ]
        registrar_importacao(db_path, "a.pdf", "1", 3, "sucesso", None, bolsas)
        dist = obter_distribuicao_bolsas(db_path)
        assert len(dist["por_gs_rh"]) == 2
        assert dist["por_gs_rh"][0]["tipo"] == "O/POS"
        assert dist["por_gs_rh"][0]["count"] == 2
        assert len(dist["por_hemocomponente"]) == 2
        assert dist["por_volume"] is not None


class TestTopBolsasRecentes:
    def test_vazio(self, db_path):
        result = obter_top_bolsas_recentes(db_path, limit=5)
        assert result == []

    def test_com_dados(self, db_path):
        bolsas = [BolsaMock(), BolsaMock(num_bolsa="111")]
        registrar_importacao(db_path, "a.pdf", "1", 2, "sucesso", None, bolsas)
        result = obter_top_bolsas_recentes(db_path, limit=5)
        assert len(result) == 2
        assert "num_bolsa" in result[0]
        assert "timestamp" in result[0]

    def test_respects_limit(self, db_path):
        bolsas = [BolsaMock(num_bolsa=str(i)) for i in range(10)]
        registrar_importacao(db_path, "a.pdf", "1", 10, "sucesso", None, bolsas)
        result = obter_top_bolsas_recentes(db_path, limit=3)
        assert len(result) == 3
