import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from src.pdf_extractor import BolsaExtraida, Comprovante


@dataclass
class LinhaPlanilha:
    dias_antes_vencimento: str  # Formula
    status: str                 # Formula
    data_entrada: date
    data_validade: date
    tipo_hemocomponente: str
    gs_rh: str
    volume: int
    responsavel_recepcao: str
    num_bolsa: str
    inst_coleta: str = ""


# Mapping from normalized PDF component substrings to BASE tab names.
# Order matters: more specific entries must come before less specific ones.
HEMOCOMPONENTE_MAP = {
    # --- Fenotipado + Desleucocitado + Irradiado (mais específico primeiro) ---
    "concentrado hemacias fenotipado desleucocitado irradiado": "CHFDI -\u00a0Concentrado de Hem\u00e1cias Fenotipado, Desleucocitado e Irradiado",
    "concentrado hemacias fenotipado deleucocitado irradiado": "CHFDI -\u00a0Concentrado de Hem\u00e1cias Fenotipado, Desleucocitado e Irradiado",
    # --- Fenotipado + Desleucocitado ---
    "concentrado hemacias fenotipado desleucocitado": "CHFD - Concentrado de Hem\u00e1cias Fenotipado e Desleucocitado",
    "concentrado hemacias fenotipado deleucocitado": "CHFD - Concentrado de Hem\u00e1cias Fenotipado e Desleucocitado",
    # --- Desleucocitado + Irradiado (com e sem "e" intermediário) ---
    "concentrado hemacias desleucocitado irradiado": "CHDI \u2013 Concentrado de Hem\u00e1cias Desleucocitado e Irradiado",
    "concentrado hemacias deleucocitado irradiado": "CHDI \u2013 Concentrado de Hem\u00e1cias Desleucocitado e Irradiado",
    "concentrado hemacias desleucocitado e irradiado": "CHDI \u2013 Concentrado de Hem\u00e1cias Desleucocitado e Irradiado",
    "concentrado hemacias deleucocitado e irradiado": "CHDI \u2013 Concentrado de Hem\u00e1cias Desleucocitado e Irradiado",
    # --- Hemácias Aférese Desleucocitado (PDF usa "CONC. DE HEMACIAS AFERESE") ---
    "hemacias aferese desleucocitado": "HAFD \u2013 Eritroaf\u00e9rese Desleucocitada",
    "hemacias aferese deleucocitado": "HAFD \u2013 Eritroaf\u00e9rese Desleucocitada",
    # --- Irradiado (sem desleucocitado) ---
    "concentrado hemacias irradiado": "CHI- Concentrado de Hem\u00e1cias Radiado",
    # --- Fenotipado (sem desleucocitado) ---
    "concentrado hemacias fenotipado": "CHF -  Concentrado de Hem\u00e1cias Fenotipado",
    # --- Desleucocitado (simples) ---
    "concentrado hemacias desleucocitado": "CHD -  Concentrado de Hem\u00e1cias Desleucocitado",
    "concentrado hemacias deleucocitado": "CHD -  Concentrado de Hem\u00e1cias Desleucocitado",
    # --- Camada Leucoplaquetária Removida (formas completa e abreviada) ---
    "concentrado hemacias camada leucoplaquetaria": "CHCR - Concentrado de Hem\u00e1cias Camada Leucoplaquet\u00e1ria Removida",
    "conc hemacias camada leucoplaq": "CHCR - Concentrado de Hem\u00e1cias Camada Leucoplaquet\u00e1ria Removida",
    "hemacias camada leucoplaq": "CHCR - Concentrado de Hem\u00e1cias Camada Leucoplaquet\u00e1ria Removida",
    # --- Hemácias Comum (formas com e sem "comum") ---
    "concentrado hemacias comum": "CHM -  Concentrado de Hem\u00e1cias Comum",
    # --- Plasma ---
    "plasma fresco congelado": "PFC - Plasma Fresco Congelado ",
    "plasma de 24": "P24h \u2013 Plasma 24h",
    "plasma 24": "P24h \u2013 Plasma 24h",
    # --- Crioprecipitado ---
    "crioprecipitado": "CRIO \u2013 Crioprecipitado ",
    # --- Plaquetas Randômicas ---
    "plaqueta randomica irradiada": "CPQI \u2013 Plaqueta Rand\u00f4mica Irradiada",
    "plaqueta randomica": "CPQ \u2013 Plaqueta Rand\u00f4mica",
    # --- Eritroaférese ---
    "eritroaferese desleucocitada irradiada": "HAFDI - Eritroaf\u00e9rese Desleucocitada Irradiada",
    "eritroaferese desleucocitada": "HAFD \u2013 Eritroaf\u00e9rese Desleucocitada",
    # --- Plaquetaférese ---
    "plaquetaferese desleucocitada irradiada": "PAFDI - Plaquetaf\u00e9rese Desleucocitada Irradiada",
    "plaquetaferese desleucocitada": "PAFD \u2013 Plaquetaf\u00e9rese Desleucocitada",
    # --- Pool de Plaquetas ---
    "pool de plaquetas desleucocitado irradiado": "PCPDI - Pool de Plaquetas Desleucocitado Irradiado",
    "pool de plaquetas desleucocitado": "PCPD \u2013 Pool de Plaquetas Desleucocitado",
    "pool de plaquetas inativacao": "IPPD - Pool de Plaquetas com inativa\u00e7\u00e3o de Pat\u00f3genos",
    "pool plaq inativacao": "IPPD - Pool de Plaquetas com inativa\u00e7\u00e3o de Pat\u00f3genos",
    "pool de plaquetas ressuspensos": "IPPA - Pool de plaquetas ressuspensos em PAS",
    # --- Eritrocitoaférese ---
    "eritrocitoaferese desleucocitada fenotipada": "HAFDF - Eritrocitoaf\u00e9rese Desleucocitada e Fenotipada",
}

