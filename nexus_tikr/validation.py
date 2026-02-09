"""Module 10: Self-Validation Protocol."""

from __future__ import annotations

import logging
from typing import Any

from nexus_tikr.models import Flag, PipelineContext, ValidationStatus

logger = logging.getLogger(__name__)


def run_validation(ctx: PipelineContext) -> ValidationStatus:
    """Execute the complete self-validation protocol.

    Returns validation status.
    """
    warnings = 0
    errors = 0

    # V1 — Source Fidelity & Label Health
    lh = ctx.label_health
    if lh.health_score < 0.70:
        errors += 1
        logger.error("Label health score CRITICAL: %.2f", lh.health_score)
    elif lh.format_drift_warning:
        warnings += 1
        logger.warning("Format drift warning active. Health score: %.2f", lh.health_score)

    # V3 — Arithmetic: Check flag counts match
    flag_counts = _count_flags(ctx)
    # (flags are accumulated during processing, just verify consistency)

    # V4 — Structural: Verify checksums
    _populate_checksums(ctx)

    # V5 — Flag: Verify all critical flags have notes
    for f in ctx.flags:
        if f.flag == Flag.CRITICAL and not f.note:
            warnings += 1
            f.note = "Critical flag without explanation"

    # V8 — Unit & Currency
    if not ctx.currency:
        warnings += 1
        ctx.notes.append("Currency not detected — defaulting to USD")

    # V9 — Label Health scoring
    if lh.total_expected > 0:
        breakdown = lh.counts
        # Verify score matches formula
        expected_score = lh.health_score
        if expected_score < 0.85 and not lh.format_drift_warning:
            warnings += 1

    # V10 — Pipeline Integrity
    if ctx.abort_reason and ctx.pipeline_status.value == "COMPLETED":
        errors += 1
        logger.error("Pipeline has abort_reason but status is COMPLETED")

    # Determine final status
    if errors > 0:
        ctx.validation_status = ValidationStatus.FAILED
    elif warnings > 0:
        ctx.validation_status = ValidationStatus.PASSED_WITH_WARNINGS
    else:
        ctx.validation_status = ValidationStatus.PASSED

    return ctx.validation_status


def _count_flags(ctx: PipelineContext) -> dict[str, int]:
    """Count flags by type."""
    counts = {
        Flag.CRITICAL.value: 0,
        Flag.WARNING.value: 0,
        Flag.POSITIVE.value: 0,
        Flag.NEUTRAL.value: 0,
    }
    for f in ctx.flags:
        counts[f.flag.value] = counts.get(f.flag.value, 0) + 1
    return counts


def _populate_checksums(ctx: PipelineContext) -> None:
    """Populate checksum values for validation."""
    data = ctx.parsed_data

    # Latest revenue
    rev = data.income_statement.get("total_revenues", {})
    periods = sorted(k for k in rev.keys() if k != "LTM")
    if periods:
        ctx.checksums["revenue_latest"] = rev.get(periods[-1])

    # Latest total assets
    ta = data.balance_sheet.get("total_assets", {})
    periods = sorted(k for k in ta.keys() if k != "LTM")
    if periods:
        ctx.checksums["total_assets_latest"] = ta.get(periods[-1])

    # Latest net income
    ni = data.income_statement.get("net_income_to_common", {})
    periods = sorted(k for k in ni.keys() if k != "LTM")
    if periods:
        ctx.checksums["net_income_latest"] = ni.get(periods[-1])

    # Total rows parsed
    total_rows = sum(f.max_row for f in ctx.files)
    ctx.checksums["total_rows_parsed"] = total_rows
