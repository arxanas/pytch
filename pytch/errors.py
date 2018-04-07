import collections
from enum import Enum
import itertools
import re
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

import click
from typing_extensions import Protocol

from . import FileInfo, Range

T = TypeVar("T")


class ErrorCode(Enum):
    UNEXPECTED_TOKEN = 1000
    EXPECTED_EXPRESSION = 1001
    EXPECTED_LPAREN = 1002
    EXPECTED_RPAREN = 1003
    EXPECTED_PATTERN = 1004
    EXPECTED_EQUALS = 1005
    EXPECTED_DUMMY_IN = 1006
    EXPECTED_LET_EXPRESSION = 1007

    NOT_A_REAL_ERROR = 1234
    """Not a real error code, just for testing purposes."""


class Glyphs:
    """The set of glyphs to be used when printing out error messages."""

    def __init__(
        self,
        make_colored: Callable[[str, str], str],
        make_bold: Callable[[str], str],
        make_inverted: Callable[[str], str],
        box_vertical: str,
        box_horizontal: str,
        box_upper_left: str,
        box_upper_right: str,
        box_lower_left: str,
        box_lower_right: str,
        box_continuation_left: str,
        box_continuation_right: str,
        underline_start_character: str,
        underline_character: str,
        underline_end_character: str,
        underline_point_character: str,
    ) -> None:
        self.make_colored = make_colored
        self.make_bold = make_bold
        self.make_inverted = make_inverted
        self.box_vertical = box_vertical
        self.box_horizontal = box_horizontal
        self.box_upper_left = box_upper_left
        self.box_upper_right = box_upper_right
        self.box_lower_left = box_lower_left
        self.box_lower_right = box_lower_right
        self.box_continuation_left = box_continuation_left
        self.box_continuation_right = box_continuation_right
        self.underline_start_character = underline_start_character
        self.underline_character = underline_character
        self.underline_end_character = underline_end_character
        self.underline_point_character = underline_point_character


class Diagnostic(Protocol):
    @property
    def file_info(self) -> FileInfo:
        ...

    @property
    def color(self) -> str:
        ...

    @property
    def preamble_message(self) -> str:
        ...

    @property
    def message(self) -> str:
        ...

    @property
    def range(self) -> Optional[Range]:
        ...


class _DiagnosticContext:
    def __init__(
        self,
        file_info: FileInfo,
        line_range: Optional[Tuple[int, int]],
    ) -> None:
        self.file_info = file_info
        self.line_range = line_range

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _DiagnosticContext):
            return False
        return (
            self.file_info == other.file_info
            and self.line_range == other.line_range
        )


class Note:
    color = "green"
    preamble_message = "Note:"

    def __init__(
        self,
        file_info: FileInfo,
        message: str,
        range: Range = None,
    ) -> None:
        self._file_info = file_info
        self._message = message
        self._range = range

    def __repr__(self) -> str:
        return (
            f"<Note" +
            f" message={self.message!r}" +
            f" range={self.range!r}" +
            f">"
        )

    @property
    def file_info(self) -> FileInfo:
        return self._file_info

    @property
    def message(self) -> str:
        return self._message

    @property
    def range(self) -> Optional[Range]:
        return self._range


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


class Error:
    color = "red"
    preamble_message = "Error:"

    def __init__(
        self,
        file_info: FileInfo,
        code: ErrorCode,
        severity: Severity,
        message: str,
        notes: List[Note],
        range: Range = None,
    ) -> None:
        self._file_info = file_info
        self._code = code
        self._severity = severity
        self._message = message
        self._notes = notes
        self._range = range

    def __repr__(self) -> str:
        return (
            f"<Error" +
            f" code={self.code!r}" +
            f" severity={self.severity!r}" +
            f" message={self.message!r}" +
            f" notes={self.notes!r}" +
            f" range={self.range!r}" +
            f">"
        )

    @property
    def file_info(self) -> FileInfo:
        return self._file_info

    @property
    def code(self) -> ErrorCode:
        return self._code

    @property
    def severity(self) -> Severity:
        return self._severity

    @property
    def message(self) -> str:
        return self._message

    @property
    def notes(self) -> List[Note]:
        return self._notes

    @property
    def range(self) -> Optional[Range]:
        return self._range


def get_colored_diagnostic_message(
    glyphs: Glyphs,
    diagnostic: Diagnostic,
) -> str:
    return glyphs.make_colored(
        diagnostic.preamble_message + " " + diagnostic.message,
        diagnostic.color,
    )


