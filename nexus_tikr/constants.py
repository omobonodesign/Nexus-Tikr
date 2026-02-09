"""Constants, thresholds, and label dictionaries for NEXUS-TIKR v2.1."""

from nexus_tikr.models import Sector, ThresholdProfile, LabelImpact

# File type detection patterns (A1 cell content)
FILE_TYPE_PATTERNS = {
    "TIKR_INCOME_STATEMENT": "Income Statement | TIKR.com",
    "TIKR_BALANCE_SHEET": "Balance Sheet | TIKR.com",
    "TIKR_CASH_FLOW": "Cash Flow | TIKR.com",
    "TIKR_RATIOS": "Ratios | TIKR.com",
    "TIKR_SEGMENTS": "Segments | TIKR.com",
    "TIKR_MULTIPLES": "Multiples | TIKR.com",
    "TIKR_STREET_TARGETS": "Street Targets | TIKR.com",
}

# For Actuals_Forward: R2 contains the pattern
ACTUALS_FORWARD_PATTERN = "Actuals & Forward Estimates | TIKR.com"

# For Quarterly Earnings: R1="Quarterly Estimates in Millions", R3 contains pattern
QE_R1_PATTERN = "Quarterly Estimates in Millions"
QE_R3_PATTERN = "Earnings | TIKR.com"

# Sector threshold profiles
THRESHOLD_PROFILES = {
    Sector.INDUSTRIALS: ThresholdProfile(1.5, 2.5, 15.0, 3.0, 20.0),
    Sector.BASIC_MATERIALS: ThresholdProfile(1.0, 2.0, 12.0, 3.0, 15.0,
        "Cyclical: flag margin compression >30% peak-to-trough"),
    Sector.UTILITIES: ThresholdProfile(2.0, 3.0, 10.0, 3.5, 30.0,
        "Regulated: D/E tolerance higher"),
    Sector.TECHNOLOGY: ThresholdProfile(0.8, 1.5, 20.0, 2.0, 40.0,
        "R&D-to-Revenue important"),
    Sector.CONSUMER_CYCLICAL: ThresholdProfile(1.5, 2.5, 12.0, 3.0, 25.0),
    Sector.CONSUMER_DEFENSIVE: ThresholdProfile(1.2, 2.0, 15.0, 2.5, 30.0,
        "Dividend consistency critical"),
    Sector.HEALTHCARE: ThresholdProfile(1.0, 2.0, 15.0, 2.5, 40.0,
        "Pipeline optionality not captured"),
    Sector.FINANCIAL_SERVICES: ThresholdProfile(0.0, 0.0, 12.0, 0.0, 0.0,
        "Use: ROE, ROA, Efficiency Ratio, CET1 if available"),
    Sector.REAL_ESTATE: ThresholdProfile(2.5, 4.0, 0.0, 4.0, 0.0,
        "FFO-based metrics if available"),
    Sector.ENERGY: ThresholdProfile(1.5, 2.5, 12.0, 3.0, 20.0,
        "Cyclical: use normalized earnings if available"),
    Sector.COMMUNICATION_SERVICES: ThresholdProfile(1.5, 2.5, 15.0, 3.0, 35.0),
    Sector.UNKNOWN: ThresholdProfile(1.5, 2.5, 15.0, 3.0, 20.0),
}

# ============================================================
# LABEL DICTIONARIES — Module 4 Parsing Templates
# ============================================================

# Each entry: output_field -> (label_key, parse_type, impact)
# parse_type: "number", "pct_decimal", "string_multiple", "bps", "raw"

INCOME_STATEMENT_LABELS = {
    "total_revenues": ("Total Revenues", "number", LabelImpact.CRITICAL),
    "revenue_yoy_pct": ("% Change YoY", "pct_decimal", LabelImpact.IMPORTANT),
    "cost_of_goods_sold": ("Cost Of Goods Sold", "number", LabelImpact.IMPORTANT),
    "gross_profit": ("Gross Profit", "number", LabelImpact.CRITICAL),
    "gross_margin_pct": ("% Margins", "pct_decimal", LabelImpact.CRITICAL),
    "salaries_and_benefits": ("Salaries And Benefits", "number", LabelImpact.MINOR),
    "other_operating_expenses": ("Other Operating Expenses", "number", LabelImpact.MINOR),
    "total_operating_expenses": ("Total Operating Expenses", "number", LabelImpact.IMPORTANT),
    "operating_income": ("Operating Income", "number", LabelImpact.CRITICAL),
    "operating_margin_pct": ("% Margins", "pct_decimal", LabelImpact.CRITICAL),
    "interest_expense": ("Interest Expense", "number", LabelImpact.CRITICAL),
    "interest_income": ("Interest Income", "number", LabelImpact.MINOR),
    "other_non_operating": ("Other Non Operating Income (Expenses)", "number", LabelImpact.MINOR),
    "impairment": ("Impairment Of Goodwill & Intangibles", "number", LabelImpact.MINOR),
    "other_unusual_items": ("Other Unusual Items", "number", LabelImpact.MINOR),
    "ebt_incl_unusual": ("EBT Including Unusual Items", "number", LabelImpact.IMPORTANT),
    "income_tax": ("Income Tax Expense", "number", LabelImpact.IMPORTANT),
    "effective_tax_rate": ("% Effective Tax Rate", "pct_decimal", LabelImpact.IMPORTANT),
    "earnings_continuing_ops": ("Earnings From Continuing Operations", "number", LabelImpact.IMPORTANT),
    "earnings_discontinued_ops": ("Earnings From Discontinued Operations", "number", LabelImpact.MINOR),
    "minority_interest_expense": ("Minority Interest Expense", "number", LabelImpact.MINOR),
    "net_income_to_company": ("Net Income to Company", "number", LabelImpact.IMPORTANT),
    "net_income_to_common": ("Net Income to Common Incl Extra Items", "number", LabelImpact.CRITICAL),
    "net_income_margin_pct": ("% Margins", "pct_decimal", LabelImpact.CRITICAL),
    "diluted_eps": ("Diluted EPS", "number", LabelImpact.CRITICAL),
    "basic_eps": ("Basic EPS", "number", LabelImpact.IMPORTANT),
    "normalized_diluted_eps": ("Normalized Diluted EPS", "number", LabelImpact.CRITICAL),
    "dividends_per_share": ("Dividends Per Share", "number", LabelImpact.IMPORTANT),
    "payout_ratio_pct": ("Payout Ratio %", "pct_decimal", LabelImpact.IMPORTANT),
    "weighted_avg_diluted_shares": ("Weighted Average Diluted Shares Outstanding", "number", LabelImpact.CRITICAL),
    "ebitda": ("EBITDA", "number", LabelImpact.CRITICAL),
    "normalized_ebitda": ("Normalized EBITDA", "number", LabelImpact.IMPORTANT),
    "depreciation_amortization": ("Depreciation & Amortization (from IS Supplemental)", "number", LabelImpact.IMPORTANT),
    "revenue_as_reported": ("Revenue As Reported", "number", LabelImpact.MINOR),
    "operating_income_as_reported": ("Operating Income As Reported", "number", LabelImpact.MINOR),
    "net_interest_income": ("Net Interest Income", "number", LabelImpact.MINOR),
}

# Labels that repeat and need positional disambiguation
IS_POSITIONAL_LABELS = {
    "gross_margin_pct": {"after": "Gross Profit", "label": "% Margins"},
    "operating_margin_pct": {"after": "Operating Income", "label": "% Margins"},
    "net_income_margin_pct": {"after": "Net Income to Common Incl Extra Items", "label": "% Margins"},
    "revenue_yoy_pct": {"after": "Total Revenues", "label": "% Change YoY"},
}

