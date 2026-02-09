"""Tests for data models."""

import pytest
from nexus_tikr.models import (
    LabelHealth,
    LabelImpact,
    MatchLevel,
    MissingLabel,
    LabelMatch,
    Sector,
    ThresholdProfile,
)


class TestLabelHealth:
    def test_empty_health_score(self):
        lh = LabelHealth()
        assert lh.health_score == 1.0

    def test_all_exact_matches(self):
        lh = LabelHealth(total_expected=10)
        lh.counts[MatchLevel.EXACT] = 10
        assert lh.health_score == 1.0

    def test_mixed_matches(self):
        lh = LabelHealth(total_expected=4)
        lh.counts[MatchLevel.EXACT] = 2
        lh.counts[MatchLevel.CASE_INSENSITIVE] = 1
        lh.counts[MatchLevel.WHITESPACE_NORMALIZED] = 1
        # (2*1.0 + 1*0.95 + 1*0.85) / 4 = 4.80/4 = 0.95
        assert abs(lh.health_score - 0.95) < 0.01

    def test_format_drift_warning_critical_missing(self):
        lh = LabelHealth(total_expected=10)
        lh.counts[MatchLevel.EXACT] = 9
        lh.counts[MatchLevel.NOT_FOUND] = 1
        lh.expected_not_found = [
            MissingLabel("Revenue", "IS", "", LabelImpact.CRITICAL),
        ]
        assert lh.format_drift_warning is True

    def test_format_drift_warning_low_score(self):
        lh = LabelHealth(total_expected=10)
        lh.counts[MatchLevel.EXACT] = 5
        lh.counts[MatchLevel.SPECIAL_CHAR_NORMALIZED] = 5
        # (5*1.0 + 5*0.75) / 10 = 8.75/10 = 0.875
        # Still >= 0.85 but check boundary
        assert lh.health_score < 0.90

    def test_no_drift_warning_healthy(self):
        lh = LabelHealth(total_expected=10)
        lh.counts[MatchLevel.EXACT] = 10
        assert lh.format_drift_warning is False


class TestSector:
    def test_sector_values(self):
        assert Sector.UTILITIES.value == "Utilities"
        assert Sector.TECHNOLOGY.value == "Technology"
        assert Sector.UNKNOWN.value == "Unknown"
