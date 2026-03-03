"""Tests para dashboard_service.py — agregacao de estoque."""

from datetime import date, datetime, timedelta

import pytest

from src.dashboard_service import DashboardService, _parse_date_br


HEADER = [
    "DIAS ANTES VENCIMENTO", "STATUS", "DATA ENTRADA", "DATA VALIDADE",
    "DATA TRANSFUSAO/DESTINO", "DESTINO", "NOME COMPLETO PACIENTE",
    "TIPO HEMOCOMPONENTE", "GS/RH", "VOLUME", "RESPONSAVEL RECEPCAO",
    "SETOR TRANSFUSAO", "Num DA BOLSA",
]


def _make_row(validade="05/03/2026", destino="", data_transfusao="",
              tipo="CHD - Concentrado de Hemacias Desleucocitado",
              gs_rh="O/POS", volume="292", num_bolsa="25051087"):
    return [
        "5", "VENCE EM 5 DIAS", "14/12/2025", validade,
        data_transfusao, destino, "",
        tipo, gs_rh, volume, "NILMARA", "", num_bolsa,
    ]


class TestDashboardService:
    def setup_method(self):
        self.service = DashboardService()

    def test_filtra_bolsas_em_estoque(self):
        rows = [
            _make_row(),  # Em estoque
            _make_row(destino="CENTRO CIRURGICO"),  # Transfundida
            _make_row(data_transfusao="15/02/2026"),  # Tambem transfundida
        ]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert resumo.total_em_estoque == 1

    def test_agrega_por_gs_rh(self):
        rows = [
            _make_row(gs_rh="O/POS"),
            _make_row(gs_rh="O/POS", num_bolsa="2"),
            _make_row(gs_rh="A/NEG", num_bolsa="3"),
        ]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert resumo.por_gs_rh["O/POS"] == 2
        assert resumo.por_gs_rh["A/NEG"] == 1

    def test_agrega_por_hemocomponente(self):
        rows = [
            _make_row(tipo="CHD - Concentrado de Hemacias"),
            _make_row(tipo="CHD - Concentrado de Hemacias", num_bolsa="2"),
            _make_row(tipo="PFC - Plasma Fresco Congelado", num_bolsa="3"),
        ]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert resumo.por_hemocomponente["CHD"] == 2
        assert resumo.por_hemocomponente["PFC"] == 1

    def test_detecta_vencimento_urgente(self):
        # Bolsa vencendo em 3 dias
        from datetime import date as d
        hoje = d.today()
        vence_3d = (hoje + timedelta(days=3)).strftime("%d/%m/%Y")
        rows = [_make_row(validade=vence_3d)]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert len(resumo.vencendo_7d) == 1
        assert resumo.vencendo_7d[0]["dias_restantes"] == 3

    def test_detecta_vencimento_atencao(self):
        hoje = date.today()
        vence_10d = (hoje + timedelta(days=10)).strftime("%d/%m/%Y")
        rows = [_make_row(validade=vence_10d)]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert len(resumo.vencendo_14d) == 1

    def test_bolsas_longe_nao_alertam(self):
        hoje = date.today()
        vence_60d = (hoje + timedelta(days=60)).strftime("%d/%m/%Y")
        rows = [_make_row(validade=vence_60d)]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert len(resumo.vencendo_7d) == 0
        assert len(resumo.vencendo_14d) == 0
        assert len(resumo.vencendo_30d) == 0

    def test_rows_vazias_ignoradas(self):
        rows = [
            ["", "", "", "", "", "", "", "", "", "", "", "", ""],
            _make_row(),
        ]
        resumo = self.service._agregar_dados(rows, HEADER)
        assert resumo.total_em_estoque == 1

    def test_cache_funciona(self):
        rows = [_make_row()]
        r1 = self.service.obter_estoque(HEADER, rows)
        r2 = self.service.obter_estoque(HEADER, rows)
        assert r1 is r2  # Same object = from cache

    def test_cache_invalidacao(self):
        rows = [_make_row()]
        r1 = self.service.obter_estoque(HEADER, rows)
        self.service.invalidar_cache()
        r2 = self.service.obter_estoque(HEADER, rows)
        assert r1 is not r2  # Different object = recalculated

    def test_force_refresh(self):
        rows = [_make_row()]
        r1 = self.service.obter_estoque(HEADER, rows)
        r2 = self.service.obter_estoque(HEADER, rows, force_refresh=True)
        assert r1 is not r2


class TestParseDateBr:
    def test_valid(self):
        assert _parse_date_br("14/12/2025") == date(2025, 12, 14)

    def test_empty(self):
        assert _parse_date_br("") is None

    def test_invalid(self):
        assert _parse_date_br("not-a-date") is None
