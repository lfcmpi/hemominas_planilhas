from datetime import date
from pathlib import Path

import pytest

from src.pdf_extractor import (
    _extrair_linhas_tabela,
    _normalizar_abo,
    _normalizar_nome_responsavel,
    _parse_date,
    extrair_pdf,
)

PDF_PATH = "insumos/RECEBIMENTO DE BOLSAS -15_12_2025.pdf"


class TestNormalizarAbo:
    def test_letter_o(self):
        assert _normalizar_abo("O") == "O"

    def test_zero_becomes_o(self):
        assert _normalizar_abo("0") == "O"

    def test_parenthesis_zero(self):
        assert _normalizar_abo("(0)") == "O"

    def test_parenthesis_six(self):
        assert _normalizar_abo("(6)") == "O"

    def test_letter_a(self):
        assert _normalizar_abo("A") == "A"

    def test_letter_b(self):
        assert _normalizar_abo("B") == "B"

    def test_ab(self):
        assert _normalizar_abo("AB") == "AB"

    def test_sixteen(self):
        assert _normalizar_abo("16)") == "O"

    def test_nine_becomes_o(self):
        """OCR do PDF 02/03/2026 leu 'O' como '9'."""
        assert _normalizar_abo("9") == "O"

    def test_any_single_digit_becomes_o(self):
        """Qualquer digito isolado deve virar 'O'."""
        for d in "0123456789":
            assert _normalizar_abo(d) == "O", f"Falhou para '{d}'"

    def test_multi_digit_becomes_o(self):
        """Qualquer sequencia de digitos deve virar 'O'."""
        assert _normalizar_abo("16") == "O"
        assert _normalizar_abo("19") == "O"

    def test_parenthesis_nine(self):
        assert _normalizar_abo("(9)") == "O"


class TestParseDate:
    def test_standard_format(self):
        assert _parse_date("08/01/2026") == date(2026, 1, 8)

    def test_with_spaces(self):
        assert _parse_date("14 / 12 / 2025") == date(2025, 12, 14)

    def test_with_commas(self):
        assert _parse_date("14 , 12 ,2025") == date(2025, 12, 14)

    def test_no_date(self):
        assert _parse_date("no date here") is None


@pytest.mark.skipif(not Path(PDF_PATH).exists(), reason="Real PDF not available")
class TestExtrairPdfReal:
    @pytest.fixture(scope="class")
    def comprovantes(self):
        return extrair_pdf(PDF_PATH)

    def test_encontra_dois_comprovantes(self, comprovantes):
        assert len(comprovantes) == 2

    def test_comprovante1_tem_5_bolsas(self, comprovantes):
        assert len(comprovantes[0].bolsas) == 5

    def test_comprovante2_tem_1_bolsa(self, comprovantes):
        assert len(comprovantes[1].bolsas) == 1

    def test_total_6_bolsas(self, comprovantes):
        total = sum(len(c.bolsas) for c in comprovantes)
        assert total == 6

    def test_data_expedicao_extraida(self, comprovantes):
        for comp in comprovantes:
            assert comp.data_expedicao is not None
            assert comp.data_expedicao == date(2025, 12, 14)

    def test_num_doacao_primeira_bolsa(self, comprovantes):
        assert comprovantes[0].bolsas[0].num_doacao == "25051087"

    def test_abo_normalizado(self, comprovantes):
        valid_abo = {"O", "A", "B", "AB"}
        for comp in comprovantes:
            for bolsa in comp.bolsas:
                assert bolsa.abo in valid_abo, f"Invalid ABO: {bolsa.abo}"

    def test_rh_values(self, comprovantes):
        for comp in comprovantes:
            for bolsa in comp.bolsas:
                assert bolsa.rh in ("P", "N"), f"Invalid Rh: {bolsa.rh}"

    def test_volumes_razoaveis(self, comprovantes):
        for comp in comprovantes:
            for bolsa in comp.bolsas:
                assert 200 <= bolsa.volume <= 500, f"Volume fora do range: {bolsa.volume}"

    def test_validades_futuras(self, comprovantes):
        for comp in comprovantes:
            for bolsa in comp.bolsas:
                assert bolsa.validade is not None
                assert bolsa.validade > date(2025, 12, 14)

    def test_componente_contem_concentrado(self, comprovantes):
        for comp in comprovantes:
            for bolsa in comp.bolsas:
                assert "CONCENTRADO HEMACIAS" in bolsa.componente_pdf

    def test_expedido_por_comp2(self, comprovantes):
        # Phase 2: name is now normalized to Title Case
        assert "Ana Oliveira" in comprovantes[1].expedido_por

    def test_dados_esperados_bolsa1(self, comprovantes):
        b = comprovantes[0].bolsas[0]
        assert b.inst_coleta == "B3013"
        assert b.num_doacao == "25051087"
        assert b.volume == 292
        assert b.abo == "O"
        assert b.rh == "P"
        assert b.validade == date(2026, 1, 8)

    def test_responsavel_sem_espacos_duplos(self, comprovantes):
        for comp in comprovantes:
            assert "  " not in comp.expedido_por, (
                f"Espacos duplos em: '{comp.expedido_por}'"
            )

    def test_responsavel_nao_vazio(self, comprovantes):
        for comp in comprovantes:
            assert comp.expedido_por.strip() != "", (
                f"Responsavel vazio no comprovante {comp.numero}"
            )


