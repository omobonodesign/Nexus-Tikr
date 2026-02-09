"""Module 5: Cross-File Derived Metrics."""

from __future__ import annotations

import logging
from typing import Any, Optional

from nexus_tikr.constants import DERIVED_THRESHOLDS, THRESHOLD_PROFILES
from nexus_tikr.models import Flag, FlagEntry, ParsedData, PipelineContext, Sector

logger = logging.getLogger(__name__)


def calculate_derived_metrics(ctx: PipelineContext) -> dict[str, Any]:
    """Calculate all cross-file derived metrics.

    Only calculates when ALL required source files are present.
    """
    data = ctx.parsed_data
    derived: dict[str, Any] = {}
    file_types = set(ctx.file_types_processed)

    has_is = "TIKR_INCOME_STATEMENT" in file_types
    has_bs = "TIKR_BALANCE_SHEET" in file_types
    has_cf = "TIKR_CASH_FLOW" in file_types
    has_af = "TIKR_ACTUALS_FORWARD" in file_types
    has_mult = "TIKR_MULTIPLES" in file_types
    has_st = "TIKR_STREET_TARGETS" in file_types
    has_qe = "TIKR_QUARTERLY_EARNINGS" in file_types

    # Get latest period values
    latest_period = _get_latest_period(data)

    # Module 5.1: IS + BS
    if has_is and has_bs:
        derived["leverage"] = _calc_leverage(data, latest_period, ctx)

    # Module 5.2: IS + CF
    if has_is and has_cf:
        derived["quality"] = _calc_quality(data, latest_period, ctx)

    # Module 5.3: BS + CF — included in quality if both present
    if has_cf:
        derived.setdefault("quality", {})
        _add_cf_metrics(data, latest_period, derived["quality"], ctx)

    # Module 5.5: Multiples ↔ Street Targets price cross-validation
    if has_mult and has_st:
        derived["price_cross_validation"] = _price_cross_validation(data, ctx)

    # Module 5.6: QE cross-validations
    if has_qe:
        derived["quarterly_signals"] = _qe_signals(data, ctx)

    # Valuation context
    if has_mult or has_st:
        derived["valuation_context"] = _valuation_context(data, ctx)

    # Shareholder returns
    derived["shareholder_returns"] = _shareholder_returns(data, latest_period, ctx)

    ctx.derived_metrics = derived
    return derived


def _get_latest_period(data: ParsedData) -> Optional[str]:
    """Get the latest fiscal year period key."""
    # Try income statement first
    if data.income_statement:
        first_metric = next(iter(data.income_statement.values()), {})
        periods = [k for k in first_metric.keys() if k != "LTM"]
        if periods:
            return sorted(periods)[-1]

    # Try balance sheet
    if data.balance_sheet:
        first_metric = next(iter(data.balance_sheet.values()), {})
        periods = [k for k in first_metric.keys() if k != "LTM"]
        if periods:
            return sorted(periods)[-1]

    return None


def _get_val(data_section: dict, field: str, period: str) -> Optional[float]:
    """Safely get a value from parsed data."""
    field_data = data_section.get(field, {})
    val = field_data.get(period) if period else None
    if val is None:
        # Try LTM
        val = field_data.get("LTM")
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _calc_leverage(data: ParsedData, period: Optional[str], ctx: PipelineContext) -> dict[str, Any]:
    """IS + BS leverage metrics."""
    result: dict[str, Any] = {}

    net_debt = _get_val(data.balance_sheet, "net_debt", period)
    ebitda = _get_val(data.income_statement, "ebitda", period)
    oi = _get_val(data.income_statement, "operating_income", period)
    int_exp = _get_val(data.income_statement, "interest_expense", period)
    total_de = _get_val(data.balance_sheet, "total_common_equity", period)
    total_debt_bs = _get_val(data.balance_sheet, "long_term_debt", period)
    current_debt = _get_val(data.balance_sheet, "current_debt", period)

    # Net Debt / EBITDA
    if net_debt is not None and ebitda is not None and ebitda != 0:
        nd_ebitda = round(net_debt / ebitda, 2)
        result["net_debt_to_ebitda"] = nd_ebitda
        _flag_metric(ctx, "net_debt_to_ebitda", nd_ebitda, "nd_ebitda")

    # Interest Coverage
    if oi is not None and int_exp is not None and int_exp != 0:
        ic = round(abs(oi / int_exp), 2)
        result["interest_coverage"] = ic
        _flag_metric(ctx, "interest_coverage", ic, "interest_coverage")

    # Debt to Equity
    total_debt = 0.0
    if total_debt_bs is not None:
        total_debt += abs(total_debt_bs)
    if current_debt is not None:
        total_debt += abs(current_debt)
    if total_de is not None and total_de != 0 and total_debt > 0:
        de = round(total_debt / abs(total_de), 2)
        result["debt_to_equity"] = de
        # Use sector thresholds
        tp = ctx.threshold_profile
        if tp and ctx.sector != Sector.FINANCIAL_SERVICES:
            if de > tp.de_crit:
                ctx.flags.append(FlagEntry("debt_to_equity", de, Flag.CRITICAL,
                                           f">{tp.de_crit} ({ctx.sector.value})",
                                           "Leverage above critical threshold"))
            elif de > tp.de_warn:
                ctx.flags.append(FlagEntry("debt_to_equity", de, Flag.WARNING,
                                           f">{tp.de_warn} ({ctx.sector.value})",
                                           "Leverage approaching critical"))
            else:
                ctx.flags.append(FlagEntry("debt_to_equity", de, Flag.POSITIVE,
                                           f"<{tp.de_warn} ({ctx.sector.value})",
                                           "Healthy leverage"))

    return result


