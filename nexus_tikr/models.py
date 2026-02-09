"""Data models for NEXUS-TIKR v2.1 pipeline."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


class FileTypeID(enum.Enum):
    TIKR_INCOME_STATEMENT = "TIKR_INCOME_STATEMENT"
    TIKR_BALANCE_SHEET = "TIKR_BALANCE_SHEET"
    TIKR_CASH_FLOW = "TIKR_CASH_FLOW"
    TIKR_RATIOS = "TIKR_RATIOS"
    TIKR_SEGMENTS = "TIKR_SEGMENTS"
    TIKR_ACTUALS_FORWARD = "TIKR_ACTUALS_FORWARD"
    TIKR_MULTIPLES = "TIKR_MULTIPLES"
    TIKR_STREET_TARGETS = "TIKR_STREET_TARGETS"
    TIKR_QUARTERLY_EARNINGS = "TIKR_QUARTERLY_EARNINGS"
    UNKNOWN = "UNKNOWN"


class Flag(enum.Enum):
    CRITICAL = "🔴"
    WARNING = "🟠"
    POSITIVE = "🟢"
    NEUTRAL = "⚪"


class MatchLevel(enum.Enum):
    EXACT = 1
    CASE_INSENSITIVE = 2
    WHITESPACE_NORMALIZED = 3
    SPECIAL_CHAR_NORMALIZED = 4
    NOT_FOUND = 5


class LabelImpact(enum.Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    MINOR = "MINOR"


class OutputMode(enum.Enum):
    SINGLE = "SINGLE"
    COMPACT = "COMPACT"
    SPLIT = "SPLIT"


class PipelineStatus(enum.Enum):
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class ValidationStatus(enum.Enum):
    PASSED = "PASSED"
    PASSED_WITH_WARNINGS = "PASSED_WITH_WARNINGS"
    FAILED = "FAILED"


class Sector(enum.Enum):
    INDUSTRIALS = "Industrials"
    BASIC_MATERIALS = "Basic_Materials"
    UTILITIES = "Utilities"
    TECHNOLOGY = "Technology"
    CONSUMER_CYCLICAL = "Consumer_Cyclical"
    CONSUMER_DEFENSIVE = "Consumer_Defensive"
    HEALTHCARE = "Healthcare"
    FINANCIAL_SERVICES = "Financial_Services"
    REAL_ESTATE = "Real_Estate"
    ENERGY = "Energy"
    COMMUNICATION_SERVICES = "Communication_Services"
    UNKNOWN = "Unknown"


@dataclass
class ThresholdProfile:
    de_warn: float
    de_crit: float
    roe_positive: float
    nd_ebitda_warn: float
    gm_floor: float
    special_rules: str = ""


@dataclass
class FlagEntry:
    metric: str
    value: Any
    flag: Flag
    threshold: str
    note: str


@dataclass
class LabelMatch:
    label_key: str
    source_label_raw: Optional[str]
    match_level: MatchLevel
    row_number: Optional[int]
    normalization_applied: str = ""


@dataclass
class MissingLabel:
    label_key: str
    file_type: str
    section_anchor: str
    impact: LabelImpact


@dataclass
class UnmappedLabel:
    source_label: str
    row_number: int
    section_context: str
    sample_values: list


@dataclass
class LabelHealth:
    expected_not_found: list[MissingLabel] = field(default_factory=list)
    found_with_variant: list[LabelMatch] = field(default_factory=list)
    unmapped_source_labels: list[UnmappedLabel] = field(default_factory=list)
    counts: dict[MatchLevel, int] = field(default_factory=lambda: {
        MatchLevel.EXACT: 0,
        MatchLevel.CASE_INSENSITIVE: 0,
        MatchLevel.WHITESPACE_NORMALIZED: 0,
        MatchLevel.SPECIAL_CHAR_NORMALIZED: 0,
        MatchLevel.NOT_FOUND: 0,
    })
    total_expected: int = 0

    @property
    def health_score(self) -> float:
        if self.total_expected == 0:
            return 1.0
        weights = {
            MatchLevel.EXACT: 1.0,
            MatchLevel.CASE_INSENSITIVE: 0.95,
            MatchLevel.WHITESPACE_NORMALIZED: 0.85,
            MatchLevel.SPECIAL_CHAR_NORMALIZED: 0.75,
        }
        score = sum(
            self.counts.get(level, 0) * w
            for level, w in weights.items()
        )
        return score / self.total_expected

    @property
    def format_drift_warning(self) -> bool:
        crit_missing = sum(
            1 for m in self.expected_not_found if m.impact == LabelImpact.CRITICAL
        )
        return (
            len(self.found_with_variant) > 10
            or crit_missing > 0
            or self.health_score < 0.85
        )


@dataclass
class FileInfo:
    filename: str
    filepath: str
    file_type: FileTypeID = FileTypeID.UNKNOWN
    detection_confidence: float = 0.0
    max_row: int = 0
    max_col: int = 0
    fiscal_years: list[str] = field(default_factory=list)
    ltm_available: bool = False
    ltm_col: Optional[int] = None
    date_columns: dict[str, int] = field(default_factory=dict)  # year_str -> col_idx
    ticker_from_file: Optional[str] = None
    currency: Optional[str] = None


@dataclass
class QESectionMap:
    section_1_anchor: Optional[int] = None
    section_1_end: Optional[int] = None
    section_1_found: bool = False
    section_2_anchor: Optional[int] = None
    section_2_end: Optional[int] = None
    section_2_found: bool = False
    section_3_anchor: Optional[int] = None
    section_3_end: Optional[int] = None
    section_3_found: bool = False


@dataclass
class ForwardGroup:
    metric: str
    confidence: str  # HIGH, MEDIUM, LOW
    signals: list[str] = field(default_factory=list)
    avg_value: float = 0.0
    row_start: int = 0
    row_end: int = 0
    rows_data: list[dict] = field(default_factory=list)


@dataclass
class ParsedData:
    """Container for all parsed data from all files."""
    income_statement: dict[str, dict[str, Any]] = field(default_factory=dict)
    balance_sheet: dict[str, dict[str, Any]] = field(default_factory=dict)
    cash_flow: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_returns: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_margins: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_efficiency: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_liquidity: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_solvency: dict[str, dict[str, Any]] = field(default_factory=dict)
    ratios_per_share: dict[str, dict[str, Any]] = field(default_factory=dict)
    valuation_trailing: dict[str, dict[str, Any]] = field(default_factory=dict)
    valuation_forward: dict[str, dict[str, Any]] = field(default_factory=dict)
    multiples_historical: dict[str, dict[str, Any]] = field(default_factory=dict)
    segments_business: dict[str, dict[str, Any]] = field(default_factory=dict)
    segments_geographic: dict[str, dict[str, Any]] = field(default_factory=dict)
    consensus_estimates: dict[str, dict[str, Any]] = field(default_factory=dict)
    consensus_ae_markers: dict[str, str] = field(default_factory=dict)
    consensus_cagr: dict[str, Any] = field(default_factory=dict)
    quarterly_latest: dict[str, Any] = field(default_factory=dict)
    beats_misses: dict[str, dict[str, Any]] = field(default_factory=dict)
    beats_misses_meta: dict[str, Any] = field(default_factory=dict)
    forward_quarterly: list[ForwardGroup] = field(default_factory=list)
    street_targets: dict[str, Any] = field(default_factory=dict)
    adaptive_data: list[dict] = field(default_factory=list)
    multiples_range: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Global context for the processing pipeline."""
    ticker: str = "UNKNOWN"
    company: str = ""
    currency: str = ""
    sector: Sector = Sector.UNKNOWN
    units: str = "Millions"
    data_date: str = ""
    ltm_available: bool = False
    files: list[FileInfo] = field(default_factory=list)
    file_types_processed: list[str] = field(default_factory=list)
    fiscal_years_covered: str = ""
    quarters_covered: str = ""
    output_mode: OutputMode = OutputMode.SINGLE
    estimated_tokens: int = 0
    core_tokens: int = 0
    historical_tokens: int = 0
    data_quality_score: float = 0.0
    anomalies_detected: int = 0
    validation_status: ValidationStatus = ValidationStatus.PASSED
    pipeline_status: PipelineStatus = PipelineStatus.COMPLETED
    abort_reason: Optional[str] = None
    label_health: LabelHealth = field(default_factory=LabelHealth)
    qe_section_map: Optional[QESectionMap] = None
    qe_forward_groups: list[ForwardGroup] = field(default_factory=list)
    flags: list[FlagEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    checksums: dict[str, Any] = field(default_factory=dict)
    parsed_data: ParsedData = field(default_factory=ParsedData)
    threshold_profile: Optional[ThresholdProfile] = None
    price_cross_validation: dict[str, Any] = field(default_factory=dict)
    derived_metrics: dict[str, Any] = field(default_factory=dict)
