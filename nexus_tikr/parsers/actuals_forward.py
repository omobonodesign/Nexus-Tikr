"""Template F: TIKR_ACTUALS_FORWARD parser."""

from __future__ import annotations

import logging
from typing import Any, Optional

import openpyxl

from nexus_tikr.constants import ACTUALS_FORWARD_LABELS, AF_MARGIN_METRICS, AF_YOY_METRICS
from nexus_tikr.file_access import detect_date_columns_actuals_forward
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_actuals_forward(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> tuple[dict[str, dict[str, Any]], dict[str, str], dict[str, Any]]:
    """Parse Actuals & Forward Estimates file.

    Returns:
        (data, ae_markers, cagr_data)
        data: dict of output_field -> {period: value}
        ae_markers: dict of period -> "A" or "E"
        cagr_data: dict of metric -> cagr_value
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    # Detect columns with A/E markers
    date_columns, ae_markers, cagr_col = detect_date_columns_actuals_forward(ws)
    file_info.date_columns = date_columns

    result: dict[str, dict[str, Any]] = {}
    cagr_data: dict[str, Any] = {}
    mapped_rows: set[int] = set()

    for field_name, (label_key, parse_type, impact) in ACTUALS_FORWARD_LABELS.items():
        row = engine.find_label(
            label_key,
            file_type="TIKR_ACTUALS_FORWARD",
            impact=impact,
        )
        if row is not None:
            mapped_rows.add(row)
            values = engine.extract_row_values(row, date_columns, parse_type)
            result[field_name] = values

            # Extract CAGR if available
            if cagr_col is not None:
                cagr_val = ws.cell(row=row, column=cagr_col).value
                if cagr_val is not None:
                    from nexus_tikr.label_engine import _parse_pct_decimal
                    cagr_data[field_name] = _parse_pct_decimal(cagr_val)

            # Look for associated YoY row
            if field_name in AF_YOY_METRICS:
                yoy_row = _find_associated_row(engine, row, "% Change YoY")
                if yoy_row is not None:
                    mapped_rows.add(yoy_row)
                    yoy_values = engine.extract_row_values(
                        yoy_row, date_columns, "pct_decimal"
                    )
                    result[f"{field_name}_yoy_pct"] = yoy_values

            # Look for associated margin row
            if field_name in AF_MARGIN_METRICS:
                margin_row = _find_associated_row(engine, row, "% Margins")
                if margin_row is None:
                    margin_row = _find_associated_row(engine, row, "% EBITDA Margins")
                if margin_row is not None:
                    mapped_rows.add(margin_row)
                    margin_values = engine.extract_row_values(
                        margin_row, date_columns, "pct_decimal"
                    )
                    result[f"{field_name}_margin_pct"] = margin_values

    engine.get_all_unmapped_labels(mapped_rows)
    return result, ae_markers, cagr_data


def _find_associated_row(
    engine: SemanticLabelEngine,
    anchor_row: int,
    label_key: str,
    max_distance: int = 3,
) -> Optional[int]:
    """Find an associated sub-row (YoY, margin) within a few rows of the anchor."""
    for offset in range(1, max_distance + 1):
        target_row = anchor_row + offset
        if target_row > engine.max_row:
            break
        raw = engine._col_a_cache.get(target_row)
        if raw and raw.strip() == label_key:
            return target_row
        if raw and raw.strip().lower() == label_key.lower():
            return target_row
    return None
