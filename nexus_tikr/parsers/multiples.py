"""Template G: TIKR_MULTIPLES parser."""

from __future__ import annotations

import logging
from typing import Any, Optional

import openpyxl

from nexus_tikr.constants import (
    MULTIPLES_FORWARD_LABELS,
    MULTIPLES_PRICE_FACTORS_LABELS,
    MULTIPLES_TRAILING_LABELS,
)
from nexus_tikr.file_access import detect_multiples_date_columns
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_multiples(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, float]]]:
    """Parse Multiples file with Forward/Trailing/Price Factors sections.

    Returns:
        (data, range_summary)
        data: dict of metric -> {date: value}
        range_summary: dict of key_metric -> {min, max, avg, current}
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    date_columns = detect_multiples_date_columns(ws)
    file_info.date_columns = date_columns

    result: dict[str, dict[str, Any]] = {}
    mapped_rows: set[int] = set()

    # Find section anchors
    forward_anchor = engine.find_section_anchor(["Forward Multiples"])
    trailing_anchor = engine.find_section_anchor(["Trailing Multiples"])
    price_anchor = engine.find_section_anchor(["Price Factors"])

    # Parse Forward Multiples section
    if forward_anchor is not None:
        end = (trailing_anchor - 1) if trailing_anchor else (
            (price_anchor - 1) if price_anchor else engine.max_row
        )
        for field_name, (label_key, parse_type, impact) in MULTIPLES_FORWARD_LABELS.items():
            row = engine.find_label(
                label_key,
                file_type="TIKR_MULTIPLES",
                section_anchor="Forward Multiples",
                impact=impact,
                start_row=forward_anchor + 1,
                end_row=end,
            )
            if row is not None:
                mapped_rows.add(row)
                values = engine.extract_row_values(row, date_columns, parse_type)
                result[field_name] = values

    # Parse Trailing Multiples section
    if trailing_anchor is not None:
        end = (price_anchor - 1) if price_anchor else engine.max_row
        for field_name, (label_key, parse_type, impact) in MULTIPLES_TRAILING_LABELS.items():
            row = engine.find_label(
                label_key,
                file_type="TIKR_MULTIPLES",
                section_anchor="Trailing Multiples",
                impact=impact,
                start_row=trailing_anchor + 1,
                end_row=end,
            )
            if row is not None:
                mapped_rows.add(row)
                values = engine.extract_row_values(row, date_columns, parse_type)
                result[field_name] = values

    # Parse Price Factors section
    if price_anchor is not None:
        for field_name, (label_key, parse_type, impact) in MULTIPLES_PRICE_FACTORS_LABELS.items():
            row = engine.find_label(
                label_key,
                file_type="TIKR_MULTIPLES",
                section_anchor="Price Factors",
                impact=impact,
                start_row=price_anchor + 1,
            )
            if row is not None:
                mapped_rows.add(row)
                values = engine.extract_row_values(row, date_columns, parse_type)
                result[field_name] = values

    # Calculate range summaries for key multiples
    range_summary = _calc_range_summaries(result, date_columns)

    engine.get_all_unmapped_labels(mapped_rows)
    return result, range_summary


def _calc_range_summaries(
    data: dict[str, dict[str, Any]],
    date_columns: dict[str, int],
) -> dict[str, dict[str, float]]:
    """Calculate min/max/avg/current for key multiples."""
    summary: dict[str, dict[str, float]] = {}

    key_metrics = [
        ("ev_ebitda_ntm", "ntm_ev_ebitda"),
        ("pe_ntm", "ntm_pe_normalized"),
        ("pb_ltm", "ltm_pb"),
        ("div_yield_ntm", "ntm_div_yield"),
        ("ev_ebitda_ltm", "ltm_ev_ebitda"),
        ("pe_ltm", "ltm_pe_diluted"),
    ]

    sorted_dates = sorted(date_columns.keys())

    for summary_key, data_key in key_metrics:
        if data_key not in data:
            continue

        values = data[data_key]
        nums = [v for v in values.values() if v is not None and isinstance(v, (int, float))]

        if not nums:
            continue

        current = None
        if sorted_dates:
            latest = sorted_dates[-1]
            current = values.get(latest)

        summary[summary_key] = {
            "min": min(nums),
            "max": max(nums),
            "avg": round(sum(nums) / len(nums), 2),
            "current": current if isinstance(current, (int, float)) else (nums[-1] if nums else None),
        }

    return summary
