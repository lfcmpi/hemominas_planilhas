import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path


@dataclass
class BolsaExtraida:
    inst_coleta: str
    num_doacao: str
    componente_pdf: str
    cod_isbt: str
    seq: int
    volume: int
    abo: str
    rh: str
    validade: date


@dataclass
class Comprovante:
    numero: str
    data_emissao: datetime | None
    instituicao: str
    expedido_por: str
    data_expedicao: date | None
    bolsas: list[BolsaExtraida] = field(default_factory=list)
    total_bolsas_declarado: int = 0


def _normalizar_abo(raw: str) -> str:
    """Normalize ABO blood type from OCR output.

    OCR often misreads 'O' as digits (0, 6, 9, 16, etc.).
    Rule: any all-digit value must be 'O' — the only blood group
    that OCR confuses with numbers.
    """
    cleaned = re.sub(r"[()|\[\]]", "", raw).strip()
    if cleaned.isdigit():
        return "O"
    if cleaned.upper() in ("O", "A", "B", "AB"):
        return cleaned.upper()
    # Fallback: try to extract a letter
    match = re.search(r"[OoAaBb]", cleaned)
    if match:
        return match.group().upper()
    return cleaned.upper()


def _parse_date(text: str) -> date | None:
    """Parse date from DD/MM/YYYY format, tolerant of OCR spaces/separators."""
    match = re.search(r"(\d{1,2})\s*[/,.\-]\s*(\d{1,2})\s*[/,.\-]\s*(\d{4})", text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def _parse_datetime(text: str) -> datetime | None:
    """Parse datetime from DD/MM/YYYY HH:MM:SS format."""
    match = re.search(
        r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})", text
    )
    if match:
        try:
            return datetime(
                int(match.group(3)), int(match.group(2)), int(match.group(1)),
                int(match.group(4)), int(match.group(5)), int(match.group(6)),
            )
        except ValueError:
            return None
    return None


def _extrair_comprovante_numero(text: str) -> str:
    """Extract comprovante number from OCR text."""
    # Look for patterns like "Nº 1292305" or "[ne 4202305" or "Nº 4292307"
    match = re.search(r"[Nn][ºo°e]\s*(\d{5,8})", text)
    if match:
        return match.group(1)
    # Fallback: look for 7-digit number near "Comprovante" or "Expedição"
    match = re.search(r"(?:Comprovante|Expedi)[^\n]*?(\d{7})", text)
    if match:
        return match.group(1)
    return ""


def _normalizar_nome_responsavel(nome: str) -> str:
    """Normalize a person's name: clean whitespace and apply title case."""
    # Clean OCR artifacts and newlines
    nome = re.sub(r"[\n\r]+", " ", nome)
    # Collapse multiple spaces (including non-breaking)
    nome = nome.replace("\xa0", " ")
    nome = re.sub(r"\s+", " ", nome).strip()
    if not nome:
        return ""
    # Apply title case
    nome = nome.title()
    return nome


