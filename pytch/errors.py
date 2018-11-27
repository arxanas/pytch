"""Error types and pretty-printing.

## Grammar

  * Use the first-person: the compiler should be a tool that works with you,
  rather than against you. For example, see the Elm error messages:
  http://elm-lang.org/blog/compiler-errors-for-humans

  * Don't be terse. Specify subjects and pronouns explicitly.

  BAD: Missing ')'.

  GOOD: I was expecting a ')' here.

  * Use the past progressive rather than the simple past tense. We don't use
  the present tense to indicate that the compilation already happened -- it's
  not still in the process of happening. We don't use the simple past tense
  simply not to remind the user of terser compilers which use it.

  BAD: Expected X.

  GOOD: I was expecting an X.

## Word choice

  * Use articles where possible.

  BAD: I was expecting ')' here.

  GOOD: I was expecting a ')' here.

  * Prefer the term "binding" over the term "variable".

## Typography

  * Use single-quotes (') instead of backticks (`) or fancy Unicode quotes.

  BAD: I was expecting a `)` here.

  GOOD: I was expecting a ')' here.

"""
import collections
from enum import Enum
import itertools
import re
from typing import (
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import attr
import click
from typing_extensions import Protocol

from .utils import FileInfo, Range

T = TypeVar("T")


class ErrorCode(Enum):
    INVALID_TOKEN = 1000
    UNEXPECTED_TOKEN = 1001
    EXPECTED_EXPRESSION = 1010
    EXPECTED_LPAREN = 1011
    EXPECTED_RPAREN = 1012
    EXPECTED_PATTERN = 1013
    EXPECTED_EQUALS = 1014
    EXPECTED_DUMMY_IN = 1015
    EXPECTED_LET_EXPRESSION = 1016
    EXPECTED_COMMA = 1017
    EXPECTED_END_OF_ARGUMENT_LIST = 1018
    EXPECTED_END_OF_PARAMETER_LIST = 1019

    UNBOUND_NAME = 2000

    INCOMPATIBLE_TYPES = 3000
    EXPECTED_VOID = 3001
    CANNOT_BIND_TO_VOID = 3002

    PARSED_LENGTH_MISMATCH = 9000
    NOT_A_REAL_ERROR = 9001
    """Not a real error code, just for testing purposes."""
    SHOULD_END_WITH_EOF = 9002
    LET_IN_MISMATCH = 9003
    IF_ENDIF_MISMATCH = 9004


@attr.s(auto_attribs=True, frozen=True)
class Glyphs:
    """The set of glyphs to be used when printing out error messages."""

    make_colored: Callable[[str, str], str]
    make_bold: Callable[[str], str]
    make_inverted: Callable[[str], str]
    box_vertical: str
    box_horizontal: str
    box_upper_left: str
    box_upper_right: str
    box_lower_left: str
    box_lower_right: str
    box_continuation_left: str
    box_continuation_right: str
    underline_start_character: str
    underline_character: str
    underline_end_character: str
    underline_point_character: str
    vertical_colon: str


@attr.s(auto_attribs=True, frozen=True)
class OutputEnv:
    glyphs: Glyphs
    max_width: int


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


@attr.s(auto_attribs=True, frozen=True)
class _DiagnosticContext:
    file_info: FileInfo
    line_ranges: Optional[List[Tuple[int, int]]]


@attr.s(auto_attribs=True, frozen=True)
class Note:
    color = "blue"
    preamble_message = "Note"

    file_info: FileInfo
    message: str
    range: Optional[Range] = attr.ib(default=None)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@attr.s(auto_attribs=True, frozen=True)
class Error:
    file_info: FileInfo
    code: ErrorCode
    severity: Severity
    message: str
    notes: List[Note]
    range: Optional[Range] = attr.ib(default=None)

    @property
    def color(self) -> str:
        if self.severity == Severity.ERROR:
            return "red"
        elif self.severity == Severity.WARNING:
            return "yellow"
        else:
            assert False, f"Unhandled severity: {self.severity}"

    @property
    def preamble_message(self) -> str:
        return self.severity.value.title()


def get_full_diagnostic_message(diagnostic: Diagnostic,) -> str:
    return f"{diagnostic.preamble_message}: {diagnostic.message}"


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
            vertical_colon=":",
        )
    else:
        return Glyphs(
            make_colored=lambda text, color: click.style(text, fg=color, bold=True),
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
            vertical_colon=":",  # TODO: use Unicode vertical colon
        )


