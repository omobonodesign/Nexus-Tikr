"""Template H: TIKR_STREET_TARGETS parser."""

from __future__ import annotations

import logging
from typing import Any

import openpyxl

from nexus_tikr.constants import STREET_TARGETS_LABELS
from nexus_tikr.label_engine import SemanticLabelEngine
from nexus_tikr.models import FileInfo, LabelHealth

logger = logging.getLogger(__name__)


def parse_street_targets(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    file_info: FileInfo,
    label_health: LabelHealth,
) -> dict[str, Any]:
    """Parse Street Targets file.

    Returns:
        Dict with price targets and analyst recommendations.
    """
    engine = SemanticLabelEngine(ws)
    engine.label_health = label_health

    result: dict[str, Any] = {}
    mapped_rows: set[int] = set()

    # Street Targets typically has date columns too
    # Use the latest column for current values
    last_col = ws.max_column or 2

    for field_name, (label_key, parse_type, impact) in STREET_TARGETS_LABELS.items():
        row = engine.find_label(
            label_key,
            file_type="TIKR_STREET_TARGETS",
            impact=impact,
        )
        if row is not None:
            mapped_rows.add(row)
            # Get value from last data column
            raw_val = ws.cell(row=row, column=last_col).value
            from nexus_tikr.label_engine import _parse_number
            result[field_name] = _parse_number(raw_val)

    # Calculate derived values
    _calc_street_derived(result)

    engine.get_all_unmapped_labels(mapped_rows)
    return result


def _calc_street_derived(data: dict[str, Any]) -> None:
    """Calculate derived street target metrics."""
    buys = data.get("buys") or 0
    outperforms = data.get("outperforms") or 0
    holds = data.get("holds") or 0
    underperforms = data.get("underperforms") or 0
    sells = data.get("sells") or 0

    total = buys + outperforms + holds + underperforms + sells
    data["total_analysts"] = total if total > 0 else None

    if total > 0:
        data["bullish_pct"] = round((buys + outperforms) / total * 100, 1)
        data["bearish_pct"] = round((underperforms + sells) / total * 100, 1)

        # Weighted consensus score
        weighted = (buys * 5 + outperforms * 4 + holds * 3 +
                    underperforms * 2 + sells * 1) / total
        data["consensus_score"] = round(weighted, 2)

        if weighted >= 4.5:
            data["consensus_label"] = "Strong Buy"
        elif weighted >= 3.5:
            data["consensus_label"] = "Buy"
        elif weighted >= 2.5:
            data["consensus_label"] = "Hold"
        elif weighted >= 1.5:
            data["consensus_label"] = "Sell"
        else:
            data["consensus_label"] = "Strong Sell"
    else:
        data["bullish_pct"] = None
        data["bearish_pct"] = None
        data["consensus_label"] = None

    # Consensus upside
    price = data.get("price_close")
    target_mean = data.get("target_mean")
    if price and target_mean and price > 0:
        data["consensus_upside_pct"] = round((target_mean / price - 1) * 100, 1)
    else:
        data["consensus_upside_pct"] = None
