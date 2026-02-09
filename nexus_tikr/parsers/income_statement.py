"""Template A: TIKR_INCOME_STATEMENT parser."""

from __future__ import annotations

import logging
from typing import Any, Optional

import openpyxl

from nexus_tikr.constants import (
    INCOME_STATEMENT_LABELS,
    IS_POSITIONAL_LABELS,
)
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_income_statement(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> dict[str, dict[str, Any]]:
    """Parse Income Statement file using semantic label matching.

    Returns:
        Dict of output_field -> {period_label: value}
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    date_columns = file_info.date_columns
    ltm_col = file_info.ltm_col

    result: dict[str, dict[str, Any]] = {}
    mapped_rows: set[int] = set()

    # Handle positional labels first (% Margins, % Change YoY)
    positional_fields = set(IS_POSITIONAL_LABELS.keys())

    for field_name, (label_key, parse_type, impact) in INCOME_STATEMENT_LABELS.items():
        if field_name in positional_fields:
            # Use positional disambiguation
            pos_info = IS_POSITIONAL_LABELS[field_name]
            row = engine.find_positional_label(
                label_key=pos_info["label"],
                after_label=pos_info["after"],
                file_type="TIKR_INCOME_STATEMENT",
                section_anchor="",
                impact=impact,
            )
        else:
            # Special handling for EBIT-related disambiguation
            if field_name == "ebitda":
                # Find EBITDA first (before EBIT)
                row = engine.find_label(
                    label_key,
                    file_type="TIKR_INCOME_STATEMENT",
                    impact=impact,
                )
            elif label_key == "Operating Income":
                # Make sure we don't match "Operating Income As Reported"
                row = engine.find_label(
                    label_key,
                    file_type="TIKR_INCOME_STATEMENT",
                    impact=impact,
                )
            else:
                row = engine.find_label(
                    label_key,
                    file_type="TIKR_INCOME_STATEMENT",
                    impact=impact,
                )

        if row is not None:
            mapped_rows.add(row)
            values = engine.extract_row_values(row, date_columns, parse_type, ltm_col)
            result[field_name] = values

    # Track unmapped labels
    engine.get_all_unmapped_labels(mapped_rows)

    return result