BALANCE_SHEET_LABELS = {
    "cash_and_equivalents": ("Cash And Equivalents", "number", LabelImpact.CRITICAL),
    "short_term_investments": ("Short Term Investments", "number", LabelImpact.MINOR),
    "total_cash_and_st_inv": ("Total Cash And Short Term Investments", "number", LabelImpact.IMPORTANT),
    "accounts_receivable": ("Accounts Receivable", "number", LabelImpact.IMPORTANT),
    "total_inventory": ("Total Inventory", "number", LabelImpact.IMPORTANT),
    "total_current_assets": ("Total Current Assets", "number", LabelImpact.CRITICAL),
    "net_ppe": ("Net Property Plant And Equipment", "number", LabelImpact.IMPORTANT),
    "gross_ppe": ("Gross Property Plant And Equipment", "number", LabelImpact.MINOR),
    "accumulated_depreciation": ("Accumulated Depreciation", "number", LabelImpact.MINOR),
    "construction_in_progress": ("Construction In Progress", "number", LabelImpact.MINOR),
    "long_term_investments": ("Long-term Investments", "number", LabelImpact.MINOR),
    "goodwill": ("Goodwill", "number", LabelImpact.IMPORTANT),
    "other_intangibles": ("Other Intangibles", "number", LabelImpact.IMPORTANT),
    "total_assets": ("Total Assets", "number", LabelImpact.CRITICAL),
    "accounts_payable": ("Accounts Payable", "number", LabelImpact.IMPORTANT),
    "current_debt": ("Current Debt", "number", LabelImpact.IMPORTANT),
    "total_current_liabilities": ("Total Current Liabilities", "number", LabelImpact.CRITICAL),
    "long_term_debt": ("Long-Term Debt", "number", LabelImpact.CRITICAL),
    "lt_debt_and_capital_leases": ("Long-Term Debt and Capital Leases", "number", LabelImpact.IMPORTANT),
    "deferred_tax_liability_nc": ("Deferred Tax Liability Non Current", "number", LabelImpact.MINOR),
    "total_liabilities": ("Total Liabilities", "number", LabelImpact.CRITICAL),
    "common_stock": ("Common Stock", "number", LabelImpact.MINOR),
    "retained_earnings": ("Retained Earnings", "number", LabelImpact.IMPORTANT),
    "treasury_stock": ("Treasury Stock", "number", LabelImpact.MINOR),
    "total_common_equity": ("Total Common Equity", "number", LabelImpact.CRITICAL),
    "minority_interest": ("Minority Interest", "number", LabelImpact.MINOR),
    "total_equity": ("Total Equity", "number", LabelImpact.CRITICAL),
    "shares_outstanding": ("Total Shares Out. on Filing Date", "number", LabelImpact.CRITICAL),
    "net_debt": ("Net Debt", "number", LabelImpact.CRITICAL),
}

CASH_FLOW_LABELS = {
    "net_income": ("Net Income", "number", LabelImpact.IMPORTANT),
    "depreciation": ("Depreciation", "number", LabelImpact.MINOR),
    "total_da": ("Total Depreciation & Amortization", "number", LabelImpact.IMPORTANT),
    "change_in_inventories": ("Change In Inventories", "number", LabelImpact.MINOR),
    "change_in_payable": ("Change In Payable", "number", LabelImpact.MINOR),
    "other_cfo_items": ("Other CFO Items", "number", LabelImpact.MINOR),
    "cash_from_operations": ("Cash from Operations", "number", LabelImpact.CRITICAL),
    "change_nwc": ("Memo: Change in Net Working Capital", "number", LabelImpact.MINOR),
    "capital_expenditure": ("Capital Expenditure", "number", LabelImpact.CRITICAL),
    "cash_acquisitions": ("Cash Acquisitions", "number", LabelImpact.MINOR),
    "investment_securities": ("Investment in Marketable and Equity Securities", "number", LabelImpact.MINOR),
    "other_cfi_items": ("Other CFI Items", "number", LabelImpact.MINOR),
    "cash_from_investing": ("Cash from Investing", "number", LabelImpact.IMPORTANT),
    "total_debt_issued": ("Total Debt Issued", "number", LabelImpact.CRITICAL),
    "total_debt_repaid": ("Total Debt Repaid", "number", LabelImpact.CRITICAL),
    "issuance_common_stock": ("Issuance of Common Stock", "number", LabelImpact.MINOR),
    "repurchase_common_stock": ("Repurchase of Common Stock", "number", LabelImpact.IMPORTANT),
    "total_dividends_paid": ("Total Dividends Paid", "number", LabelImpact.CRITICAL),
    "other_financing": ("Other Financing Activities", "number", LabelImpact.MINOR),
    "cash_from_financing": ("Cash from Financing", "number", LabelImpact.CRITICAL),
    "changes_in_cash": ("Changes In Cash", "number", LabelImpact.IMPORTANT),
    "fx_adjustments": ("Foreign Exchange Rate Adjustments", "number", LabelImpact.MINOR),
    "cash_beginning": ("Cash and Cash Equivalents, Beginning of Period", "number", LabelImpact.MINOR),
    "cash_ending": ("Cash and Cash Equivalents, End of Period", "number", LabelImpact.IMPORTANT),
    "free_cash_flow": ("Free Cash Flow", "number", LabelImpact.CRITICAL),
    "fcf_margin_pct": ("% Free Cash Flow Margins", "pct_decimal", LabelImpact.CRITICAL),
    "cfo_before_nwc": ("Cash Flow from Operations before NWC", "number", LabelImpact.MINOR),
}

RATIOS_RETURNS_LABELS = {
    "roa_pct": ("Return on Assets %", "pct_decimal", LabelImpact.CRITICAL),
    "roic_pct": ("Return on Invested Capital %", "pct_decimal", LabelImpact.CRITICAL),
    "roe_pct": ("Return On Equity %", "pct_decimal", LabelImpact.CRITICAL),
    "normalized_roic_pct": ("Normalized ROIC %", "pct_decimal", LabelImpact.IMPORTANT),
}

RATIOS_MARGINS_LABELS = {
    "gross_margin_pct": ("Gross Profit Margin %", "pct_decimal", LabelImpact.CRITICAL),
    "ebitda_margin_pct": ("EBITDA Margin %", "pct_decimal", LabelImpact.CRITICAL),
    "ebit_margin_pct": ("EBIT Margin %", "pct_decimal", LabelImpact.IMPORTANT),
    "ebt_margin_pct": ("EBT Margin %", "pct_decimal", LabelImpact.MINOR),
    "net_income_margin_pct": ("Net Income Margin %", "pct_decimal", LabelImpact.CRITICAL),
    "normalized_ni_margin_pct": ("Normalized Net Income Margin %", "pct_decimal", LabelImpact.MINOR),
    "effective_tax_rate_pct": ("Effective Tax Rate %", "pct_decimal", LabelImpact.IMPORTANT),
    "fcf_margin_pct": ("Free Cash Flow Margin %", "pct_decimal", LabelImpact.CRITICAL),
    "fcf_to_ni_pct": ("Free / Net Income %", "pct_decimal", LabelImpact.IMPORTANT),
    "capex_to_sales_pct": ("Capex / Sales %", "pct_decimal", LabelImpact.IMPORTANT),
    "capex_to_ebitda_pct": ("Capex / EBITDA %", "pct_decimal", LabelImpact.MINOR),
}