def _calc_quality(data: ParsedData, period: Optional[str], ctx: PipelineContext) -> dict[str, Any]:
    """IS + CF quality metrics."""
    result: dict[str, Any] = {}

    cfo = _get_val(data.cash_flow, "cash_from_operations", period)
    ni = _get_val(data.income_statement, "net_income_to_common", period)
    fcf = _get_val(data.cash_flow, "free_cash_flow", period)
    capex = _get_val(data.cash_flow, "capital_expenditure", period)
    rev = _get_val(data.income_statement, "total_revenues", period)
    ebitda = _get_val(data.income_statement, "ebitda", period)

    # Earnings Quality (CFO / NI)
    if cfo is not None and ni is not None and ni != 0:
        eq = round(cfo / ni, 2)
        result["earnings_quality_cfo_ni"] = eq
        _flag_metric(ctx, "earnings_quality", eq, "earnings_quality")

    # FCF Conversion (FCF / NI)
    if fcf is not None and ni is not None and ni != 0:
        fc = round(fcf / ni, 2)
        result["fcf_conversion_fcf_ni"] = fc
        _flag_metric(ctx, "fcf_conversion", fc, "fcf_conversion")

    # CapEx Intensity
    if capex is not None and rev is not None and rev != 0:
        ci = round(abs(capex) / rev * 100, 1)
        result["capex_intensity_pct"] = ci

    # CFO-to-EBITDA
    if cfo is not None and ebitda is not None and ebitda != 0:
        result["cfo_to_ebitda"] = round(cfo / ebitda, 2)

    return result


def _add_cf_metrics(
    data: ParsedData,
    period: Optional[str],
    quality_dict: dict[str, Any],
    ctx: PipelineContext,
) -> None:
    """Add CF-only derived metrics."""
    div_paid = _get_val(data.cash_flow, "total_dividends_paid", period)
    cfo = _get_val(data.cash_flow, "cash_from_operations", period)

    if div_paid is not None and cfo is not None and cfo != 0:
        quality_dict["dividend_coverage_cfo"] = round(abs(cfo / div_paid), 2)


def _price_cross_validation(data: ParsedData, ctx: PipelineContext) -> dict[str, Any]:
    """Module 5.5: Cross-validate prices between Multiples and Street Targets."""
    result: dict[str, Any] = {"status": "NOT_APPLICABLE"}

    mult_data = data.multiples_historical
    st_data = data.street_targets

    mult_price_data = mult_data.get("price", {})
    st_price = st_data.get("price_close")

    if not mult_price_data or st_price is None:
        return result

    # Get latest multiples price
    sorted_dates = sorted(mult_price_data.keys())
    if not sorted_dates:
        return result

    latest_date = sorted_dates[-1]
    mult_price = mult_price_data.get(latest_date)

    if mult_price is None or not isinstance(mult_price, (int, float)):
        return result

    result["multiples_price"] = mult_price
    result["multiples_date"] = latest_date
    result["street_price"] = st_price
    result["street_date"] = ""  # Would need date from street targets file

    if st_price > 0:
        divergence = abs(mult_price - st_price) / st_price * 100
        result["divergence_pct"] = round(divergence, 2)

        if divergence < 2:
            result["status"] = "CONCORDANT"
            result["canonical_source"] = "Multiples"
            result["canonical_reason"] = "primary source"
        elif divergence < 10:
            result["status"] = "MINOR_DIVERGENCE"
            result["canonical_source"] = "Multiples"
            result["canonical_reason"] = "primary source"
            ctx.flags.append(FlagEntry(
                "price_cross_validation", divergence, Flag.WARNING,
                "2-10% divergence",
                f"Price in Multiples ({mult_price}) vs Street Targets ({st_price}): "
                f"{divergence:.1f}% gap"
            ))
        else:
            result["status"] = "MAJOR_DIVERGENCE"
            result["canonical_source"] = "Multiples"
            result["canonical_reason"] = "more recent"
            ctx.flags.append(FlagEntry(
                "price_cross_validation", divergence, Flag.CRITICAL,
                ">10% divergence",
                f"CRITICAL: Price divergence {divergence:.1f}% between Multiples and Street Targets"
            ))

    return result


