import pytest

from fundprint.classify import asset_class, classify_isin, UNCLASSIFIED

CASES = [
    ("Open Ended Schemes(Equity Scheme - Flexi Cap Fund)", "X Flexi Cap", "Equity"),
    ("Open Ended Schemes(Debt Scheme - Liquid Fund)", "X Liquid", "Debt"),
    ("Open Ended Schemes(Hybrid Scheme - Aggressive Hybrid Fund)", "X Hybrid", "Hybrid"),
    ("Open Ended Schemes(Other Scheme - Index Funds)", "X Nifty 50 Index Fund", "Equity"),
    ("Open Ended Schemes(Other Scheme - Index Funds)", "X CRISIL IBX SDL Index Fund", "Debt"),
    ("Open Ended Schemes(Other Scheme - Other ETFs)", "X Gold ETF", "Commodity"),
    ("Open Ended Schemes(Other Scheme - FoF Domestic)", "X Gold and Silver FoF", "Commodity"),
    ("Open Ended Schemes(Other Scheme - FoF Overseas)", "X Global FoF", "Other"),
    ("Something unexpected", "X", "Other"),
]


@pytest.mark.parametrize("cat,name,expected", CASES)
def test_rules(cat, name, expected):
    assert asset_class(cat, name) == expected


def test_unclassified():
    assert classify_isin(None, "X", {}) == UNCLASSIFIED
    assert classify_isin("INF9", "X", {}) == UNCLASSIFIED


@pytest.mark.parametrize("name", [
    "X Overnight Fund Index", "X Nifty 10 yr Benchmark G-Sec Index Fund", "X Gilt Index Fund",
    "X Treasury Bill ETF", "X Floater Index", "X Target Maturity 2030 Index",
])
def test_index_fund_debt_names(name):
    assert asset_class("Open Ended Schemes(Other Scheme - Index Funds)", name) == "Debt"


@pytest.mark.parametrize("cat,expected", [
    ("Open Ended Schemes(Exchange Traded Funds (ETFs) - Equity ETF)", "Equity"),
    ("Open Ended Schemes(Exchange Traded Funds (ETFs) - Debt ETF)", "Debt"),
    ("Open Ended Schemes(Exchange Traded Funds (ETFs) - Silver ETF)", "Commodity"),
    ("Close Ended Schemes(ELSS)", "Equity"),
    ("Open Ended Schemes(Gilt)", "Debt"),
])
def test_amfi_edge_categories(cat, expected):
    assert asset_class(cat, "Some Fund") == expected
