"""Servico de sincronizacao bidirecional Google Sheets <-> SQLite."""

import logging
import unicodedata
from datetime import datetime

from src.config import GOOGLE_SHEETS_ID
from src.history_store import get_db
from src.sheets_reader import ler_planilha_completa

logger = logging.getLogger(__name__)


def _normalizar_header(texto: str) -> str:
    """Normalize header text: strip accents, lowercase, collapse whitespace, remove special chars."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove special chars like º, *, () but keep / for GS/RH
    import re
    limpo = re.sub(r"[º°\*\(\)\.\,]", "", sem_acento)
    return re.sub(r"\s+", " ", limpo.lower()).strip()


# Header names expected in row 10 of MAPA DE TRANSFUSAO (columns A-S)
_HEADER_MAP = {
    "dias_antes_vencimento": ["dias antes vencimento", "dias antes do vencimento", "dias"],
    "status_vencimento": ["status", "status vencimento"],
    "data_entrada": ["data entrada", "data de entrada", "entrada"],
    "data_validade": ["data validade", "data de validade", "validade"],
    "data_transfusao": ["data transfusao", "data de transfusao", "transfusao",
                        "data transfusao/destino"],
    "destino": ["destino"],
    "nome_paciente": ["nome completo do paciente", "nome paciente", "paciente"],
    "tipo_hemocomponente": ["tipo hemocomponente", "tipo de hemocomponente",
                            "hemocomponente", "tipo"],
    "gs_rh": ["gs rh", "gs/rh", "tipo sanguineo"],
    "volume": ["volume", "volume ml", "volume (ml)", "vol"],
    "responsavel_recepcao": ["responsavel recepcao", "responsavel", "recebido por"],
    "setor_transfusao": ["setor da transfusao", "setor transfusao", "setor"],
    "num_bolsa": ["num bolsa", "numero bolsa", "n bolsa", "bolsa", "n da bolsa",
                  "no da bolsa"],
    "prontuario_salus": ["no prontuario salus", "n prontuario salus", "prontuario salus"],
    "prontuario_mv": ["n prontuario mv", "no prontuario mv", "prontuario mv"],
    "sus_laudo": ["sus no laudo / no aih / no apac / bpai",
                  "sus n laudo / n aih / n apac / bpai", "sus", "n laudo"],
    "reacao_transfusional": ["reacao transfusional", "reacao"],
    "bolsa_sbs": ["no bolsa sbs", "n bolsa sbs", "bolsa sbs"],
}

# Fallback: positional mapping (A=0..S=18)
_POSITIONAL_MAP = {
    0: "dias_antes_vencimento",   # A
    1: "status_vencimento",        # B
    2: "data_entrada",             # C
    3: "data_validade",            # D
    4: "data_transfusao",          # E
    5: "destino",                  # F
    6: "nome_paciente",            # G
    7: "tipo_hemocomponente",      # H
    8: "gs_rh",                    # I
    9: "volume",                   # J
    10: "responsavel_recepcao",    # K
    11: "setor_transfusao",        # L
    12: "num_bolsa",               # M
    13: "prontuario_salus",        # N
    14: "prontuario_mv",           # O
    15: "sus_laudo",               # P
    # 16: column Q (sub-header "2", skipped)
    17: "reacao_transfusional",    # R
    18: "bolsa_sbs",               # S
}


def _build_column_index(header: list[str]) -> dict[str, int]:
    """Map field names to column indices by matching header text.

    Uses accent-normalized comparison so "RESPONSÁVEL" matches "responsavel".
    Falls back to positional mapping if header matching fails.
    """
    col_map = {}
    header_norm = [_normalizar_header(h) for h in header]

    for field, aliases in _HEADER_MAP.items():
        for i, h in enumerate(header_norm):
            if h in aliases:
                col_map[field] = i
                break

    # Fallback to positional if we didn't match enough columns
    if len(col_map) < 10:
        col_map = {}
        for pos, field in _POSITIONAL_MAP.items():
            if pos < len(header):
                col_map[field] = pos

    return col_map


def _safe_int(val) -> int | None:
    """Convert value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(str(val).strip().replace("ml", "").replace("mL", "").strip())
    except (ValueError, TypeError):
        return None


def _cell(row: list, idx: int | None) -> str:
    """Safely get cell value from row by index."""
    if idx is None or idx >= len(row):
        return ""
    val = row[idx]
    return str(val).strip() if val else ""


