"""Template B: TIKR_BALANCE_SHEET parser."""

from __future__ import annotations

import logging
from typing import Any

import openpyxl

from nexus_tikr.constants import BALANCE_SHEET_LABELS
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_balance_sheet(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> dict[str, dict[str, Any]]:
    """Parse Balance Sheet file using semantic label matching."""
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    date_columns = file_info.date_columns
    ltm_col = file_info.ltm_col

    result: dict[str, dict[str, Any]] = {}
    mapped_rows: set[int] = set()

    for field_name, (label_key, parse_type, impact) in BALANCE_SHEET_LABELS.items():
        row = engine.find_label(
            label_key,
            file_type="TIKR_BALANCE_SHEET",
            impact=impact,
        )
        if row is not None:
            mapped_rows.add(row)
            values = engine.extract_row_values(row, date_columns, parse_type, ltm_col)
            result[field_name] = values

    engine.get_all_unmapped_labels(mapped_rows)
    return result
