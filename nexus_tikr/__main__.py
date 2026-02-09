"""CLI entry point for NEXUS-TIKR v2.1."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from nexus_tikr.pipeline import generate_italian_summary, run_pipeline


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="nexus-tikr",
        description="NEXUS-TIKR v2.1 — Financial Data Processor for TiKR XLSX exports",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more TiKR .xlsx files to process",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=".",
        help="Output directory for generated artifacts (default: current directory)",
    )
    parser.add_argument(
        "-t", "--ticker",
        default=None,
        help="Override ticker symbol (auto-detected from filenames if not provided)",
    )
    parser.add_argument(
        "-s", "--sector",
        default=None,
        help="Specify sector for threshold profiles "
             "(e.g., Utilities, Technology, Healthcare)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continue even if label health score is below threshold",
    )
    parser.add_argument(
        "--dump-debug",
        action="store_true",
        help="Dump raw parsed data to JSON file for debugging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.debug else (
        logging.INFO if args.verbose else logging.WARNING
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Run pipeline
    ctx, output_files = run_pipeline(
        file_paths=args.files,
        output_dir=args.output_dir,
        user_ticker=args.ticker,
        user_sector=args.sector,
        force=args.force,
    )

    # Print Italian summary
    summary = generate_italian_summary(ctx)
    print()
    print("=" * 60)
    print("NEXUS-TIKR v2.1 — Riepilogo")
    print("=" * 60)
    print()
    print(summary)
    print()

    # Print output files
    if output_files:
        print("File generati:")
        for f in output_files:
            print(f"  -> {f}")
        print()

    # Print key metrics
    if ctx.pipeline_status.value == "COMPLETED":
        print(f"Ticker:    {ctx.ticker}")
        print(f"Settore:   {ctx.sector.value}")
        print(f"Valuta:    {ctx.currency}")
        print(f"Qualita:   {ctx.data_quality_score:.0%}")
        print(f"Anomalie:  {ctx.anomalies_detected}")
        print(f"Validaz.:  {ctx.validation_status.value}")
        print(f"Label HS:  {ctx.label_health.health_score:.2f}")
        print(f"Output:    {ctx.output_mode.value}")
        print()

    # Print label health diagnostics if verbose/debug or pipeline aborted
    if args.verbose or args.debug or ctx.pipeline_status.value == "ABORTED":
        _print_diagnostics(ctx)

    # Dump debug data if requested
    if args.dump_debug:
        _dump_debug_json(ctx, args.output_dir)

    return 0 if ctx.pipeline_status.value == "COMPLETED" else 1


def _print_diagnostics(ctx) -> None:
    """Print detailed diagnostic information."""
    from nexus_tikr.models import MatchLevel

    lh = ctx.label_health
    print("-" * 60)
    print("DIAGNOSTICA LABEL HEALTH")
    print("-" * 60)
    print(f"Score: {lh.health_score:.2f}")
    print(f"  L1 (exact):       {lh.counts.get(MatchLevel.EXACT, 0)}")
    print(f"  L2 (case-ins):    {lh.counts.get(MatchLevel.CASE_INSENSITIVE, 0)}")
    print(f"  L3 (whitespace):  {lh.counts.get(MatchLevel.WHITESPACE_NORMALIZED, 0)}")
    print(f"  L4 (special):     {lh.counts.get(MatchLevel.SPECIAL_CHAR_NORMALIZED, 0)}")
    print(f"  L5 (alias):       {lh.counts.get(MatchLevel.ALIAS, 0)}")
    print(f"  Not found:        {lh.counts.get(MatchLevel.NOT_FOUND, 0)}")
    print(f"  Total expected:   {lh.total_expected}")
    print()

    # Show alias matches (recovered data)
    alias_matches = [m for m in lh.found_with_variant
                     if m.match_level == MatchLevel.ALIAS]
    if alias_matches:
        print(f"Label recuperate via ALIAS ({len(alias_matches)}):")
        for m in alias_matches[:30]:
            print(f"  \"{m.label_key}\" -> \"{m.source_label_raw.strip()}\" (riga {m.row_number})")
        if len(alias_matches) > 30:
            print(f"  ... e altre {len(alias_matches) - 30}")
        print()

    if lh.expected_not_found:
        print(f"Label NON trovate ({len(lh.expected_not_found)}):")
        for m in lh.expected_not_found[:30]:
            print(f"  [{m.impact.value:>9}] {m.file_type}: \"{m.label_key}\"")
        if len(lh.expected_not_found) > 30:
            print(f"  ... e altre {len(lh.expected_not_found) - 30}")
        print()

    # Show detected file types and date columns
    if ctx.files:
        print("File rilevati:")
        for f in ctx.files:
            n_dates = len(f.date_columns)
            ltm_str = " +LTM" if f.ltm_available else ""
            print(f"  {f.filename}")
            print(f"    tipo:    {f.file_type.value} (conf: {f.detection_confidence:.2f})")
            print(f"    righe:   {f.max_row}, colonne: {f.max_col}")
            print(f"    date:    {n_dates} colonne{ltm_str}")
            if f.date_columns:
                years = sorted(f.date_columns.keys())
                print(f"    periodi: {', '.join(years[:10])}")
        print()

    # Show parsed data statistics
    print("-" * 60)
    print("STATISTICHE DATI ESTRATTI")
    print("-" * 60)
    data = ctx.parsed_data
    _print_section_stats("Income Statement", data.income_statement)
    _print_section_stats("Balance Sheet", data.balance_sheet)
    _print_section_stats("Cash Flow", data.cash_flow)
    _print_section_stats("Ratios Returns", data.ratios_returns)
    _print_section_stats("Ratios Margins", data.ratios_margins)
    _print_section_stats("Ratios Efficiency", data.ratios_efficiency)
    _print_section_stats("Ratios Liquidity", data.ratios_liquidity)
    _print_section_stats("Ratios Solvency", data.ratios_solvency)
    _print_section_stats("Ratios Per Share", data.ratios_per_share)
    _print_section_stats("Valuation Trailing", data.valuation_trailing)
    _print_section_stats("Valuation Forward", data.valuation_forward)
    _print_section_stats("Multiples Historical", data.multiples_historical)
    _print_section_stats("Segments Business", data.segments_business)
    _print_section_stats("Segments Geographic", data.segments_geographic)
    _print_section_stats("Consensus Estimates", data.consensus_estimates)
    _print_section_stats("Quarterly Latest", data.quarterly_latest)
    _print_section_stats("Beats/Misses", data.beats_misses)
    _print_section_stats("Street Targets", data.street_targets)
    print()


def _print_section_stats(name: str, data: dict) -> None:
    """Print stats for a single data section."""
    if not data:
        print(f"  {name:30s}  VUOTO")
        return

    n_fields = len(data)
    # Count fields with actual non-null values
    n_with_values = 0
    total_values = 0
    for field_name, field_data in data.items():
        if isinstance(field_data, dict):
            non_null = sum(1 for v in field_data.values() if v is not None)
            if non_null > 0:
                n_with_values += 1
            total_values += non_null
        elif field_data is not None:
            n_with_values += 1
            total_values += 1

    print(f"  {name:30s}  {n_fields} campi, {n_with_values} con dati, {total_values} valori")


def _dump_debug_json(ctx, output_dir: str) -> None:
    """Dump complete parsed data and file info to JSON for debugging."""
    data = ctx.parsed_data
    out_dir = Path(output_dir)

    debug_data = {
        "ticker": ctx.ticker,
        "company": ctx.company,
        "currency": ctx.currency,
        "sector": ctx.sector.value,
        "pipeline_status": ctx.pipeline_status.value,
        "abort_reason": ctx.abort_reason,
        "label_health_score": ctx.label_health.health_score,
        "files": [],
        "parsed_data": {},
        "missing_labels": [],
        "alias_matches": [],
        "unmapped_labels": [],
    }

    # File info
    for f in ctx.files:
        debug_data["files"].append({
            "filename": f.filename,
            "file_type": f.file_type.value,
            "confidence": f.detection_confidence,
            "max_row": f.max_row,
            "max_col": f.max_col,
            "date_columns": f.date_columns,
            "ltm_col": f.ltm_col,
            "ltm_available": f.ltm_available,
            "fiscal_years": f.fiscal_years,
            "ticker": f.ticker_from_file,
            "currency": f.currency,
        })

    # Parsed data (convert to JSON-serializable)
    sections = {
        "income_statement": data.income_statement,
        "balance_sheet": data.balance_sheet,
        "cash_flow": data.cash_flow,
        "ratios_returns": data.ratios_returns,
        "ratios_margins": data.ratios_margins,
        "ratios_efficiency": data.ratios_efficiency,
        "ratios_liquidity": data.ratios_liquidity,
        "ratios_solvency": data.ratios_solvency,
        "ratios_per_share": data.ratios_per_share,
        "valuation_trailing": data.valuation_trailing,
        "valuation_forward": data.valuation_forward,
        "multiples_historical": data.multiples_historical,
        "segments_business": data.segments_business,
        "segments_geographic": data.segments_geographic,
        "consensus_estimates": data.consensus_estimates,
        "quarterly_latest": data.quarterly_latest,
        "beats_misses": data.beats_misses,
        "street_targets": data.street_targets,
    }
    for name, section in sections.items():
        debug_data["parsed_data"][name] = _make_json_safe(section)

    # Missing labels
    for m in ctx.label_health.expected_not_found:
        debug_data["missing_labels"].append({
            "label": m.label_key,
            "file_type": m.file_type,
            "section": m.section_anchor,
            "impact": m.impact.value,
        })

    # Alias matches
    from nexus_tikr.models import MatchLevel
    for m in ctx.label_health.found_with_variant:
        if m.match_level == MatchLevel.ALIAS:
            debug_data["alias_matches"].append({
                "expected": m.label_key,
                "found": m.source_label_raw.strip() if m.source_label_raw else "",
                "row": m.row_number,
            })

    # Unmapped labels
    for u in ctx.label_health.unmapped_source_labels:
        debug_data["unmapped_labels"].append({
            "label": u.source_label,
            "row": u.row_number,
            "section": u.section_context,
            "sample_values": [str(v) for v in u.sample_values],
        })

    debug_path = out_dir / f"{ctx.ticker}_debug_dump.json"
    debug_path.write_text(json.dumps(debug_data, indent=2, default=str), encoding="utf-8")
    print(f"Debug dump salvato: {debug_path}")


def _make_json_safe(obj):
    """Convert object to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(item) for item in obj]
    return str(obj)


if __name__ == "__main__":
    sys.exit(main())