def executar_sync(db_path: str) -> dict:
    """Sync all data from Google Sheets MAPA DE TRANSFUSAO into SQLite planilha_data.

    Returns dict with status, rows_synced, timestamp.
    """
    now = datetime.now().isoformat()
    try:
        header, data_rows = ler_planilha_completa(GOOGLE_SHEETS_ID)

        if not header:
            result = {"status": "sucesso", "rows_synced": 0, "timestamp": now}
            _update_sync_metadata(db_path, now, "sucesso", 0, None)
            return result

        col_map = _build_column_index(header)
        num_bolsa_idx = col_map.get("num_bolsa")

        if num_bolsa_idx is None:
            raise ValueError("Coluna num_bolsa nao encontrada no header da planilha")

        rows_synced = 0
        with get_db(db_path) as conn:
            for row_num, row in enumerate(data_rows, start=11):
                num_bolsa = _cell(row, num_bolsa_idx)
                if not num_bolsa:
                    continue

                volume = _safe_int(_cell(row, col_map.get("volume")))

                conn.execute(
                    """INSERT INTO planilha_data
                        (num_bolsa, dias_antes_vencimento, status_vencimento,
                         data_entrada, data_validade, data_transfusao, destino,
                         nome_paciente, tipo_hemocomponente, gs_rh, volume,
                         responsavel_recepcao, setor_transfusao,
                         prontuario_salus, prontuario_mv, sus_laudo,
                         reacao_transfusional, bolsa_sbs,
                         sheet_row, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(num_bolsa) DO UPDATE SET
                        dias_antes_vencimento=excluded.dias_antes_vencimento,
                        status_vencimento=excluded.status_vencimento,
                        data_entrada=excluded.data_entrada,
                        data_validade=excluded.data_validade,
                        data_transfusao=excluded.data_transfusao,
                        destino=excluded.destino,
                        nome_paciente=excluded.nome_paciente,
                        tipo_hemocomponente=excluded.tipo_hemocomponente,
                        gs_rh=excluded.gs_rh,
                        volume=excluded.volume,
                        responsavel_recepcao=excluded.responsavel_recepcao,
                        setor_transfusao=excluded.setor_transfusao,
                        prontuario_salus=excluded.prontuario_salus,
                        prontuario_mv=excluded.prontuario_mv,
                        sus_laudo=excluded.sus_laudo,
                        reacao_transfusional=excluded.reacao_transfusional,
                        bolsa_sbs=excluded.bolsa_sbs,
                        sheet_row=excluded.sheet_row,
                        updated_at=excluded.updated_at
                    """,
                    (
                        num_bolsa,
                        _cell(row, col_map.get("dias_antes_vencimento")),
                        _cell(row, col_map.get("status_vencimento")),
                        _cell(row, col_map.get("data_entrada")),
                        _cell(row, col_map.get("data_validade")),
                        _cell(row, col_map.get("data_transfusao")),
                        _cell(row, col_map.get("destino")),
                        _cell(row, col_map.get("nome_paciente")),
                        _cell(row, col_map.get("tipo_hemocomponente")),
                        _cell(row, col_map.get("gs_rh")),
                        volume,
                        _cell(row, col_map.get("responsavel_recepcao")),
                        _cell(row, col_map.get("setor_transfusao")),
                        _cell(row, col_map.get("prontuario_salus")),
                        _cell(row, col_map.get("prontuario_mv")),
                        _cell(row, col_map.get("sus_laudo")),
                        _cell(row, col_map.get("reacao_transfusional")),
                        _cell(row, col_map.get("bolsa_sbs")),
                        row_num,
                        now,
                    ),
                )
                rows_synced += 1

        _update_sync_metadata(db_path, now, "sucesso", rows_synced, None)

        # After successful Sheets→SQLite sync, try pushing pending local rows
        try:
            sincronizar_pendentes(db_path)
        except Exception:
            pass  # Non-critical: will retry on next sync cycle

        return {"status": "sucesso", "rows_synced": rows_synced, "timestamp": now}

    except Exception as e:
        _update_sync_metadata(db_path, now, "erro", 0, str(e))
        return {"status": "erro", "error": str(e), "timestamp": now}


def _update_sync_metadata(db_path: str, timestamp: str, status: str,
                          rows: int, error: str | None):
    """Update the sync_metadata singleton row."""
    with get_db(db_path) as conn:
        conn.execute(
            """INSERT INTO sync_metadata (id, last_sync_at, last_sync_status,
                last_sync_rows, last_sync_error)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_sync_at=excluded.last_sync_at,
                last_sync_status=excluded.last_sync_status,
                last_sync_rows=excluded.last_sync_rows,
                last_sync_error=excluded.last_sync_error
            """,
            (timestamp, status, rows, error),
        )