def get_output_env(ascii: bool) -> OutputEnv:
    glyphs = get_glyphs(ascii=ascii)
    if ascii:
        max_width = 79
    else:
        (terminal_width, _terminal_height) = click.get_terminal_size()
        max_width = terminal_width - 1
    return OutputEnv(glyphs=glyphs, max_width=max_width)


@attr.s(auto_attribs=True, frozen=True)
class _MessageLine:
    text: str
    color: Optional[str]
    is_wrappable: bool

    def wrap(self, max_width: int) -> List[str]:
        match = re.match(r"\s*\S+", self.text)
        if not match:
            return [self.text]
        prefix = match.group()
        text = self.text[len(prefix) :]
        wrapped_text = click.wrap_text(text, width=max_width, initial_indent=prefix)
        if wrapped_text:
            return wrapped_text.splitlines()
        else:
            return [prefix]

    def get_wrapped_width(self, max_width: int) -> int:
        return max(map(len, self.wrap(max_width)))


@attr.s(auto_attribs=True, frozen=True)
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

    output_env: OutputEnv
    header: Optional[str]
    gutter_lines: Optional[List[str]] = attr.ib()
    message_lines: List[_MessageLine]

    @gutter_lines.validator
    def check(self, attribute, value) -> None:
        if self.gutter_lines is not None:
            assert len(self.gutter_lines) == len(self.message_lines)

    is_context_continuation: bool = attr.ib(default=False)
    """"Whether this segment is a vertical-colon-delimited continuation of
    the previous segment."""

    @property
    def gutter_width(self) -> int:
        if not self.gutter_lines:
            return 0
        num_padding_characters = len("  ")
        max_gutter_line_length = max(len(line) for line in self.gutter_lines)
        return num_padding_characters + max_gutter_line_length

    def get_box_width(self, gutter_width: int) -> int:
        num_box_characters = len("||")
        num_padding_characters = len("  ")
        max_message_line_length = max(
            line.get_wrapped_width(
                self.output_env.max_width
                - num_box_characters
                - num_padding_characters
                - gutter_width
            )
            for line in self.message_lines
        )
        if self.header is not None:
            max_message_line_length = max(max_message_line_length, len(self.header))
        return max_message_line_length + num_box_characters + num_padding_characters

    def render_lines(
        self, is_first: bool, is_last: bool, gutter_width: int, box_width: int
    ) -> List[str]:
        if self.gutter_lines is None:
            gutter_lines = [""] * len(self.message_lines)
        else:
            gutter_lines = self.gutter_lines

        empty_gutter = " " * gutter_width

        lines = []

        glyphs = self.output_env.glyphs
        # if self._is_context_continuation:
        #     assert not is_first, (
        #         "The first context should not be a continuation context, "
        #         + "since it has no previous context to continue."
        #     )
        #     top_line =
        # else:
        # if self._is_context_continuation:
        #     is_first = False
        top_line = ""
        if is_first:
            top_line += glyphs.box_upper_left
        else:
            top_line += glyphs.box_continuation_left
        top_line = top_line.ljust(box_width - 1, glyphs.box_horizontal)
        if is_first:
            top_line += glyphs.box_upper_right
        else:
            top_line += glyphs.box_continuation_right
        lines.append(empty_gutter + top_line)

        if self.header:
            header_line = (" " + self.header).ljust(box_width - 2)
            header_line = (
                glyphs.box_vertical
                + glyphs.make_bold(header_line)
                + glyphs.box_vertical
            )
            lines.append(empty_gutter + header_line)

        num_box_characters = len("||")
        num_padding_characters = len("  ")
        padding = num_box_characters + num_padding_characters

        for gutter_line, message_line in zip(gutter_lines, self.message_lines):
            if message_line.is_wrappable:
                wrapped_message_lines = message_line.wrap(box_width - padding)
            else:
                wrapped_message_lines = [message_line.text]

            for wrapped_message_line in wrapped_message_lines:
                gutter = gutter_line.rjust(gutter_width - num_padding_characters)
                gutter = " " + gutter + " "

                line_length = len(wrapped_message_line)
                if message_line.color is not None:
                    wrapped_message_line = glyphs.make_colored(
                        wrapped_message_line, message_line.color
                    )

                message = (
                    glyphs.box_vertical
                    + " "
                    + wrapped_message_line
                    + (" " * (box_width - line_length - padding))
                    + " "
                    + glyphs.box_vertical
                )
                lines.append(gutter + message)

        if is_last:
            footer = ""
            footer += glyphs.box_lower_left
            footer = footer.ljust(box_width - 1, glyphs.box_horizontal)
            footer += glyphs.box_lower_right
            lines.append(empty_gutter + footer)

        return lines