RATIOS_EFFICIENCY_LABELS = {
    "asset_turnover": ("Asset Turnover", "string_multiple", LabelImpact.IMPORTANT),
    "fixed_asset_turnover": ("Fixed Assets Turnover", "string_multiple", LabelImpact.MINOR),
    "receivables_turnover": ("Receivables Turnover", "string_multiple", LabelImpact.MINOR),
    "inventory_turnover": ("Inventory Turnover", "string_multiple", LabelImpact.MINOR),
    "days_sales_outstanding": ("Avg. Days Sales Outstanding", "number", LabelImpact.IMPORTANT),
    "days_inventory": ("Avg. Days Outstanding Inventory", "number", LabelImpact.MINOR),
    "days_payable": ("Avg. Days Payable Outstanding", "number", LabelImpact.MINOR),
    "cash_conversion_cycle": ("Avg. Cash Conversion Cycle", "number", LabelImpact.IMPORTANT),
}

RATIOS_LIQUIDITY_LABELS = {
    "current_ratio": ("Current Ratio", "string_multiple", LabelImpact.CRITICAL),
    "quick_ratio": ("Quick Ratio", "string_multiple", LabelImpact.IMPORTANT),
    "cash_ratio": ("Cash Ratio", "string_multiple", LabelImpact.MINOR),
}

RATIOS_SOLVENCY_LABELS = {
    "assets_to_equity": ("Assets / Equity", "string_multiple", LabelImpact.MINOR),
    "total_debt_to_equity": ("Total Debt / Equity", "number", LabelImpact.CRITICAL),
    "debt_to_assets": ("Debt / Assets", "number", LabelImpact.IMPORTANT),
    "equity_to_assets": ("Common Equity / Assets", "number", LabelImpact.MINOR),
    "lt_debt_to_capital": ("LT Debt / Capital", "number", LabelImpact.IMPORTANT),
    "ebit_interest_coverage": ("EBIT / Interest Expense", "string_multiple", LabelImpact.CRITICAL),
    "solvency_ratio": ("Solvency Ratio", "number", LabelImpact.MINOR),
}

RATIOS_PER_SHARE_LABELS = {
    "sales_per_share": ("Sales Per Share", "number", LabelImpact.MINOR),
    "book_value_per_share": ("Book Value Per Share", "number", LabelImpact.IMPORTANT),
    "tangible_bv_per_share": ("Tangible Book Value Per Share", "number", LabelImpact.MINOR),
    "cfo_per_share": ("CFO Per Share", "number", LabelImpact.MINOR),
    "fcf_per_share": ("FCF Per Share", "number", LabelImpact.IMPORTANT),
    "working_capital_per_share": ("Working Capital Per Share", "number", LabelImpact.MINOR),
}

VALUATION_TRAILING_LABELS = {
    "ev_revenue": ("EV/Revenue", "string_multiple", LabelImpact.IMPORTANT),
    "price_sales": ("Price/Sales", "string_multiple", LabelImpact.MINOR),
    "ev_ebitda": ("EV/EBITDA", "string_multiple", LabelImpact.CRITICAL),
    "ev_ebit": ("EV/EBIT", "string_multiple", LabelImpact.IMPORTANT),
    "ev_fcf": ("EV/FCF", "string_multiple", LabelImpact.IMPORTANT),
    "pe_ratio": ("P/E Ratio", "string_multiple", LabelImpact.CRITICAL),
    "normalized_pe": ("Normalized P/E Ratio", "string_multiple", LabelImpact.IMPORTANT),
    "pb_ratio": ("P/B Ratio", "string_multiple", LabelImpact.IMPORTANT),
    "fcf_yield_pct": ("FCF Yield", "pct_decimal", LabelImpact.CRITICAL),
    "earning_yield_pct": ("Earning Yield", "pct_decimal", LabelImpact.IMPORTANT),
    "trailing_div_yield_pct": ("Trailing Dividend Yield", "pct_decimal", LabelImpact.IMPORTANT),
    "payout_ratio_pct": ("Payout Ratio", "pct_decimal", LabelImpact.IMPORTANT),
}

VALUATION_FORWARD_LABELS = {
    "ev_fwd_revenue": ("EV/Forward Revenue", "string_multiple", LabelImpact.IMPORTANT),
    "ev_fwd_ebitda": ("EV/Forward EBITDA", "string_multiple", LabelImpact.CRITICAL),
    "ev_fwd_ebit": ("EV/Forward EBIT", "string_multiple", LabelImpact.IMPORTANT),
    "fwd_pe": ("Forward P/E Ratio", "string_multiple", LabelImpact.CRITICAL),
    "fwd_div_yield_pct": ("Forward Dividend Yield", "pct_decimal", LabelImpact.IMPORTANT),
    "fwd_earning_yield_pct": ("Forward Earning Yield", "pct_decimal", LabelImpact.MINOR),
    "peg_ratio": ("PEG Ratio", "string_multiple", LabelImpact.IMPORTANT),
}

# Ratios file section anchors (multiple variants per section)
RATIOS_SECTION_ANCHORS = {
    "returns": ["Return Ratios:", "Return Ratios", "Returns:", "Returns"],
    "margins": ["Margin Analysis:", "Margin Analysis", "Margins:", "Profitability:"],
    "efficiency": ["Asset Efficiency:", "Efficiency:", "Efficiency", "Asset Efficiency",
                    "Efficiency Ratios:"],
    "liquidity": ["Liquidity:", "Liquidity", "Liquidity Ratios:"],
    "solvency": ["Solvency:", "Solvency", "Solvency Ratios:", "Leverage:"],
    "per_share": ["Per Share Data:", "Per Share Data", "Per Share:", "Per Share Ratios:"],
    "trailing_valuation": ["Trailing Valuation:", "Trailing Valuation", "Trailing:"],
    "forward_valuation": ["Forward Valuation:", "Forward Valuation", "Forward:"],
}

# Multiples labels
MULTIPLES_FORWARD_LABELS = {
    "ntm_ev_revenue": ("NTM EV / Revenue", "string_multiple", LabelImpact.IMPORTANT),
    "ntm_ps": ("NTM Price / Sales", "string_multiple", LabelImpact.MINOR),
    "ntm_ev_ebitda": ("NTM EV / EBITDA", "string_multiple", LabelImpact.CRITICAL),
    "ntm_ev_ebit": ("NTM EV / EBIT", "string_multiple", LabelImpact.IMPORTANT),
    "ntm_pe_normalized": ("NTM Normalized P/E", "string_multiple", LabelImpact.CRITICAL),
    "ntm_mcap_fcf": ("NTM Mkt Cap / LFCF", "string_multiple", LabelImpact.IMPORTANT),
    "ntm_lfcf_yield": ("NTM LFCF Yield", "pct_decimal", LabelImpact.IMPORTANT),
    "ntm_div_yield": ("NTM Dividend Yield", "pct_decimal", LabelImpact.IMPORTANT),
}

MULTIPLES_TRAILING_LABELS = {
    "ltm_ev_revenue": ("LTM EV / Revenue", "string_multiple", LabelImpact.IMPORTANT),
    "ltm_ps": ("LTM Price / Sales", "string_multiple", LabelImpact.MINOR),
    "ltm_ev_gross_profit": ("LTM EV / Gross Profit", "string_multiple", LabelImpact.MINOR),
    "ltm_ev_ebitda": ("LTM EV / EBITDA", "string_multiple", LabelImpact.CRITICAL),
    "ltm_ev_ebit": ("LTM EV / EBIT", "string_multiple", LabelImpact.IMPORTANT),
    "ltm_pe_diluted": ("LTM Diluted P/E", "string_multiple", LabelImpact.CRITICAL),
    "ltm_pb": ("LTM Price / Book", "string_multiple", LabelImpact.IMPORTANT),
    "ltm_p_tangible_bv": ("LTM Price / Tangible Book", "string_multiple", LabelImpact.MINOR),
    "ltm_ev_ulfcf": ("LTM EV / ULFCF", "string_multiple", LabelImpact.MINOR),
    "ltm_mcap_lfcf": ("LTM Mkt Cap / LFCF", "string_multiple", LabelImpact.IMPORTANT),
    "ltm_div_yield": ("LTM Dividend Yield", "pct_decimal", LabelImpact.IMPORTANT),
}

