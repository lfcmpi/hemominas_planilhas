from datetime import date

import pytest

from src.field_mapper import (
    converter_gs_rh,
    mapear_hemocomponente,
    mapear_comprovantes,
    montar_row,
)
from src.pdf_extractor import BolsaExtraida, Comprovante


class TestConverterGsRh:
    @pytest.mark.parametrize("abo,rh,expected", [
        ("O", "P", "O/POS"),
        ("O", "N", "O/NEG"),
        ("A", "P", "A/POS"),
        ("A", "N", "A/NEG"),
        ("B", "P", "B/POS"),
        ("B", "N", "B/NEG"),
        ("AB", "P", "AB/POS"),
        ("AB", "N", "AB/NEG"),
    ])
    def test_all_combinations(self, abo, rh, expected):
        assert converter_gs_rh(abo, rh) == expected


class TestMapearHemocomponente:
    def test_deleucocitado_maps_to_chd(self):
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado")
        assert "CHD" in result
        assert "Desleucocitado" in result

    def test_desleucocitado_maps_to_chd(self):
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS Desleucocitado Sist. Fechado")
        assert "CHD" in result

    def test_plasma_fresco(self):
        result = mapear_hemocomponente("PLASMA FRESCO CONGELADO")
        assert "PFC" in result

    def test_crioprecipitado(self):
        result = mapear_hemocomponente("CRIOPRECIPITADO")
        assert "CRIO" in result

    def test_plaqueta_randomica(self):
        result = mapear_hemocomponente("PLAQUETA RANDOMICA")
        assert "CPQ" in result

    def test_concentrado_comum(self):
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS Comum")
        assert "CHM" in result

    def test_conc_hemacias_camada_leucoplaq_removida(self):
        """PDF abbreviation 'CONC HEMACIAS CAMADA LEUCOPLAQ REMOVIDA'."""
        result = mapear_hemocomponente("CONC HEMACIAS CAMADA LEUCOPLAQ REMOVIDA")
        assert "CHCR" in result

    def test_deleucocitado_e_irradiado_with_e(self):
        """PDF uses 'Deleucocitado e Irradiado' with 'e' in between."""
        result = mapear_hemocomponente(
            "CONCENTRADO HEMACIAS Deleucocitado e Irradiado Sist. Fechado"
        )
        assert "CHDI" in result

    def test_concentrado_hemacias_plain(self):
        """Plain 'CONCENTRADO HEMACIAS' without qualifier → CHM Comum."""
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS")
        assert "CHM" in result

    def test_plasma_de_24_horas(self):
        """'PLASMA DE 24 HORAS' with 'de' between plasma and 24."""
        result = mapear_hemocomponente("PLASMA DE 24 HORAS")
        assert "P24h" in result

    def test_pool_plaq_inativacao(self):
        """PDF abbreviation 'POOL PLAQ INATIVACAO DE PATOGENOS PAS...'."""
        result = mapear_hemocomponente(
            "POOL PLAQ INATIVACAO DE PATOGENOS PAS Deleucocitado e ALIQUOTADO e Inativado Sist. Fechado"
        )
        assert "IPPD" in result

    def test_conc_hemacias_aferese_desleucocitado(self):
        """PDF uses 'CONC. DE HEMACIAS AFERESE DESLEUCOCITADO'."""
        result = mapear_hemocomponente(
            "CONC. DE HEMACIAS AFERESE DESLEUCOCITADO Deleucocitado Sist. Fechado"
        )
        assert "HAFD" in result

    def test_fenotipado(self):
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS Fenotipado")
        assert "CHF" in result

    def test_fenotipado_desleucocitado(self):
        result = mapear_hemocomponente("CONCENTRADO HEMACIAS Fenotipado Desleucocitado")
        assert "CHFD" in result

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="nao mapeado"):
            mapear_hemocomponente("TIPO DESCONHECIDO XYZ")

    def test_tolerante_retorna_valor_bruto(self):
        result = mapear_hemocomponente("TIPO DESCONHECIDO XYZ", tolerante=True)
        assert result == "TIPO DESCONHECIDO XYZ"

    def test_tolerante_nao_afeta_match_valido(self):
        result = mapear_hemocomponente(
            "CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado", tolerante=True
        )
        assert "CHD" in result


