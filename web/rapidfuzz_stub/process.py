from . import fuzz as _fuzz


def extractOne(query, choices, *, scorer=_fuzz.ratio, processor=None, score_cutoff=None, **_):
    """Best match as (choice, score, position), or None if nothing reaches the cutoff."""
    best = None
    q = processor(query) if processor else query
    for i, choice in enumerate(choices):
        c = processor(choice) if processor else choice
        score = scorer(q, c)
        if best is None or score > best[1]:
            best = (choice, score, i)
    if best is None or (score_cutoff is not None and best[1] < score_cutoff):
        return None
    return best


def extract(query, choices, *, limit=5, **kw):
    scored = []
    for i, ch in enumerate(choices):
        r = extractOne(query, [ch], **kw)
        if r:
            scored.append((ch, r[1], i))
    return sorted(scored, key=lambda x: -x[1])[:limit]