def get_glyphs(ascii: bool) -> Glyphs:
    if ascii:
        return Glyphs(
            make_colored=lambda text, color: text,
            make_bold=lambda text: text,
            make_inverted=lambda text: text,
            box_vertical="|",
            box_horizontal="-",
            box_upper_left="+",
            box_upper_right="+",
            box_lower_left="+",
            box_lower_right="+",
            box_continuation_left="+",
            box_continuation_right="+",
            underline_start_character="^",
            underline_character="~",
            underline_end_character="~",
            underline_point_character="^",
        )
    else:
        return Glyphs(
            make_colored=lambda text, color: click.style(
                text,
                fg=color,
                bold=True,
            ),
            make_bold=lambda text: click.style(text, bold=True),
            make_inverted=lambda text: click.style(text, reverse=True),
            box_vertical="│",
            box_horizontal="─",
            box_upper_left="┌",
            box_upper_right="┐",
            box_lower_left="└",
            box_lower_right="┘",
            box_continuation_left="├",
            box_continuation_right="┤",
            underline_start_character="┕",
            underline_character="━",
            underline_end_character="┙",
            underline_point_character="↑",
        )


class Segment:
    """A box-enclosed segment of the error display.

    For example, the message

    ```
    +------------------+
    | Error: something |
    +------------------+
    ```

    or the code fragment

    ```
      +------------+
    1 | let foo =  |
    2 |   bar(baz) |
      +------------+
    ```

    constitute "segments".
    """

    def __init__(
        self,
        glyphs: Glyphs,
        header: Optional[str],
        gutter_lines: Optional[List[str]],
        message_lines: List[str],
    ) -> None:
        if gutter_lines is not None:
            assert len(gutter_lines) == len(message_lines)
        self._glyphs = glyphs
        self._header = header
        self._gutter_lines = gutter_lines
        self._message_lines = message_lines

    @property
    def gutter_width(self) -> int:
        if not self._gutter_lines:
            return 0
        num_padding_characters = len("  ")
        max_gutter_line_length = max(len(line) for line in self._gutter_lines)
        return num_padding_characters + max_gutter_line_length

    @property
    def box_width(self) -> int:
        num_box_characters = len("||")
        num_padding_characters = len("  ")
        max_message_line_length = max(
            self._line_length(line) for line in self._message_lines
        )
        return (
            num_box_characters
            + num_padding_characters
            + max_message_line_length
        )

    def _line_length(self, line: str) -> int:
        # https://stackoverflow.com/a/14693789
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        return len(ansi_escape.sub("", line))

    def render_lines(
        self,
        is_first: bool,
        is_last: bool,
        gutter_width: int,
        box_width: int,
    ) -> List[str]:
        if self._gutter_lines is None:
            gutter_lines = [""] * len(self._message_lines)
        else:
            gutter_lines = self._gutter_lines

        empty_gutter = " " * gutter_width

        lines = []

        top_line = ""
        if is_first:
            top_line += self._glyphs.box_upper_left
        else:
            top_line += self._glyphs.box_continuation_left
        top_line = top_line.ljust(box_width - 1, self._glyphs.box_horizontal)
        if is_first:
            top_line += self._glyphs.box_upper_right
        else:
            top_line += self._glyphs.box_continuation_right
        lines.append(empty_gutter + top_line)

        if self._header:
            header_line = (" " + self._header).ljust(box_width - 2)
            header_line = (
                self._glyphs.box_vertical
                + self._glyphs.make_bold(header_line)
                + self._glyphs.box_vertical
            )
            lines.append(empty_gutter + header_line)

        for gutter_line, message_line in zip(gutter_lines, self._message_lines):
            gutter = gutter_line.rjust(gutter_width - 2)
            gutter = " " + gutter + " "

            message = (
                self._glyphs.box_vertical
                + " "
                + message_line
                + (" " * (box_width - self._line_length(message_line) - 4))
                + " "
                + self._glyphs.box_vertical
            )
            lines.append(gutter + message)

        if is_last:
            footer = ""
            footer += self._glyphs.box_lower_left
            footer = footer.ljust(box_width - 1, self._glyphs.box_horizontal)
            footer += self._glyphs.box_lower_right
            lines.append(empty_gutter + footer)

        return lines