def get_error_lines(error: Error, ascii: bool = False) -> List[str]:
    output_env = get_output_env(ascii=ascii)
    glyphs = output_env.glyphs

    output_lines = []
    if error.range is not None:
        line = str(error.range.start.line + 1)
        character = str(error.range.start.character + 1)
        output_lines.append(
            glyphs.make_bold(f"{error.code.name}[{error.code.value}]")
            + f" in {glyphs.make_bold(error.file_info.file_path)}, "
            + f"line {glyphs.make_bold(line)}, "
            + f"character {glyphs.make_bold(character)}:"
        )
    else:
        output_lines.append(
            glyphs.make_bold(f"{error.code.name}[{error.code.value}] ")
            + f"in {glyphs.make_bold(error.file_info.file_path)}:"
        )
    output_lines.append(
        glyphs.make_colored(
            click.wrap_text(
                text=f"{error.preamble_message}: {error.message}",
                width=output_env.max_width,
            ),
            error.color,
        )
    )

    segments = get_error_segments(output_env=output_env, error=error)
    if segments:
        gutter_width = max(segment.gutter_width for segment in segments)
        box_width = max(segment.get_box_width(gutter_width) for segment in segments)
        for i, segment in enumerate(segments):
            is_first = i == 0
            is_last = i == len(segments) - 1
            output_lines.extend(
                segment.render_lines(
                    is_first=is_first,
                    is_last=is_last,
                    gutter_width=gutter_width,
                    box_width=box_width,
                )
            )
    return output_lines


def get_error_segments(output_env: OutputEnv, error: Error):
    diagnostics: List[Diagnostic] = [error]
    diagnostics.extend(error.notes)
    diagnostic_contexts = [
        get_context(file_info=diagnostic.file_info, range=diagnostic.range)
        for diagnostic in diagnostics
    ]

    def key(
        context: _DiagnosticContext,
    ) -> List[Tuple[Union[int, float], Union[int, float]]]:
        if context.line_ranges is not None:
            return cast(
                List[Tuple[Union[int, float], Union[int, float]]], context.line_ranges
            )
        else:
            return [(float("inf"), float("inf"))]

    sorted_diagnostic_contexts = sorted(diagnostic_contexts, key=key)

    partitioned_diagnostic_contexts = itertools.groupby(
        sorted_diagnostic_contexts, lambda context: context.file_info.file_path
    )

    segments: List[Segment] = []
    for _file_path, contexts in partitioned_diagnostic_contexts:
        for context in _merge_contexts(list(contexts)):
            context_segments = get_context_segments(
                output_env=output_env, context=context, diagnostics=diagnostics
            )
            if context_segments is not None:
                segments.extend(context_segments)

    segments.extend(
        get_segments_without_ranges(output_env=output_env, diagnostics=diagnostics)
    )
    return segments