def _extrair_expedido_por(text: str) -> tuple[str, date | None]:
    """Extract 'Expedido por' name and date from OCR text.

    Phase 2: Enhanced with multiple patterns, title case normalization,
    and robust error handling.
    """
    try:
        name = ""
        # Try multiple patterns for name extraction
        name_patterns = [
            r"Expedido\s+por\s*:\s*(.+?)\s+em\s*:",
            r"Expedido\s+por\s*:\s*(.+?)(?:\s+\d{1,2}\s*[/,]\s*\d{1,2}\s*[/,]\s*\d{4})",
            r"Expedido\s+por\s*:\s*(.+?)$",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                name = _normalizar_nome_responsavel(match.group(1))
                if name:
                    break

        # Extract date after "Expedido por...em:" — may span lines
        exp_date = None
        date_match = re.search(
            r"Expedido\s+por\s*.+?em\s*:\s*(\d{1,2})\s*[/,]\s*(\d{1,2})\s*[/,]\s*(\d{4})",
            text, re.IGNORECASE | re.DOTALL
        )
        if date_match:
            try:
                exp_date = date(
                    int(date_match.group(3)),
                    int(date_match.group(2)),
                    int(date_match.group(1)),
                )
            except ValueError:
                pass

        # Fallback: if no date from Expedido, use Emissão date
        if exp_date is None:
            emissao_match = re.search(r"Emiss[ãa]o\s*:\s*(\d{2})/(\d{2})/(\d{4})", text)
            if emissao_match:
                try:
                    exp_date = date(
                        int(emissao_match.group(3)),
                        int(emissao_match.group(2)),
                        int(emissao_match.group(1)),
                    )
                except ValueError:
                    pass

        return name, exp_date
    except Exception:
        return "", None


def _extrair_total_declarado(text: str) -> int:
    """Extract declared total from 'Total de bolsa(s) expedida(s): N'."""
    match = re.search(r"Total\s+de\s+bolsa\(s\)\s+expedida\(s\)\s*[;:]\s*(\d+)", text)
    if match:
        return int(match.group(1))
    return 0


def _extrair_linhas_tabela(text: str) -> list[BolsaExtraida]:
    """Extract blood bag rows from the OCR text table."""
    bolsas = []
    lines = text.split("\n")

    # Regex for a table row: B#### NNNNNNNN | COMPONENT E####V## N NNN ABO RH DD/MM/YYYY
    row_pattern = re.compile(
        r"(B\d{4})\s+"           # inst_coleta
        r"(\d{8})\s+"            # num_doacao
        r"[|]?\s*"               # optional pipe from OCR
        r"(.+?)\s+"              # componente (greedy until ISBT code)
        r"(E\d{4}V[A-Z0-9]\d)\s+"  # cod_isbt (V00, VA0, VB0, etc.)
        r"(\d+)\s+"              # seq
        r"(\d{2,3})\s+"          # volume
        r"([A-Za-z0-9()|\[\]]+)\s+"  # abo (may have OCR artifacts)
        r"([PN])\s+"             # rh
        r"(\d{2}/\d{2}/\d{4})"  # validade
    )

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = row_pattern.search(line)
        if match:
            componente = match.group(3).strip()
            # Check next line for continuation (e.g., "Sist. Fechado")
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not row_pattern.search(next_line) and not next_line.startswith("Total"):
                    # Check if it's a component continuation (like "Sist. Fechado")
                    if re.match(r"^[A-Za-z]", next_line) and len(next_line) < 50:
                        componente += " " + next_line
                        i += 1

            validade = _parse_date(match.group(9))
            bolsa = BolsaExtraida(
                inst_coleta=match.group(1),
                num_doacao=match.group(2),
                componente_pdf=componente,
                cod_isbt=match.group(4),
                seq=int(match.group(5)),
                volume=int(match.group(6)),
                abo=_normalizar_abo(match.group(7)),
                rh=match.group(8),
                validade=validade,
            )
            bolsas.append(bolsa)
        i += 1

    return bolsas


def _extrair_instituicao(text: str) -> str:
    """Extract institution name from OCR text."""
    match = re.search(r"(HMOB[^\n]*)", text)
    if match:
        # Clean up the line
        inst = match.group(1).strip()
        # Remove trailing artifacts
        inst = re.sub(r"\s+[-–—].*$", "", inst)
        return inst
    return ""


def extrair_pdf(file_path: str) -> list[Comprovante]:
    """Extract comprovantes and bolsas from a Hemominas PDF.

    Uses OCR (tesseract) since these PDFs are image-based (scanned).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    images = convert_from_path(str(path), dpi=300)
    comprovantes = []

    for page_img in images:
        text = pytesseract.image_to_string(page_img, lang="por")
        if not text.strip():
            continue

        # Extract comprovante metadata
        numero = _extrair_comprovante_numero(text)
        data_emissao = _parse_datetime(text)
        instituicao = _extrair_instituicao(text)
        expedido_por, data_expedicao = _extrair_expedido_por(text)
        total_declarado = _extrair_total_declarado(text)

        # Extract table rows
        bolsas = _extrair_linhas_tabela(text)

        if bolsas:
            comprovante = Comprovante(
                numero=numero,
                data_emissao=data_emissao,
                instituicao=instituicao,
                expedido_por=expedido_por,
                data_expedicao=data_expedicao,
                bolsas=bolsas,
                total_bolsas_declarado=total_declarado,
            )
            comprovantes.append(comprovante)

    return comprovantes
