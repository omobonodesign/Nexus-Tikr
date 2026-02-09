"""Module 3: Semantic Label Engine — core parsing architecture."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import openpyxl

from nexus_tikr.constants import LABEL_ALIASES
from nexus_tikr.models import (
    LabelHealth,
    LabelImpact,
    LabelMatch,
    MatchLevel,
    MissingLabel,
    UnmappedLabel,
)

logger = logging.getLogger(__name__)


class SemanticLabelEngine:
    """Scans Column A for exact text labels using STRICT MATCHING HIERARCHY.

    NEVER uses hardcoded row numbers — always uses Column A text.
    Row numbers in templates are APPROXIMATE GUIDANCE ONLY.
    """

    def __init__(self, ws: openpyxl.worksheet.worksheet.Worksheet):
        self.ws = ws
        self.max_row = ws.max_row or 0
        self.max_col = ws.max_column or 0
        self._col_a_cache: dict[int, str] = {}
        self._build_col_a_cache()
        self.label_health = LabelHealth()

    def _build_col_a_cache(self) -> None:
        """Pre-read all Column A values for efficient searching."""
        for row in range(1, self.max_row + 1):
            val = self.ws.cell(row=row, column=1).value
            if val is not None:
                self._col_a_cache[row] = str(val)

    def find_label(
        self,
        label_key: str,
        file_type: str = "",
        section_anchor: str = "",
        impact: LabelImpact = LabelImpact.MINOR,
        start_row: int = 1,
        end_row: Optional[int] = None,
        after_row: Optional[int] = None,
    ) -> Optional[int]:
        """Find a row by its Column A label using STRICT MATCHING HIERARCHY.

        Args:
            label_key: The exact text to search for in Column A.
            file_type: File type for label health tracking.
            section_anchor: Section context for health tracking.
            impact: Impact level for health tracking.
            start_row: Start searching from this row.
            end_row: Stop searching at this row (inclusive).
            after_row: Only match rows after this row number.

        Returns:
            Row number if found, None if not found.
        """
        if end_row is None:
            end_row = self.max_row

        self.label_health.total_expected += 1

        # Try each matching level in order
        for level in (MatchLevel.EXACT, MatchLevel.CASE_INSENSITIVE,
                      MatchLevel.WHITESPACE_NORMALIZED, MatchLevel.SPECIAL_CHAR_NORMALIZED):
            row = self._match_at_level(label_key, level, start_row, end_row, after_row)
            if row is not None:
                self.label_health.counts[level] = self.label_health.counts.get(level, 0) + 1

                # Track variant matches
                if level in (MatchLevel.WHITESPACE_NORMALIZED, MatchLevel.SPECIAL_CHAR_NORMALIZED):
                    raw_label = self._col_a_cache.get(row, "")
                    self.label_health.found_with_variant.append(LabelMatch(
                        label_key=label_key,
                        source_label_raw=raw_label,
                        match_level=level,
                        row_number=row,
                        normalization_applied=level.name,
                    ))

                return row

        # Try alias matching as fallback (Level 5: ALIAS)
        row = self._match_alias(label_key, start_row, end_row, after_row)
        if row is not None:
            self.label_health.counts[MatchLevel.ALIAS] = (
                self.label_health.counts.get(MatchLevel.ALIAS, 0) + 1
            )
            raw_label = self._col_a_cache.get(row, "")
            self.label_health.found_with_variant.append(LabelMatch(
                label_key=label_key,
                source_label_raw=raw_label,
                match_level=MatchLevel.ALIAS,
                row_number=row,
                normalization_applied=f"ALIAS: {raw_label.strip()}",
            ))
            logger.debug("Alias match: '%s' -> '%s' at row %d", label_key, raw_label.strip(), row)
            return row

        # Not found
        self.label_health.counts[MatchLevel.NOT_FOUND] = (
            self.label_health.counts.get(MatchLevel.NOT_FOUND, 0) + 1
        )
        self.label_health.expected_not_found.append(MissingLabel(
            label_key=label_key,
            file_type=file_type,
            section_anchor=section_anchor,
            impact=impact,
        ))
        return None

    def find_positional_label(
        self,
        label_key: str,
        after_label: str,
        file_type: str = "",
        section_anchor: str = "",
        impact: LabelImpact = LabelImpact.MINOR,
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> Optional[int]:
        """Find a repeated label that appears after a specific anchor label.

        Used for disambiguating repeated labels like "% Margins" and "% Change YoY".
        """
        if end_row is None:
            end_row = self.max_row

        # First find the anchor label via standard matching
        anchor_row = self._match_at_level(after_label, MatchLevel.EXACT, start_row, end_row)
        if anchor_row is None:
            anchor_row = self._match_at_level(after_label, MatchLevel.CASE_INSENSITIVE, start_row, end_row)
        if anchor_row is None:
            anchor_row = self._match_at_level(after_label, MatchLevel.WHITESPACE_NORMALIZED, start_row, end_row)
        if anchor_row is None:
            anchor_row = self._match_at_level(after_label, MatchLevel.SPECIAL_CHAR_NORMALIZED, start_row, end_row)
        # Try aliases for the anchor label
        if anchor_row is None:
            anchor_row = self._match_alias(after_label, start_row, end_row)

        if anchor_row is None:
            # Anchor not found — can't position the label
            self.label_health.total_expected += 1
            self.label_health.counts[MatchLevel.NOT_FOUND] = (
                self.label_health.counts.get(MatchLevel.NOT_FOUND, 0) + 1
            )
            self.label_health.expected_not_found.append(MissingLabel(
                label_key=f"{label_key} (after {after_label})",
                file_type=file_type,
                section_anchor=section_anchor,
                impact=impact,
            ))
            return None

        # Now find the target label after the anchor
        return self.find_label(
            label_key,
            file_type=file_type,
            section_anchor=section_anchor,
            impact=impact,
            start_row=anchor_row + 1,
            end_row=min(anchor_row + 5, end_row),  # Look within 5 rows
            after_row=anchor_row,
        )

    def find_section_anchor(
        self,
        anchor_texts: list[str],
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> Optional[int]:
        """Find a section header row (e.g., 'Return Ratios:').

        Tries exact match, case-insensitive, and also matches
        with/without trailing colon for flexibility.
        """
        if end_row is None:
            end_row = self.max_row

        for anchor_text in anchor_texts:
            for row in range(start_row, end_row + 1):
                raw = self._col_a_cache.get(row)
                if raw is None:
                    continue
                stripped = raw.strip()
                # Exact or case-insensitive
                if stripped == anchor_text or stripped.lower() == anchor_text.lower():
                    return row
                # Try without trailing colon (source has colon, anchor doesn't or vice versa)
                stripped_no_colon = stripped.rstrip(":")
                anchor_no_colon = anchor_text.rstrip(":")
                if (stripped_no_colon.lower() == anchor_no_colon.lower()
                        and stripped_no_colon):
                    return row
        return None

    def find_next_section_anchor(
        self,
        after_row: int,
        end_row: Optional[int] = None,
    ) -> Optional[int]:
        """Find the next section header (ending with ':') after a given row."""
        if end_row is None:
            end_row = self.max_row

        for row in range(after_row + 1, end_row + 1):
            raw = self._col_a_cache.get(row)
            if raw and raw.strip().endswith(":"):
                return row
        return None

    def extract_row_values(
        self,
        row: int,
        data_columns: dict[str, int],
        parse_type: str = "number",
        ltm_col: Optional[int] = None,
    ) -> dict[str, Any]:
        """Extract values from a row across all date columns.

        Args:
            row: The row number to extract from.
            data_columns: Dict of period_label -> column_index.
            parse_type: How to parse values ("number", "pct_decimal", "string_multiple", "bps").
            ltm_col: Optional LTM column index.

        Returns:
            Dict of period_label -> parsed_value.
        """
        result = {}
        for label, col_idx in data_columns.items():
            raw_val = self.ws.cell(row=row, column=col_idx).value
            result[label] = self._parse_value(raw_val, parse_type)

        if ltm_col is not None:
            raw_val = self.ws.cell(row=row, column=ltm_col).value
            result["LTM"] = self._parse_value(raw_val, parse_type)

        return result

    def get_all_unmapped_labels(
        self,
        mapped_rows: set[int],
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> list[UnmappedLabel]:
        """Find labels in Column A that weren't matched by any template."""
        if end_row is None:
            end_row = self.max_row

        unmapped = []
        current_section = ""

        for row in range(start_row, end_row + 1):
            raw = self._col_a_cache.get(row)
            if raw is None:
                continue

            stripped = raw.strip()
            if not stripped:
                continue

            # Track section context
            if stripped.endswith(":"):
                current_section = stripped
                continue

            if row in mapped_rows:
                continue

            # Skip header rows and non-metric labels
            if "TIKR.com" in stripped:
                continue

            # Collect sample values
            samples = []
            for col in range(2, min(5, self.max_col + 1)):
                val = self.ws.cell(row=row, column=col).value
                if val is not None:
                    samples.append(val)

            if samples:
                unmapped.append(UnmappedLabel(
                    source_label=stripped,
                    row_number=row,
                    section_context=current_section,
                    sample_values=samples[:3],
                ))

        self.label_health.unmapped_source_labels = unmapped
        return unmapped

    # ============================================================
    # Internal matching methods
    # ============================================================

    def _match_at_level(
        self,
        label_key: str,
        level: MatchLevel,
        start_row: int,
        end_row: int,
        after_row: Optional[int] = None,
    ) -> Optional[int]:
        """Try to match label_key at a specific matching level."""
        for row in range(start_row, end_row + 1):
            if after_row is not None and row <= after_row:
                continue

            raw = self._col_a_cache.get(row)
            if raw is None:
                continue

            if self._matches(raw, label_key, level):
                return row
        return None

    def _match_alias(
        self,
        label_key: str,
        start_row: int,
        end_row: int,
        after_row: Optional[int] = None,
    ) -> Optional[int]:
        """Try to match using known aliases for the label.

        Looks up the label_key in LABEL_ALIASES and tries each alias
        with case-insensitive + special char normalized matching.
        """
        aliases = LABEL_ALIASES.get(label_key, [])
        if not aliases:
            return None

        for alias in aliases:
            # Try each alias with progressively looser matching
            for level in (MatchLevel.EXACT, MatchLevel.CASE_INSENSITIVE,
                          MatchLevel.SPECIAL_CHAR_NORMALIZED):
                row = self._match_at_level(alias, level, start_row, end_row, after_row)
                if row is not None:
                    return row
        return None

    def _matches(self, source: str, target: str, level: MatchLevel) -> bool:
        """Check if source matches target at the given level."""
        if level == MatchLevel.EXACT:
            return source.strip() == target

        elif level == MatchLevel.CASE_INSENSITIVE:
            return source.strip().lower() == target.lower()

        elif level == MatchLevel.WHITESPACE_NORMALIZED:
            normalized = re.sub(r"^\s+", "", source)
            return normalized == target

        elif level == MatchLevel.SPECIAL_CHAR_NORMALIZED:
            normalized = self._normalize_special_chars(source)
            target_normalized = self._normalize_special_chars(target)
            return normalized == target_normalized

        return False

    @staticmethod
    def _normalize_special_chars(s: str) -> str:
        """Level 4 normalization: special characters."""
        # Replace non-breaking spaces
        s = s.replace("\u00a0", " ")
        # Remove BOM
        s = s.replace("\ufeff", "")
        # Collapse multiple spaces
        s = re.sub(r"\s+", " ", s)
        # Normalize dashes
        s = s.replace("\u2013", "-").replace("\u2014", "-")
        return s.strip()

    @staticmethod
    def _parse_value(val: Any, parse_type: str) -> Any:
        """Parse a cell value according to its expected type."""
        if val is None:
            return None
        if isinstance(val, str):
            s = val.strip()
            if s in ("-", "N/A", "NA", "n/a", ""):
                return None

        if parse_type == "number":
            return _parse_number(val)

        elif parse_type == "pct_decimal":
            return _parse_pct_decimal(val)

        elif parse_type == "string_multiple":
            return _parse_string_multiple(val)

        elif parse_type == "bps":
            return _parse_bps(val)

        elif parse_type == "mixed_margins":
            # Could be decimal->% or bps string
            if isinstance(val, str) and "bps" in val.lower():
                return _parse_bps(val)
            return _parse_pct_decimal(val)

        return val  # raw


