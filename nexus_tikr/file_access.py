"""Module 0: File Access Protocol + Module 1: File Type Detection Engine."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import openpyxl

from nexus_tikr.constants import (
    ACTUALS_FORWARD_PATTERN,
    FILE_TYPE_PATTERNS,
    QE_R1_PATTERN,
    QE_R3_PATTERN,
)
from nexus_tikr.models import FileInfo, FileTypeID

logger = logging.getLogger(__name__)


class FileAccessError(Exception):
    """Raised when file access fails."""


class FileDetectionError(Exception):
    """Raised when file type detection fails."""


def validate_file(filepath: str) -> Path:
    """Module 0.2: Validate file exists and is .xlsx."""
    path = Path(filepath)
    if not path.exists():
        raise FileAccessError(f"File not found: {filepath}")
    if path.suffix.lower() != ".xlsx":
        raise FileAccessError(
            "Errore: NEXUS-TIKR v2.1 supporta esclusivamente file .xlsx. "
            "Il file caricato non è compatibile."
        )
    return path


def open_workbook(filepath: str) -> openpyxl.Workbook:
    """Module 0.1: Open XLSX file programmatically with openpyxl."""
    path = validate_file(filepath)
    try:
        wb = openpyxl.load_workbook(str(path), data_only=True)
        return wb
    except Exception as e:
        raise FileAccessError(f"Failed to open workbook {filepath}: {e}")


def detect_file_type(ws: openpyxl.worksheet.worksheet.Worksheet) -> tuple[FileTypeID, float]:
    """Module 1.2: Detect TiKR file type from worksheet content."""
    a1 = _safe_cell_str(ws, 1, 1)
    a2 = _safe_cell_str(ws, 2, 1)
    a3 = _safe_cell_str(ws, 3, 1)

    # Check standard patterns (A1-based)
    for type_id_str, pattern in FILE_TYPE_PATTERNS.items():
        if a1 and pattern.lower() in a1.lower():
            return FileTypeID[type_id_str], 0.99

    # Check Actuals & Forward (R2 based)
    if a2 and ACTUALS_FORWARD_PATTERN.lower() in a2.lower():
        return FileTypeID.TIKR_ACTUALS_FORWARD, 0.99

    # Check Quarterly Earnings (R1 + R3)
    if a1 and QE_R1_PATTERN.lower() in a1.lower():
        if a3 and QE_R3_PATTERN.lower() in a3.lower():
            return FileTypeID.TIKR_QUARTERLY_EARNINGS, 0.99
        return FileTypeID.TIKR_QUARTERLY_EARNINGS, 0.85

    # Scan first 20 rows for any known pattern
    for row in range(1, min(21, ws.max_row + 1)):
        for col in range(1, min(6, ws.max_column + 1)):
            val = _safe_cell_str(ws, row, col)
            if val and "TIKR.com" in val:
                # Partial match
                for type_id_str, pattern in FILE_TYPE_PATTERNS.items():
                    if pattern.split("|")[0].strip().lower() in val.lower():
                        return FileTypeID[type_id_str], 0.80
                if ACTUALS_FORWARD_PATTERN.split("|")[0].strip().lower() in val.lower():
                    return FileTypeID.TIKR_ACTUALS_FORWARD, 0.80
                if "Earnings" in val and "Quarterly" not in a1:
                    return FileTypeID.TIKR_QUARTERLY_EARNINGS, 0.70

    return FileTypeID.UNKNOWN, 0.0


def detect_date_columns(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_type: FileTypeID,
    header_row: int = 1,
) -> tuple[dict[str, int], Optional[int], bool]:
    """Module 1.4: Detect date/fiscal year columns and LTM column.

    Returns:
        (date_columns, ltm_col, ltm_available)
        date_columns: dict of year_label -> column_index
        ltm_col: column index of LTM column or None
        ltm_available: whether LTM column exists
    """
    date_columns: dict[str, int] = {}
    ltm_col: Optional[int] = None
    ltm_available = False

    for col in range(2, ws.max_column + 1):
        cell_val = ws.cell(row=header_row, column=col).value
        if cell_val is None:
            continue

        cell_str = str(cell_val).strip()

        # Check for LTM
        if "LTM" in cell_str.upper():
            ltm_col = col
            ltm_available = True
            continue

        # Try to parse as date
        dt = _parse_date_value(cell_val)
        if dt:
            year_label = str(dt.year)
            date_columns[year_label] = col
            continue

        # Try year-like patterns
        year_match = re.match(r"^(19|20)\d{2}$", cell_str)
        if year_match:
            date_columns[cell_str] = col

    return date_columns, ltm_col, ltm_available


def detect_date_columns_actuals_forward(
    ws: openpyxl.worksheet.worksheet.Worksheet,
) -> tuple[dict[str, int], dict[str, str], Optional[int]]:
    """Detect date columns for Actuals_Forward files.

    Returns:
        (date_columns, ae_markers, cagr_col)
        date_columns: dict of year_label -> column_index
        ae_markers: dict of year_label -> "A" or "E"
        cagr_col: column index of CAGR column or None
    """
    date_columns: dict[str, int] = {}
    ae_markers: dict[str, str] = {}
    cagr_col: Optional[int] = None

    # Row 2 has the "Actuals & Forward Estimates" header
    # Row 3 typically has date headers with A/E markers
    # Try row 2 first for column headers, then row 3
    header_row = 2
    marker_row = None

    # Find the row with A/E markers
    for r in range(2, min(6, ws.max_row + 1)):
        for c in range(2, ws.max_column + 1):
            val = _safe_cell_str(ws, r, c)
            if val and val.strip() in ("A", "E"):
                marker_row = r
                break
        if marker_row:
            break

    # Find date row (usually one row above marker row, or row 1)
    date_row = 1
    if marker_row and marker_row > 1:
        # Check the row above marker for dates
        for c in range(2, ws.max_column + 1):
            val = ws.cell(row=marker_row - 1, column=c).value
            dt = _parse_date_value(val)
            if dt:
                date_row = marker_row - 1
                break

    for col in range(2, ws.max_column + 1):
        cell_val = ws.cell(row=date_row, column=col).value
        if cell_val is None:
            continue

        cell_str = str(cell_val).strip()

        if cell_str.upper() == "CAGR":
            cagr_col = col
            continue

        dt = _parse_date_value(cell_val)
        if dt:
            year_label = str(dt.year)
            date_columns[year_label] = col

            # Check for A/E marker
            if marker_row:
                marker = _safe_cell_str(ws, marker_row, col)
                if marker and marker.strip() in ("A", "E"):
                    ae_markers[year_label] = marker.strip()

    return date_columns, ae_markers, cagr_col


def detect_multiples_date_columns(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    header_row: int = 1,
) -> dict[str, int]:
    """Detect date columns for Multiples file (datetime snapshots)."""
    date_columns: dict[str, int] = {}

    for col in range(2, ws.max_column + 1):
        cell_val = ws.cell(row=header_row, column=col).value
        if cell_val is None:
            continue
        dt = _parse_date_value(cell_val)
        if dt:
            date_label = dt.strftime("%Y-%m-%d")
            date_columns[date_label] = col

    return date_columns


def extract_ticker_from_filename(filename: str) -> Optional[str]:
    """Module 2.1: Extract ticker from TiKR filename pattern."""
    # Pattern: TIKR_-_{TICKER}_-_...
    match = re.match(r"TIKR_-_([A-Z0-9.]+)_-_", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Try simpler pattern: TIKR_{TICKER}_...
    match = re.match(r"TIKR_([A-Z0-9.]+)_", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def extract_ticker_from_qe(ws: openpyxl.worksheet.worksheet.Worksheet) -> Optional[str]:
    """Extract ticker from Quarterly Earnings R3 pattern."""
    a3 = _safe_cell_str(ws, 3, 1)
    if a3:
        match = re.match(r"^(\w+)\s+Q\d+\s+Earnings", a3)
        if match:
            return match.group(1).upper()
    return None


def extract_currency_from_header(ws: openpyxl.worksheet.worksheet.Worksheet) -> Optional[str]:
    """Module 2.2: Extract currency from file headers."""
    for row in range(1, 4):
        val = _safe_cell_str(ws, row, 1)
        if not val:
            continue
        # Pattern: "... in Millions of {CURRENCY} from ..."
        match = re.search(r"in Millions of\s+(\w[\w\s]*?)(?:\s+from|\s*\|)", val, re.IGNORECASE)
        if match:
            currency_name = match.group(1).strip()
            return _normalize_currency(currency_name)
        # Pattern: "... in Millions of {CURRENCY}"
        match = re.search(r"in Millions of\s+(\w[\w\s]+)", val, re.IGNORECASE)
        if match:
            currency_name = match.group(1).strip()
            return _normalize_currency(currency_name)
    return None


def build_file_info(filepath: str) -> FileInfo:
    """Build complete FileInfo for a single file."""
    path = validate_file(filepath)
    wb = open_workbook(filepath)
    ws = wb.active

    file_type, confidence = detect_file_type(ws)

    info = FileInfo(
        filename=path.name,
        filepath=filepath,
        file_type=file_type,
        detection_confidence=confidence,
        max_row=ws.max_row or 0,
        max_col=ws.max_column or 0,
    )

    # Extract ticker
    info.ticker_from_file = extract_ticker_from_filename(path.name)
    if not info.ticker_from_file and file_type == FileTypeID.TIKR_QUARTERLY_EARNINGS:
        info.ticker_from_file = extract_ticker_from_qe(ws)

    # Extract currency
    info.currency = extract_currency_from_header(ws)

    # Detect date columns
    if file_type == FileTypeID.TIKR_ACTUALS_FORWARD:
        date_cols, ae_markers, cagr_col = detect_date_columns_actuals_forward(ws)
        info.date_columns = date_cols
        info.fiscal_years = sorted(date_cols.keys())
    elif file_type == FileTypeID.TIKR_MULTIPLES:
        date_cols = detect_multiples_date_columns(ws)
        info.date_columns = date_cols
    elif file_type not in (FileTypeID.TIKR_STREET_TARGETS, FileTypeID.UNKNOWN):
        date_cols, ltm_col, ltm_avail = detect_date_columns(ws)
        info.date_columns = date_cols
        info.ltm_col = ltm_col
        info.ltm_available = ltm_avail
        info.fiscal_years = sorted(date_cols.keys())

    wb.close()
    return info


# ============================================================
# Internal helpers
# ============================================================

def _safe_cell_str(ws, row: int, col: int) -> Optional[str]:
    """Safely read a cell as string."""
    try:
        val = ws.cell(row=row, column=col).value
        if val is None:
            return None
        return str(val).strip()
    except Exception:
        return None


def _parse_date_value(val) -> Optional[datetime]:
    """Parse various date formats from TiKR cells."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    # Try DD/MM/YY
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _normalize_currency(name: str) -> str:
    """Normalize currency name to ISO code."""
    mapping = {
        "euro": "EUR",
        "euros": "EUR",
        "eur": "EUR",
        "us dollar": "USD",
        "us dollars": "USD",
        "usd": "USD",
        "british pound": "GBP",
        "pound sterling": "GBP",
        "gbp": "GBP",
        "japanese yen": "JPY",
        "jpy": "JPY",
        "swiss franc": "CHF",
        "chf": "CHF",
        "canadian dollar": "CAD",
        "cad": "CAD",
        "australian dollar": "AUD",
        "aud": "AUD",
        "swedish krona": "SEK",
        "sek": "SEK",
        "norwegian krone": "NOK",
        "nok": "NOK",
        "danish krone": "DKK",
        "dkk": "DKK",
        "chinese yuan": "CNY",
        "cny": "CNY",
        "hong kong dollar": "HKD",
        "hkd": "HKD",
        "indian rupee": "INR",
        "inr": "INR",
        "korean won": "KRW",
        "krw": "KRW",
        "brazilian real": "BRL",
        "brl": "BRL",
    }
    lower = name.lower().strip()
    return mapping.get(lower, name.upper())
