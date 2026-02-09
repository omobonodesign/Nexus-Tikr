"""Tests for Module 3: Semantic Label Engine."""

import pytest
from unittest.mock import MagicMock, PropertyMock
from nexus_tikr.label_engine import (
    SemanticLabelEngine,
    _parse_number,
    _parse_pct_decimal,
    _parse_string_multiple,
    _parse_bps,
)
from nexus_tikr.models import LabelImpact, MatchLevel


# ============================================================
# Value parsing tests
# ============================================================

class TestParseNumber:
    def test_none(self):
        assert _parse_number(None) is None

    def test_integer(self):
        assert _parse_number(42) == 42

    def test_float(self):
        assert _parse_number(3.14) == 3.14

    def test_dash(self):
        assert _parse_number("-") is None

    def test_na(self):
        assert _parse_number("N/A") is None
        assert _parse_number("n/a") is None
        assert _parse_number("NA") is None

    def test_empty_string(self):
        assert _parse_number("") is None

    def test_us_format(self):
        assert _parse_number("1,234.56") == 1234.56

    def test_european_format(self):
        assert _parse_number("1.234,56") == 1234.56

    def test_parentheses_negative(self):
        assert _parse_number("(100)") == -100.0

    def test_simple_string_number(self):
        assert _parse_number("42.5") == 42.5

    def test_thousands_separator_only(self):
        assert _parse_number("1,234") == 1234.0


class TestParsePctDecimal:
    def test_none(self):
        assert _parse_pct_decimal(None) is None

    def test_decimal_to_percent(self):
        assert _parse_pct_decimal(0.25) == 25.0

    def test_small_decimal(self):
        assert _parse_pct_decimal(0.05) == 5.0

    def test_negative_decimal(self):
        assert _parse_pct_decimal(-0.10) == -10.0

    def test_already_percentage(self):
        # Values > 5.0 are assumed to already be percentages
        assert _parse_pct_decimal(25.0) == 25.0

    def test_percent_string(self):
        assert _parse_pct_decimal("25%") == 25.0

    def test_dash(self):
        assert _parse_pct_decimal("-") is None

    def test_zero(self):
        assert _parse_pct_decimal(0.0) == 0.0


class TestParseStringMultiple:
    def test_none(self):
        assert _parse_string_multiple(None) is None

    def test_numeric(self):
        assert _parse_string_multiple(9.61) == 9.61

    def test_locale_formatted(self):
        assert _parse_string_multiple("9,61x") == 9.61

    def test_negative_locale(self):
        assert _parse_string_multiple("(849,09x)") == -849.09

    def test_simple_x(self):
        assert _parse_string_multiple("12.5x") == 12.5

    def test_dash(self):
        assert _parse_string_multiple("-") is None

    def test_na(self):
        assert _parse_string_multiple("N/A") is None

    def test_plain_number(self):
        assert _parse_string_multiple("5.5") == 5.5


class TestParseBps:
    def test_none(self):
        assert _parse_bps(None) is None

    def test_positive(self):
        assert _parse_bps("241bps") == 241

    def test_negative_parentheses(self):
        assert _parse_bps("(49bps)") == -49

    def test_dash(self):
        assert _parse_bps("-") is None

    def test_na(self):
        assert _parse_bps("N/A") is None


# ============================================================
# Semantic Label Engine tests (mock worksheet)
# ============================================================

def _make_mock_ws(col_a_values: dict[int, str], max_row: int = 100, max_col: int = 10):
    """Create a mock worksheet with specified Column A values."""
    ws = MagicMock()
    ws.max_row = max_row
    ws.max_column = max_col

    def cell_side_effect(row, column):
        mock_cell = MagicMock()
        if column == 1:
            mock_cell.value = col_a_values.get(row)
        else:
            mock_cell.value = None
        return mock_cell

    ws.cell = cell_side_effect
    return ws


class TestSemanticLabelEngineMatching:
    def test_exact_match(self):
        ws = _make_mock_ws({1: "Header", 5: "Total Revenues", 10: "Gross Profit"})
        engine = SemanticLabelEngine(ws)
        row = engine.find_label("Total Revenues")
        assert row == 5

    def test_case_insensitive_match(self):
        ws = _make_mock_ws({5: "total revenues"})
        engine = SemanticLabelEngine(ws)
        row = engine.find_label("Total Revenues")
        assert row == 5

    def test_whitespace_normalized_match(self):
        ws = _make_mock_ws({5: "  Total Revenues"})
        engine = SemanticLabelEngine(ws)
        row = engine.find_label("Total Revenues")
        assert row == 5

    def test_not_found(self):
        ws = _make_mock_ws({5: "Revenue"})
        engine = SemanticLabelEngine(ws)
        row = engine.find_label("Total Revenues")
        assert row is None

    def test_label_health_tracking(self):
        ws = _make_mock_ws({5: "Total Revenues", 10: "Missing Label"})
        engine = SemanticLabelEngine(ws)
        engine.find_label("Total Revenues", impact=LabelImpact.CRITICAL)
        engine.find_label("Net Income", impact=LabelImpact.CRITICAL)

        assert engine.label_health.counts[MatchLevel.EXACT] == 1
        assert engine.label_health.counts[MatchLevel.NOT_FOUND] == 1
        assert len(engine.label_health.expected_not_found) == 1
        assert engine.label_health.total_expected == 2

    def test_positional_label(self):
        ws = _make_mock_ws({
            5: "Gross Profit",
            6: "% Margins",
            10: "Operating Income",
            11: "% Margins",
        })
        engine = SemanticLabelEngine(ws)
        row = engine.find_positional_label("% Margins", after_label="Operating Income")
        assert row == 11

    def test_section_anchor(self):
        ws = _make_mock_ws({
            5: "Return Ratios:",
            6: "Return on Assets %",
            15: "Margin Analysis:",
            16: "Gross Profit Margin %",
        })
        engine = SemanticLabelEngine(ws)
        row = engine.find_section_anchor(["Return Ratios:"])
        assert row == 5
        row = engine.find_section_anchor(["Margin Analysis:"])
        assert row == 15

    def test_bounded_search(self):
        ws = _make_mock_ws({
            5: "Return Ratios:",
            6: "Return on Assets %",
            15: "Margin Analysis:",
            16: "Return on Assets %",  # Same label in different section
        })
        engine = SemanticLabelEngine(ws)
        row = engine.find_label("Return on Assets %", start_row=5, end_row=14)
        assert row == 6

    def test_health_score_calculation(self):
        ws = _make_mock_ws({
            5: "Total Revenues",
            6: "gross profit",  # case insensitive -> L2
            7: "  Net Income",  # leading whitespace, but .strip() catches it -> L1
        })
        engine = SemanticLabelEngine(ws)
        engine.find_label("Total Revenues")  # L1 match
        engine.find_label("Gross Profit")    # L2 match
        engine.find_label("Net Income")      # L1 match (strip removes leading spaces)
        engine.find_label("Missing")         # not found

        score = engine.label_health.health_score
        # L1=2 (Total Revenues, Net Income), L2=1 (Gross Profit), NOT_FOUND=1
        expected = (2 * 1.0 + 1 * 0.95 + 0.0) / 4
        assert abs(score - expected) < 0.01