class TestExtrairLinhasTabela:
    """Tests for table row extraction regex, including alphanumeric ISBT codes."""

    def test_standard_isbt_v00(self):
        line = "B3013 25051087 | CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado E6514V00 1 292 O P 08/01/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].cod_isbt == "E6514V00"
        assert bolsas[0].num_doacao == "25051087"

    def test_isbt_with_letter_va0(self):
        """ISBT code E5854VA0 (Pool Plaquetas seq 1) must be extracted."""
        line = "B3013 26701521 | POOL PLAQ INATIVACAO DE PATOGENOS PAS Deleucocitado E5854VA0 1 174 O N 16/02/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].cod_isbt == "E5854VA0"
        assert bolsas[0].volume == 174

    def test_isbt_with_letter_vb0(self):
        """ISBT code E5854VB0 (Pool Plaquetas seq 2) must be extracted."""
        line = "B3013 26701509 | POOL PLAQ INATIVACAO DE PATOGENOS PAS Deleucocitado E5854VB0 2 162 O N 16/02/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].cod_isbt == "E5854VB0"
        assert bolsas[0].seq == 2

    def test_isbt_e6467v00(self):
        """ISBT code E6467V00 (CONC HEMACIAS CAMADA LEUCOPLAQ)."""
        line = "B3209 26002026 | CONC HEMACIAS CAMADA LEUCOPLAQ REMOVIDA E6467V00 1 270 A P 10/04/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].cod_isbt == "E6467V00"
        assert bolsas[0].abo == "A"

    def test_isbt_e4544v00_aferese(self):
        """ISBT code E4544V00 (CONC. DE HEMACIAS AFERESE)."""
        line = "B3013 26007133 | CONC. DE HEMACIAS AFERESE DESLEUCOCITADO Deleucocitado E4544V00 1 340 O N 26/03/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].cod_isbt == "E4544V00"
        assert bolsas[0].volume == 340

    def test_crioprecipitado_small_volume(self):
        """Crioprecipitado has small volumes (23-36 mL)."""
        line = "B3200 25005583 | CRIOPRECIPITADO E3571V00 1 31 AB P 15/04/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].volume == 31
        assert bolsas[0].abo == "AB"

    def test_plasma_24_horas(self):
        """PLASMA DE 24 HORAS extraction."""
        line = "B3200 25019154 | PLASMA DE 24 HORAS E7604V00 1 258 AB P 24/12/2026"
        bolsas = _extrair_linhas_tabela(line)
        assert len(bolsas) == 1
        assert bolsas[0].componente_pdf == "PLASMA DE 24 HORAS"


class TestNormalizarNomeResponsavel:
    def test_title_case(self):
        assert _normalizar_nome_responsavel("nilmara tania") == "Nilmara Tania"

    def test_remove_espacos_extras(self):
        assert _normalizar_nome_responsavel("nilmara  tania") == "Nilmara Tania"

    def test_remove_newlines(self):
        assert _normalizar_nome_responsavel("nilmara\ntania") == "Nilmara Tania"

    def test_remove_nbsp(self):
        assert _normalizar_nome_responsavel("nilmara\xa0tania") == "Nilmara Tania"

    def test_vazio_retorna_vazio(self):
        assert _normalizar_nome_responsavel("") == ""

    def test_apenas_espacos(self):
        assert _normalizar_nome_responsavel("   ") == ""
