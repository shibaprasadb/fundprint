"""Stand-in for rapidfuzz, which has no browser build.

casparser-isin only uses it to guess a fund when a statement has no ISIN.
We handle missing ISINs ourselves, so these functions find nothing.
"""
from . import fuzz, process, utils  # noqa: F401