def salvar_linhas_local(db_path: str, linhas) -> dict:
    """Save LinhaPlanilha objects to planilha_data with pending_sync=1.

    Used as fallback when Google Sheets is unavailable.
    Returns dict with count of rows saved.
    """
    now = datetime.now().isoformat()
    saved = 0
    with get_db(db_path) as conn:
        for linha in linhas:
            data_entrada = linha.data_entrada
            data_validade = linha.data_validade
            if hasattr(data_entrada, 'strftime'):
                data_entrada = data_entrada.strftime("%d/%m/%Y")
            if hasattr(data_validade, 'strftime'):
                data_validade = data_validade.strftime("%d/%m/%Y")

            inst_coleta = getattr(linha, 'inst_coleta', '')
            conn.execute(
                """INSERT INTO planilha_data
                    (num_bolsa, inst_coleta, data_entrada, data_validade,
                     tipo_hemocomponente, gs_rh, volume,
                     responsavel_recepcao, pending_sync, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(num_bolsa) DO UPDATE SET
                    inst_coleta=excluded.inst_coleta,
                    data_entrada=excluded.data_entrada,
                    data_validade=excluded.data_validade,
                    tipo_hemocomponente=excluded.tipo_hemocomponente,
                    gs_rh=excluded.gs_rh,
                    volume=excluded.volume,
                    responsavel_recepcao=excluded.responsavel_recepcao,
                    pending_sync=1,
                    updated_at=excluded.updated_at
                """,
                (
                    linha.num_bolsa,
                    inst_coleta,
                    data_entrada,
                    data_validade,
                    linha.tipo_hemocomponente,
                    linha.gs_rh,
                    linha.volume,
                    linha.responsavel_recepcao,
                    now,
                ),
            )
            saved += 1
    return {"salvas_localmente": saved}


def sincronizar_pendentes(db_path: str) -> dict:
    """Push pending_sync=1 rows from SQLite to Google Sheets.

    On success, marks them as pending_sync=0.
    Returns dict with status and counts.
    """
    with get_db(db_path) as conn:
        pending_rows = conn.execute(
            "SELECT * FROM planilha_data WHERE pending_sync = 1"
        ).fetchall()

    if not pending_rows:
        return {"status": "nenhum_pendente", "total": 0}

    try:
        from src.field_mapper import LinhaPlanilha
        from src.sheets_writer import escrever_linhas

        linhas = []
        for row in pending_rows:
            row_dict = dict(row)
            # Parse dates back to date objects
            from datetime import date as date_type
            dt_entrada = _parse_date(row_dict.get("data_entrada", ""))
            dt_validade = _parse_date(row_dict.get("data_validade", ""))

            linha = LinhaPlanilha(
                dias_antes_vencimento="",
                status="",
                data_entrada=dt_entrada,
                data_validade=dt_validade,
                tipo_hemocomponente=row_dict.get("tipo_hemocomponente", ""),
                gs_rh=row_dict.get("gs_rh", ""),
                volume=row_dict.get("volume", 0) or 0,
                responsavel_recepcao=row_dict.get("responsavel_recepcao", ""),
                num_bolsa=row_dict.get("num_bolsa", ""),
                inst_coleta=row_dict.get("inst_coleta", ""),
            )
            linhas.append(linha)

        resultado = escrever_linhas(linhas)

        # Mark as synced
        with get_db(db_path) as conn:
            for row in pending_rows:
                conn.execute(
                    "UPDATE planilha_data SET pending_sync = 0 WHERE num_bolsa = ?",
                    (row["num_bolsa"],),
                )

        logger.info("Sincronizados %d registros pendentes com Google Sheets", len(linhas))
        return {
            "status": "sucesso",
            "total": len(linhas),
            "linhas_inseridas": resultado.get("linhas_inseridas", 0),
        }

    except Exception as e:
        logger.warning("Falha ao sincronizar pendentes: %s", e)
        return {"status": "erro", "error": str(e), "total": len(pending_rows)}


def _parse_date(date_str: str):
    """Parse date string (DD/MM/YYYY or YYYY-MM-DD) to date object."""
    from datetime import date as date_type
    if not date_str:
        return date_type.today()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return date_type.today()


def contar_pendentes(db_path: str) -> int:
    """Return count of rows with pending_sync=1."""
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM planilha_data WHERE pending_sync = 1"
        ).fetchone()
        return row["c"]


def obter_sync_status(db_path: str) -> dict:
    """Return last sync info from sync_metadata."""
    with get_db(db_path) as conn:
        row = conn.execute("SELECT * FROM sync_metadata WHERE id = 1").fetchone()
        if not row:
            return {
                "last_sync_at": None,
                "last_sync_status": None,
                "last_sync_rows": 0,
                "last_sync_error": None,
            }
        return {
            "last_sync_at": row["last_sync_at"],
            "last_sync_status": row["last_sync_status"],
            "last_sync_rows": row["last_sync_rows"],
            "last_sync_error": row["last_sync_error"],
        }


