"""Module 6: Data Quality Scoring & Anomaly Detection."""

from __future__ import annotations

import logging
from typing import Any, Optional

from nexus_tikr.constants import CRITICAL_FIELDS
from nexus_tikr.models import Flag, FlagEntry, ParsedData, PipelineContext

logger = logging.getLogger(__name__)


def calculate_quality_score(ctx: PipelineContext) -> float:
    """Calculate data quality score based on critical field availability."""
    data = ctx.parsed_data
    total_critical = 0
    available_critical = 0

    file_types = set(ctx.file_types_processed)

    for file_type, fields in CRITICAL_FIELDS.items():
        if file_type not in file_types:
            continue

        section_data = _get_section_for_file_type(data, file_type)
        if section_data is None:
            total_critical += len(fields)
            continue

        for field in fields:
            total_critical += 1
            if field in section_data:
                values = section_data[field]
                if isinstance(values, dict):
                    # Check if at least one non-null value exists
                    if any(v is not None for v in values.values()):
                        available_critical += 1
                elif values is not None:
                    available_critical += 1

    if total_critical == 0:
        return 1.0

    score = available_critical / total_critical
    ctx.data_quality_score = round(score, 2)
    return score


def run_anomaly_detection(ctx: PipelineContext) -> int:
    """Run anomaly detection checks on parsed data.

    Returns number of anomalies detected.
    """
    data = ctx.parsed_data
    anomalies = 0

    # V3 checks from validation protocol
    anomalies += _check_sign_validation(data, ctx)
    anomalies += _check_magnitude(data, ctx)
    anomalies += _check_accounting_identity(data, ctx)

    ctx.anomalies_detected = anomalies
    return anomalies


def _get_section_for_file_type(data: ParsedData, file_type: str) -> Optional[dict]:
    """Map file type to its parsed data section."""
    mapping = {
        "TIKR_INCOME_STATEMENT": data.income_statement,
        "TIKR_BALANCE_SHEET": data.balance_sheet,
        "TIKR_CASH_FLOW": data.cash_flow,
        "TIKR_RATIOS": None,  # Ratios split into sub-sections
        "TIKR_ACTUALS_FORWARD": data.consensus_estimates,
        "TIKR_QUARTERLY_EARNINGS": data.quarterly_latest,
    }

    if file_type == "TIKR_RATIOS":
        # Combine all ratio sub-sections
        combined = {}
        for section in (data.ratios_returns, data.ratios_margins,
                        data.ratios_efficiency, data.ratios_liquidity,
                        data.ratios_solvency):
            combined.update(section)
        return combined if combined else None

    return mapping.get(file_type)


def _check_sign_validation(data: ParsedData, ctx: PipelineContext) -> int:
    """Check sign conventions: revenue positive, margins bounded, etc."""
    anomalies = 0

    # Revenue should be positive
    rev = data.income_statement.get("total_revenues", {})
    for period, val in rev.items():
        if isinstance(val, (int, float)) and val < 0:
            anomalies += 1
            ctx.flags.append(FlagEntry(
                f"revenue_{period}", val, Flag.CRITICAL,
                ">0", f"Negative revenue in {period}"
            ))

    return anomalies


def _check_magnitude(data: ParsedData, ctx: PipelineContext) -> int:
    """Check for extreme YoY changes (>500%)."""
    anomalies = 0

    # Check revenue YoY
    rev = data.income_statement.get("total_revenues", {})
    sorted_periods = sorted(k for k in rev.keys() if k != "LTM")

    for i in range(1, len(sorted_periods)):
        prev_val = rev.get(sorted_periods[i - 1])
        curr_val = rev.get(sorted_periods[i])
        if (isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float))
                and prev_val != 0):
            yoy = abs((curr_val - prev_val) / prev_val * 100)
            if yoy > 500:
                anomalies += 1
                ctx.notes.append(
                    f"ANOMALY: Revenue YoY change {yoy:.0f}% in {sorted_periods[i]}"
                )

    return anomalies


def _check_accounting_identity(data: ParsedData, ctx: PipelineContext) -> int:
    """Check Total Assets ≈ Total Liabilities + Total Equity (±2%)."""
    anomalies = 0

    ta = data.balance_sheet.get("total_assets", {})
    tl = data.balance_sheet.get("total_liabilities", {})
    te = data.balance_sheet.get("total_equity", {})

    for period in ta:
        ta_val = ta.get(period)
        tl_val = tl.get(period)
        te_val = te.get(period)

        if (isinstance(ta_val, (int, float)) and isinstance(tl_val, (int, float))
                and isinstance(te_val, (int, float)) and ta_val != 0):
            computed = tl_val + te_val
            diff_pct = abs(ta_val - computed) / abs(ta_val) * 100
            if diff_pct > 2.0:
                anomalies += 1
                ctx.notes.append(
                    f"ANOMALY: BS identity mismatch in {period}: "
                    f"TA={ta_val:.0f}, TL+TE={computed:.0f} (diff {diff_pct:.1f}%)"
                )

    return anomalies