def _parse_number(val: Any) -> Any:
    """Parse a numeric value, preserving precision."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if s in ("-", "N/A", "NA", "n/a", ""):
        return None
    # Handle parentheses as negative
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    # Remove thousands separators (be careful with locale)
    # If contains both . and , need to determine which is decimal separator
    if "," in s and "." in s:
        # Assume last separator is decimal
        if s.rfind(",") > s.rfind("."):
            # European: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # US: 1,234.56
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        # Could be thousands separator (1,234) or decimal (1,5)
        # If single comma with <= 2 digits after, treat as decimal
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_pct_decimal(val: Any) -> Any:
    """Parse TiKR percentage stored as decimal (0.25 = 25%)."""
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        if s in ("-", "N/A", "NA", "n/a", ""):
            return None
        # Handle already-percentage values (e.g., "25%")
        if s.endswith("%"):
            s = s[:-1]
            try:
                return float(s)
            except ValueError:
                return None
    num = _parse_number(val)
    if num is None:
        return None
    # TiKR stores percentages as decimals: 0.25 = 25%
    # If value is between -5.0 and 5.0, assume decimal -> convert
    if -5.0 <= num <= 5.0:
        return round(num * 100, 4)
    # Already a percentage
    return num


def _parse_string_multiple(val: Any) -> Any:
    """Parse TiKR locale-formatted multiples like '9,61x' or '(849,09x)'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if s in ("-", "N/A", "NA", "n/a", ""):
        return None

    # Handle parentheses as negative
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    # Strip trailing 'x'
    s = s.rstrip("x").rstrip("X").strip()

    # Replace comma with dot for decimal
    # TiKR uses locale-formatted: "9,61" = 9.61
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    elif "," in s and "." in s:
        # Both present - assume comma is thousands separator
        if s.rfind(",") < s.rfind("."):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")

    try:
        result = float(s)
        return -result if negative else result
    except ValueError:
        return None


def _parse_bps(val: Any) -> Any:
    """Parse TiKR basis points strings like '241bps' or '(49bps)'."""
    if val is None:
        return None
    s = str(val).strip()
    if s in ("-", "N/A", "NA", "n/a", ""):
        return None

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    s = s.replace("bps", "").replace("BPS", "").strip()

    # Handle comma as decimal
    if "," in s:
        s = s.replace(",", ".")

    try:
        result = float(s)
        return int(-result) if negative else int(result)
    except ValueError:
        return None
