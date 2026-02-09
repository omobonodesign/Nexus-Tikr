"""Template E: TIKR_SEGMENTS parser."""

from __future__ import annotations

import logging
from typing import Any, Optional

import openpyxl

from nexus_tikr.label_engine import SemanticLabelEngine, _parse_number
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_segments(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Parse Segments file. Structure is irregular with sub-sections.

    Returns:
        (business_segments, geographic_segments)
        Each: dict of segment_name -> {period: value}
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    date_columns = file_info.date_columns
    max_row = ws.max_row or 0

    # Find section dividers
    business_row = None
    geographic_row = None

    for row in range(1, max_row + 1):
        val = ws.cell(row=row, column=1).value
        if val is None:
            continue
        s = str(val).strip()
        if s.lower().startswith("business segment"):
            business_row = row
        elif s.lower().startswith("geographic segment"):
            geographic_row = row

    business_segments: dict[str, dict[str, Any]] = {}
    geographic_segments: dict[str, dict[str, Any]] = {}

    if business_row is not None:
        end = (geographic_row - 1) if geographic_row else max_row
        business_segments = _parse_segment_section(ws, business_row, end, date_columns)

    if geographic_row is not None:
        geographic_segments = _parse_segment_section(ws, geographic_row, max_row, date_columns)

    return business_segments, geographic_segments


def _parse_segment_section(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    start_row: int,
    end_row: int,
    date_columns: dict[str, int],
) -> dict[str, dict[str, Any]]:
    """Parse a single segment section (business or geographic).

    Extracts the first metric block (assumed to be Revenue).
    """
    result: dict[str, dict[str, Any]] = {}
    in_first_block = True

    for row in range(start_row + 1, end_row + 1):
        label = ws.cell(row=row, column=1).value
        if label is None:
            continue
        label_str = str(label).strip()
        if not label_str:
            continue

        # Skip section headers
        if label_str.endswith(":") or "TIKR.com" in label_str:
            continue

        # SegmentTotal marks end of a block
        if "SegmentTotal" in label_str or "Segment Total" in label_str:
            if not in_first_block:
                break
            in_first_block = False
            continue

        # Skip "% of Total" rows
        if label_str.startswith("% of Total") or label_str.startswith("% "):
            continue

        # Extract values for this segment
        values: dict[str, Any] = {}
        for period_label, col_idx in date_columns.items():
            raw = ws.cell(row=row, column=col_idx).value
            values[period_label] = _parse_number(raw)

        if any(v is not None for v in values.values()):
            result[label_str] = values

    return result
