from enum import Enum
import re
from typing import Callable, List, Optional, Tuple

import click
from typing_extensions import Protocol

from . import FileInfo, OffsetRange, Range


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


class Note:
    def __init__(
        self,
        file_info: FileInfo,
        message: str,
        offset_range: Optional[OffsetRange] = None,
    ) -> None:
        self._file_info = file_info
        self._message = message
        self._offset_range = offset_range

    @property
    def file_info(self) -> FileInfo:
        return self._file_info

    @property
    def message(self) -> str:
        return self._message

    @property
    def range(self) -> Optional[Range]:
        offset_range = self._offset_range
        if offset_range is None:
            return None
        return Range(
            start=self._file_info.get_position_for_offset(
                offset_range.start,
            ),
            end=self._file_info.get_position_for_offset(
                offset_range.end,
            )
        )


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


class Error:
    def __init__(
        self,
        file_info: FileInfo,
        title: str,
        code: int,
        severity: Severity,
        message: str,
        notes: List[Note],
        offset_range: Optional[OffsetRange] = None,
    ) -> None:
        self._file_info = file_info
        self._title = title
        self._code = code
        self._severity = severity
        self._message = message
        self._notes = notes
        self._offset_range = offset_range

    @property
    def file_info(self) -> FileInfo:
        return self._file_info

    @property
    def title(self) -> str:
        return self._title

    @property
    def code(self) -> int:
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
        offset_range = self._offset_range
        if offset_range is None:
            return None
        return Range(
            start=self._file_info.get_position_for_offset(
                offset_range.start,
            ),
            end=self._file_info.get_position_for_offset(
                offset_range.end,
            )
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
            assert gutter_lines or len(gutter_lines) == len(message_lines)
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
            if gutter:
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


class HasContext(Protocol):
    @property
    def file_info(self) -> FileInfo:
        ...

    @property
    def range(self) -> Optional[Range]:
        ...


def get_context(
    item: HasContext,
) -> Optional[Tuple[int, Range, List[str]]]:
    if not item.range:
        return None

    # Add a line before and after the requested lines for context. But clamp
    # the lower end to 0 to avoid slicing with a negative integer.
    start_line_index = max(0, item.range.start.line - 1)
    end_line_index = item.range.end.line + 1
    context_lines = item.file_info.lines[start_line_index:end_line_index + 1]

    return (start_line_index, item.range, context_lines)


def underline_lines(
    glyphs: Glyphs,
    start_line_index: int,
    context_lines: List[str],
    underline_range: Range,
    underline_color: str,
) -> Tuple[List[str], List[str]]:
    start_position = underline_range.start
    end_position = underline_range.end

    gutter_lines = []
    message_lines = []
    for line_num, line in enumerate(context_lines, start=start_line_index):
        # 1-index the line number for display.
        gutter_lines.append(str(line_num + 1))
        message_lines.append(line)

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

            underline_width = underline_end - underline_start + 1
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

            gutter_lines.append("")
            message_lines.append(underline_line)

    return (gutter_lines, message_lines)


def get_error_lines(error: Error, ascii: bool = False) -> List[str]:
    glyphs = get_glyphs(ascii=ascii)

    # TODO: There is a bug here because `click` includes ANSI escape codes in
    # its calculation of line lengths during text wrapping. A solution would be
    # to set `initial_indent` for `wrap_text` to a dummy string of the correct
    # length, and then replacing it with the actual colored text.
    error_message = click.wrap_text(
        glyphs.make_colored("Error: ", "red")
        + error.message
    )
    error_context = get_context(error)
    if not error_context:
        error_segments = [Segment(
            glyphs=glyphs,
            header=error.file_info.file_path,
            gutter_lines=None,
            message_lines=error_message.splitlines(),
        )]
    else:
        (start_line_index, underline_range, context_lines) = error_context
        (gutter_lines, message_lines) = underline_lines(
            glyphs=glyphs,
            start_line_index=start_line_index,
            context_lines=context_lines,
            underline_range=underline_range,
            underline_color="red",
        )
        error_segments = [
            Segment(
                glyphs=glyphs,
                header=None,
                gutter_lines=None,
                message_lines=error_message.splitlines(),
            ), Segment(
                glyphs=glyphs,
                header=error.file_info.file_path,
                gutter_lines=gutter_lines,
                message_lines=message_lines,
            ),
        ]

    note_segments = []
    for note in error.notes:
        note_message = click.wrap_text(
            glyphs.make_colored("Note: ", "green") + note.message
        )
        note_context = get_context(note)

        # Unlike the error segments, never include a header.
        if not note_context:
            note_segments.append(Segment(
                glyphs=glyphs,
                header=None,
                gutter_lines=None,
                message_lines=note_message.splitlines(),
            ))
        else:
            (start_line_index, underline_range, context_lines) = note_context
            (gutter_lines, message_lines) = underline_lines(
                glyphs=glyphs,
                start_line_index=start_line_index,
                context_lines=context_lines,
                underline_range=underline_range,
                underline_color="green",
            )
            note_segments.extend([
                Segment(
                    glyphs=glyphs,
                    header=None,
                    gutter_lines=None,
                    message_lines=note_message.splitlines(),
                ), Segment(
                    glyphs=glyphs,
                    header=error.file_info.file_path,
                    gutter_lines=gutter_lines,
                    message_lines=message_lines,
                ),
            ])

    segments = error_segments + note_segments
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
        glyphs.make_bold(error.title + f"[{error.code}]")
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


__all__ = ["Error", "get_error_lines", "Note", "Severity"]
