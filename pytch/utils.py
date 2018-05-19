from typing import List


def splitlines(s: str) -> List[str]:
    """Don't use `str.splitlines`.

    This splits on multiple Unicode newline-like characters, which we don't
    want to include. See
    https://docs.python.org/3/library/stdtypes.html#str.splitlines
    """
    lines = s.split("\n")
    if lines[-1] == "":
        lines = lines[:-1]
    return lines


__all__ = ["splitlines"]