MULTIPLES_PRICE_FACTORS_LABELS = {
    "price": ("Price", "number", LabelImpact.CRITICAL),
    "tev_mm": ("TEV ($mm)", "number", LabelImpact.IMPORTANT),
    "market_cap_mm": ("Mkt Cap ($mm)", "number", LabelImpact.CRITICAL),
}

STREET_TARGETS_LABELS = {
    "price_close": ("Price Close", "number", LabelImpact.CRITICAL),
    "target_mean": ("Target Stock Price Mean", "number", LabelImpact.CRITICAL),
    "target_median": ("Target Stock Price Median", "number", LabelImpact.IMPORTANT),
    "target_high": ("Target Stock Price High", "number", LabelImpact.IMPORTANT),
    "target_low": ("Target Stock Price Low", "number", LabelImpact.IMPORTANT),
    "num_estimates": ("Target Stock Price (# Est)", "number", LabelImpact.IMPORTANT),
    "target_vs_close": ("Target Stock Price / Close Price", "number", LabelImpact.MINOR),
    "buys": ("# of Buys", "number", LabelImpact.IMPORTANT),
    "outperforms": ("# of Outperforms", "number", LabelImpact.IMPORTANT),
    "holds": ("# of Holds", "number", LabelImpact.IMPORTANT),
    "underperforms": ("# of Underperforms", "number", LabelImpact.IMPORTANT),
    "sells": ("# of Sells", "number", LabelImpact.IMPORTANT),
}

ACTUALS_FORWARD_LABELS = {
    "revenue": ("Revenue", "number", LabelImpact.CRITICAL),
    "ebitda": ("EBITDA", "number", LabelImpact.CRITICAL),
    "ebit": ("EBIT", "number", LabelImpact.IMPORTANT),
    "ebt_normalized": ("EBT (Normalized)", "number", LabelImpact.MINOR),
    "net_income_normalized": ("Net Income (Normalized)", "number", LabelImpact.CRITICAL),
    "eps_normalized": ("EPS (Normalized)", "number", LabelImpact.CRITICAL),
    "eps_gaap": ("EPS (GAAP)", "number", LabelImpact.IMPORTANT),
    "free_cash_flow": ("Free Cash Flow", "number", LabelImpact.CRITICAL),
    "dividend_per_share": ("Dividend Per Share", "number", LabelImpact.CRITICAL),
    "gross_margin": ("Gross Margin", "pct_decimal", LabelImpact.IMPORTANT),
    "interest_expense": ("Interest Expense", "number", LabelImpact.MINOR),
    "depreciation_amortization": ("Depreciation & Amortization", "number", LabelImpact.MINOR),
    "effective_tax_rate": ("Effective Tax Rate", "pct_decimal", LabelImpact.MINOR),
    "cash_from_operations": ("Cash from Operations", "number", LabelImpact.IMPORTANT),
    "capital_expenditure": ("Capital Expenditure", "number", LabelImpact.IMPORTANT),
    "cash_flow_per_share": ("Cash Flow Per Share", "number", LabelImpact.MINOR),
    "net_debt": ("Net Debt", "number", LabelImpact.IMPORTANT),
    "net_debt_to_ebitda": ("Net Debt / EBITDA", "string_multiple", LabelImpact.IMPORTANT),
    "book_value_per_share": ("Book Value Per Share", "number", LabelImpact.MINOR),
    "roe": ("ROE", "pct_decimal", LabelImpact.IMPORTANT),
    "roa": ("ROA", "pct_decimal", LabelImpact.MINOR),
    "market_cap": ("Market Cap", "number", LabelImpact.MINOR),
    "price_close": ("Price Close", "number", LabelImpact.MINOR),
    "tev": ("TEV", "number", LabelImpact.MINOR),
}

# Labels that have associated YoY / Margin sub-rows in Actuals_Forward
AF_YOY_METRICS = ["revenue", "ebitda", "ebit", "ebt_normalized", "net_income_normalized"]
AF_MARGIN_METRICS = ["ebitda", "ebit"]

# QE Section 1 labels
QE_SECTION1_LABELS = {
    "revenue": ("Revenue", "number", LabelImpact.CRITICAL),
    "ebitda": ("EBITDA", "number", LabelImpact.CRITICAL),
    "ebitda_margins": ("% EBITDA Margins", "mixed_margins", LabelImpact.IMPORTANT),
    "ebit": ("EBIT", "number", LabelImpact.IMPORTANT),
    "ebit_margins": ("EBIT Margins", "mixed_margins", LabelImpact.MINOR),
    "net_income": ("Net Income", "number", LabelImpact.CRITICAL),
    "adjusted_eps": ("Adjusted EPS", "number", LabelImpact.CRITICAL),
    "eps_gaap": ("EPS GAAP", "number", LabelImpact.IMPORTANT),
    "cfo": ("CFO", "number", LabelImpact.IMPORTANT),
    "capex": ("CAPEX", "number", LabelImpact.MINOR),
    "fcf": ("FCF", "number", LabelImpact.IMPORTANT),
}

# QE Section 2 metric groups
QE_SECTION2_METRICS = [
    ("Revenue", "Avg. Estimated Revenue", "Actual Revenue"),
    ("EBITDA", "Avg. Estimated EBITDA", "Actual EBITDA"),
    ("EBIT", "Avg. Estimated EBIT", "Actual EBIT"),
    ("Net Income", "Avg. Estimated Net Income", "Actual Net Income"),
    ("Adjusted EPS", "Avg. Estimated Adjusted EPS", "Actual Adjusted EPS"),
    ("EPS GAAP", "Avg. Estimated EPS GAAP", "Actual EPS GAAP"),
    ("CFO", "Avg. Estimated CFO", "Actual CFO"),
    ("CAPEX", "Avg. Estimated CAPEX", "Actual CAPEX"),
    ("FCF", "Avg. Estimated FCF", "Actual FCF"),
]

# Adaptive parser trigger words per category
ADAPTIVE_CATEGORIES = {
    "A": {
        "label": "Financial Statements",
        "triggers": ["Revenue", "EBITDA", "EPS", "Assets", "Equity", "Liabilities",
                     "Net Income", "Cash Flow", "Operating Income", "Depreciation"],
        "threshold": 5,
    },
    "B": {
        "label": "Valuation / Multiples",
        "triggers": ["P/E", "EV/EBITDA", "DCF", "WACC", "Fair Value", "Discount Rate",
                     "Terminal Value", "Multiple", "Implied Price", "Intrinsic Value"],
        "threshold": 3,
    },
    "C": {
        "label": "Peer / Comparative",
        "triggers": ["Peer", "Comparison", "Benchmark", "Ranking", "Median", "Average",
                     "Sector", "Industry", "Percentile", "Relative"],
        "threshold": 3,
    },
    "D": {
        "label": "ESG / Qualitative",
        "triggers": ["ESG", "Sustainability", "Governance", "Carbon", "Emissions",
                     "Social", "Environmental", "Diversity", "Climate", "Score"],
        "threshold": 3,
    },
    "E": {
        "label": "Custom Model / Projection",
        "triggers": ["Scenario", "Assumption", "Projection", "Sensitivity", "Base Case",
                     "Bull Case", "Bear Case", "Forecast", "Model", "Probability"],
        "threshold": 3,
    },
    "F": {
        "label": "Unclassifiable",
        "triggers": [],
        "threshold": 0,
    },
}