def get_error_lines(error: Error, ascii: bool = False) -> List[str]:
    glyphs = get_glyphs(ascii=ascii)

    segments = get_error_segments(glyphs=glyphs, error=error)
    gutter_width = max(segment.gutter_width for segment in segments)
    box_width = max(segment.box_width for segment in segments)

    output_lines = []
    if error.range is not None:
        line = str(error.range.start.line + 1)
        character = str(error.range.start.character + 1)
        output_lines.append(
            f"In {glyphs.make_bold(error.file_info.file_path)}, "
            f"line {glyphs.make_bold(line)}, "
            f"character {glyphs.make_bold(character)}:"
        )
    else:
        output_lines.append(
            f"In {glyphs.make_bold(error.file_info.file_path)}:"
        )
    output_lines.append(
        glyphs.make_bold(f"{error.code.name}[{error.code.value}]")
        + ": "
        + error.message
    )
    for i, segment in enumerate(segments):
        is_first = (i == 0)
        is_last = (i == len(segments) - 1)
        output_lines.extend(segment.render_lines(
            is_first=is_first,
            is_last=is_last,
            gutter_width=gutter_width,
            box_width=box_width,
        ))
    return output_lines


def get_error_segments(glyphs: Glyphs, error: Error):
    diagnostics: List[Diagnostic] = [error]
    diagnostics.extend(error.notes)
    diagnostic_contexts = [
        get_context(
            file_info=diagnostic.file_info,
            range=diagnostic.range,
        )
        for diagnostic in diagnostics
    ]
    partitioned_diagnostic_contexts = itertools.groupby(
        diagnostic_contexts,
        lambda context: context.file_info.file_path,
    )

    segments: List[Segment] = []
    for _file_path, contexts in partitioned_diagnostic_contexts:
        for context in _merge_contexts(contexts):
            segments.append(get_context_segment(
                glyphs=glyphs,
                context=context,
                diagnostics=diagnostics,
            ))
    return segments


def get_context(
    file_info: FileInfo,
    range: Optional[Range],
) -> _DiagnosticContext:
    """Get the diagnostic context including the line before and after the
    given range.
    """
    if range is None:
        return _DiagnosticContext(file_info=file_info, line_range=None)

    start_line_index = max(0, range.start.line - 1)

    # The range is exclusive, but `range.end.line` is inclusive, so add 1. Then
    # add 1 again because we want to include the line after `range.end.line`,
    # if there is one.
    end_line_index = min(len(file_info.lines), range.end.line + 1 + 1)

    return _DiagnosticContext(
        file_info=file_info,
        line_range=(start_line_index, end_line_index),
    )


def _merge_contexts(
    contexts: Iterable[_DiagnosticContext],
) -> Iterable[_DiagnosticContext]:
    """Combine adjacent contexts with ranges into a list of contexts sorted by
    range.

    For example, convert the list of contexts with ranges

        [(2, 4), (1, 3), None, (3, 5)]

    into the result

        [(1, 4), None, (3, 5)]
    """
    mergeable_contexts = _group_by_pred(
        contexts,
        pred=lambda lhs, rhs: _ranges_overlap(lhs.line_range, rhs.line_range),
    )

    def merge(contexts: List[_DiagnosticContext]) -> _DiagnosticContext:
        file_info = contexts[0].file_info
        assert all(context.file_info == file_info for context in contexts)

        if contexts[0].line_range is None:
            assert len(contexts) == 1
            line_range = contexts[0].line_range
        else:
            line_ranges = [
                context.line_range
                for context in contexts
                if context.line_range is not None
            ]
            assert len(line_ranges) == len(contexts)
            start = min((line_range[0] for line_range in line_ranges))
            end = max((line_range[1] for line_range in line_ranges))
            line_range = (start, end)

        return _DiagnosticContext(
            file_info=file_info,
            line_range=line_range,
        )

    return map(merge, mergeable_contexts)


def _ranges_overlap(
    lhs: Optional[Tuple[int, int]],
    rhs: Optional[Tuple[int, int]],
) -> bool:
    if lhs is None or rhs is None:
        return False

    assert lhs[0] <= lhs[1]
    assert rhs[0] <= rhs[1]

    return not (
        lhs[1] < rhs[0]
        or rhs[1] < lhs[0]
    )


def _group_by_pred(
    seq: Iterable[T],
    pred: Callable[[T, T], bool],
) -> Iterable[List[T]]:
    current_group: List[T] = []
    for i in seq:
        if current_group and not pred(current_group[-1], i):
            yield current_group
            current_group = []
        current_group.append(i)
    if current_group:
        yield current_group


