from difflib import SequenceMatcher


def ratio(a, b, **_):
    """Similarity of two strings, 0 to 100."""
    return 100.0 * SequenceMatcher(None, a, b).ratio()


def token_sort_ratio(a, b, processor=None, **_):
    """Compare two names ignoring word order (the scorer casparser-isin uses)."""
    if processor:
        a, b = processor(a), processor(b)
    return ratio(" ".join(sorted(str(a).split())), " ".join(sorted(str(b).split())))


def partial_ratio(a, b, **_):
    return ratio(a, b)


token_set_ratio = token_sort_ratio
WRatio = token_sort_ratio
