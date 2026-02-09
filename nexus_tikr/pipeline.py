"""Module 11: Execution Pipeline — orchestrates the complete NEXUS-TIKR processing."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Optional

import openpyxl

from nexus_tikr.adaptive_parser import parse_adaptive
from nexus_tikr.company_sector import populate_context
from nexus_tikr.derived_metrics import calculate_derived_metrics
from nexus_tikr.file_access import (
    FileAccessError,
    build_file_info,
    open_workbook,
)
from nexus_tikr.models import (
    FileTypeID,
    OutputMode,
    ParsedData,
    PipelineContext,
    PipelineStatus,
)
from nexus_tikr.output_builder import build_output, build_split_output, estimate_tokens
from nexus_tikr.parsers import (
    parse_actuals_forward,
    parse_balance_sheet,
    parse_cash_flow,
    parse_income_statement,
    parse_multiples,
    parse_quarterly_earnings,
    parse_ratios,
    parse_segments,
    parse_street_targets,
)
from nexus_tikr.quality import calculate_quality_score, run_anomaly_detection
from nexus_tikr.validation import run_validation

logger = logging.getLogger(__name__)


class PipelineAbortError(Exception):
    """Raised when pipeline must abort."""

    def __init__(self, module: str, message: str):
        self.module = module
        self.message = message
        super().__init__(f"Module {module}: {message}")


def run_pipeline(
    file_paths: list[str],
    output_dir: str = ".",
    user_ticker: Optional[str] = None,
    user_sector: Optional[str] = None,
    force: bool = False,
) -> tuple[PipelineContext, list[str]]:
    """Run the complete NEXUS-TIKR v2.1 processing pipeline.

    Args:
        file_paths: List of XLSX file paths to process.
        output_dir: Directory for output artifacts.
        user_ticker: Optional user-provided ticker.
        user_sector: Optional user-provided sector.

    Returns:
        (context, output_file_paths)
    """
    ctx = PipelineContext()
    output_files: list[str] = []

    try:
        # STEP 1 — ACCESS: Open all files
        logger.info("STEP 1: Accessing %d file(s)...", len(file_paths))
        file_infos = []
        for fp in file_paths:
            try:
                info = build_file_info(fp)
                file_infos.append(info)
            except FileAccessError as e:
                raise PipelineAbortError("0", f"File access failed — {e}")

        if not file_infos:
            raise PipelineAbortError("0", "No files provided")

        # STEP 2 — DETECT: Check that at least one file was detected
        logger.info("STEP 2: Detecting file types...")
        detected = [f for f in file_infos if f.file_type != FileTypeID.UNKNOWN]
        unknown = [f for f in file_infos if f.file_type == FileTypeID.UNKNOWN]
        low_confidence = [f for f in file_infos
                          if f.file_type != FileTypeID.UNKNOWN and f.detection_confidence < 0.90]

        if not detected and not unknown:
            raise PipelineAbortError("1", "No valid TiKR files detected")

        # STEP 3 — VALIDATE: File integrity (already done in build_file_info)
        logger.info("STEP 3: Validating file integrity...")

        # STEP 4 — CURRENCY: Detect and validate
        logger.info("STEP 4: Detecting currency...")
        error = populate_context(ctx, file_infos, user_ticker, user_sector)
        if error:
            if "CURRENCY_MISMATCH" in str(error):
                raise PipelineAbortError("2", f"Currency mismatch: {error}")
            if "Ticker mismatch" in str(error):
                raise PipelineAbortError("2", f"Ticker mismatch: {error}")

        # STEP 5 — SECTOR: Already populated
        logger.info("STEP 5: Sector = %s", ctx.sector.value)

        # STEP 6 — COLUMNS: Verify date structure
        logger.info("STEP 6: Checking date column structure...")
        has_dates = any(f.date_columns for f in file_infos
                        if f.file_type not in (FileTypeID.TIKR_STREET_TARGETS,
                                               FileTypeID.UNKNOWN))
        if not has_dates and detected:
            raise PipelineAbortError("1", "No date structure detected in any file")

        # STEP 7 — ESTIMATE: Token estimation
        logger.info("STEP 7: Estimating output size...")
        # Will be called after parsing

        # STEP 8 — PARSE: Apply Semantic Label Engine
        logger.info("STEP 8: Parsing files...")
        _parse_all_files(ctx, file_infos)

        # Handle unknown / low-confidence files via Module 9
        for f in unknown + low_confidence:
            logger.info("STEP 8b: Adaptive parsing for %s", f.filename)
            try:
                wb = open_workbook(f.filepath)
                ws = wb.active
                adaptive_result = parse_adaptive(ws, f)
                ctx.parsed_data.adaptive_data.append(adaptive_result)
                wb.close()
            except Exception as e:
                logger.warning("Adaptive parsing failed for %s: %s", f.filename, e)

        # Check label health
        logger.info("STEP 9: Checking label health (score: %.2f)...", ctx.label_health.health_score)
        if ctx.label_health.health_score < 0.70 and not force:
            raise PipelineAbortError(
                "3",
                f"Label health CRITICAL ({ctx.label_health.health_score:.2f})"
            )

        # STEP 10 — CALCULATE: Derived metrics
        logger.info("STEP 10: Calculating derived metrics...")
        calculate_derived_metrics(ctx)

        # STEP 11 — SCORE: Data quality
        logger.info("STEP 11: Scoring data quality...")
        calculate_quality_score(ctx)

        # STEP 12 — FLAG: Anomaly detection
        logger.info("STEP 12: Running anomaly detection...")
        run_anomaly_detection(ctx)

        # STEP 7 (deferred) — Token estimation
        estimate_tokens(ctx)

        # STEP 13 — ASSEMBLE + STEP 14 — CHUNK
        logger.info("STEP 13-14: Assembling output (mode: %s)...", ctx.output_mode.value)

        # STEP 15 — VALIDATE
        logger.info("STEP 15: Running validation...")
        run_validation(ctx)

        # STEP 17 — DELIVER
        logger.info("STEP 17: Delivering output...")
        output_files = _write_output(ctx, output_dir)

        ctx.pipeline_status = PipelineStatus.COMPLETED
        logger.info("Pipeline COMPLETED successfully.")

    except PipelineAbortError as e:
        ctx.pipeline_status = PipelineStatus.ABORTED
        ctx.abort_reason = f"{e.module}: {e.message}"
        logger.error("PIPELINE ABORTED at Module %s: %s", e.module, e.message)

    except Exception as e:
        ctx.pipeline_status = PipelineStatus.ABORTED
        ctx.abort_reason = f"Unexpected: {e}"
        logger.error("PIPELINE ABORTED unexpectedly: %s", e, exc_info=True)

    return ctx, output_files


def _parse_all_files(ctx: PipelineContext, file_infos: list) -> None:
    """Parse all detected files into the shared ParsedData structure."""
    data = ctx.parsed_data

    for f in file_infos:
        if f.file_type == FileTypeID.UNKNOWN:
            continue  # Handled separately via adaptive parser

        try:
            wb = open_workbook(f.filepath)
            ws = wb.active

            if f.file_type == FileTypeID.TIKR_INCOME_STATEMENT:
                data.income_statement = parse_income_statement(ws, f, ctx.label_health)

            elif f.file_type == FileTypeID.TIKR_BALANCE_SHEET:
                data.balance_sheet = parse_balance_sheet(ws, f, ctx.label_health)

            elif f.file_type == FileTypeID.TIKR_CASH_FLOW:
                data.cash_flow = parse_cash_flow(ws, f, ctx.label_health)

            elif f.file_type == FileTypeID.TIKR_RATIOS:
                ratios = parse_ratios(ws, f, ctx.label_health)
                data.ratios_returns = ratios.get("returns", {})
                data.ratios_margins = ratios.get("margins", {})
                data.ratios_efficiency = ratios.get("efficiency", {})
                data.ratios_liquidity = ratios.get("liquidity", {})
                data.ratios_solvency = ratios.get("solvency", {})
                data.ratios_per_share = ratios.get("per_share", {})
                data.valuation_trailing = ratios.get("trailing_valuation", {})
                data.valuation_forward = ratios.get("forward_valuation", {})

            elif f.file_type == FileTypeID.TIKR_SEGMENTS:
                biz, geo = parse_segments(ws, f, ctx.label_health)
                data.segments_business = biz
                data.segments_geographic = geo

            elif f.file_type == FileTypeID.TIKR_ACTUALS_FORWARD:
                af_data, ae_markers, cagr = parse_actuals_forward(ws, f, ctx.label_health)
                data.consensus_estimates = af_data
                data.consensus_ae_markers = ae_markers
                data.consensus_cagr = cagr

            elif f.file_type == FileTypeID.TIKR_MULTIPLES:
                mult_data, mult_range = parse_multiples(ws, f, ctx.label_health)
                data.multiples_historical = mult_data
                data.multiples_range = mult_range

            elif f.file_type == FileTypeID.TIKR_STREET_TARGETS:
                data.street_targets = parse_street_targets(ws, f, ctx.label_health)

            elif f.file_type == FileTypeID.TIKR_QUARTERLY_EARNINGS:
                # Get latest quarterly revenue from IS for cross-validation
                is_rev = None
                if data.income_statement:
                    rev_data = data.income_statement.get("total_revenues", {})
                    periods = sorted(k for k in rev_data.keys() if k != "LTM")
                    if periods:
                        is_rev = rev_data.get(periods[-1])
                        # Approximate quarterly revenue
                        if isinstance(is_rev, (int, float)):
                            is_rev = is_rev / 4

                s1, s2, s2_meta, fwd_groups, section_map = parse_quarterly_earnings(
                    ws, f, ctx.label_health, is_rev
                )
                data.quarterly_latest = s1
                data.beats_misses = s2
                data.beats_misses_meta = s2_meta
                data.forward_quarterly = fwd_groups
                ctx.qe_section_map = section_map
                ctx.qe_forward_groups = fwd_groups

            wb.close()

        except Exception as e:
            logger.error("Failed to parse %s (%s): %s", f.filename, f.file_type.value, e)
            ctx.notes.append(f"Parse failure for {f.filename}: {e}")


def _write_output(ctx: PipelineContext, output_dir: str) -> list[str]:
    """Write output artifact(s) to disk."""
    today = date.today().isoformat()
    ticker = ctx.ticker
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_files = []

    if ctx.output_mode == OutputMode.SPLIT:
        part_a, part_b = build_split_output(ctx)
        path_a = out_dir / f"{ticker}_tikr_core_{today}.md"
        path_a.write_text(part_a, encoding="utf-8")
        output_files.append(str(path_a))

        if part_b:
            path_b = out_dir / f"{ticker}_tikr_historical_{today}.md"
            path_b.write_text(part_b, encoding="utf-8")
            output_files.append(str(path_b))

    elif ctx.output_mode == OutputMode.COMPACT:
        content = build_output(ctx)
        path = out_dir / f"{ticker}_tikr_compact_{today}.md"
        path.write_text(content, encoding="utf-8")
        output_files.append(str(path))

    else:
        content = build_output(ctx)
        path = out_dir / f"{ticker}_tikr_{today}.md"
        path.write_text(content, encoding="utf-8")
        output_files.append(str(path))

    return output_files


def generate_italian_summary(ctx: PipelineContext) -> str:
    """Generate the Italian language summary (3-5 sentences)."""
    if ctx.pipeline_status == PipelineStatus.ABORTED:
        return (
            f"⚠️ PIPELINE INTERROTTA al {ctx.abort_reason}. "
            f"Nessun output generato per evitare dati corrotti o incompleti."
        )

    lines = []

    # Files processed
    n_files = len(ctx.file_types_processed)
    lines.append(
        f"Elaborati {n_files} file TiKR per {ctx.ticker} "
        f"({', '.join(ctx.file_types_processed)})."
    )

    # Quality
    quality_desc = "eccellente" if ctx.data_quality_score >= 0.90 else (
        "buona" if ctx.data_quality_score >= 0.70 else (
            "sufficiente" if ctx.data_quality_score >= 0.50 else "scarsa"
        )
    )
    lines.append(f"Qualità dei dati: {quality_desc} ({ctx.data_quality_score:.0%}).")

    # Key flags
    critical_count = sum(1 for f in ctx.flags if f.flag.value == "🔴")
    warning_count = sum(1 for f in ctx.flags if f.flag.value == "🟠")
    if critical_count > 0:
        lines.append(f"Rilevati {critical_count} segnali critici 🔴 e {warning_count} avvertimenti 🟠.")
    elif warning_count > 0:
        lines.append(f"Rilevati {warning_count} avvertimenti 🟠, nessun segnale critico.")
    else:
        lines.append("Nessun segnale critico rilevato.")

    # Label health warning
    if ctx.label_health.format_drift_warning:
        lines.append(
            "⚠️ ATTENZIONE: Rilevata possibile variazione nel formato dei file TiKR. "
            f"Health score: {ctx.label_health.health_score:.2f}."
        )

    # Output mode
    lines.append(f"Output generato in modalità {ctx.output_mode.value}.")

    return " ".join(lines)