def get_context(file_info: FileInfo, range: Optional[Range]) -> _DiagnosticContext:
    """Get the diagnostic context including the line before and after the
    given range.
    """
    if range is None:
        return _DiagnosticContext(file_info=file_info, line_ranges=None)

    start_line_index = max(0, range.start.line - 1)

    # The range is exclusive, but `range.end.line` is inclusive, so add 1. Then
    # add 1 again because we want to include the line after `range.end.line`,
    # if there is one.
    end_line_index = min(len(file_info.lines), range.end.line + 1 + 1)

    return _DiagnosticContext(
        file_info=file_info, line_ranges=[(start_line_index, end_line_index)]
    )


def _merge_contexts(contexts: List[_DiagnosticContext],) -> List[_DiagnosticContext]:
    """Combine adjacent contexts with ranges into a list of contexts sorted by
    range.

    For example, convert the list of contexts with ranges

        [(2, 4), (1, 3), None, (6, 8)]

    into the result

        [(1, 4), (6, 8), None]
    """
    file_info = contexts[0].file_info
    assert all(context.file_info == file_info for context in contexts)

    contexts_with_ranges = [
        context for context in contexts if context.line_ranges is not None
    ]
    contexts_without_ranges = [
        context for context in contexts if context.line_ranges is None
    ]

    line_ranges = sorted(
        line_range
        for context in contexts_with_ranges
        for line_range in context.line_ranges  # type: ignore
    )
    merged_line_ranges: List[Tuple[int, int]] = []
    for line_range in line_ranges:
        if not merged_line_ranges:
            merged_line_ranges.append(line_range)
        elif line_range[0] <= merged_line_ranges[-1][1]:
            current_line_range = merged_line_ranges.pop()
            merged_line_ranges.append((current_line_range[0], line_range[1]))
        else:
            merged_line_ranges.append(line_range)

    merged_diagnostic_context = _DiagnosticContext(
        file_info=file_info, line_ranges=merged_line_ranges
    )

    return [merged_diagnostic_context] + contexts_without_ranges


def _ranges_overlap(
    lhs: Optional[Tuple[int, int]], rhs: Optional[Tuple[int, int]]
) -> bool:
    if lhs is None or rhs is None:
        return False

    assert lhs[0] <= lhs[1]
    assert rhs[0] <= rhs[1]

    return not (lhs[1] < rhs[0] or rhs[1] < lhs[0])


def _group_by_pred(seq: Iterable[T], pred: Callable[[T, T], bool]) -> Iterable[List[T]]:
    current_group: List[T] = []
    for i in seq:
        if current_group and not pred(current_group[-1], i):
            yield current_group
            current_group = []
        current_group.append(i)
    if current_group:
        yield current_group


def get_context_segments(
    output_env: OutputEnv, context: _DiagnosticContext, diagnostics: List[Diagnostic]
) -> Optional[List[Segment]]:
    diagnostics = [
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.file_info == context.file_info
    ]

    diagnostic_lines_to_insert = _get_diagnostic_lines_to_insert(
        output_env=output_env, context=context, diagnostics=diagnostics
    )
    line_ranges = context.line_ranges
    if line_ranges is None:
        return None

    segments = []
    is_first = True
    for line_range in line_ranges:
        gutter_lines = []
        message_lines = []
        (start_line, end_line) = line_range
        lines = context.file_info.lines[start_line:end_line]
        for line_num, line in enumerate(lines, start_line):
            # 1-index the line number for display.
            gutter_lines.append(str(line_num + 1))
            message_lines.append(
                _MessageLine(
                    text=line,
                    color=None,
                    # Code segment -- print this verbatim, do not wrap.
                    is_wrappable=False,
                )
            )

            diagnostic_lines = diagnostic_lines_to_insert.get(line_num, [])
            for diagnostic_line in diagnostic_lines:
                gutter_lines.append("")
                message_lines.append(diagnostic_line)

        if not is_first:
            header = None
        else:
            header = context.file_info.file_path
        segments.append(
            Segment(
                output_env=output_env,
                header=header,
                gutter_lines=gutter_lines,
                message_lines=message_lines,
                is_context_continuation=(not is_first),
            )
        )
        is_first = False

    return segments


