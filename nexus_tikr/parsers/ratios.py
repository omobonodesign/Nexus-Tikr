"""Template D: TIKR_RATIOS parser."""

from __future__ import annotations

import logging
from typing import Any

import openpyxl

from nexus_tikr.constants import (
    RATIOS_EFFICIENCY_LABELS,
    RATIOS_LIQUIDITY_LABELS,
    RATIOS_MARGINS_LABELS,
    RATIOS_PER_SHARE_LABELS,
    RATIOS_RETURNS_LABELS,
    RATIOS_SECTION_ANCHORS,
    RATIOS_SOLVENCY_LABELS,
    VALUATION_FORWARD_LABELS,
    VALUATION_TRAILING_LABELS,
)
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_ratios(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Parse Ratios file using semantic label matching with section anchors.

    Returns:
        Dict of section_name -> {field_name: {period: value}}
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    date_columns = file_info.date_columns
    ltm_col = file_info.ltm_col

    result: dict[str, dict[str, dict[str, Any]]] = {}
    mapped_rows: set[int] = set()

    # Define section -> labels mapping
    sections = [
        ("returns", RATIOS_SECTION_ANCHORS["returns"], RATIOS_RETURNS_LABELS),
        ("margins", RATIOS_SECTION_ANCHORS["margins"], RATIOS_MARGINS_LABELS),
        ("efficiency", RATIOS_SECTION_ANCHORS["efficiency"], RATIOS_EFFICIENCY_LABELS),
        ("liquidity", RATIOS_SECTION_ANCHORS["liquidity"], RATIOS_LIQUIDITY_LABELS),
        ("solvency", RATIOS_SECTION_ANCHORS["solvency"], RATIOS_SOLVENCY_LABELS),
        ("per_share", RATIOS_SECTION_ANCHORS["per_share"], RATIOS_PER_SHARE_LABELS),
        ("trailing_valuation", RATIOS_SECTION_ANCHORS["trailing_valuation"], VALUATION_TRAILING_LABELS),
        ("forward_valuation", RATIOS_SECTION_ANCHORS["forward_valuation"], VALUATION_FORWARD_LABELS),
    ]

    for section_name, anchor_texts, labels_dict in sections:
        section_data: dict[str, dict[str, Any]] = {}

        # Find section anchor
        anchor_row = engine.find_section_anchor(anchor_texts)
        if anchor_row is None:
            logger.debug("Section anchor not found for %s", section_name)
            continue

        # Find next section boundary
        next_anchor = engine.find_next_section_anchor(anchor_row)
        end_row = next_anchor - 1 if next_anchor else engine.max_row

        for field_name, (label_key, parse_type, impact) in labels_dict.items():
            row = engine.find_label(
                label_key,
                file_type="TIKR_RATIOS",
                section_anchor=section_name,
                impact=impact,
                start_row=anchor_row + 1,
                end_row=end_row,
            )
            if row is not None:
                mapped_rows.add(row)
                values = engine.extract_row_values(row, date_columns, parse_type, ltm_col)
                section_data[field_name] = values

        if section_data:
            result[section_name] = section_data

    engine.get_all_unmapped_labels(mapped_rows)
    return result
