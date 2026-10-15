"""Spot funds whose history in the statement is incomplete, and word the warning about them (spec 006).

Two checks per fund:
- partial history: units were already held on the statement's first day (`open` above zero),
  so the statement starts after the first purchase.
- doesn't reconcile: opening units plus every transaction don't come to the closing units.

The warning names funds only. It never shows amounts or unit counts.
"""
import re
from typing import NamedTuple

import pandas as pd

from .insights import short_name

OPEN_TOLERANCE = 0.001      # units; above this the fund was already held when the statement starts
CLOSE_TOLERANCE = 0.01      # units; a bigger difference from the closing balance means "doesn't reconcile"
MAX_LISTED = 5              # funds named in each block before "and N more"

FEEDBACK_URL = "https://tally.so/r/2EqQGg"

PARTIAL_HEAD = ("**Some of your history is missing.** "
                "Your statement starts after you first invested in these funds:")
PARTIAL_TAIL = ("Units bought before the statement's start date aren't included in the results below, "
                "because their purchase date and cost aren't in the statement. Everything else is calculated "
                "normally.  \nFor complete results, request your statement again with an earlier start date. "
                "How to do this is just below.")
UNRECONCILED_HEAD = ("**Some funds don't add up.** The units for these funds don't match the statement's "
                     "closing balance, so their results may be off:")
UNRECONCILED_TAIL = f"If this keeps happening, please [send feedback]({FEEDBACK_URL}) (no statement needed)."


class HistoryIssues(NamedTuple):
    partial: list        # short fund names with missing history
    unreconciled: list   # short fund names whose units don't add up

    def __bool__(self):
        return bool(self.partial or self.unreconciled)


def _names(rows):
    """Short names in statement order, each once (the same fund in two folios is one fund)."""
    out = []
    for name in rows:
        n = short_name(name)
        if n not in out:
            out.append(n)
    return out


def history_issues(parsed):
    schemes, txns = parsed.schemes, parsed.txns
    opening = schemes["open"].fillna(0) if "open" in schemes else pd.Series(0.0, index=schemes.index)
    partial = schemes.scheme[opening > OPEN_TOLERANCE]

    unreconciled = []
    if "close" in schemes:
        moved = txns.groupby(["folio", "scheme"]).units.sum()
        for (folio, scheme, close), start in zip(schemes[["folio", "scheme", "close"]].itertuples(index=False),
                                                 opening):
            if pd.isna(close):
                continue
            if abs(start + moved.get((folio, scheme), 0.0) - close) > CLOSE_TOLERANCE:
                unreconciled.append(scheme)
    return HistoryIssues(_names(partial), _names(unreconciled))


_PUNCTUATION = re.compile(r"([!-/:-@\[-`{-~])")   # every ASCII punctuation mark


def plain(name):
    """A fund name made safe to place inside Markdown.

    Names come from the PDF. Escaping every punctuation mark means a name can't become a link,
    an image, HTML or a formula (audit finding FP-01); it is always shown as the text it is.
    """
    name = " ".join("".join(c if c.isprintable() else " " for c in name).split())
    return _PUNCTUATION.sub(r"\\\1", name)


def _block(head, names, tail, max_listed):
    shown = [f"- {plain(n)}" for n in names[:max_listed]]
    if len(names) > max_listed:
        shown.append(f"- and {len(names) - max_listed} more")
    return "\n\n".join([head, "\n".join(shown), tail])


def warning_text(issues, max_listed=MAX_LISTED):
    """Markdown for one warning box; an empty string when there is nothing to warn about."""
    blocks = []
    if issues.partial:
        blocks.append(_block(PARTIAL_HEAD, issues.partial, PARTIAL_TAIL, max_listed))
    if issues.unreconciled:
        blocks.append(_block(UNRECONCILED_HEAD, issues.unreconciled, UNRECONCILED_TAIL, max_listed))
    return "\n\n".join(blocks)