def get_segments_without_ranges(
    output_env: OutputEnv, diagnostics: List[Diagnostic]
) -> List[Segment]:
    segments = []
    for diagnostic in diagnostics:
        if diagnostic.range is None:
            segments.append(
                Segment(
                    output_env=output_env,
                    header=None,
                    gutter_lines=[""],
                    message_lines=[
                        _MessageLine(
                            text=get_full_diagnostic_message(diagnostic),
                            color=diagnostic.color,
                            # Diagnostic message, wrap this if necessary.
                            is_wrappable=True,
                        )
                    ],
                )
            )
    return segments


def _get_diagnostic_lines_to_insert(
    output_env: OutputEnv,
    context: _DiagnosticContext,
    diagnostics: Sequence[Diagnostic],
) -> Mapping[int, Sequence[_MessageLine]]:
    result: Dict[int, List[_MessageLine]] = collections.defaultdict(list)
    if context.line_ranges is None:
        return result
    for line_range in context.line_ranges:
        context_lines = context.file_info.lines[line_range[0] : line_range[1]]
        for diagnostic in diagnostics:
            diagnostic_range = diagnostic.range
            if diagnostic_range is None:
                continue

            underlined_lines = underline_lines(
                output_env=output_env,
                start_line_index=line_range[0],
                context_lines=context_lines,
                underline_range=diagnostic_range,
                underline_color=diagnostic.color,
            )
            if underlined_lines:
                last_line = underlined_lines.pop().text
                last_line += " " + get_full_diagnostic_message(diagnostic)
                underlined_lines.append(
                    _MessageLine(
                        text=last_line,
                        color=diagnostic.color,
                        # Diagnostic message, wrap this if necessary.
                        is_wrappable=True,
                    )
                )
            for line_num, line in enumerate(
                underlined_lines, diagnostic_range.start.line
            ):
                result[line_num].append(line)
    return result


def underline_lines(
    output_env: OutputEnv,
    start_line_index: int,
    context_lines: List[str],
    underline_range: Range,
    underline_color: str,
) -> List[_MessageLine]:
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
                i for i, c in enumerate(line) if not c.isspace()
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
                f"line #{line_num} was before the index of the first "
                + f"non-whitespace character ({underline_start}) on this line. "
                + f"It's unclear how this should be rendered. This may be a "
                + f"bug in the caller, or it's possible that the rendering "
                + f"logic should be changed to handle this case."
            )

            glyphs = output_env.glyphs
            if underline_width == 1:
                if has_underline_start and has_underline_end:
                    underline = glyphs.underline_point_character
                elif has_underline_start:
                    underline = glyphs.underline_start_character
                elif has_underline_end:
                    underline = glyphs.underline_end_character
                else:
                    underline = glyphs.underline_character
            else:
                underline = glyphs.underline_character * (
                    underline_end - underline_start - 2
                )
                if has_underline_start:
                    underline = glyphs.underline_start_character + underline
                else:
                    underline = glyphs.underline_character + underline
                if has_underline_end:
                    underline = underline + glyphs.underline_end_character
                else:
                    underline = underline + glyphs.underline_character
            underline_line += underline
            message_lines.append(
                _MessageLine(
                    text=underline_line,
                    color=underline_color,
                    # Underline, do not wrap (although it should never require
                    # wrapping, since the code should not be wrapped).
                    is_wrappable=False,
                )
            )
    return message_lines
