"""Module 2: Company & Sector Detection."""

from __future__ import annotations

import logging
import re
from typing import Optional

from nexus_tikr.constants import THRESHOLD_PROFILES
from nexus_tikr.models import FileInfo, PipelineContext, Sector, ThresholdProfile

logger = logging.getLogger(__name__)


def detect_ticker(files: list[FileInfo], user_ticker: Optional[str] = None) -> str:
    """Detect ticker from files or user input. Priority: user > filename > QE."""
    if user_ticker:
        return user_ticker.upper()

    tickers = set()
    for f in files:
        if f.ticker_from_file:
            tickers.add(f.ticker_from_file)

    if len(tickers) == 1:
        return tickers.pop()
    elif len(tickers) > 1:
        # Multiple tickers — return first but flag
        logger.warning("Multiple tickers detected: %s", tickers)
        return sorted(tickers)[0]

    return "UNKNOWN"


def validate_ticker_consistency(files: list[FileInfo]) -> Optional[str]:
    """Check all files reference the same ticker. Returns error message if mismatch."""
    tickers = set()
    for f in files:
        if f.ticker_from_file:
            tickers.add(f.ticker_from_file)

    if len(tickers) > 1:
        return (
            f"Ticker mismatch across files: {', '.join(sorted(tickers))}. "
            "Cannot merge data from different companies."
        )
    return None


def validate_currency_consistency(files: list[FileInfo]) -> Optional[str]:
    """Check all files use the same currency. Returns error message if mismatch."""
    currencies = set()
    for f in files:
        if f.currency:
            currencies.add(f.currency)

    if len(currencies) > 1:
        return (
            f"CURRENCY_MISMATCH: Files use different currencies: "
            f"{', '.join(sorted(currencies))}. Cannot merge numeric values."
        )
    return None


def detect_currency(files: list[FileInfo]) -> str:
    """Detect the common currency across files."""
    for f in files:
        if f.currency:
            return f.currency
    return "USD"  # Default


def detect_sector(user_sector: Optional[str] = None) -> Sector:
    """Detect sector from user input or inference."""
    if user_sector:
        user_lower = user_sector.lower().replace(" ", "_")
        for s in Sector:
            if s.value.lower().replace(" ", "_") == user_lower:
                return s
            if s.name.lower() == user_lower:
                return s
    return Sector.UNKNOWN


def get_threshold_profile(sector: Sector) -> ThresholdProfile:
    """Get threshold profile for the detected sector."""
    return THRESHOLD_PROFILES.get(sector, THRESHOLD_PROFILES[Sector.UNKNOWN])


def populate_context(
    ctx: PipelineContext,
    files: list[FileInfo],
    user_ticker: Optional[str] = None,
    user_sector: Optional[str] = None,
) -> Optional[str]:
    """Populate pipeline context from detected files.

    Returns error message if critical validation fails, None if OK.
    """
    ctx.files = files
    ctx.file_types_processed = [f.file_type.value for f in files if f.file_type.value != "UNKNOWN"]

    # Validate ticker consistency
    ticker_error = validate_ticker_consistency(files)
    if ticker_error:
        return ticker_error

    # Validate currency consistency
    currency_error = validate_currency_consistency(files)
    if currency_error:
        return currency_error

    ctx.ticker = detect_ticker(files, user_ticker)
    ctx.currency = detect_currency(files)
    ctx.sector = detect_sector(user_sector)
    ctx.threshold_profile = get_threshold_profile(ctx.sector)

    # Determine LTM availability
    ctx.ltm_available = any(f.ltm_available for f in files)

    # Determine fiscal years covered
    all_years = set()
    for f in files:
        all_years.update(f.fiscal_years)
    if all_years:
        sorted_years = sorted(all_years)
        ctx.fiscal_years_covered = f"{sorted_years[0]} to {sorted_years[-1]}"

    # Determine data date (latest fiscal date)
    if all_years:
        ctx.data_date = sorted(all_years)[-1]

    return None
