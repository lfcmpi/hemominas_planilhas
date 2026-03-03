"""Tests for validators module."""

from datetime import date

import pytest

from src.field_mapper import LinhaPlanilha
from src.pdf_extractor import BolsaExtraida, Comprovante
from src.sheets_reader import ValoresBase
from src.validators import (
    DuplicataInfo,
    LinhaPreview,
    ValidacaoErro,
    _normalizar,
    detectar_duplicatas,
    montar_preview,
    validar_campo,
    validar_linha,
)
from datetime import datetime


def _make_base():
    return ValoresBase(
        tipos_hemocomponente=[
            "CHD - Concentrado de Hemacias Desleucocitado",
            "PFC - Plasma Fresco Congelado",
        ],
        gs_rh=["O/POS", "O/NEG", "A/POS", "A/NEG"],
        responsaveis=["Ana Silva", "Joao Santos"],
        destinos=["UTI", "Enfermaria", "Centro Cirurgico"],
        reacoes_transfusionais=["Nenhuma", "Febril", "Alergica"],
        timestamp=datetime.now(),
    )


def _make_linha(**kwargs):
    defaults = {
        "dias_antes_vencimento": "",
        "status": "",
        "data_entrada": date(2025, 12, 14),
        "data_validade": date(2026, 1, 8),
        "tipo_hemocomponente": "CHD - Concentrado de Hemacias Desleucocitado",
        "gs_rh": "O/POS",
        "volume": 292,
        "responsavel_recepcao": "Nilmara Veloso",
        "num_bolsa": "25014485",
    }
    defaults.update(kwargs)
    return LinhaPlanilha(**defaults)


class TestNormalizar:
    def test_remove_acentos(self):
        assert _normalizar("Hemácias") == "hemacias"

    def test_remove_nbsp(self):
        assert _normalizar("valor\xa0teste") == "valor teste"

    def test_lowercase(self):
        assert _normalizar("O/POS") == "o/pos"

    def test_strip(self):
        assert _normalizar("  teste  ") == "teste"


class TestValidarLinha:
    def test_linha_valida_sem_erros(self):
        erros = validar_linha(_make_linha(), _make_base())
        assert erros == []

    def test_tipo_invalido_retorna_error(self):
        linha = _make_linha(tipo_hemocomponente="DESCONHECIDO")
        erros = validar_linha(linha, _make_base())
        assert len(erros) == 1
        assert erros[0].campo == "tipo_hemocomponente"
        assert erros[0].nivel == "error"
        assert len(erros[0].valores_validos) == 2

    def test_gs_rh_invalido_retorna_error(self):
        linha = _make_linha(gs_rh="X/YYY")
        erros = validar_linha(linha, _make_base())
        assert len(erros) == 1
        assert erros[0].campo == "gs_rh"
        assert erros[0].nivel == "error"

    def test_volume_zero_retorna_warning(self):
        linha = _make_linha(volume=0)
        erros = validar_linha(linha, _make_base())
        assert len(erros) == 1
        assert erros[0].campo == "volume"
        assert erros[0].nivel == "warning"

    def test_responsavel_vazio_retorna_warning(self):
        linha = _make_linha(responsavel_recepcao="")
        erros = validar_linha(linha, _make_base())
        assert len(erros) == 1
        assert erros[0].campo == "responsavel_recepcao"
        assert erros[0].nivel == "warning"

    def test_multiplos_erros(self):
        linha = _make_linha(
            tipo_hemocomponente="DESCONHECIDO",
            gs_rh="X/Y",
            volume=0,
            responsavel_recepcao="",
        )
        erros = validar_linha(linha, _make_base())
        assert len(erros) == 4
        errors = [e for e in erros if e.nivel == "error"]
        warnings = [e for e in erros if e.nivel == "warning"]
        assert len(errors) == 2
        assert len(warnings) == 2

    def test_comparacao_normalizada_com_acentos(self):
        base = _make_base()
        # Value with accent should match base without accent
        linha = _make_linha(tipo_hemocomponente="CHD - Concentrado de Hemácias Desleucocitado")
        erros = validar_linha(linha, base)
        assert erros == []