# Critical fields per file type for data quality scoring
CRITICAL_FIELDS = {
    "TIKR_INCOME_STATEMENT": [
        "total_revenues", "gross_profit", "operating_income", "ebitda",
        "net_income_to_common", "diluted_eps", "normalized_diluted_eps",
        "weighted_avg_diluted_shares", "interest_expense", "gross_margin_pct",
        "operating_margin_pct", "net_income_margin_pct",
    ],
    "TIKR_BALANCE_SHEET": [
        "total_assets", "total_current_assets", "cash_and_equivalents",
        "total_liabilities", "total_current_liabilities", "long_term_debt",
        "total_common_equity", "total_equity", "net_debt", "shares_outstanding",
    ],
    "TIKR_CASH_FLOW": [
        "cash_from_operations", "capital_expenditure", "free_cash_flow",
        "fcf_margin_pct", "total_dividends_paid", "total_debt_issued",
        "total_debt_repaid", "cash_from_financing",
    ],
    "TIKR_RATIOS": [
        "roe_pct", "roa_pct", "roic_pct", "gross_margin_pct",
        "ebitda_margin_pct", "current_ratio", "total_debt_to_equity",
        "ebit_interest_coverage", "pe_ratio", "fcf_yield_pct",
    ],
    "TIKR_ACTUALS_FORWARD": [
        "revenue", "ebitda", "eps_normalized", "free_cash_flow",
        "dividend_per_share",
    ],
    "TIKR_QUARTERLY_EARNINGS": [
        "revenue", "ebitda", "adjusted_eps",
    ],
}

# Derived metric thresholds
DERIVED_THRESHOLDS = {
    "nd_ebitda": {"green": 2.0, "warn_low": 3.0, "warn_high": 4.0},
    "interest_coverage": {"green": 6.0, "warn_low": 3.0, "warn_high": 4.0},
    "earnings_quality": {"green": 1.0, "warn_low": 0.7, "warn_high": 0.8},
    "fcf_conversion": {"green": 0.80, "warn_low": 0.50, "warn_high": 0.70},
    "payout_ratio": {"green": 0.70, "warn_low": 0.70, "warn_high": 0.90},
    "fcf_margin": {"green": 0.15, "warn_low": 0.05, "warn_high": 0.10},
    "roe": {"green": 0.15, "warn_low": 0.08, "warn_high": 0.10},
    "consensus_upside": {"green": 15.0, "warn_low": 5.0, "warn_high": 10.0},
    "bullish_pct": {"green": 60.0, "warn_low": 30.0, "warn_high": 50.0},
    "beat_rate": {"green": 75.0, "warn_low": 40.0, "warn_high": 60.0},
}

# ============================================================
# LABEL ALIASES — Fallback alternative names for label matching
# ============================================================
# Maps canonical label -> list of known alternative names.
# Used when the 4-level strict matching fails, to recover data
# that exists under a slightly different label name.

