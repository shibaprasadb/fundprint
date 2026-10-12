"""Work out whether a fund is Equity, Debt, Hybrid, Commodity or Other.

AMFI publishes a category for every scheme. We match on ISIN (Direct and
Regular plans have different ISINs, so no fuzzy matching is needed). Funds
with no ISIN or no match are "Unclassified" and the user can set them by hand.
"""
import re

ASSET_CLASSES = ["Equity", "Debt", "Hybrid", "Commodity", "Other"]
UNCLASSIFIED = "Unclassified"

# Words in a scheme name that tell us what an index fund / ETF / FoF holds.
# Checked top to bottom, first match wins.
NAME_RULES = [
    (re.compile(r"gold|silver|commodity", re.I), "Commodity"),
    (re.compile(r"sdl|g-?sec|gilt|bond|target maturity|crisil.*(ibx|index)|t-?bill|treasury|liquid|overnight|money market|ultra short|low duration|short duration|floater|floating|10 ?yr|fixed maturity|fmp", re.I), "Debt"),
    (re.compile(r"nifty|sensex|equity|bse|midcap|smallcap|momentum|quality|alpha|low vol|nasdaq|s&p", re.I), "Equity"),
]

# AMFI category prefix -> asset class. "Other Scheme" is handled by name rules.
CATEGORY_PREFIX_RULES = [
    ("Equity Scheme", "Equity"),
    ("Debt Scheme", "Debt"),
    ("Hybrid Scheme", "Hybrid"),
    # older AMFI wording still used for some rows (incl. closed-ended schemes)
    ("Income/Debt Oriented", "Debt"),
    ("Income", "Debt"),
    ("Growth/Equity Oriented", "Equity"),
    ("Growth", "Equity"),
    ("Balanced", "Hybrid"),
    ("ELSS", "Equity"),
    ("Gilt", "Debt"),
    ("Index Funds - Hybrid", "Hybrid"),
    ("Index Funds - Equity", "Equity"),
    ("Index Funds - Debt", "Debt"),
]


ETF_SUBCATEGORIES = [
    ("Equity ETF", "Equity"), ("Debt ETF", "Debt"), ("Gold ETF", "Commodity"),
    ("Silver ETF", "Commodity"), ("Hybrid ETF", "Hybrid"),
]


def category_text(raw_header):
    """'Open Ended Schemes(Equity Scheme - Flexi Cap Fund)' -> 'Equity Scheme - Flexi Cap Fund'."""
    m = re.search(r"\((.*)\)\s*$", raw_header)
    return (m.group(1) if m else raw_header).strip()


def _by_name(name):
    for pattern, asset_class in NAME_RULES:
        if pattern.search(name):
            return asset_class
    return "Other"


def asset_class(amfi_category, scheme_name):
    """Map an AMFI category (plus the scheme name) to one of ASSET_CLASSES."""
    cat = category_text(amfi_category or "")
    for prefix, result in CATEGORY_PREFIX_RULES:
        if cat.startswith(prefix):
            return result
    # ETF sub-categories say what the fund holds, so trust them before the name
    for tail, result in ETF_SUBCATEGORIES:
        if cat.startswith("Exchange Traded Funds") and cat.endswith(tail):
            return result
    if cat.startswith("Other Scheme") or cat.startswith("Exchange Traded Funds") or cat.startswith("Fund of Funds Scheme"):
        if re.search(r"FoF", cat, re.I):
            # Fund of funds: only gold/silver is clear from the name
            return "Commodity" if re.search(r"gold|silver", scheme_name or "", re.I) else "Other"
        return _by_name(scheme_name or "")
    return "Other"


def classify_isin(isin, scheme_name, categories):
    """Look an ISIN up in the public categories table; 'Unclassified' if missing."""
    row = categories.get(isin) if isin else None
    if not row:
        return UNCLASSIFIED
    return row["asset_class"]