class TestDetectarDuplicatas:
    def test_sem_duplicatas(self):
        linhas = [_make_linha(num_bolsa="B320211111111")]
        bolsas = {"B320222222222", "B320233333333"}
        result = detectar_duplicatas(linhas, bolsas)
        assert result == {}

    def test_com_duplicata(self):
        linhas = [_make_linha(num_bolsa="B320225014485")]
        bolsas = {"B320225014485", "B320233333333"}
        result = detectar_duplicatas(linhas, bolsas)
        assert "B320225014485" in result
        assert isinstance(result["B320225014485"], DuplicataInfo)

    def test_set_vazio(self):
        linhas = [_make_linha()]
        result = detectar_duplicatas(linhas, set())
        assert result == {}


class TestMontarPreview:
    def _make_comprovante(self):
        return Comprovante(
            numero="1292305",
            data_emissao=None,
            instituicao="HMOB",
            expedido_por="Nilmara",
            data_expedicao=date(2025, 12, 14),
            bolsas=[
                BolsaExtraida(
                    inst_coleta="B3202",
                    num_doacao="25014485",
                    componente_pdf="CONCENTRADO HEMACIAS DESLEUCOCITADO",
                    cod_isbt="E0793V00",
                    seq=1,
                    volume=292,
                    abo="O",
                    rh="P",
                    validade=date(2026, 1, 8),
                )
            ],
            total_bolsas_declarado=1,
        )

    def test_preview_basico(self):
        comp = self._make_comprovante()
        linha = _make_linha(num_bolsa="B320225014485")
        base = _make_base()

        preview = montar_preview([linha], [comp], base, set())
        assert len(preview) == 1
        assert preview[0].selecionada is True
        assert preview[0].duplicata is None
        assert preview[0].num_comprovante == "1292305"

    def test_duplicata_desmarcada(self):
        comp = self._make_comprovante()
        linha = _make_linha(num_bolsa="B320225014485")
        base = _make_base()

        preview = montar_preview([linha], [comp], base, {"B320225014485"})
        assert len(preview) == 1
        assert preview[0].selecionada is False
        assert preview[0].duplicata is not None
        assert preview[0].duplicata.num_bolsa == "B320225014485"

    def test_mix_novas_e_duplicatas(self):
        comp = self._make_comprovante()
        comp.bolsas.append(
            BolsaExtraida(
                inst_coleta="B3202", num_doacao="99999999",
                componente_pdf="CONCENTRADO HEMACIAS DESLEUCOCITADO",
                cod_isbt="E0793V00", seq=2, volume=280,
                abo="A", rh="P", validade=date(2026, 1, 10),
            )
        )
        linhas = [
            _make_linha(num_bolsa="B320225014485"),
            _make_linha(num_bolsa="B320299999999"),
        ]
        base = _make_base()

        preview = montar_preview(linhas, [comp], base, {"B320225014485"})
        assert preview[0].selecionada is False  # duplicata
        assert preview[1].selecionada is True   # nova


class TestValidarCampo:
    def test_tipo_valido(self):
        base = _make_base()
        valido, msg = validar_campo(
            "tipo_hemocomponente",
            "CHD - Concentrado de Hemacias Desleucocitado",
            base,
        )
        assert valido is True
        assert msg is None

    def test_tipo_invalido(self):
        base = _make_base()
        valido, msg = validar_campo("tipo_hemocomponente", "DESCONHECIDO", base)
        assert valido is False
        assert msg is not None

    def test_gs_rh_valido(self):
        base = _make_base()
        valido, msg = validar_campo("gs_rh", "O/POS", base)
        assert valido is True

    def test_gs_rh_invalido(self):
        base = _make_base()
        valido, msg = validar_campo("gs_rh", "X/Y", base)
        assert valido is False

    def test_campo_desconhecido_sempre_valido(self):
        base = _make_base()
        valido, msg = validar_campo("outro", "qualquer", base)
        assert valido is True
