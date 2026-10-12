"""A small pure-Python stand-in for rapidfuzz, which has no browser build.

casparser-isin uses it in one place: choosing the closest fund name when a fund
matches several rows in its ISIN database. This version gives the same kind of
answer (best name, a 0-100 score, its position) using Python's difflib.
"""
from . import fuzz, process, utils  # noqa: F401
