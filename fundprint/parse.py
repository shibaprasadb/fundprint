"""Read a CAMS/KFintech detailed CAS and flatten it into plain tables.

Privacy: nothing here is cached, logged or written to disk. The PDF is read
from memory only, and error messages never contain anything from the file.
"""
import logging
from dataclasses import dataclass
from io import BytesIO

import pandas as pd


# The PDF libraries write a debug line for almost every token they read. Some hosts
# (the browser build sets the root logger to DEBUG and forwards every line to the page)
# turn that into hundreds of thousands of messages, which freezes or crashes the tab.
# Keep these libraries to warnings and errors only.
for _name in ("pdfminer", "casparser", "casparser_isin"):
    logging.getLogger(_name).setLevel(logging.WARNING)


class CasError(Exception):
    """A problem we can safely show to the user (never contains statement data)."""


@dataclass
class ParsedCas:
    txns: pd.DataFrame      # one row per transaction that changes units
    schemes: pd.DataFrame   # one row per fund: folio, scheme, isin, nav, nav_date
    period_start: pd.Timestamp | None
    period_end: pd.Timestamp | None


def read_pdf(pdf_bytes, password=""):
    """Open the PDF in memory and return casparser's data as a plain dict."""
    import casparser  # imported here so the rest of the package works without it

    try:
        cas = casparser.read_cas_pdf(BytesIO(pdf_bytes), password or "")
    except Exception as exc:  # deliberately generic: tracebacks can leak values
        name = type(exc).__name__
        if "Incorrect" in name or "Password" in name:
            raise CasError("That password didn't work for this statement.") from None
        raise CasError(
            "Couldn't read this statement. Is it a CAMS/KFintech detailed CAS?"
        ) from None
    return cas.model_dump() if hasattr(cas, "model_dump") else cas


def from_dict(cas):
    """Flatten casparser's dict into a ParsedCas."""
    kind = cas.get("cas_type")
    kind = str(getattr(kind, "value", kind) or "").upper()
    if kind == "SUMMARY":
        raise CasError("This looks like a Summary CAS. Please request the Detailed one.")

    txns, schemes = [], []
    for folio in cas.get("folios", []):
        for s in folio.get("schemes", []):
            val = s.get("valuation") or {}
            if val.get("nav") is None:
                continue
            schemes.append({
                "folio": folio["folio"], "scheme": s["scheme"], "isin": s.get("isin"),
                "nav": float(val["nav"]), "nav_date": pd.Timestamp(val["date"]),
            })
            for t in s.get("transactions", []):
                # rows without units (stamp duty, STT, TDS) don't change holdings
                if t.get("units") is None:
                    continue
                tkind = str(getattr(t["type"], "value", t["type"]))
                amount = float(t.get("amount") or 0)
                # reinvested dividends came out of the fund's own NAV, not the
                # investor's pocket, so they cost nothing
                if tkind == "DIVIDEND_REINVEST":
                    amount = 0.0
                txns.append({
                    "folio": folio["folio"], "scheme": s["scheme"], "isin": s.get("isin"),
                    "date": pd.Timestamp(t["date"]), "kind": tkind,
                    "units": float(t["units"]), "amount": amount,
                })
    if not schemes:
        raise CasError("Couldn't find any funds in this statement.")

    period = cas.get("statement_period") or {}
    def _ts(v):
        return pd.Timestamp(v) if v else None
    return ParsedCas(
        pd.DataFrame(txns, columns=["folio", "scheme", "isin", "date", "kind", "units", "amount"]),
        pd.DataFrame(schemes),
        _ts(period.get("from_") or period.get("from")), _ts(period.get("to")),
    )


def parse_cas(pdf_bytes, password=""):
    return from_dict(read_pdf(pdf_bytes, password))
