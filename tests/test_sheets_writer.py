from datetime import date
from unittest.mock import MagicMock, patch

from src.field_mapper import LinhaPlanilha
import pytest
from src.sheets_writer import escrever_linhas, _validar_rows_destino


def _make_linha():
    return LinhaPlanilha(
        dias_antes_vencimento="",
        status="",
        data_entrada=date(2025, 12, 14),
        data_validade=date(2026, 1, 8),
        tipo_hemocomponente="CHD -  Concentrado de Hemácias Desleucocitado",
        gs_rh="O/POS",
        volume=292,
        responsavel_recepcao="NILMARA TANIA VELOSO MATOS",
        num_bolsa="25051087",
    )


def _setup_mocks():
    mock_worksheet = MagicMock()
    mock_worksheet.get_all_values.return_value = [["header"] * 13] * 10
    mock_worksheet.get.return_value = []  # Target rows are empty
    return mock_worksheet


class TestEscreverLinhas:
    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_appends_rows(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        linhas = [_make_linha(), _make_linha()]
        result = escrever_linhas(linhas)

        assert result["linhas_inseridas"] == 2
        mock_ws.append_rows.assert_called_once()

        call_args = mock_ws.append_rows.call_args
        rows = call_args[0][0]
        assert len(rows) == 2

        # First row formulas with row 11 (10 existing + 1)
        assert "D11" in rows[0][0]
        assert "A11" in rows[0][1]

        # Second row formulas with row 12
        assert "D12" in rows[1][0]
        assert "A12" in rows[1][1]

        assert call_args[1]["value_input_option"] == "USER_ENTERED"

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_empty_linhas(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        result = escrever_linhas([])
        assert result["linhas_inseridas"] == 0
        mock_ws.append_rows.assert_not_called()

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_row_has_13_columns(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha()])

        row = mock_ws.append_rows.call_args[0][0][0]
        assert len(row) == 13  # A through M

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_manual_columns_are_empty(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha()])

        row = mock_ws.append_rows.call_args[0][0][0]
        assert row[4] == ""   # E - manual
        assert row[5] == ""   # F - manual
        assert row[6] == ""   # G - manual
        assert row[11] == ""  # L - manual

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_data_fields_formatted(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha()])

        row = mock_ws.append_rows.call_args[0][0][0]
        assert row[2] == "14/12/2025"  # C: data entrada
        assert row[3] == "08/01/2026"  # D: data validade
        assert row[8] == "O/POS"       # I: gs_rh
        assert row[9] == 292           # J: volume
        assert row[12] == "25051087"   # M: num bolsa


class TestValidarRowsDestino:
    def test_rows_vazias_ok(self):
        mock_ws = MagicMock()
        mock_ws.get.return_value = []
        _validar_rows_destino(mock_ws, 100, 3)  # Should not raise

    def test_rows_com_dados_levanta_erro(self):
        mock_ws = MagicMock()
        mock_ws.get.return_value = [["formula_existente"]]
        with pytest.raises(ValueError, match="ja contem dados"):
            _validar_rows_destino(mock_ws, 100, 1)

    def test_api_error_nao_bloqueia(self):
        mock_ws = MagicMock()
        mock_ws.get.side_effect = ConnectionError("API unavailable")
        _validar_rows_destino(mock_ws, 100, 1)  # Should not raise


class TestFormulasRobustez:
    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_formula_a_pattern(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha()])
        row = mock_ws.append_rows.call_args[0][0][0]
        # Column A: =IF(D{row}="","",D{row}-TODAY())
        assert row[0] == '=IF(D11="","",D11-TODAY())'

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_formula_b_pattern(self, mock_get_client, mock_get_ws):
        mock_ws = _setup_mocks()
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha()])
        row = mock_ws.append_rows.call_args[0][0][0]
        # Column B: complex IF formula
        expected = (
            '=IF(A11="","",IF(A11<0,"VENCIDO",'
            'IF(A11=0,"VENCE HOJE",'
            'CONCATENATE("VENCE EM ",A11," DIAS"))))'
        )
        assert row[1] == expected

    @patch("src.sheets_writer._get_worksheet")
    @patch("src.sheets_writer._get_client")
    def test_row_numbers_increment_correctly(self, mock_get_client, mock_get_ws):
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = [["h"] * 13] * 50  # 50 existing rows
        mock_ws.get.return_value = []
        mock_get_ws.return_value = mock_ws

        escrever_linhas([_make_linha(), _make_linha(), _make_linha()])
        rows = mock_ws.append_rows.call_args[0][0]
        # 50 existing → next is 51
        assert "D51" in rows[0][0]
        assert "D52" in rows[1][0]
        assert "D53" in rows[2][0]
