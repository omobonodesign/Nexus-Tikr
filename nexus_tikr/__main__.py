"""CLI entry point for NEXUS-TIKR v2.1."""

from __future__ import annotations

import argparse
import logging
import sys

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
            print(f"  → {f}")
        print()

    # Print key metrics
    if ctx.pipeline_status.value == "COMPLETED":
        print(f"Ticker:    {ctx.ticker}")
        print(f"Settore:   {ctx.sector.value}")
        print(f"Valuta:    {ctx.currency}")
        print(f"Qualità:   {ctx.data_quality_score:.0%}")
        print(f"Anomalie:  {ctx.anomalies_detected}")
        print(f"Validaz.:  {ctx.validation_status.value}")
        print(f"Label HS:  {ctx.label_health.health_score:.2f}")
        print(f"Output:    {ctx.output_mode.value}")
        print()

    return 0 if ctx.pipeline_status.value == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
