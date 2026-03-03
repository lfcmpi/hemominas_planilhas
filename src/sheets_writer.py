from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEETS_ID, SHEET_TAB_NAME
from src.field_mapper import LinhaPlanilha, montar_row

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


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


def _get_worksheet(client: gspread.Client) -> gspread.Worksheet:
    """Open the target spreadsheet and worksheet."""
    if not GOOGLE_SHEETS_ID:
        raise ValueError(
            "GOOGLE_SHEETS_ID not configured. Set it in .env file."
        )
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
    return spreadsheet.worksheet(SHEET_TAB_NAME)


def escrever_linhas(linhas: list[LinhaPlanilha]) -> dict:
    """Write mapped lines to Google Sheets (append only).

    Returns dict with linhas_inseridas count and mensagem.
    Phase 2: Added pre-write validation of target rows.
    """
    if not linhas:
        return {
            "linhas_inseridas": 0,
            "mensagem": "Nenhuma linha para inserir.",
        }

    client = _get_client()
    worksheet = _get_worksheet(client)

    # Find the next empty row after existing data
    all_values = worksheet.get_all_values()
    next_row = len(all_values) + 1

    # Phase 2: Validate that target rows are actually empty
    _validar_rows_destino(worksheet, next_row, len(linhas))

    # Build rows with correct row numbers for formulas
    rows = []
    for i, linha in enumerate(linhas):
        row_num = next_row + i
        rows.append(montar_row(linha, row_num))

    # Append all rows at once using USER_ENTERED so formulas are interpreted
    worksheet.append_rows(
        rows,
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS",
        table_range=f"A{next_row}",
    )

    return {
        "linhas_inseridas": len(rows),
        "mensagem": f"{len(rows)} linha(s) inserida(s) com sucesso na planilha.",
    }


def _validar_rows_destino(
    worksheet: gspread.Worksheet, start_row: int, num_linhas: int
) -> None:
    """Verify that target rows are empty before writing.

    Raises ValueError if any target row already contains data.
    """
    end_row = start_row + num_linhas - 1
    range_check = f"A{start_row}:A{end_row}"
    try:
        existing = worksheet.get(range_check)
        if existing and any(row for row in existing if row and row[0]):
            raise ValueError(
                f"Rows {start_row}-{end_row} ja contem dados. "
                "Abortando para evitar sobrescrita."
            )
    except ValueError:
        raise  # Re-raise our own validation error
    except Exception:
        # If range check fails (e.g., API error, new rows), proceed
        pass


def testar_conexao() -> dict:
    """Test connection to Google Sheets. Returns spreadsheet info."""
    client = _get_client()
    worksheet = _get_worksheet(client)
    all_values = worksheet.get_all_values()
    return {
        "titulo": worksheet.spreadsheet.title,
        "aba": worksheet.title,
        "total_linhas": len(all_values),
        "status": "OK",
    }
