from typing import List


Offset = int
"""A zero-indexed offset into a file."""


class OffsetRange:
    def __init__(self, start: Offset, end: Offset) -> None:
        self._start = start
        self._end = end

    @property
    def start(self) -> Offset:
        """The inclusive start offset of the range."""
        return self._start

    @property
    def end(self) -> Offset:
        """The exclusive end offset of the range."""
        return self._end


class Position:
    def __init__(self, line: int, character: int) -> None:
        self._line = line
        self._character = character

    @property
    def line(self) -> int:
        return self._line

    @property
    def character(self) -> int:
        return self._character


class Range:
    def __init__(self, start: Position, end: Position) -> None:
        self._start = start
        self._end = end

    @property
    def start(self) -> Position:
        """The inclusive start position of the range."""
        return self._start

    @property
    def end(self) -> Position:
        """The exclusive end position of the range."""
        return self._end


class FileInfo:
    def __init__(self, file_path: str, source_code: str) -> None:
        self._file_path = file_path
        self._source_code = source_code
        self._lines = source_code.splitlines()

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def source_code(self) -> str:
        return self._source_code

    @property
    def lines(self) -> List[str]:
        return list(self._lines)

    def get_position_for_offset(self, offset: int) -> Position:
        # 0-based index ranges are inclusive on the left and exclusive on the
        # right, which means that the length of the source code is a valid
        # index for constructing a range.
        assert offset <= len(self._source_code)

        current_offset = 0
        current_line = 0

        # Add 1 to the length of the line to account for the removed "\n"
        # character.
        while (
            current_line < len(self._lines)
            and current_offset + len(self._lines[current_line]) + 1 <= offset
        ):
            current_offset += len(self._lines[current_line]) + 1
            current_line += 1
        character = offset - current_offset
        return Position(line=current_line, character=character)


__all__ = ["FileInfo", "Position", "Range"]