class TestMapearComprovantes:
    def _make_comprovante(self):
        bolsa = BolsaExtraida(
            inst_coleta="B3013",
            num_doacao="25051087",
            componente_pdf="CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado",
            cod_isbt="E6514V00",
            seq=1,
            volume=292,
            abo="O",
            rh="P",
            validade=date(2026, 1, 8),
        )
        return Comprovante(
            numero="1292305",
            data_emissao=None,
            instituicao="HMOB",
            expedido_por="NILMARA TANIA VELOSO MATOS",
            data_expedicao=date(2025, 12, 14),
            bolsas=[bolsa],
            total_bolsas_declarado=1,
        )

    def test_returns_correct_count(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert len(linhas) == 1

    def test_gs_rh_mapping(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert linhas[0].gs_rh == "O/POS"

    def test_hemocomponente_mapping(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert "CHD" in linhas[0].tipo_hemocomponente

    def test_data_entrada(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert linhas[0].data_entrada == date(2025, 12, 14)

    def test_data_validade(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert linhas[0].data_validade == date(2026, 1, 8)

    def test_volume(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert linhas[0].volume == 292

    def test_num_bolsa(self):
        comp = self._make_comprovante()
        linhas = mapear_comprovantes([comp])
        assert linhas[0].num_bolsa == "B301325051087"
        assert linhas[0].inst_coleta == "B3013"

    def test_num_bolsa_with_seq_gt_1(self):
        """When seq > 1, num_bolsa should include '-seq' suffix."""
        bolsa1 = BolsaExtraida(
            inst_coleta="B3013", num_doacao="26007133",
            componente_pdf="CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado",
            cod_isbt="E4544V00", seq=1, volume=340,
            abo="O", rh="N", validade=date(2026, 3, 26),
        )
        bolsa2 = BolsaExtraida(
            inst_coleta="B3013", num_doacao="26007133",
            componente_pdf="CONCENTRADO HEMACIAS Deleucocitado Sist. Fechado",
            cod_isbt="E4545V00", seq=2, volume=340,
            abo="O", rh="N", validade=date(2026, 3, 26),
        )
        comp = Comprovante(
            numero="1320327", data_emissao=None, instituicao="HMOB",
            expedido_por="Test", data_expedicao=date(2026, 2, 15),
            bolsas=[bolsa1, bolsa2], total_bolsas_declarado=2,
        )
        linhas = mapear_comprovantes([comp])
        assert len(linhas) == 2
        assert linhas[0].num_bolsa == "B301326007133"
        assert linhas[1].num_bolsa == "B301326007133-2"

    def test_tolerante_nao_levanta_excecao(self):
        bolsa = BolsaExtraida(
            inst_coleta="B3013", num_doacao="99999999",
            componente_pdf="TIPO DESCONHECIDO XYZ",
            cod_isbt="E0000V00", seq=1, volume=100,
            abo="O", rh="P", validade=date(2026, 1, 1),
        )
        comp = Comprovante(
            numero="000", data_emissao=None, instituicao="HMOB",
            expedido_por="Test", data_expedicao=date(2025, 12, 14),
            bolsas=[bolsa], total_bolsas_declarado=1,
        )
        linhas = mapear_comprovantes([comp], tolerante=True)
        assert len(linhas) == 1
        assert linhas[0].tipo_hemocomponente == "TIPO DESCONHECIDO XYZ"

    def test_sem_tolerante_levanta_excecao(self):
        bolsa = BolsaExtraida(
            inst_coleta="B3013", num_doacao="99999999",
            componente_pdf="TIPO DESCONHECIDO XYZ",
            cod_isbt="E0000V00", seq=1, volume=100,
            abo="O", rh="P", validade=date(2026, 1, 1),
        )
        comp = Comprovante(
            numero="000", data_emissao=None, instituicao="HMOB",
            expedido_por="Test", data_expedicao=date(2025, 12, 14),
            bolsas=[bolsa], total_bolsas_declarado=1,
        )
        with pytest.raises(ValueError):
            mapear_comprovantes([comp], tolerante=False)


class TestMontarRow:
    def test_row_structure(self):
        from src.field_mapper import LinhaPlanilha
        linha = LinhaPlanilha(
            dias_antes_vencimento="",
            status="",
            data_entrada=date(2025, 12, 14),
            data_validade=date(2026, 1, 8),
            tipo_hemocomponente="CHD -  Concentrado de Hemácias Desleucocitado",
            gs_rh="O/POS",
            volume=292,
            responsavel_recepcao="NILMARA TANIA VELOSO MATOS",
            num_bolsa="B301325051087",
        )
        row = montar_row(linha, 11)
        assert len(row) == 13  # Columns A through M
        assert row[0].startswith("=IF(D11")  # A: formula
        assert row[1].startswith("=IF(A11")  # B: formula
        assert row[2] == "14/12/2025"         # C: data entrada
        assert row[3] == "08/01/2026"         # D: data validade
        assert row[4] == ""                   # E: manual
        assert row[5] == ""                   # F: manual
        assert row[6] == ""                   # G: manual
        assert "CHD" in row[7]                # H: tipo hemocomponente
        assert row[8] == "O/POS"              # I: gs/rh
        assert row[9] == 292                  # J: volume
        assert row[10] == "NILMARA TANIA VELOSO MATOS"  # K: responsavel
        assert row[11] == ""                  # L: manual
        assert row[12] == "B301325051087"     # M: num bolsa (inst_coleta + num_doacao)
