"""Module 7: Adaptive Output Schema — builds hybrid YAML + Markdown output."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from nexus_tikr.models import (
    Flag,
    FlagEntry,
    ForwardGroup,
    LabelHealth,
    LabelImpact,
    MatchLevel,
    OutputMode,
    ParsedData,
    PipelineContext,
)

logger = logging.getLogger(__name__)


def estimate_tokens(ctx: PipelineContext) -> int:
    """Estimate output token count to decide chunking strategy."""
    data = ctx.parsed_data

    # Count fiscal years
    all_years = set()
    for f in ctx.files:
        all_years.update(f.fiscal_years)
    P = len(all_years)
    L = 1 if ctx.ltm_available else 0
    total_cols = P + L

    # Core tokens
    base = 800
    segments = 300 if (data.segments_business or data.segments_geographic) else 0
    consensus = len(data.consensus_estimates) * 80
    quarterly = 1200 if data.quarterly_latest else 0
    street = 300 if data.street_targets else 0
    derived = 500 if len(ctx.file_types_processed) > 1 else 0
    adaptive = 400 * len(data.adaptive_data)
    flags = 400
    core_estimate = base + segments + consensus + quarterly + street + derived + adaptive + flags

    # Historical tokens
    is_cols = 16
    bs_cols = 14
    cf_cols = 12
    ratios_cols = 40
    val_cols = 20
    tokens_per_fy = (is_cols + bs_cols + cf_cols + ratios_cols + val_cols) * 1.5
    historical_estimate = int(tokens_per_fy * total_cols + 1200)

    mult_dates = len(data.multiples_historical.get("price", {})) if "price" in data.multiples_historical else 0
    multiples_estimate = int(mult_dates * 25 * 1.5) if mult_dates > 0 else 0

    total = core_estimate + historical_estimate + multiples_estimate

    ctx.estimated_tokens = total
    ctx.core_tokens = core_estimate
    ctx.historical_tokens = historical_estimate + multiples_estimate

    # Determine output mode
    if total > 14000:
        ctx.output_mode = OutputMode.SPLIT
    elif total > 12000:
        ctx.output_mode = OutputMode.COMPACT
    else:
        ctx.output_mode = OutputMode.SINGLE

    return total


def build_output(ctx: PipelineContext) -> str:
    """Build the complete hybrid output document."""
    sections = []

    # 1. Meta block (YAML)
    sections.append(_build_meta(ctx))

    # 2. Snapshot (YAML)
    snapshot = _build_snapshot(ctx)
    if snapshot:
        sections.append(snapshot)

    # 3-5. Financial statements (Markdown tables)
    if ctx.parsed_data.income_statement:
        sections.append(_build_income_statement_table(ctx))
    if ctx.parsed_data.balance_sheet:
        sections.append(_build_balance_sheet_table(ctx))
    if ctx.parsed_data.cash_flow:
        sections.append(_build_cash_flow_table(ctx))

    # 6-10. Ratios (Markdown tables)
    if ctx.parsed_data.ratios_returns:
        sections.append(_build_ratio_table(ctx, "ratios_returns", "ratios_returns",
                                           _RETURNS_COLS))
    if ctx.parsed_data.ratios_margins:
        sections.append(_build_ratio_table(ctx, "ratios_margins", "ratios_margins",
                                           _MARGINS_COLS))
    if ctx.parsed_data.ratios_efficiency:
        sections.append(_build_ratio_table(ctx, "ratios_efficiency", "ratios_efficiency",
                                           _EFFICIENCY_COLS))
    if ctx.parsed_data.ratios_liquidity or ctx.parsed_data.ratios_solvency:
        sections.append(_build_liquidity_solvency_table(ctx))
    if ctx.parsed_data.ratios_per_share:
        sections.append(_build_ratio_table(ctx, "ratios_per_share", "ratios_per_share",
                                           _PER_SHARE_COLS))

    # 11-12. Valuation (Markdown tables)
    if ctx.parsed_data.valuation_trailing:
        sections.append(_build_ratio_table(ctx, "valuation_trailing", "valuation_trailing",
                                           _VAL_TRAILING_COLS))
    if ctx.parsed_data.valuation_forward:
        sections.append(_build_ratio_table(ctx, "valuation_forward", "valuation_forward",
                                           _VAL_FORWARD_COLS))

    # 13. Multiples historical
    if ctx.parsed_data.multiples_historical:
        sections.append(_build_multiples_table(ctx))

    # 14. Segments
    if ctx.parsed_data.segments_business:
        sections.append(_build_segments_table(ctx, "business"))
    if ctx.parsed_data.segments_geographic:
        sections.append(_build_segments_table(ctx, "geographic"))

    # 15. Consensus estimates
    if ctx.parsed_data.consensus_estimates:
        sections.append(_build_consensus_table(ctx))

    # 16. Quarterly earnings latest (YAML)
    if ctx.parsed_data.quarterly_latest:
        sections.append(_build_quarterly_latest(ctx))

    # 17. Beats & Misses
    if ctx.parsed_data.beats_misses:
        sections.append(_build_beats_misses(ctx))

    # 18. Forward quarterly
    if ctx.parsed_data.forward_quarterly:
        sections.append(_build_forward_quarterly(ctx))

    # 19. Street targets (YAML)
    if ctx.parsed_data.street_targets:
        sections.append(_build_street_targets(ctx))

    # 20. Derived metrics (YAML)
    if ctx.derived_metrics:
        sections.append(_build_derived_metrics(ctx))

    # 21. Adaptive data (YAML)
    if ctx.parsed_data.adaptive_data:
        sections.append(_build_adaptive_data(ctx))

    # 22. Flags (YAML)
    sections.append(_build_flags(ctx))

    return "\n\n".join(s for s in sections if s)


def build_split_output(ctx: PipelineContext) -> tuple[str, str]:
    """Build SPLIT mode output as two parts."""
    part_a = build_output(ctx)  # In a real implementation, would filter sections
    part_b = ""  # Historical sections only
    return part_a, part_b


# ============================================================
# Column definitions for Markdown tables
# ============================================================

_RETURNS_COLS = [
    ("roe_pct", "roe%"), ("roa_pct", "roa%"), ("roic_pct", "roic%"),
    ("normalized_roic_pct", "nroic%"),
]

_MARGINS_COLS = [
    ("gross_margin_pct", "gm%"), ("ebitda_margin_pct", "ebitda_m%"),
    ("ebit_margin_pct", "ebit_m%"), ("net_income_margin_pct", "nm%"),
    ("fcf_margin_pct", "fcf_m%"), ("capex_to_sales_pct", "capex/sales%"),
    ("capex_to_ebitda_pct", "capex/ebitda%"),
]

_EFFICIENCY_COLS = [
    ("asset_turnover", "at"), ("fixed_asset_turnover", "fat"),
    ("inventory_turnover", "invt"), ("receivables_turnover", "rect"),
    ("days_sales_outstanding", "dso"), ("days_inventory", "dio"),
    ("days_payable", "dpo"), ("cash_conversion_cycle", "ccc"),
]

_PER_SHARE_COLS = [
    ("sales_per_share", "rev_ps"), ("book_value_per_share", "bvps"),
    ("tangible_bv_per_share", "tbvps"), ("cfo_per_share", "cfo_ps"),
    ("fcf_per_share", "fcf_ps"), ("working_capital_per_share", "wc_ps"),
]

_VAL_TRAILING_COLS = [
    ("ev_revenue", "ev/rev"), ("ev_ebitda", "ev/ebitda"), ("ev_ebit", "ev/ebit"),
    ("ev_fcf", "ev/fcf"), ("pe_ratio", "pe"), ("normalized_pe", "pe_norm"),
    ("pb_ratio", "pb"), ("price_sales", "ps"), ("trailing_div_yield_pct", "dy%"),
    ("fcf_yield_pct", "fcfy%"), ("earning_yield_pct", "ey%"),
]

_VAL_FORWARD_COLS = [
    ("ev_fwd_revenue", "fwd_ev/rev"), ("ev_fwd_ebitda", "fwd_ev/ebitda"),
    ("ev_fwd_ebit", "fwd_ev/ebit"), ("fwd_pe", "fwd_pe"),
    ("fwd_div_yield_pct", "fwd_dy%"), ("fwd_earning_yield_pct", "fwd_ey%"),
    ("peg_ratio", "peg"),
]


# ============================================================
# Section builders
# ============================================================

def _build_meta(ctx: PipelineContext) -> str:
    """Build the meta YAML block."""
    lh = ctx.label_health
    lines = [
        "---",
        "# ══════════════════════════════════════════════════════════════",
        "# NEXUS-TIKR OUTPUT v2.1",
        "# ══════════════════════════════════════════════════════════════",
        "",
        "meta:",
        '  processor_version: "NEXUS-TIKR-2.1"',
        '  output_format: "hybrid (YAML + Markdown Tables)"',
        '  source: "TIKR"',
        f'  ticker: "{ctx.ticker}"',
        f'  company: "{ctx.company}"',
        f'  currency: "{ctx.currency}"',
        f'  sector: "{ctx.sector.value}"',
        f'  threshold_profile: "{ctx.sector.value}"',
        f'  units: "{ctx.units}"',
        f'  data_date: "{ctx.data_date}"',
        f"  ltm_available: {str(ctx.ltm_available).lower()}",
        "  file_types_processed:",
    ]
    for ft in ctx.file_types_processed:
        lines.append(f'    - "{ft}"')

    lines.append("  files_read:")
    for f in ctx.files:
        lines.extend([
            f'    - filename: "{f.filename}"',
            f"      rows: {f.max_row}",
            f"      columns: {f.max_col}",
            f'      type: "{f.file_type.value}"',
            f"      detection_confidence: {f.detection_confidence:.2f}",
        ])

    # Missing files
    all_types = {
        "TIKR_INCOME_STATEMENT", "TIKR_BALANCE_SHEET", "TIKR_CASH_FLOW",
        "TIKR_RATIOS", "TIKR_SEGMENTS", "TIKR_ACTUALS_FORWARD",
        "TIKR_MULTIPLES", "TIKR_STREET_TARGETS", "TIKR_QUARTERLY_EARNINGS",
    }
    missing = all_types - set(ctx.file_types_processed)
    if missing:
        lines.append("  files_missing_for_complete_analysis:")
        for m in sorted(missing):
            lines.append(f'    - "{m}"')

    lines.extend([
        f'  fiscal_years_covered: "{ctx.fiscal_years_covered}"',
        f'  output_mode: "{ctx.output_mode.value}"',
        f"  estimated_tokens: {ctx.estimated_tokens}",
        f"  data_quality_score: {ctx.data_quality_score:.2f}",
        f"  anomalies_detected: {ctx.anomalies_detected}",
        f'  validation_status: "{ctx.validation_status.value}"',
        f'  pipeline_status: "{ctx.pipeline_status.value}"',
        f"  abort_reason: {_yaml_val(ctx.abort_reason)}",
    ])

    # Label health
    lines.extend([
        "  label_health:",
        f"    expected_not_found:",
        f"      count: {len(lh.expected_not_found)}",
        f"      critical: {sum(1 for m in lh.expected_not_found if m.impact == LabelImpact.CRITICAL)}",
        f"      important: {sum(1 for m in lh.expected_not_found if m.impact == LabelImpact.IMPORTANT)}",
        f"      minor: {sum(1 for m in lh.expected_not_found if m.impact == LabelImpact.MINOR)}",
        f"    found_with_variant:",
        f"      count: {len(lh.found_with_variant)}",
        f"    unmapped_source_labels:",
        f"      count: {len(lh.unmapped_source_labels)}",
        f"    health_score: {lh.health_score:.2f}",
        f"    health_score_breakdown:",
        f"      L1: {lh.counts.get(MatchLevel.EXACT, 0)}",
        f"      L2: {lh.counts.get(MatchLevel.CASE_INSENSITIVE, 0)}",
        f"      L3: {lh.counts.get(MatchLevel.WHITESPACE_NORMALIZED, 0)}",
        f"      L4: {lh.counts.get(MatchLevel.SPECIAL_CHAR_NORMALIZED, 0)}",
        f"      L5_alias: {lh.counts.get(MatchLevel.ALIAS, 0)}",
        f"      not_found: {lh.counts.get(MatchLevel.NOT_FOUND, 0)}",
        f"    format_drift_warning: {str(lh.format_drift_warning).lower()}",
    ])

    # QE section map
    if ctx.qe_section_map:
        sm = ctx.qe_section_map
        lines.extend([
            "  qe_section_map:",
            f"    section_1: {{anchor_row: {sm.section_1_anchor or 'null'}, found: {str(sm.section_1_found).lower()}}}",
            f"    section_2: {{anchor_row: {sm.section_2_anchor or 'null'}, found: {str(sm.section_2_found).lower()}}}",
            f"    section_3: {{anchor_row: {sm.section_3_anchor or 'null'}, found: {str(sm.section_3_found).lower()}}}",
        ])

    # Forward groups
    if ctx.qe_forward_groups:
        lines.append("  qe_forward_groups:")
        for fg in ctx.qe_forward_groups:
            lines.append(
                f'    - {{metric: "{fg.metric}", confidence: "{fg.confidence}", '
                f"rows: [{fg.row_start}, {fg.row_end}]}}"
            )

    # Price cross-validation
    pcv = ctx.price_cross_validation
    if pcv:
        lines.append(f'  price_cross_validation:')
        lines.append(f'    status: "{pcv.get("status", "NOT_APPLICABLE")}"')

    # Checksums
    lines.append("  checksums:")
    for k, v in ctx.checksums.items():
        lines.append(f"    {k}: {_yaml_val(v)}")

    lines.append('  glossary_reference: "See OUTPUT FORMAT PROTOCOL > Column Header Glossary"')

    # Notes
    if ctx.notes:
        lines.append("  notes:")
        for note in ctx.notes:
            lines.append(f'    - "{note}"')

    lines.append("---")
    return "\n".join(lines)


def _build_snapshot(ctx: PipelineContext) -> str:
    """Build snapshot YAML block."""
    data = ctx.parsed_data

    # Get price from multiples or street targets
    price = None
    price_source = ""
    price_date = ""

    mult = data.multiples_historical
    if "price" in mult:
        sorted_dates = sorted(mult["price"].keys())
        if sorted_dates:
            latest = sorted_dates[-1]
            p = mult["price"].get(latest)
            if p is not None:
                price = p
                price_source = "Multiples"
                price_date = latest

    st = data.street_targets
    if price is None and st.get("price_close") is not None:
        price = st["price_close"]
        price_source = "Street Targets"

    mkt_cap = None
    if "market_cap_mm" in mult:
        sorted_dates = sorted(mult["market_cap_mm"].keys())
        if sorted_dates:
            mkt_cap = mult["market_cap_mm"].get(sorted_dates[-1])

    tev = None
    if "tev_mm" in mult:
        sorted_dates = sorted(mult["tev_mm"].keys())
        if sorted_dates:
            tev = mult["tev_mm"].get(sorted_dates[-1])

    shares = None
    bs = data.balance_sheet
    if "shares_outstanding" in bs:
        periods = sorted(k for k in bs["shares_outstanding"].keys() if k != "LTM")
        if periods:
            shares = bs["shares_outstanding"].get(periods[-1])

    net_debt = None
    if "net_debt" in bs:
        periods = sorted(k for k in bs["net_debt"].keys() if k != "LTM")
        if periods:
            net_debt = bs["net_debt"].get(periods[-1])

    if price is None and mkt_cap is None and shares is None:
        return ""

    lines = [
        "snapshot:",
        f"  price: {_yaml_val(price)}",
        f'  price_source: "{price_source}"',
        f'  price_date: "{price_date}"',
        f"  mkt_cap_M: {_yaml_val(mkt_cap)}",
        f"  enterprise_value_M: {_yaml_val(tev)}",
        f"  shares_outstanding_M: {_yaml_val(shares)}",
        f"  net_debt_M: {_yaml_val(net_debt)}",
        f'  currency: "{ctx.currency}"',
        f'  units: "Millions"',
    ]
    return "\n".join(lines)


def _build_income_statement_table(ctx: PipelineContext) -> str:
    """Build income_statement Markdown table."""
    data = ctx.parsed_data.income_statement
    periods = _get_sorted_periods(data)

    cols = [
        ("total_revenues", "rev_M"), ("revenue_yoy_pct", "rev_yoy%"),
        ("cost_of_goods_sold", "cogs_M"), ("gross_profit", "gp_M"),
        ("gross_margin_pct", "gm%"), ("operating_income", "oi_M"),
        ("operating_margin_pct", "om%"), ("interest_expense", "int_exp_M"),
        ("ebt_incl_unusual", "ebt_M"), ("income_tax", "tax_M"),
        ("effective_tax_rate", "eff_tax%"),
        ("net_income_to_common", "ni_M"), ("net_income_margin_pct", "nm%"),
        ("diluted_eps", "eps"), ("basic_eps", "eps_basic"),
        ("normalized_diluted_eps", "eps_norm"), ("dividends_per_share", "dps"),
        ("payout_ratio_pct", "payout%"), ("ebitda", "ebitda_M"),
        ("normalized_ebitda", "norm_ebitda_M"),
        ("depreciation_amortization", "da_M"),
        ("weighted_avg_diluted_shares", "shr_M"),
    ]

    # Filter to columns that have data
    active_cols = [(k, h) for k, h in cols if k in data]
    if not active_cols:
        return ""

    return _build_markdown_table(
        f"## income_statement (units: Millions, currency: {ctx.currency})",
        data, periods, active_cols,
    )


def _build_balance_sheet_table(ctx: PipelineContext) -> str:
    """Build balance_sheet Markdown table."""
    data = ctx.parsed_data.balance_sheet
    periods = _get_sorted_periods(data)

    cols = [
        ("cash_and_equivalents", "cash_M"), ("total_cash_and_st_inv", "cash_sti_M"),
        ("accounts_receivable", "ar_M"), ("total_inventory", "inv_M"),
        ("total_current_assets", "tca_M"), ("net_ppe", "net_ppe_M"),
        ("goodwill", "goodwill_M"), ("other_intangibles", "intang_M"),
        ("total_assets", "ta_M"), ("accounts_payable", "ap_M"),
        ("current_debt", "cur_debt_M"),
        ("total_current_liabilities", "tcl_M"), ("long_term_debt", "ltd_M"),
        ("total_liabilities", "tl_M"), ("total_common_equity", "tce_M"),
        ("total_equity", "te_M"), ("net_debt", "nd_M"),
        ("shares_outstanding", "shr_out_M"),
    ]

    active_cols = [(k, h) for k, h in cols if k in data]
    if not active_cols:
        return ""

    return _build_markdown_table(
        f"## balance_sheet (units: Millions, currency: {ctx.currency})",
        data, periods, active_cols,
    )


def _build_cash_flow_table(ctx: PipelineContext) -> str:
    """Build cash_flow Markdown table."""
    data = ctx.parsed_data.cash_flow
    periods = _get_sorted_periods(data)

    cols = [
        ("cash_from_operations", "cfo_M"), ("capital_expenditure", "capex_M"),
        ("free_cash_flow", "fcf_M"), ("fcf_margin_pct", "fcf_m%"),
        ("cash_acquisitions", "acq_M"), ("cash_from_investing", "cfi_M"),
        ("total_debt_issued", "debt_iss_M"), ("total_debt_repaid", "debt_rep_M"),
        ("total_dividends_paid", "div_paid_M"),
        ("repurchase_common_stock", "buyback_M"),
        ("cash_from_financing", "cff_M"), ("changes_in_cash", "net_chg_M"),
    ]

    active_cols = [(k, h) for k, h in cols if k in data]
    if not active_cols:
        return ""

    return _build_markdown_table(
        f"## cash_flow (units: Millions, currency: {ctx.currency})",
        data, periods, active_cols,
    )


def _build_ratio_table(
    ctx: PipelineContext,
    section_name: str,
    data_attr: str,
    col_defs: list[tuple[str, str]],
) -> str:
    """Build a generic ratio Markdown table."""
    data = getattr(ctx.parsed_data, data_attr, {})
    if not data:
        return ""
    periods = _get_sorted_periods(data)
    active_cols = [(k, h) for k, h in col_defs if k in data]
    if not active_cols:
        return ""

    return _build_markdown_table(f"## {section_name}", data, periods, active_cols)


def _build_liquidity_solvency_table(ctx: PipelineContext) -> str:
    """Build combined liquidity + solvency table."""
    liq = ctx.parsed_data.ratios_liquidity or {}
    sol = ctx.parsed_data.ratios_solvency or {}
    combined = {**liq, **sol}
    if not combined:
        return ""

    periods = _get_sorted_periods(combined)

    cols = [
        ("current_ratio", "cr"), ("quick_ratio", "qr"), ("cash_ratio", "cashr"),
        ("total_debt_to_equity", "d/e"), ("debt_to_assets", "d/a%"),
        ("equity_to_assets", "e/a%"), ("lt_debt_to_capital", "ltd/cap%"),
        ("ebit_interest_coverage", "ic"),
    ]
    active_cols = [(k, h) for k, h in cols if k in combined]
    if not active_cols:
        return ""

    return _build_markdown_table("## ratios_liquidity_solvency", combined, periods, active_cols)


def _build_multiples_table(ctx: PipelineContext) -> str:
    """Build multiples_historical Markdown table."""
    data = ctx.parsed_data.multiples_historical
    if not data:
        return ""

    # Get all dates from any metric
    all_dates: set[str] = set()
    for metric_data in data.values():
        if isinstance(metric_data, dict):
            all_dates.update(metric_data.keys())

    sorted_dates = sorted(all_dates)
    if not sorted_dates:
        return ""

    cols = [
        ("ntm_ev_ebitda", "ntm_ev/ebitda"), ("ntm_pe_normalized", "ntm_pe"),
        ("ntm_lfcf_yield", "ntm_lfcfy%"),
        ("ltm_ev_ebitda", "ltm_ev/ebitda"), ("ltm_pe_diluted", "ltm_pe"),
        ("ltm_pb", "ltm_pb"), ("ltm_div_yield", "ltm_dy%"),
        ("price", "price"), ("tev_mm", "tev_M"), ("market_cap_mm", "mcap_M"),
    ]

    active_cols = [(k, h) for k, h in cols if k in data]
    if not active_cols:
        return ""

    # Build table with date rows
    header = "| date | " + " | ".join(h for _, h in active_cols) + " |"
    separator = "|---" + "|---" * len(active_cols) + "|"

    rows = [header, separator]
    for d in sorted_dates:
        vals = [_fmt_val(data.get(k, {}).get(d)) for k, _ in active_cols]
        rows.append(f"| {d} | " + " | ".join(vals) + " |")

    # Add range summary
    range_data = ctx.parsed_data.multiples_range
    if range_data:
        rows.append("")
        rows.append("```yaml")
        rows.append("multiples_range:")
        for metric, stats in range_data.items():
            rows.append(f"  {metric}: {{min: {stats.get('min')}, max: {stats.get('max')}, "
                        f"avg: {stats.get('avg')}, current: {stats.get('current')}}}")
        rows.append("```")

    return "## multiples_historical\n\n" + "\n".join(rows)


def _build_segments_table(ctx: PipelineContext, seg_type: str) -> str:
    """Build segments Markdown table."""
    if seg_type == "business":
        data = ctx.parsed_data.segments_business
        title = f"## segments_business_revenue (units: Millions, currency: {ctx.currency})"
    else:
        data = ctx.parsed_data.segments_geographic
        title = f"## segments_geographic_revenue (units: Millions, currency: {ctx.currency})"

    if not data:
        return ""

    # Get periods from first segment
    first_seg = next(iter(data.values()))
    periods = sorted(k for k in first_seg.keys())

    # Calculate totals for pct_of_total
    totals: dict[str, float] = {}
    for period in periods:
        total = 0
        for seg_values in data.values():
            v = seg_values.get(period)
            if isinstance(v, (int, float)):
                total += v
        totals[period] = total

    header = "| segment | " + " | ".join(periods) + " | pct_of_total |"
    separator = "|---" + "|---" * (len(periods) + 1) + "|"

    rows = [header, separator]
    latest_period = periods[-1] if periods else None

    for seg_name, seg_values in data.items():
        vals = [_fmt_val(seg_values.get(p)) for p in periods]
        pct = ""
        if latest_period and totals.get(latest_period, 0) > 0:
            v = seg_values.get(latest_period)
            if isinstance(v, (int, float)):
                pct = f"{v / totals[latest_period] * 100:.1f}%"
        rows.append(f"| {seg_name} | " + " | ".join(vals) + f" | {pct} |")

    return title + "\n\n" + "\n".join(rows)


def _build_consensus_table(ctx: PipelineContext) -> str:
    """Build consensus_estimates Markdown table."""
    data = ctx.parsed_data.consensus_estimates
    ae_markers = ctx.parsed_data.consensus_ae_markers
    cagr = ctx.parsed_data.consensus_cagr

    if not data:
        return ""

    # Get periods
    all_periods: set[str] = set()
    for metric_data in data.values():
        if isinstance(metric_data, dict):
            all_periods.update(metric_data.keys())

    sorted_periods = sorted(all_periods)
    if not sorted_periods:
        return ""

    # Add A/E markers to column headers
    col_headers = []
    for p in sorted_periods:
        marker = ae_markers.get(p, "")
        if marker:
            col_headers.append(f"{marker}_{p}")
        else:
            col_headers.append(p)

    header = "| metric | " + " | ".join(col_headers) + " | CAGR |"
    separator = "|---" + "|---" * (len(sorted_periods) + 1) + "|"

    rows = [header, separator]
    for metric_name, metric_data in data.items():
        if not isinstance(metric_data, dict):
            continue
        vals = [_fmt_val(metric_data.get(p)) for p in sorted_periods]
        cagr_val = _fmt_val(cagr.get(metric_name))
        rows.append(f"| {metric_name} | " + " | ".join(vals) + f" | {cagr_val} |")

    return f"## consensus_estimates (units: Millions, currency: {ctx.currency})\n\n" + "\n".join(rows)


def _build_quarterly_latest(ctx: PipelineContext) -> str:
    """Build quarterly_earnings_latest YAML block."""
    data = ctx.parsed_data.quarterly_latest
    if not data:
        return ""

    lines = ["quarterly_earnings_latest:"]
    for metric_name, metric_data in data.items():
        if not isinstance(metric_data, dict):
            lines.append(f"  {metric_name}: {_yaml_val(metric_data)}")
            continue
        lines.append(f"  {metric_name}:")
        for k, v in metric_data.items():
            lines.append(f"    {k}: {_yaml_val(v)}")

    return "\n".join(lines)


def _build_beats_misses(ctx: PipelineContext) -> str:
    """Build beats_misses_history table and track_record YAML."""
    data = ctx.parsed_data.beats_misses
    meta = ctx.parsed_data.beats_misses_meta
    if not data:
        return ""

    sections = []

    # Simplified table for key metrics
    for metric_name in ("Revenue", "EBITDA", "Adjusted EPS"):
        metric = data.get(metric_name, {})
        estimated = metric.get("estimated", {})
        actual = metric.get("actual", {})
        surprise = metric.get("surprise_pct", {})

        if not estimated and not actual:
            continue

        quarters = sorted(set(list(estimated.keys()) + list(actual.keys())))
        if not quarters:
            continue

        header = f"| quarter | est | act | surp% |"
        sep = "|---|---|---|---|"
        rows = [f"### {metric_name}", "", header, sep]

        for q in quarters:
            e = _fmt_val(estimated.get(q))
            a = _fmt_val(actual.get(q))
            s = _fmt_val(surprise.get(q))
            rows.append(f"| {q} | {e} | {a} | {s} |")

        sections.append("\n".join(rows))

    # Track record YAML
    track = meta.get("track_record", {})
    if track:
        lines = ["```yaml", "track_record:"]
        for k, v in track.items():
            lines.append(f'  {k}: "{v}"' if isinstance(v, str) else f"  {k}: {v}")
        lines.append("```")
        sections.append("\n".join(lines))

    return "## beats_misses_history\n\n" + "\n\n".join(sections)


def _build_forward_quarterly(ctx: PipelineContext) -> str:
    """Build forward_quarterly_estimates table."""
    groups = ctx.parsed_data.forward_quarterly
    if not groups:
        return ""

    header = "| metric | quarter | num_a | avg_M | median_M | yoy% | qoq% | group_confidence |"
    sep = "|---|---|---|---|---|---|---|---|"
    rows = [header, sep]

    for fg in groups:
        for row_data in fg.rows_data:
            period_str = ""
            if row_data.get("period"):
                period_str = row_data["period"].strftime("%Y-%m-%d") if hasattr(row_data["period"], "strftime") else str(row_data["period"])
            elif row_data.get("period_raw"):
                period_str = row_data["period_raw"]

            analysts = _fmt_val(row_data.get("analysts"))
            avg = _fmt_val(row_data.get("average"))
            median = _fmt_val(row_data.get("median"))
            yoy = _fmt_val(row_data.get("yoy_pct"))
            qoq = _fmt_val(row_data.get("qoq_pct"))

            rows.append(
                f"| {fg.metric} | {period_str} | {analysts} | {avg} | "
                f"{median} | {yoy} | {qoq} | {fg.confidence} |"
            )

    # Derived summary
    lines = ["\n".join(rows)]

    # Calculate implied FY values
    derived_lines = ["", "```yaml", "forward_quarterly_derived:"]
    for fg in groups:
        if fg.confidence == "HIGH" and fg.metric in ("Revenue", "EBITDA"):
            vals = [r.get("average") for r in fg.rows_data[:4]
                    if r.get("average") is not None]
            if len(vals) == 4:
                implied = sum(vals)
                derived_lines.append(f"  implied_fy_{fg.metric.lower()}_M: {implied:.0f}")

    derived_lines.append("```")
    if len(derived_lines) > 3:
        lines.append("\n".join(derived_lines))

    return "## forward_quarterly_estimates\n\n" + "\n".join(lines)


def _build_street_targets(ctx: PipelineContext) -> str:
    """Build street_targets YAML block."""
    data = ctx.parsed_data.street_targets
    if not data:
        return ""

    lines = [
        "street_targets:",
        f"  current_price: {_yaml_val(data.get('price_close'))}",
        "  price_target:",
        f"    mean: {_yaml_val(data.get('target_mean'))}",
        f"    median: {_yaml_val(data.get('target_median'))}",
        f"    high: {_yaml_val(data.get('target_high'))}",
        f"    low: {_yaml_val(data.get('target_low'))}",
        f"    num_estimates: {_yaml_val(data.get('num_estimates'))}",
        f"    implied_upside_pct: {_yaml_val(data.get('consensus_upside_pct'))}",
        "  recommendations:",
        f"    total_analysts: {_yaml_val(data.get('total_analysts'))}",
        f"    buys: {_yaml_val(data.get('buys'))}",
        f"    outperforms: {_yaml_val(data.get('outperforms'))}",
        f"    holds: {_yaml_val(data.get('holds'))}",
        f"    underperforms: {_yaml_val(data.get('underperforms'))}",
        f"    sells: {_yaml_val(data.get('sells'))}",
        f"    bullish_pct: {_yaml_val(data.get('bullish_pct'))}",
        f"    bearish_pct: {_yaml_val(data.get('bearish_pct'))}",
        f'    consensus_label: "{data.get("consensus_label", "")}"',
    ]
    return "\n".join(lines)


def _build_derived_metrics(ctx: PipelineContext) -> str:
    """Build derived_metrics YAML block."""
    derived = ctx.derived_metrics
    if not derived:
        return ""

    lines = ["derived_metrics:"]

    for section_name, section_data in derived.items():
        if not isinstance(section_data, dict):
            continue
        lines.append(f"  {section_name}:")
        for k, v in section_data.items():
            if isinstance(v, dict):
                lines.append(f"    {k}:")
                for kk, vv in v.items():
                    lines.append(f"      {kk}: {_yaml_val(vv)}")
            else:
                lines.append(f"    {k}: {_yaml_val(v)}")

    return "\n".join(lines)


def _build_adaptive_data(ctx: PipelineContext) -> str:
    """Build adaptive_data YAML block."""
    ad = ctx.parsed_data.adaptive_data
    if not ad:
        return ""

    lines = ["adaptive_data:"]
    for item in ad:
        lines.append(f'  - source_file: "{item.get("source_file", "")}"')
        lines.append(f'    detected_category: "{item.get("detected_category", "F")}"')
        lines.append(f'    category_label: "{item.get("category_label", "")}"')
        lines.append(f'    confidence: "{item.get("confidence", "low")}"')
        # Simplified data output
        data = item.get("data", {})
        if data:
            lines.append("    data:")
            for k, v in list(data.items())[:20]:  # Limit output
                lines.append(f'      "{k}": {_yaml_val(v)}')

    return "\n".join(lines)


def _build_flags(ctx: PipelineContext) -> str:
    """Build flags YAML block."""
    flags = ctx.flags

    critical = [f for f in flags if f.flag == Flag.CRITICAL]
    warning = [f for f in flags if f.flag == Flag.WARNING]
    positive = [f for f in flags if f.flag == Flag.POSITIVE]
    neutral = [f for f in flags if f.flag == Flag.NEUTRAL]

    lines = [
        "flags:",
        f"  summary: {{🔴: {len(critical)}, 🟠: {len(warning)}, "
        f"🟢: {len(positive)}, ⚪: {len(neutral)}}}",
    ]

    if critical:
        lines.append("  critical:")
        for f in critical:
            lines.append(
                f'    - {{metric: "{f.metric}", value: {_yaml_val(f.value)}, '
                f'threshold: "{f.threshold}", note: "{f.note}"}}'
            )

    if warning:
        lines.append("  warning:")
        for f in warning:
            lines.append(
                f'    - {{metric: "{f.metric}", value: {_yaml_val(f.value)}, '
                f'threshold: "{f.threshold}", note: "{f.note}"}}'
            )

    if positive:
        lines.append("  positive:")
        for f in positive:
            lines.append(
                f'    - {{metric: "{f.metric}", value: {_yaml_val(f.value)}, '
                f'threshold: "{f.threshold}", note: "{f.note}"}}'
            )

    return "\n".join(lines)


# ============================================================
# Helpers
# ============================================================

def _get_sorted_periods(data: dict[str, dict]) -> list[str]:
    """Get sorted period keys from any data section."""
    all_periods: set[str] = set()
    for metric_data in data.values():
        if isinstance(metric_data, dict):
            all_periods.update(metric_data.keys())

    # Sort: years first, then LTM
    years = sorted(p for p in all_periods if p != "LTM")
    if "LTM" in all_periods:
        years.append("LTM")
    return years


def _build_markdown_table(
    title: str,
    data: dict[str, dict],
    periods: list[str],
    cols: list[tuple[str, str]],
) -> str:
    """Build a generic Markdown table from data dict."""
    header = "| year | " + " | ".join(h for _, h in cols) + " |"
    separator = "|---" + "|---" * len(cols) + "|"

    rows = [header, separator]
    for period in periods:
        vals = [_fmt_val(data.get(k, {}).get(period)) for k, _ in cols]
        rows.append(f"| {period} | " + " | ".join(vals) + " |")

    return title + "\n\n" + "\n".join(rows)


def _fmt_val(val: Any) -> str:
    """Format a value for Markdown table display."""
    if val is None:
        return "null"
    if isinstance(val, float):
        if abs(val) >= 1000:
            return f"{val:.0f}"
        elif abs(val) >= 10:
            return f"{val:.1f}"
        elif abs(val) >= 1:
            return f"{val:.2f}"
        else:
            return f"{val:.2f}"
    if isinstance(val, int):
        return str(val)
    return str(val)


def _yaml_val(val: Any) -> str:
    """Format a value for YAML output."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return str(val).lower()
    if isinstance(val, str):
        return f'"{val}"'
    if isinstance(val, float):
        if val == int(val) and abs(val) < 1e10:
            return str(int(val))
        return f"{val:.2f}"
    return str(val)
