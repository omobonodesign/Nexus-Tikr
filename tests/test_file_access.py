"""Tests for Module 0 & 1: File Access and Detection."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from nexus_tikr.file_access import (
    validate_file,
    detect_file_type,
    extract_ticker_from_filename,
    extract_currency_from_header,
    FileAccessError,
)
from nexus_tikr.models import FileTypeID


class TestValidateFile:
    def test_non_xlsx_rejected(self, tmp_path):
        # Create a non-xlsx file
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c")
        with pytest.raises(FileAccessError, match="supporta esclusivamente"):
            validate_file(str(csv_file))

    def test_missing_file_rejected(self):
        with pytest.raises(FileAccessError, match="not found"):
            validate_file("/nonexistent/file.xlsx")

    def test_valid_xlsx_accepted(self, tmp_path):
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")
        path = validate_file(str(xlsx_file))
        assert path.suffix == ".xlsx"


class TestDetectFileType:
    def _make_ws(self, cells: dict[tuple[int, int], str]):
        ws = MagicMock()
        ws.max_row = 20
        ws.max_column = 10

        def cell_fn(row, column):
            c = MagicMock()
            c.value = cells.get((row, column))
            return c

        ws.cell = cell_fn
        return ws

    def test_income_statement(self):
        ws = self._make_ws({(1, 1): "Income Statement | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_INCOME_STATEMENT
        assert conf >= 0.95

    def test_balance_sheet(self):
        ws = self._make_ws({(1, 1): "Balance Sheet | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_BALANCE_SHEET
        assert conf >= 0.95

    def test_cash_flow(self):
        ws = self._make_ws({(1, 1): "Cash Flow | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_CASH_FLOW
        assert conf >= 0.95

    def test_ratios(self):
        ws = self._make_ws({(1, 1): "Ratios | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_RATIOS
        assert conf >= 0.95

    def test_segments(self):
        ws = self._make_ws({(1, 1): "Segments | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_SEGMENTS
        assert conf >= 0.95

    def test_multiples(self):
        ws = self._make_ws({(1, 1): "Multiples | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_MULTIPLES
        assert conf >= 0.95

    def test_street_targets(self):
        ws = self._make_ws({(1, 1): "Street Targets | TIKR.com"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_STREET_TARGETS
        assert conf >= 0.95

    def test_actuals_forward(self):
        ws = self._make_ws({
            (1, 1): "Annual Estimates in Millions of Euro",
            (2, 1): "Actuals & Forward Estimates | TIKR.com",
        })
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_ACTUALS_FORWARD
        assert conf >= 0.95

    def test_quarterly_earnings(self):
        ws = self._make_ws({
            (1, 1): "Quarterly Estimates in Millions of Euro",
            (3, 1): "TERNA Q3 Earnings | TIKR.com",
        })
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.TIKR_QUARTERLY_EARNINGS
        assert conf >= 0.95

    def test_unknown(self):
        ws = self._make_ws({(1, 1): "Some random file"})
        file_type, conf = detect_file_type(ws)
        assert file_type == FileTypeID.UNKNOWN
        assert conf == 0.0


class TestTickerExtraction:
    def test_standard_pattern(self):
        assert extract_ticker_from_filename("TIKR_-_AAPL_-_Income_Statement.xlsx") == "AAPL"

    def test_simple_pattern(self):
        assert extract_ticker_from_filename("TIKR_MSFT_Balance_Sheet.xlsx") == "MSFT"

    def test_no_match(self):
        assert extract_ticker_from_filename("random_file.xlsx") is None

    def test_ticker_with_dot(self):
        assert extract_ticker_from_filename("TIKR_-_BRK.B_-_Ratios.xlsx") == "BRK.B"


class TestCurrencyExtraction:
    def _make_ws(self, a1: str = "", a2: str = "", a3: str = ""):
        ws = MagicMock()
        ws.max_row = 5
        ws.max_column = 5

        def cell_fn(row, column):
            c = MagicMock()
            if column == 1:
                c.value = {1: a1, 2: a2, 3: a3}.get(row, "")
            else:
                c.value = None
            return c

        ws.cell = cell_fn
        return ws

    def test_euro_detection(self):
        ws = self._make_ws(a1="Annual Estimates in Millions of Euro from 2020")
        assert extract_currency_from_header(ws) == "EUR"

    def test_usd_detection(self):
        ws = self._make_ws(a1="Quarterly Estimates in Millions of US Dollar from 2020")
        assert extract_currency_from_header(ws) == "USD"

    def test_no_currency(self):
        ws = self._make_ws(a1="Income Statement | TIKR.com")
        assert extract_currency_from_header(ws) is None