# Columns that can be edited inline (excludes computed fields and primary key)
_EDITABLE_COLUMNS = {
    "data_transfusao", "destino", "nome_paciente", "setor_transfusao",
    "prontuario_salus", "prontuario_mv", "sus_laudo",
    "reacao_transfusional", "bolsa_sbs", "responsavel_recepcao",
}


def atualizar_campo_planilha(db_path: str, num_bolsa: str, campo: str,
                              valor: str, user_email: str) -> dict:
    """Update a single field in planilha_data for inline editing.

    Validates that the column is in the allowed editable set.
    Records who edited and when for audit trail.
    Returns dict with status.
    """
    if campo not in _EDITABLE_COLUMNS:
        raise ValueError(f"Campo '{campo}' nao pode ser editado.")

    now = datetime.now().isoformat()
    with get_db(db_path) as conn:
        existing = conn.execute(
            f"SELECT id, {campo} FROM planilha_data WHERE num_bolsa = ?", (num_bolsa,)
        ).fetchone()
        if not existing:
            raise ValueError(f"Bolsa '{num_bolsa}' nao encontrada.")

        valor_anterior = existing[campo] or ""

        conn.execute(
            f"UPDATE planilha_data SET {campo} = ?, edited_by = ?, edited_at = ?, updated_at = ? "
            "WHERE num_bolsa = ?",
            (valor, user_email, now, now, num_bolsa),
        )

    return {"status": "sucesso", "campo": campo, "valor": valor,
            "valor_anterior": valor_anterior, "num_bolsa": num_bolsa}


_ALLOWED_SORT_COLUMNS = {
    "num_bolsa", "data_entrada", "data_validade", "tipo_hemocomponente",
    "gs_rh", "volume", "responsavel_recepcao", "status_vencimento",
    "dias_antes_vencimento", "data_transfusao", "destino", "sheet_row",
    "nome_paciente", "setor_transfusao", "prontuario_salus",
    "prontuario_mv", "reacao_transfusional", "bolsa_sbs",
}

_SEARCH_COLUMNS = [
    "num_bolsa", "tipo_hemocomponente", "gs_rh", "destino",
    "responsavel_recepcao", "nome_paciente", "prontuario_salus",
    "prontuario_mv", "bolsa_sbs",
]


def consultar_planilha(db_path: str, page: int = 1, per_page: int = 25,
                       search: str = "", sort_by: str = "data_entrada",
                       sort_dir: str = "desc", filters: dict | None = None) -> dict:
    """Query planilha_data with pagination, search, sort, and filters."""
    if sort_by not in _ALLOWED_SORT_COLUMNS:
        sort_by = "data_entrada"
    if sort_dir.lower() not in ("asc", "desc"):
        sort_dir = "desc"

    where_clauses = []
    params = []

    # Text search across multiple columns
    if search:
        search_conditions = [f"{col} LIKE ?" for col in _SEARCH_COLUMNS]
        where_clauses.append(f"({' OR '.join(search_conditions)})")
        for _ in _SEARCH_COLUMNS:
            params.append(f"%{search}%")

    # Exact-match filters
    _ALLOWED_FILTERS = {"gs_rh", "tipo_hemocomponente", "status_vencimento"}
    if filters:
        for col, val in filters.items():
            if col in _ALLOWED_FILTERS and val:
                where_clauses.append(f"{col} = ?")
                params.append(val)

        # Filter: vencidas (expired bags, dias < 0)
        if filters.get("vencidas"):
            where_clauses.append(
                "CAST(dias_antes_vencimento AS INTEGER) < 0"
            )
        else:
            # Range filter: dias_vencimento_max (bags expiring within N days)
            dias_max = filters.get("dias_vencimento_max")
            if dias_max is not None:
                try:
                    dias_max_int = int(dias_max)
                    where_clauses.append(
                        "CAST(dias_antes_vencimento AS INTEGER) >= 0 "
                        "AND CAST(dias_antes_vencimento AS INTEGER) <= ?"
                    )
                    params.append(dias_max_int)
                except (ValueError, TypeError):
                    pass

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    with get_db(db_path) as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) as total FROM planilha_data {where_sql}",
            params,
        ).fetchone()
        total = count_row["total"]

        offset = (page - 1) * per_page
        rows = conn.execute(
            f"SELECT * FROM planilha_data {where_sql} "
            f"ORDER BY {sort_by} {sort_dir} "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()

        return {
            "rows": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