def _qe_signals(data: ParsedData, ctx: PipelineContext) -> dict[str, Any]:
    """Module 5.6: Quarterly Earnings signals."""
    result: dict[str, Any] = {}

    track = data.beats_misses_meta.get("track_record", {})
    if track:
        result["management_credibility"] = track.get("management_credibility", "Unknown")

        # Latest quarter verdict
        qe_latest = data.quarterly_latest
        if qe_latest:
            rev_data = qe_latest.get("revenue", {})
            eps_data = qe_latest.get("adjusted_eps", {})
            rev_surp = rev_data.get("beat_miss")
            eps_surp = eps_data.get("beat_miss")

            beats = 0
            misses = 0
            for surp in (rev_surp, eps_surp):
                if isinstance(surp, (int, float)):
                    if surp > 0:
                        beats += 1
                    elif surp < 0:
                        misses += 1

            if beats > misses:
                result["latest_quarter_verdict"] = "Beat"
            elif misses > beats:
                result["latest_quarter_verdict"] = "Miss"
            else:
                result["latest_quarter_verdict"] = "In-Line"

        # Beat consistency
        eps_beat_str = track.get("adjusted_eps_beat_rate", "")
        if eps_beat_str:
            import re
            pct_match = re.search(r"\(([\d.]+)%\)", eps_beat_str)
            if pct_match:
                pct = float(pct_match.group(1))
                if pct >= 75:
                    result["beat_consistency"] = "Consistent Beater"
                elif pct >= 50:
                    result["beat_consistency"] = "Mixed"
                else:
                    result["beat_consistency"] = "Consistent Misser"

    return result


def _valuation_context(data: ParsedData, ctx: PipelineContext) -> dict[str, Any]:
    """Valuation context from multiples and street targets."""
    result: dict[str, Any] = {}

    # Historical PE avg vs current
    if data.multiples_historical:
        range_data = getattr(data, "multiples_range", {})
        # This would come from the multiples parser
        pass

    # Consensus implied upside from street targets
    st = data.street_targets
    if st:
        upside = st.get("consensus_upside_pct")
        if upside is not None:
            result["consensus_implied_upside"] = upside

    return result


def _shareholder_returns(data: ParsedData, period: Optional[str], ctx: PipelineContext) -> dict[str, Any]:
    """Shareholder return metrics."""
    result: dict[str, Any] = {}

    # Dividend yield from ratios or valuation
    if data.valuation_trailing:
        dy = _get_val(data.valuation_trailing, "trailing_div_yield_pct", period)
        if dy is not None:
            result["dividend_yield_pct"] = dy

    # Payout ratio
    is_data = data.income_statement
    payout = _get_val(is_data, "payout_ratio_pct", period)
    if payout is not None:
        result["payout_ratio_pct"] = payout

    return result


def _flag_metric(ctx: PipelineContext, name: str, value: float, threshold_key: str) -> None:
    """Apply flag to a derived metric using standard thresholds."""
    th = DERIVED_THRESHOLDS.get(threshold_key)
    if th is None:
        return

    green = th["green"]
    warn_low = th.get("warn_low", green)
    warn_high = th.get("warn_high", green)

    # Different logic for different metrics
    if threshold_key in ("nd_ebitda",):
        # Lower is better
        if value > warn_high:
            ctx.flags.append(FlagEntry(name, value, Flag.CRITICAL, f">{warn_high}", "Above critical"))
        elif value > warn_low:
            ctx.flags.append(FlagEntry(name, value, Flag.WARNING, f">{warn_low}", "Approaching critical"))
        elif value < green:
            ctx.flags.append(FlagEntry(name, value, Flag.POSITIVE, f"<{green}", "Healthy"))
    elif threshold_key in ("interest_coverage", "earnings_quality", "fcf_conversion"):
        # Higher is better
        if value < warn_low:
            ctx.flags.append(FlagEntry(name, value, Flag.CRITICAL, f"<{warn_low}", "Below critical"))
        elif value < warn_high:
            ctx.flags.append(FlagEntry(name, value, Flag.WARNING, f"<{warn_high}", "Below warning"))
        elif value >= green:
            ctx.flags.append(FlagEntry(name, value, Flag.POSITIVE, f">={green}", "Healthy"))