RH_MAP = {"P": "POS", "N": "NEG"}


def _normalizar_texto(texto: str) -> str:
    """Normalize text: lowercase, remove accents, collapse whitespace."""
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase and collapse whitespace
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def converter_gs_rh(abo: str, rh: str) -> str:
    """Convert ABO + Rh to spreadsheet GS/RH format (e.g., 'O/POS')."""
    rh_texto = RH_MAP.get(rh.upper(), rh.upper())
    return f"{abo.upper()}/{rh_texto}"


def mapear_hemocomponente(componente_pdf: str, tolerante: bool = False) -> str:
    """Map PDF component name to standardized BASE tab name.

    Args:
        componente_pdf: Raw component name from PDF.
        tolerante: If True, return raw value instead of raising ValueError
                   when no match is found (Phase 2 preview mode).
    """
    normalizado = _normalizar_texto(componente_pdf)
    for chave, valor in HEMOCOMPONENTE_MAP.items():
        if chave in normalizado:
            return valor
    # Fallback: "CONCENTRADO HEMACIAS" sem qualificador → CHM Comum
    if "concentrado hemacias" in normalizado or "conc hemacias" in normalizado:
        return "CHM -  Concentrado de Hem\u00e1cias Comum"
    if tolerante:
        return componente_pdf
    raise ValueError(f"Hemocomponente nao mapeado: {componente_pdf}")


def _formula_dias_vencimento(row: int) -> str:
    return f'=IF(D{row}="","",D{row}-TODAY())'


def _formula_status(row: int) -> str:
    return (
        f'=IF(A{row}="","",IF(A{row}<0,"VENCIDO",'
        f'IF(A{row}=0,"VENCE HOJE",'
        f'CONCATENATE("VENCE EM ",A{row}," DIAS"))))'
    )


def mapear_comprovantes(
    comprovantes: list[Comprovante], tolerante: bool = False
) -> list[LinhaPlanilha]:
    """Convert extracted comprovantes to spreadsheet rows.

    Args:
        comprovantes: Extracted comprovante data from PDF.
        tolerante: If True, don't raise on unmapped components (Phase 2 mode).
    """
    linhas = []
    for comp in comprovantes:
        for bolsa in comp.bolsas:
            # Build unique bag number: inst_coleta + num_doacao
            # Append "-seq" when seq > 1 to distinguish multiple products
            num_bolsa = f"{bolsa.inst_coleta}{bolsa.num_doacao}"
            if bolsa.seq > 1:
                num_bolsa = f"{bolsa.inst_coleta}{bolsa.num_doacao}-{bolsa.seq}"
            linha = LinhaPlanilha(
                dias_antes_vencimento="",  # Formula added when row number is known
                status="",                 # Formula added when row number is known
                data_entrada=comp.data_expedicao,
                data_validade=bolsa.validade,
                tipo_hemocomponente=mapear_hemocomponente(
                    bolsa.componente_pdf, tolerante=tolerante
                ),
                gs_rh=converter_gs_rh(bolsa.abo, bolsa.rh),
                volume=bolsa.volume,
                responsavel_recepcao=comp.expedido_por,
                num_bolsa=num_bolsa,
                inst_coleta=bolsa.inst_coleta,
            )
            linhas.append(linha)
    return linhas


def montar_row(linha: LinhaPlanilha, row_num: int) -> list:
    """Build a row array for Google Sheets API (columns A through M)."""
    return [
        _formula_dias_vencimento(row_num),          # A
        _formula_status(row_num),                   # B
        linha.data_entrada.strftime("%d/%m/%Y"),     # C
        linha.data_validade.strftime("%d/%m/%Y"),    # D
        "",                                          # E - manual
        "",                                          # F - manual
        "",                                          # G - manual
        linha.tipo_hemocomponente,                   # H
        linha.gs_rh,                                 # I
        linha.volume,                                # J
        linha.responsavel_recepcao,                  # K
        "",                                          # L - manual
        linha.num_bolsa,                             # M
    ]
