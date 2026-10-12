import re


def default_process(s):
    """Lower-case, and turn anything that is not a letter or digit into a space."""
    return re.sub(r"[\W_]+", " ", str(s), flags=re.UNICODE).lower().strip()
