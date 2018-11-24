from typing import List

import attr


Offset = int
"""A zero-indexed offset into a file."""


@attr.s(auto_attribs=True, frozen=True)
class OffsetRange:
    start: Offset
    """The inclusive start offset of the range."""

    end: Offset
    """The exclusive end offset of the range."""


@attr.s(auto_attribs=True, frozen=True)
class Position:
    line: int
    character: int


@attr.s(auto_attribs=True, frozen=True)
class Range:
    start: Position
    end: Position


@attr.s(auto_attribs=True)
class FileInfo:
    file_path: str
    source_code: str
    lines: List[str] = attr.ib(init=False)

    def __attrs_post_init__(self) -> None:
        self.lines = splitlines(self.source_code)

    def get_position_for_offset(self, offset: int) -> Position:
        # 0-based index ranges are inclusive on the left and exclusive on the
        # right, which means that the length of the source code is a valid
        # index for constructing a range.
        assert (
            0 <= offset <= len(self.source_code)
        ), f"offset {offset} is not in range [0, {len(self.source_code)}]"

        current_offset = 0
        current_line = 0

        # Add 1 to the length of the line to account for the removed "\n"
        # character.
        while (
            current_line < len(self.lines)
            and current_offset + len(self.lines[current_line]) + 1 <= offset
        ):
            current_offset += len(self.lines[current_line]) + 1
            current_line += 1
        character = offset - current_offset
        return Position(line=current_line, character=character)

    def get_range_from_offset_range(self, offset_range: OffsetRange) -> Range:
        return Range(
            start=self.get_position_for_offset(offset_range.start),
            end=self.get_position_for_offset(offset_range.end),
        )


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
