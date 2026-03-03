"""Phase 2: Reading from Google Sheets (BASE tab + column M for duplicates).

Includes local fallback functions that read from SQLite when Sheets is unavailable.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from src.config import (
    BASE_CACHE_TTL_MINUTES,
    BASE_DESTINOS_RANGE,
    BASE_GS_RH_RANGE,
    BASE_REACAO_RANGE,
    BASE_RESPONSAVEIS_RANGE,
    BASE_TAB_NAME,
    BASE_TIPOS_RANGE,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SHEETS_ID,
    SHEET_TAB_NAME,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


@dataclass
class ValoresBase:
    """Cache of reference lists from the BASE tab."""
    tipos_hemocomponente: list[str]
    gs_rh: list[str]
    responsaveis: list[str]
    destinos: list[str]
    reacoes_transfusionais: list[str]
    timestamp: datetime


_base_cache: ValoresBase | None = None


def _get_client() -> gspread.Client:
    """Authenticate and return a gspread client using service account."""
    creds_path = Path(GOOGLE_CREDENTIALS_PATH)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google credentials not found at {creds_path}. "
            "Download your service account JSON and place it there."
        )
    credentials = Credentials.from_service_account_file(
        str(creds_path), scopes=SCOPES
    )
    return gspread.authorize(credentials)


def _extrair_valores(cells: list[list[str]]) -> list[str]:
    """Extract non-empty string values from a column range result."""
    valores = []
    for row in cells:
        if row and row[0].strip():
            valores.append(row[0].strip())
    return valores


def ler_valores_base(spreadsheet_id: str | None = None) -> ValoresBase:
    """Read reference values from the BASE tab.

    Caches results for BASE_CACHE_TTL_MINUTES minutes.
    """
    global _base_cache
    if (
        _base_cache is not None
        and datetime.now() - _base_cache.timestamp
        < timedelta(minutes=BASE_CACHE_TTL_MINUTES)
    ):
        return _base_cache

    sid = spreadsheet_id or GOOGLE_SHEETS_ID
    client = _get_client()
    sheet = client.open_by_key(sid)
    base_ws = sheet.worksheet(BASE_TAB_NAME)

    gs_rh_cells = base_ws.get(BASE_GS_RH_RANGE)
    tipos_cells = base_ws.get(BASE_TIPOS_RANGE)
    resp_cells = base_ws.get(BASE_RESPONSAVEIS_RANGE)
    destinos_cells = base_ws.get(BASE_DESTINOS_RANGE)
    reacao_cells = base_ws.get(BASE_REACAO_RANGE)

    _base_cache = ValoresBase(
        tipos_hemocomponente=_extrair_valores(tipos_cells),
        gs_rh=_extrair_valores(gs_rh_cells),
        responsaveis=_extrair_valores(resp_cells),
        destinos=_extrair_valores(destinos_cells),
        reacoes_transfusionais=_extrair_valores(reacao_cells),
        timestamp=datetime.now(),
    )
    return _base_cache


def ler_bolsas_existentes(spreadsheet_id: str | None = None) -> set[str]:
    """Read existing bag numbers from column M of MAPA DE TRANSFUSAO.

    Always reads fresh (no cache) to ensure duplicate detection is current.
    Returns a set for O(1) lookup.
    """
    sid = spreadsheet_id or GOOGLE_SHEETS_ID
    client = _get_client()
    sheet = client.open_by_key(sid)
    mapa_ws = sheet.worksheet(SHEET_TAB_NAME)

    # Column M from row 11 (data start) onwards
    col_m_cells = mapa_ws.get("M11:M")

    bolsas: set[str] = set()
    if col_m_cells:
        for row in col_m_cells:
            if row:
                val = str(row[0]).strip()
                if val:
                    bolsas.add(val)
    return bolsas


def invalidar_cache_base() -> None:
    """Invalidate the BASE cache (for testing or forced refresh)."""
    global _base_cache
    _base_cache = None


def ler_valores_base_local(db_path: str) -> ValoresBase:
    """Fallback: read reference values from SQLite planilha_data + import_bolsas.

    Extracts distinct tipo_hemocomponente and gs_rh from local data.
    Responsaveis are extracted from import_bolsas via import_records.
    """
    from src.history_store import get_db

    with get_db(db_path) as conn:
        # Tipos from planilha_data
        tipos_pd = conn.execute(
            "SELECT DISTINCT tipo_hemocomponente FROM planilha_data "
            "WHERE tipo_hemocomponente != '' AND tipo_hemocomponente IS NOT NULL"
        ).fetchall()
        # Also from import_bolsas (may have types not yet synced)
        tipos_ib = conn.execute(
            "SELECT DISTINCT tipo_hemocomponente FROM import_bolsas "
            "WHERE tipo_hemocomponente != '' AND tipo_hemocomponente IS NOT NULL"
        ).fetchall()
        tipos_set = {r[0] for r in tipos_pd} | {r[0] for r in tipos_ib}

        # GS/RH from planilha_data
        gs_pd = conn.execute(
            "SELECT DISTINCT gs_rh FROM planilha_data "
            "WHERE gs_rh != '' AND gs_rh IS NOT NULL"
        ).fetchall()
        gs_ib = conn.execute(
            "SELECT DISTINCT gs_rh FROM import_bolsas "
            "WHERE gs_rh != '' AND gs_rh IS NOT NULL"
        ).fetchall()
        gs_set = {r[0] for r in gs_pd} | {r[0] for r in gs_ib}

        # Responsaveis from planilha_data
        resp_rows = conn.execute(
            "SELECT DISTINCT responsavel_recepcao FROM planilha_data "
            "WHERE responsavel_recepcao != '' AND responsavel_recepcao IS NOT NULL"
        ).fetchall()
        resp_set = {r[0] for r in resp_rows}

        # Destinos from planilha_data
        dest_rows = conn.execute(
            "SELECT DISTINCT destino FROM planilha_data "
            "WHERE destino != '' AND destino IS NOT NULL"
        ).fetchall()
        dest_set = {r[0] for r in dest_rows}

    return ValoresBase(
        tipos_hemocomponente=sorted(tipos_set),
        gs_rh=sorted(gs_set),
        responsaveis=sorted(resp_set),
        destinos=sorted(dest_set),
        reacoes_transfusionais=[],
        timestamp=datetime.now(),
    )


def ler_bolsas_existentes_local(db_path: str) -> set[str]:
    """Fallback: read existing bag numbers from SQLite planilha_data."""
    from src.history_store import get_db

    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT num_bolsa FROM planilha_data WHERE num_bolsa != '' AND num_bolsa IS NOT NULL"
        ).fetchall()
    return {r[0] for r in rows}


def ler_planilha_completa(spreadsheet_id: str | None = None) -> tuple[list[str], list[list[str]]]:
    """Read entire MAPA DE TRANSFUSAO: header (row 10) + all data rows (11+).

    Returns (header_row, data_rows). Single API call for efficiency.
    """
    sid = spreadsheet_id or GOOGLE_SHEETS_ID
    client = _get_client()
    sheet = client.open_by_key(sid)
    mapa_ws = sheet.worksheet(SHEET_TAB_NAME)

    all_values = mapa_ws.get_all_values()

    # Header is at row 10 (index 9)
    if len(all_values) < 10:
        return [], []

    header = all_values[9]  # Row 10 (0-indexed = 9)
    data_rows = all_values[10:]  # Rows 11+ (0-indexed = 10+)

    return header, data_rows
