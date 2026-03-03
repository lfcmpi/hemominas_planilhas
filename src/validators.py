"""Phase 2: Validation of extracted data against BASE tab + duplicate detection."""

import unicodedata
from dataclasses import dataclass, field

from src.field_mapper import LinhaPlanilha
from src.pdf_extractor import Comprovante
from src.sheets_reader import ValoresBase


@dataclass
class ValidacaoErro:
    campo: str
    valor_atual: str
    mensagem: str
    nivel: str  # "error" (blocks) | "warning" (does not block)
    valores_validos: list[str] = field(default_factory=list)


@dataclass
class DuplicataInfo:
    num_bolsa: str
    linha_planilha: int
    data_cadastro: str | None = None


@dataclass
class LinhaPreview:
    """Extends LinhaPlanilha with preview metadata."""
    linha: LinhaPlanilha
    num_comprovante: str
    selecionada: bool = True
    erros: list[ValidacaoErro] = field(default_factory=list)
    duplicata: DuplicataInfo | None = None
    editada: bool = False


def _normalizar(valor: str) -> str:
    """Normalize value for comparison only (never for display/storage).

    Strips whitespace (including non-breaking space \\xa0),
    removes accents, and lowercases.
    """
    valor = valor.replace("\xa0", " ").strip()
    valor = unicodedata.normalize("NFD", valor)
    valor = "".join(c for c in valor if unicodedata.category(c) != "Mn")
    return valor.lower()


def validar_linha(linha: LinhaPlanilha, base: ValoresBase) -> list[ValidacaoErro]:
    """Validate a single row against BASE reference values.

    Returns list of errors/warnings found.
    """
    erros = []

    # Validate tipo_hemocomponente (critical)
    tipos_norm = {_normalizar(t): t for t in base.tipos_hemocomponente}
    if _normalizar(linha.tipo_hemocomponente) not in tipos_norm:
        erros.append(ValidacaoErro(
            campo="tipo_hemocomponente",
            valor_atual=linha.tipo_hemocomponente,
            mensagem="Tipo de hemocomponente nao encontrado na aba BASE",
            nivel="error",
            valores_validos=base.tipos_hemocomponente,
        ))

    # Validate gs_rh (critical)
    gs_norm = {_normalizar(g): g for g in base.gs_rh}
    if _normalizar(linha.gs_rh) not in gs_norm:
        erros.append(ValidacaoErro(
            campo="gs_rh",
            valor_atual=linha.gs_rh,
            mensagem="GS/RH nao encontrado na aba BASE",
            nivel="error",
            valores_validos=base.gs_rh,
        ))

    # Validate volume (warning only)
    if linha.volume <= 0:
        erros.append(ValidacaoErro(
            campo="volume",
            valor_atual=str(linha.volume),
            mensagem="Volume deve ser maior que zero",
            nivel="warning",
        ))

    # Validate responsavel (warning only)
    if not linha.responsavel_recepcao.strip():
        erros.append(ValidacaoErro(
            campo="responsavel_recepcao",
            valor_atual="",
            mensagem="Responsavel nao extraido do PDF",
            nivel="warning",
            valores_validos=base.responsaveis,
        ))

    return erros


def detectar_duplicatas(
    linhas: list[LinhaPlanilha], bolsas_existentes: set[str]
) -> dict[str, DuplicataInfo]:
    """Check which bag numbers already exist in the spreadsheet.

    Returns dict mapping num_bolsa -> DuplicataInfo for duplicates found.
    """
    duplicatas = {}
    for linha in linhas:
        num = str(linha.num_bolsa).strip()
        if num and num in bolsas_existentes:
            duplicatas[num] = DuplicataInfo(
                num_bolsa=num,
                linha_planilha=0,  # Exact row unknown from set lookup
            )
    return duplicatas


def montar_preview(
    linhas: list[LinhaPlanilha],
    comprovantes: list[Comprovante],
    base: ValoresBase,
    bolsas_existentes: set[str],
) -> list[LinhaPreview]:
    """Build preview data with validation errors and duplicate detection.

    Maps each LinhaPlanilha back to its comprovante number.
    Duplicates are deselected by default.
    """
    duplicatas = detectar_duplicatas(linhas, bolsas_existentes)

    # Build comprovante-to-bolsa mapping for num_comprovante lookup
    # Key uses inst_coleta + num_doacao to match the concatenated num_bolsa
    comp_map: dict[str, str] = {}
    for comp in comprovantes:
        for bolsa in comp.bolsas:
            comp_map[f"{bolsa.inst_coleta}{bolsa.num_doacao}"] = comp.numero

    preview = []
    for linha in linhas:
        erros = validar_linha(linha, base)
        dup = duplicatas.get(str(linha.num_bolsa).strip())

        preview.append(LinhaPreview(
            linha=linha,
            num_comprovante=comp_map.get(linha.num_bolsa, ""),
            selecionada=dup is None,  # Deselect duplicates
            erros=erros,
            duplicata=dup,
        ))

    return preview


def validar_campo(campo: str, valor: str, base: ValoresBase) -> tuple[bool, str | None]:
    """Validate a single field value against BASE (for inline edit revalidation).

    Returns (is_valid, error_message_or_none).
    """
    if campo == "tipo_hemocomponente":
        tipos_norm = {_normalizar(t) for t in base.tipos_hemocomponente}
        if _normalizar(valor) in tipos_norm:
            return True, None
        return False, "Tipo de hemocomponente nao encontrado na aba BASE"

    if campo == "gs_rh":
        gs_norm = {_normalizar(g) for g in base.gs_rh}
        if _normalizar(valor) in gs_norm:
            return True, None
        return False, "GS/RH nao encontrado na aba BASE"

    return True, None
