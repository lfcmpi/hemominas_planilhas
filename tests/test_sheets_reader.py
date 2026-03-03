"""Tests for sheets_reader module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.sheets_reader import (
    ValoresBase,
    _extrair_valores,
    invalidar_cache_base,
    ler_bolsas_existentes,
    ler_valores_base,
)


class TestExtrairValores:
    def test_filtra_vazios(self):
        cells = [["O/POS"], [""], ["A/NEG"], []]
        assert _extrair_valores(cells) == ["O/POS", "A/NEG"]

    def test_strip_whitespace(self):
        cells = [["  O/POS  "], ["A/NEG "]]
        assert _extrair_valores(cells) == ["O/POS", "A/NEG"]

    def test_lista_vazia(self):
        assert _extrair_valores([]) == []

    def test_rows_vazias(self):
        cells = [[], [], []]
        assert _extrair_valores(cells) == []


class TestLerValoresBase:
    @patch("src.sheets_reader._get_client")
    def test_retorna_valores_base(self, mock_client):
        invalidar_cache_base()
        mock_ws = MagicMock()
        mock_ws.get.side_effect = [
            [["O/POS"], ["O/NEG"], ["A/POS"], ["A/NEG"]],  # GS/RH
            [["CHD - Concentrado"], ["PFC - Plasma"]],       # Tipos
            [["Ana Silva"], ["Joao Santos"]],                 # Responsaveis
            [["UTI"], ["Enfermaria"]],                        # Destinos
            [["Nenhuma"], ["Febril"]],                        # Reacoes
        ]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result = ler_valores_base("test_id")

        assert isinstance(result, ValoresBase)
        assert len(result.gs_rh) == 4
        assert len(result.tipos_hemocomponente) == 2
        assert len(result.responsaveis) == 2
        assert len(result.destinos) == 2
        assert len(result.reacoes_transfusionais) == 2
        assert "O/POS" in result.gs_rh
        assert "CHD - Concentrado" in result.tipos_hemocomponente

    @patch("src.sheets_reader._get_client")
    def test_cache_funciona(self, mock_client):
        invalidar_cache_base()
        mock_ws = MagicMock()
        mock_ws.get.side_effect = [
            [["O/POS"]],
            [["CHD"]],
            [["Ana"]],
            [["UTI"]],
            [["Nenhuma"]],
        ]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result1 = ler_valores_base("test_id")
        result2 = ler_valores_base("test_id")

        assert result1 is result2
        # Client called only once due to cache
        assert mock_client.call_count == 1

    @patch("src.sheets_reader._get_client")
    def test_cache_expira(self, mock_client):
        invalidar_cache_base()
        mock_ws = MagicMock()
        mock_ws.get.side_effect = [
            [["O/POS"]], [["CHD"]], [["Ana"]], [["UTI"]], [["Nenhuma"]],  # First call
            [["O/NEG"]], [["PFC"]], [["Joao"]], [["Enf"]], [["Febril"]],  # Second call after expiry
        ]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result1 = ler_valores_base("test_id")
        # Force cache expiry
        result1.timestamp = datetime.now() - timedelta(minutes=10)

        result2 = ler_valores_base("test_id")
        assert mock_client.call_count == 2


class TestLerBolsasExistentes:
    @patch("src.sheets_reader._get_client")
    def test_retorna_set_bolsas(self, mock_client):
        mock_ws = MagicMock()
        mock_ws.get.return_value = [
            ["25014485"],
            ["25051087"],
            ["25014486"],
        ]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result = ler_bolsas_existentes("test_id")

        assert isinstance(result, set)
        assert len(result) == 3
        assert "25014485" in result
        assert "25051087" in result

    @patch("src.sheets_reader._get_client")
    def test_filtra_vazios_e_whitespace(self, mock_client):
        mock_ws = MagicMock()
        mock_ws.get.return_value = [
            ["25014485"],
            [""],
            ["  "],
            [],
            ["25051087"],
        ]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result = ler_bolsas_existentes("test_id")

        assert len(result) == 2
        assert "25014485" in result

    @patch("src.sheets_reader._get_client")
    def test_sem_bolsas_retorna_set_vazio(self, mock_client):
        mock_ws = MagicMock()
        mock_ws.get.return_value = []
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        result = ler_bolsas_existentes("test_id")

        assert isinstance(result, set)
        assert len(result) == 0

    @patch("src.sheets_reader._get_client")
    def test_nunca_cacheia(self, mock_client):
        mock_ws = MagicMock()
        mock_ws.get.return_value = [["25014485"]]
        mock_sheet = MagicMock()
        mock_sheet.worksheet.return_value = mock_ws
        mock_client.return_value.open_by_key.return_value = mock_sheet

        ler_bolsas_existentes("test_id")
        ler_bolsas_existentes("test_id")

        # Called twice (no cache)
        assert mock_client.call_count == 2