LABEL_ALIASES: dict[str, list[str]] = {
    # --- Income Statement ---
    "Total Revenues": [
        "Revenue", "Total Revenue", "Revenues", "Net Revenue", "Net Revenues",
        "Net Sales", "Sales", "Total Net Revenue", "Total Net Revenues",
    ],
    "Cost Of Goods Sold": [
        "Cost of Revenue", "COGS", "Cost of Sales", "Cost Of Revenue",
        "Total Cost of Revenue", "Cost of Goods",
    ],
    "Gross Profit": ["Gross Income"],
    "Salaries And Benefits": [
        "Salaries & Benefits", "Salaries and Benefits",
        "Compensation and Benefits", "Employee Compensation",
    ],
    "Other Operating Expenses": [
        "Other Oper. Expenses", "SG&A", "Selling General & Admin",
        "Selling, General & Administrative",
    ],
    "Total Operating Expenses": [
        "Operating Expenses", "Total Oper. Expenses",
        "Total Operating Costs", "Operating Costs",
    ],
    "Operating Income": [
        "Operating Profit", "Income from Operations",
        "Income From Operations", "EBIT",
    ],
    "Interest Expense": [
        "Interest Expense, Net", "Net Interest Expense",
        "Interest Expense Net", "Interest Cost",
    ],
    "Interest Income": [
        "Interest and Investment Income", "Interest & Investment Income",
    ],
    "Other Non Operating Income (Expenses)": [
        "Other Non-Operating Income", "Other Non-Operating",
        "Non-Operating Income (Expense)", "Other Non Operating Income",
        "Non Operating Income (Expenses)",
    ],
    "Impairment Of Goodwill & Intangibles": [
        "Impairment of Goodwill", "Goodwill Impairment",
        "Impairment Charges", "Impairment of Goodwill & Intangibles",
        "Asset Impairment Charges",
    ],
    "Other Unusual Items": [
        "Other Unusual", "Unusual Items", "Special Items",
        "Non-Recurring Items",
    ],
    "EBT Including Unusual Items": [
        "EBT Incl. Unusual Items", "Income Before Tax",
        "Pretax Income", "Earnings Before Taxes",
        "EBT Incl Unusual Items", "Income Before Taxes",
        "Pre-Tax Income", "EBT Including Unusual",
    ],
    "Income Tax Expense": [
        "Income Taxes", "Tax Expense", "Provision for Income Taxes",
        "Income Tax", "Tax Provision",
    ],
    "% Effective Tax Rate": [
        "Effective Tax Rate", "Tax Rate %", "Effective Tax Rate %",
    ],
    "Earnings From Continuing Operations": [
        "Income from Continuing Operations", "Earnings from Cont. Ops",
        "Income From Continuing Ops",
    ],
    "Earnings From Discontinued Operations": [
        "Income from Discontinued Operations",
        "Income From Discontinued Ops",
    ],
    "Minority Interest Expense": [
        "Minority Interest", "Non-Controlling Interest Expense",
        "Noncontrolling Interest",
    ],
    "Net Income to Company": [
        "Net Income", "Net Income to Firm",
    ],
    "Net Income to Common Incl Extra Items": [
        "Net Income to Common", "Net Income Available to Common",
        "Net Income Attributable to Common", "Net Income (Common)",
        "Net Income Avail to Common", "Net Income to Common Shareholders",
        "Net Income Available To Common Shareholders",
    ],
    "Diluted EPS": [
        "EPS (Diluted)", "Earnings Per Share (Diluted)",
        "EPS Diluted", "Diluted Earnings Per Share",
    ],
    "Basic EPS": [
        "EPS (Basic)", "Earnings Per Share (Basic)",
        "EPS Basic", "Basic Earnings Per Share",
    ],
    "Normalized Diluted EPS": [
        "Normalized EPS", "Adjusted EPS", "Adj. EPS",
        "Normalized Earnings Per Share",
    ],
    "Dividends Per Share": [
        "Dividend Per Share", "DPS", "Dividends per Share",
        "Cash Dividends Per Share",
    ],
    "Payout Ratio %": [
        "Payout Ratio", "Dividend Payout Ratio",
        "Dividend Payout Ratio %",
    ],
    "Weighted Average Diluted Shares Outstanding": [
        "Diluted Shares Outstanding", "Weighted Avg. Diluted Shares",
        "Diluted Weighted Average Shares", "Wtd. Avg. Diluted Shares Out.",
        "Wtd Avg Diluted Shares Out", "Diluted Shares",
        "Weighted Avg Diluted Shares Outstanding",
        "Weighted Average Diluted Shares Out.",
        "Weighted Average Diluted Shares Out",
    ],
    "Normalized EBITDA": [
        "Adjusted EBITDA", "Adj. EBITDA", "Normalized EBITDA (TIKR)",
    ],
    "Depreciation & Amortization (from IS Supplemental)": [
        "Depreciation & Amortization", "D&A",
        "Depreciation and Amortization", "Depreciation & Amort.",
        "Depreciation And Amortization",
    ],
    "Revenue As Reported": ["Revenue as Reported"],
    "Operating Income As Reported": ["Operating Income as Reported"],
    "Net Interest Income": [
        "Net Interest Inc.", "Net Interest Revenue",
    ],

    # --- Balance Sheet ---
    "Cash And Equivalents": [
        "Cash & Equivalents", "Cash and Cash Equivalents",
        "Cash & Cash Equivalents", "Cash",
    ],
    "Short Term Investments": [
        "Short-Term Investments", "Marketable Securities",
        "Current Investments",
    ],
    "Total Cash And Short Term Investments": [
        "Total Cash & Short-Term Investments",
        "Cash and Short-Term Investments",
        "Total Cash & Short Term Investments",
        "Total Cash And Short-Term Investments",
    ],
    "Accounts Receivable": [
        "Trade Receivables", "Trade and Other Receivables",
        "Receivables", "Accounts Receivable, Net",
    ],
    "Total Inventory": [
        "Inventories", "Inventory", "Total Inventories",
    ],
    "Total Current Assets": [
        "Current Assets, Total", "Current Assets",
    ],
    "Net Property Plant And Equipment": [
        "Net PP&E", "Property, Plant & Equipment, Net",
        "Property Plant and Equipment Net",
        "Net Property, Plant and Equipment",
        "Net Property, Plant & Equipment",
        "PP&E, Net",
    ],
    "Gross Property Plant And Equipment": [
        "Gross PP&E", "Property, Plant & Equipment, Gross",
        "Total Property, Plant and Equipment",
        "Property, Plant & Equipment",
    ],
    "Accumulated Depreciation": [
        "Accum. Depreciation", "Less: Accumulated Depreciation",
        "Accumulated Depreciation & Amortization",
    ],
    "Construction In Progress": [
        "Construction in Progress", "CIP",
    ],
    "Long-term Investments": [
        "Long-Term Investments", "Long Term Investments",
        "LT Investments", "Non-Current Investments",
    ],
    "Other Intangibles": [
        "Other Intangible Assets", "Intangible Assets",
        "Intangibles", "Net Intangible Assets",
    ],
    "Accounts Payable": [
        "Trade Payables", "Trade and Other Payables",
        "Payables",
    ],
    "Current Debt": [
        "Short-Term Debt", "Short Term Debt",
        "Current Portion of Long-Term Debt",
        "Current Portion of LT Debt",
        "Short-Term Borrowings",
    ],
    "Total Current Liabilities": [
        "Current Liabilities, Total", "Current Liabilities",
    ],
    "Long-Term Debt": [
        "Long Term Debt", "LT Debt", "Non-Current Debt",
        "Long-term Debt",
    ],
    "Long-Term Debt and Capital Leases": [
        "LT Debt & Capital Leases", "Long-Term Debt & Leases",
        "Long Term Debt and Capital Leases",
        "Long-Term Debt And Capital Leases",
    ],
    "Deferred Tax Liability Non Current": [
        "Deferred Tax Liabilities", "Non-Current Deferred Tax",
        "Deferred Tax Liability", "Deferred Income Taxes",
    ],
    "Common Stock": [
        "Common Stock Par Value", "Common Shares",
    ],
    "Retained Earnings": [
        "Retained Earnings (Deficit)", "Accumulated Deficit",
    ],
    "Treasury Stock": [
        "Treasury Shares", "Treasury stock",
    ],
    "Total Common Equity": [
        "Common Equity", "Total Stockholders' Equity",
        "Total Shareholders Equity", "Stockholders Equity",
        "Total Stockholders Equity",
    ],
    "Minority Interest": [
        "Non-Controlling Interest", "Non Controlling Interest",
        "Noncontrolling Interest", "Noncontrolling Interests",
    ],
    "Total Equity": [
        "Total Shareholders' Equity", "Total Stockholders' Equity",
        "Shareholders Equity", "Total Shareholders Equity",
    ],
    "Total Shares Out. on Filing Date": [
        "Shares Outstanding", "Total Shares Outstanding",
        "Common Shares Outstanding", "Shares Out. on Filing Date",
        "Total Shares Out on Filing Date",
    ],
    "Net Debt": ["Net Financial Debt"],

    # --- Cash Flow ---
    "Depreciation": [
        "Depreciation Expense",
    ],
    "Total Depreciation & Amortization": [
        "Depreciation & Amortization", "D&A",
        "Depreciation and Amortization", "Total D&A",
        "Depreciation And Amortization",
    ],
    "Change In Inventories": [
        "Decrease (Increase) in Inventories", "Change in Inventories",
        "(Increase) Decrease in Inventories",
    ],
    "Change In Payable": [
        "Increase (Decrease) in Payables", "Change in Accounts Payable",
        "Change in Payables", "Increase (Decrease) in Accounts Payable",
    ],
    "Other CFO Items": [
        "Other Operating Activities", "Other CFO",
    ],
    "Cash from Operations": [
        "Cash From Operating Activities", "Operating Cash Flow",
        "Net Cash from Operations", "Net Cash From Operating Activities",
        "Cash Flow from Operations",
    ],
    "Memo: Change in Net Working Capital": [
        "Change in Working Capital", "Change in Net Working Capital",
        "Changes in Working Capital",
    ],
    "Capital Expenditure": [
        "Capital Expenditures", "CapEx", "CAPEX",
        "Purchases of Property, Plant and Equipment",
        "Purchases of PP&E",
    ],
    "Cash Acquisitions": [
        "Acquisitions", "Business Acquisitions",
        "Acquisition of Businesses",
    ],
    "Investment in Marketable and Equity Securities": [
        "Purchases of Investments", "Investment Securities",
        "Purchase of Investments",
    ],
    "Other CFI Items": [
        "Other Investing Activities", "Other CFI",
    ],
    "Cash from Investing": [
        "Cash From Investing Activities", "Net Cash from Investing",
        "Net Cash From Investing Activities",
        "Cash Flow from Investing",
    ],
    "Total Debt Issued": [
        "Proceeds from Debt", "Debt Issued", "Issuance of Debt",
        "Proceeds from Borrowings",
    ],
    "Total Debt Repaid": [
        "Debt Repaid", "Repayment of Debt", "Repayments of Debt",
        "Debt Repayment",
    ],
    "Issuance of Common Stock": [
        "Proceeds from Issuance of Stock", "Issuance of Stock",
        "Stock Issuance",
    ],
    "Repurchase of Common Stock": [
        "Stock Repurchases", "Share Repurchases", "Buybacks",
        "Purchase of Common Stock", "Share Buybacks",
    ],
    "Total Dividends Paid": [
        "Dividends Paid", "Cash Dividends Paid",
        "Payment of Dividends",
    ],
    "Other Financing Activities": [
        "Other Financing", "Other CFF Items",
    ],
    "Cash from Financing": [
        "Cash From Financing Activities", "Net Cash from Financing",
        "Net Cash From Financing Activities",
        "Cash Flow from Financing",
    ],
    "Changes In Cash": [
        "Change in Cash", "Net Change in Cash",
        "Net Increase (Decrease) in Cash",
    ],
    "Foreign Exchange Rate Adjustments": [
        "FX Adjustments", "Effect of Exchange Rate Changes",
        "Effect of FX on Cash", "Foreign Exchange Effects",
    ],
    "Cash and Cash Equivalents, Beginning of Period": [
        "Cash, Beginning of Period", "Beginning Cash",
        "Cash at Beginning of Period",
    ],
    "Cash and Cash Equivalents, End of Period": [
        "Cash, End of Period", "Ending Cash",
        "Cash at End of Period",
    ],
    "Free Cash Flow": ["FCF", "Free cash flow"],
    "% Free Cash Flow Margins": [
        "FCF Margin %", "Free Cash Flow Margin",
        "Free Cash Flow Margins", "% FCF Margins",
        "% Free Cash Flow Margin",
    ],
    "Cash Flow from Operations before NWC": [
        "CFO before NWC", "Cash from Ops before NWC",
    ],

    # --- Ratios: Returns ---
    "Return on Assets %": [
        "Return on Assets", "ROA %", "ROA",
        "Return On Assets %",
    ],
    "Return on Invested Capital %": [
        "Return on Invested Capital", "ROIC %", "ROIC",
    ],
    "Return On Equity %": [
        "Return on Equity", "ROE %", "ROE",
        "Return on Equity %",
    ],
    "Normalized ROIC %": [
        "Normalized ROIC", "Adjusted ROIC", "Adj. ROIC",
    ],

    # --- Ratios: Margins ---
    "Gross Profit Margin %": [
        "Gross Margin %", "Gross Margin", "Gross Profit Margin",
    ],
    "EBITDA Margin %": [
        "EBITDA Margin", "EBITDA Margins %",
    ],
    "EBIT Margin %": [
        "EBIT Margin", "Operating Margin %", "Operating Margin",
    ],
    "EBT Margin %": [
        "EBT Margin", "Pre-Tax Margin %",
    ],
    "Net Income Margin %": [
        "Net Margin %", "Net Margin", "Net Income Margin",
        "Net Profit Margin %", "Net Profit Margin",
    ],
    "Normalized Net Income Margin %": [
        "Normalized Net Margin", "Adj. Net Income Margin",
    ],
    "Effective Tax Rate %": [
        "Effective Tax Rate", "ETR", "Tax Rate",
    ],
    "Free Cash Flow Margin %": [
        "FCF Margin %", "FCF Margin", "Free Cash Flow Margin",
    ],
    "Free / Net Income %": [
        "FCF / Net Income", "Free Cash Flow / Net Income",
        "FCF/NI", "FCF / NI",
    ],
    "Capex / Sales %": [
        "CapEx/Sales", "Capital Expenditure / Sales",
        "Capex / Revenue %", "CapEx / Sales",
    ],
    "Capex / EBITDA %": [
        "CapEx/EBITDA", "Capital Expenditure / EBITDA",
        "CapEx / EBITDA",
    ],

    # --- Ratios: Efficiency ---
    "Asset Turnover": ["Total Asset Turnover"],
    "Fixed Assets Turnover": ["Fixed Asset Turnover"],
    "Receivables Turnover": ["Accounts Receivable Turnover"],
    "Inventory Turnover": ["Inventories Turnover"],
    "Avg. Days Sales Outstanding": [
        "Days Sales Outstanding", "DSO",
        "Avg Days Sales Outstanding",
    ],
    "Avg. Days Outstanding Inventory": [
        "Days Inventory Outstanding", "DIO", "Days Inventory",
        "Avg Days Outstanding Inventory",
    ],
    "Avg. Days Payable Outstanding": [
        "Days Payable Outstanding", "DPO", "Days Payable",
        "Avg Days Payable Outstanding",
    ],
    "Avg. Cash Conversion Cycle": [
        "Cash Conversion Cycle", "CCC",
        "Avg Cash Conversion Cycle",
    ],

    # --- Ratios: Solvency ---
    "Assets / Equity": [
        "Assets to Equity", "Equity Multiplier",
        "Assets/Equity",
    ],
    "Total Debt / Equity": [
        "Debt to Equity", "Debt/Equity", "D/E Ratio",
        "Total Debt/Equity",
    ],
    "Debt / Assets": [
        "Debt to Assets", "Total Debt/Assets", "Debt/Assets",
    ],
    "Common Equity / Assets": [
        "Equity to Assets", "Equity/Assets",
        "Common Equity/Assets",
    ],
    "LT Debt / Capital": [
        "Long-Term Debt / Capital", "LT Debt/Capital",
        "Long Term Debt / Capital",
    ],
    "EBIT / Interest Expense": [
        "Interest Coverage", "Interest Coverage Ratio",
        "Times Interest Earned", "EBIT/Interest Expense",
    ],

    # --- Ratios: Per Share ---
    "Sales Per Share": ["Revenue Per Share"],
    "Book Value Per Share": ["BV Per Share", "BVPS"],
    "Tangible Book Value Per Share": ["Tangible BV Per Share", "TBVPS"],
    "CFO Per Share": ["Cash Flow from Ops Per Share"],
    "FCF Per Share": ["Free Cash Flow Per Share", "FCFPS"],
    "Working Capital Per Share": ["WC Per Share"],

    # --- Valuation: Trailing ---
    "EV/Revenue": ["EV / Revenue", "Enterprise Value/Revenue", "EV/Rev"],
    "Price/Sales": ["P/S", "P/S Ratio", "Price to Sales", "Price / Sales"],
    "EV/EBITDA": ["EV / EBITDA", "Enterprise Value/EBITDA"],
    "EV/EBIT": ["EV / EBIT", "Enterprise Value/EBIT"],
    "EV/FCF": ["EV / FCF", "Enterprise Value/FCF"],
    "P/E Ratio": [
        "P/E", "Price/Earnings", "PE Ratio", "Price to Earnings",
        "Price / Earnings",
    ],
    "Normalized P/E Ratio": [
        "Normalized P/E", "Adj. P/E", "Adjusted P/E",
        "Normalized PE Ratio",
    ],
    "P/B Ratio": [
        "P/B", "Price/Book", "Price to Book", "Price / Book",
    ],
    "FCF Yield": [
        "Free Cash Flow Yield", "FCF Yield %",
    ],
    "Earning Yield": [
        "Earnings Yield", "Earning Yield %", "Earnings Yield %",
    ],
    "Trailing Dividend Yield": [
        "Trailing Div Yield", "Dividend Yield (Trailing)",
        "Trailing Dividend Yield %",
    ],

    # --- Valuation: Forward ---
    "EV/Forward Revenue": [
        "EV / Fwd Revenue", "Forward EV/Revenue",
        "EV/Fwd Revenue", "EV / Forward Revenue",
    ],
    "EV/Forward EBITDA": [
        "EV / Fwd EBITDA", "Forward EV/EBITDA",
        "EV/Fwd EBITDA", "EV / Forward EBITDA",
    ],
    "EV/Forward EBIT": [
        "EV / Fwd EBIT", "Forward EV/EBIT",
        "EV/Fwd EBIT", "EV / Forward EBIT",
    ],
    "Forward P/E Ratio": [
        "Fwd P/E", "Forward P/E", "Forward PE",
        "Forward PE Ratio", "Fwd PE",
    ],
    "Forward Dividend Yield": [
        "Fwd Dividend Yield", "Fwd Div Yield",
        "Forward Div Yield",
    ],
    "Forward Earning Yield": [
        "Fwd Earning Yield", "Fwd Earnings Yield",
        "Forward Earnings Yield",
    ],
    "PEG Ratio": ["PEG"],

    # --- Multiples ---
    "NTM EV / Revenue": ["NTM EV/Revenue", "NTM EV / Rev"],
    "NTM Price / Sales": ["NTM P/S", "NTM Price/Sales"],
    "NTM EV / EBITDA": ["NTM EV/EBITDA"],
    "NTM EV / EBIT": ["NTM EV/EBIT"],
    "NTM Normalized P/E": ["NTM Norm P/E", "NTM Normalized PE"],
    "NTM Mkt Cap / LFCF": ["NTM Mkt Cap/LFCF", "NTM MCap / LFCF"],
    "NTM LFCF Yield": ["NTM LFCF Yield %"],
    "NTM Dividend Yield": ["NTM Div Yield", "NTM Dividend Yield %"],
    "LTM EV / Revenue": ["LTM EV/Revenue", "LTM EV / Rev"],
    "LTM Price / Sales": ["LTM P/S", "LTM Price/Sales"],
    "LTM EV / Gross Profit": ["LTM EV/Gross Profit"],
    "LTM EV / EBITDA": ["LTM EV/EBITDA"],
    "LTM EV / EBIT": ["LTM EV/EBIT"],
    "LTM Diluted P/E": ["LTM Diluted PE", "LTM P/E (Diluted)"],
    "LTM Price / Book": ["LTM P/B", "LTM Price/Book"],
    "LTM Price / Tangible Book": ["LTM P/TB", "LTM Price/Tangible Book"],
    "LTM EV / ULFCF": ["LTM EV/ULFCF"],
    "LTM Mkt Cap / LFCF": ["LTM Mkt Cap/LFCF", "LTM MCap / LFCF"],
    "LTM Dividend Yield": ["LTM Div Yield", "LTM Dividend Yield %"],
    "TEV ($mm)": ["TEV", "Total Enterprise Value ($mm)", "Enterprise Value ($mm)"],
    "Mkt Cap ($mm)": [
        "Market Cap ($mm)", "Market Capitalization ($mm)", "Mkt Cap",
        "Market Cap", "Market Capitalization",
    ],

    # --- Street Targets ---
    "Price Close": ["Close Price", "Last Price", "Current Price"],
    "Target Stock Price Mean": [
        "Mean Target Price", "Avg Target Price", "Target Price Mean",
        "Target Price (Mean)", "Consensus Target Price",
    ],
    "Target Stock Price Median": [
        "Median Target Price", "Target Price Median",
        "Target Price (Median)",
    ],
    "Target Stock Price High": [
        "High Target Price", "Target Price High",
        "Target Price (High)",
    ],
    "Target Stock Price Low": [
        "Low Target Price", "Target Price Low",
        "Target Price (Low)",
    ],
    "Target Stock Price (# Est)": [
        "Number of Estimates", "# Estimates", "# of Estimates",
        "Num Estimates",
    ],
    "Target Stock Price / Close Price": [
        "Target / Close", "Target/Close Price",
    ],
    "# of Buys": ["Buys", "Buy", "Strong Buy"],
    "# of Outperforms": ["Outperforms", "Outperform", "Overweight"],
    "# of Holds": ["Holds", "Hold", "Neutral"],
    "# of Underperforms": ["Underperforms", "Underperform", "Underweight"],
    "# of Sells": ["Sells", "Sell", "Strong Sell"],

    # --- Actuals & Forward ---
    "EBT (Normalized)": ["Normalized EBT", "EBT Normalized", "Adj. EBT"],
    "Net Income (Normalized)": [
        "Normalized Net Income", "Net Income Normalized",
        "Adj. Net Income",
    ],
    "EPS (Normalized)": [
        "Normalized EPS", "EPS Normalized", "Adj. EPS",
    ],
    "EPS (GAAP)": ["GAAP EPS", "EPS GAAP", "Reported EPS"],
    "Dividend Per Share": ["Dividends Per Share", "DPS"],
    "Gross Margin": ["Gross Profit Margin", "Gross Margins"],
    "Net Debt / EBITDA": [
        "Net Debt/EBITDA", "ND/EBITDA", "Net Leverage",
    ],
    "ROE": ["Return on Equity", "Return On Equity"],
    "ROA": ["Return on Assets", "Return On Assets"],
    "TEV": ["Total Enterprise Value", "Enterprise Value"],
    "Market Cap": ["Market Capitalization", "Mkt Cap"],

    # --- QE Section 1 ---
    "% EBITDA Margins": [
        "EBITDA Margins", "EBITDA Margin %", "EBITDA Margin",
        "% EBITDA Margin",
    ],
    "EBIT Margins": ["EBIT Margin", "EBIT Margin %", "EBIT Margins %"],
    "Adjusted EPS": ["Adj. EPS", "Adj EPS", "Normalized EPS"],
    "EPS GAAP": ["GAAP EPS", "EPS (GAAP)", "Reported EPS"],
    "CFO": ["Cash from Operations", "Operating Cash Flow", "Cash From Ops"],
    "CAPEX": ["Capital Expenditure", "Capital Expenditures", "CapEx"],
    "FCF": ["Free Cash Flow", "Free cash flow"],

    # --- QE Section 2 (Avg. Estimated / Actual triplets) ---
    "Avg. Estimated Revenue": [
        "Avg Estimated Revenue", "Average Estimated Revenue",
        "Avg. Est. Revenue", "Consensus Revenue",
    ],
    "Actual Revenue": ["Revenue (Actual)", "Reported Revenue"],
    "Avg. Estimated EBITDA": [
        "Avg Estimated EBITDA", "Average Estimated EBITDA",
        "Avg. Est. EBITDA", "Consensus EBITDA",
    ],
    "Actual EBITDA": ["EBITDA (Actual)", "Reported EBITDA"],
    "Avg. Estimated EBIT": [
        "Avg Estimated EBIT", "Average Estimated EBIT",
        "Avg. Est. EBIT",
    ],
    "Actual EBIT": ["EBIT (Actual)", "Reported EBIT"],
    "Avg. Estimated Net Income": [
        "Avg Estimated Net Income", "Average Estimated Net Income",
        "Avg. Est. Net Income",
    ],
    "Actual Net Income": ["Net Income (Actual)", "Reported Net Income"],
    "Avg. Estimated Adjusted EPS": [
        "Avg Estimated Adjusted EPS", "Average Estimated Adj EPS",
        "Avg. Est. Adjusted EPS", "Consensus EPS",
    ],
    "Actual Adjusted EPS": [
        "Adjusted EPS (Actual)", "Reported Adjusted EPS",
    ],
    "Avg. Estimated EPS GAAP": [
        "Avg Estimated EPS GAAP", "Average Estimated EPS GAAP",
        "Avg. Est. EPS GAAP",
    ],
    "Actual EPS GAAP": ["EPS GAAP (Actual)", "Reported EPS GAAP"],
    "Avg. Estimated CFO": [
        "Avg Estimated CFO", "Average Estimated CFO",
        "Avg. Est. CFO",
    ],
    "Actual CFO": ["CFO (Actual)", "Reported CFO"],
    "Avg. Estimated CAPEX": [
        "Avg Estimated CAPEX", "Average Estimated CAPEX",
        "Avg. Est. CAPEX",
    ],
    "Actual CAPEX": ["CAPEX (Actual)", "Reported CAPEX"],
    "Avg. Estimated FCF": [
        "Avg Estimated FCF", "Average Estimated FCF",
        "Avg. Est. FCF",
    ],
    "Actual FCF": ["FCF (Actual)", "Reported FCF"],
}