def get_context_segment(
    glyphs: Glyphs,
    context: _DiagnosticContext,
    diagnostics: List[Diagnostic],
) -> Segment:
    diagnostics = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.file_info == context.file_info
    ]

    gutter_lines = []
    message_lines = []
    diagnostic_lines_to_insert = _get_diagnostic_lines_to_insert(
        glyphs=glyphs,
        context=context,
        diagnostics=diagnostics,
    )
    line_range = context.line_range
    if line_range is None:
        assert len(diagnostics) == 1
        diagnostic = diagnostics[0]
        gutter_lines.append("")
        message_lines.append(get_colored_diagnostic_message(
            glyphs=glyphs,
            diagnostic=diagnostic,
        ))
    else:
        (start_line, end_line) = line_range
        lines = context.file_info.lines[start_line:end_line]
        for line_num, line in enumerate(lines, start_line):
            # 1-index the line number for display.
            gutter_lines.append(str(line_num + 1))
            message_lines.append(line)

            diagnostic_lines = diagnostic_lines_to_insert.get(line_num, [])
            for diagnostic_line in diagnostic_lines:
                gutter_lines.append("")
                message_lines.append(diagnostic_line)
    return Segment(
        glyphs=glyphs,
        header=context.file_info.file_path,
        gutter_lines=gutter_lines,
        message_lines=message_lines,
    )


def _get_diagnostic_lines_to_insert(
    glyphs: Glyphs,
    context: _DiagnosticContext,
    diagnostics: Sequence[Diagnostic],
) -> Mapping[int, Sequence[str]]:
    result: Dict[int, List[str]] = collections.defaultdict(list)
    if context.line_range is None:
        return result
    context_lines = context.file_info.lines[
        context.line_range[0]:context.line_range[1]
    ]
    for diagnostic in diagnostics:
        diagnostic_range = diagnostic.range
        assert diagnostic_range is not None

        underlined_lines = underline_lines(
            glyphs=glyphs,
            start_line_index=context.line_range[0],
            context_lines=context_lines,
            underline_range=diagnostic_range,
            underline_color=diagnostic.color,
        )
        if underlined_lines:
            underlined_lines[-1] += " " + get_colored_diagnostic_message(
                glyphs=glyphs,
                diagnostic=diagnostic,
            )
        for line_num, line in enumerate(
            underlined_lines,
            diagnostic_range.start.line,
        ):
            result[line_num].append(line)
    return result


def underline_lines(
    glyphs: Glyphs,
    start_line_index: int,
    context_lines: List[str],
    underline_range: Range,
    underline_color: str,
) -> List[str]:
    start_position = underline_range.start
    end_position = underline_range.end

    message_lines = []
    for line_num, line in enumerate(context_lines, start=start_line_index):
        underline_start: Optional[int] = None
        has_underline_start = False
        if line_num == start_position.line:
            underline_start = start_position.character
            has_underline_start = True
        elif start_position.line <= line_num <= end_position.line:
            non_whitespace_characters = [
                i
                for i, c in enumerate(line)
                if not c.isspace()
            ]
            if non_whitespace_characters:
                underline_start = non_whitespace_characters[0]

        underline_end: Optional[int] = None
        has_underline_end = False
        if line_num == end_position.line:
            underline_end = end_position.character
            has_underline_end = True
        elif start_position.line <= line_num <= end_position.line:
            if underline_start is not None:
                underline_end = len(line)

        if underline_start is not None and underline_end is not None:
            underline_line = " " * underline_start

            underline_width = underline_end - underline_start
            if underline_width == 0:
                # In the event that we have a zero-length range, we want to
                # render it as an underline of width one. This could happen if
                # we're flagging the EOF token, for example.
                underline_width = 1
            assert underline_width > 0, (
                f"The index of the end of the underline ({underline_end}) on "
                f"line #{line_num} was before the index of the first " +
                f"non-whitespace character ({underline_start}) on this line. " +
                f"It's unclear how this should be rendered. This may be a " +
                f"bug in the caller, or it's possible that the rendering " +
                f"logic should be changed to handle this case."
            )
            if underline_width == 1:
                if has_underline_start and has_underline_end:
                    underline = glyphs.underline_point_character
                elif has_underline_start:
                    underline = glyphs.underline_start_character
                elif has_underline_end:
                    underline = glyphs.underline_end_character
                else:
                    assert False, (
                        "Underline with width 1 " +
                        "didn't have an endpoint on this line."
                    )
            else:
                underline = (
                    glyphs.underline_character
                    * (underline_end - underline_start - 2)
                )
                if has_underline_start:
                    underline = glyphs.underline_start_character + underline
                else:
                    underline = glyphs.underline_character + underline
                if has_underline_end:
                    underline = underline + glyphs.underline_end_character
                else:
                    underline = underline + glyphs.underline_character
            underline_line += glyphs.make_colored(
                underline,
                underline_color,
            )
            message_lines.append(underline_line)
    return message_lines


__all__ = [
    "_DiagnosticContext",
    "_get_diagnostic_lines_to_insert",
    "_group_by_pred",
    "_merge_contexts",
    "_ranges_overlap",

    "Error",
    "get_error_lines",
    "Note",
    "Severity",
]
