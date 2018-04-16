from typing import Sequence

from pytch import FileInfo, Position, Range
from pytch.errors import (
    _DiagnosticContext,
    _get_diagnostic_lines_to_insert,
    _group_by_pred,
    _merge_contexts,
    _ranges_overlap,
    Error,
    ErrorCode,
    get_error_lines,
    get_glyphs,
    Note,
    Severity,
)


def lines_to_string(lines: Sequence[str]) -> str:
    return "".join(line + "\n" for line in lines)


def test_print_error():
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="""line1
  line2
  line3
  line4
""")
    error = Error(
        file_info=file_info,
        code=ErrorCode.NOT_A_REAL_ERROR,
        severity=Severity.ERROR,
        message="Look into this",
        range=Range(
            start=Position(line=1, character=3),
            end=Position(line=2, character=2),
        ),
        notes=[Note(
            file_info=file_info,
            message="This is an additional point of interest",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=5),
            ),
        )],
    )
    lines = lines_to_string(get_error_lines(error, ascii=True))
    assert lines == """\
NOT_A_REAL_ERROR[9001] in dummy.pytch, line 2, character 4:
Error: Look into this
   +-----------------------------------------------------+
   | dummy.pytch                                         |
 1 | line1                                               |
   | ^~~~~ Note: This is an additional point of interest |
 2 |   line2                                             |
   |    ^~~~                                             |
 3 |   line3                                             |
   |   ~ Error: Look into this                           |
 4 |   line4                                             |
   +-----------------------------------------------------+
"""


def test_error_at_single_point():
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="""line1
  line2
  line3
  line4
""")
    error = Error(
        file_info=file_info,
        code=ErrorCode.NOT_A_REAL_ERROR,
        severity=Severity.ERROR,
        message="Look into this",
        range=Range(
            start=Position(line=1, character=3),
            end=Position(line=1, character=3),
        ),
        notes=[Note(
            file_info=file_info,
            message="This is an additional point of interest",
            range=Range(
                start=Position(line=2, character=3),
                end=Position(line=2, character=4),
            ),
        )],
    )
    lines = lines_to_string(get_error_lines(error, ascii=True))
    assert lines == """\
NOT_A_REAL_ERROR[9001] in dummy.pytch, line 2, character 4:
Error: Look into this
   +----------------------------------------------------+
   | dummy.pytch                                        |
 1 | line1                                              |
 2 |   line2                                            |
   |    ^ Error: Look into this                         |
 3 |   line3                                            |
   |    ^ Note: This is an additional point of interest |
 4 |   line4                                            |
   +----------------------------------------------------+
"""


def test_diagnostics_across_multiple_files() -> None:
    file_info_1 = FileInfo(
        file_path="dummy1.pytch",
        source_code="""dummy1 line1
dummy1 line2
""")
    file_info_2 = FileInfo(
        file_path="dummy2.pytch",
        source_code="""dummy2 line1
dummy2 line2
""")
    error = Error(
        file_info=file_info_1,
        code=ErrorCode.NOT_A_REAL_ERROR,
        severity=Severity.ERROR,
        message="Look into this",
        range=Range(
            start=Position(line=0, character=7),
            end=Position(line=0, character=12),
        ),
        notes=[Note(
            file_info=file_info_2,
            message="This is an additional point of interest",
            range=Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=5),
            ),
        )],
    )
    lines = lines_to_string(get_error_lines(error, ascii=True))
    print(lines)
    assert lines == """\
NOT_A_REAL_ERROR[9001] in dummy1.pytch, line 1, character 8:
Error: Look into this
   +-----------------------------------------------------+
   | dummy1.pytch                                        |
 1 | dummy1 line1                                        |
   |        ^~~~~ Error: Look into this                  |
 2 | dummy1 line2                                        |
   +-----------------------------------------------------+
   | dummy2.pytch                                        |
 1 | dummy2 line1                                        |
   | ^~~~~ Note: This is an additional point of interest |
 2 | dummy2 line2                                        |
   +-----------------------------------------------------+
"""


def test_get_diagnostic_lines_to_insert() -> None:
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="foo\nbar\nbaz\n",
    )
    diagnostics = [Error(
        file_info=file_info,
        code=ErrorCode.NOT_A_REAL_ERROR,
        severity=Severity.ERROR,
        message="An error message",
        notes=[],
        range=Range(
            start=Position(line=1, character=1),
            end=Position(line=2, character=0),
        )
    )]
    context = _DiagnosticContext(file_info=file_info, line_range=(0, 3))
    assert _get_diagnostic_lines_to_insert(
        glyphs=get_glyphs(ascii=True),
        context=context,
        diagnostics=diagnostics,
    ) == {
        1: [" ^~"],
        2: ["~ Error: An error message"],
    }


def test_ranges_overlap() -> None:
    assert not _ranges_overlap((1, 2), None)
    assert not _ranges_overlap(None, (1, 2))
    assert _ranges_overlap((1, 2), (1, 3))
    assert _ranges_overlap((1, 2), (2, 3))
    assert _ranges_overlap((1, 3), (1, 2))
    assert _ranges_overlap((2, 3), (1, 2))
    assert not _ranges_overlap((1, 2), (3, 4))
    assert _ranges_overlap((1, 1), (1, 2))


def test_group_by_pred() -> None:
    ranges = [None, (2, 3), (1, 4), None, None, (5, 6), (7, 8)]

    merged_ranges = _group_by_pred(ranges, pred=_ranges_overlap)
    assert list(merged_ranges) == [
        [None],
        [(2, 3), (1, 4)],
        [None],
        [None],
        [(5, 6)],
        [(7, 8)],
    ]

    assert list(_group_by_pred([], pred=_ranges_overlap)) == []


def test_merge_contexts() -> None:
    file_info = FileInfo(file_path="dummy.pytch", source_code="foo")
    contexts = [
        _DiagnosticContext(file_info=file_info, line_range=(2, 4)),
        _DiagnosticContext(file_info=file_info, line_range=(1, 3)),
        _DiagnosticContext(file_info=file_info, line_range=None),
        _DiagnosticContext(file_info=file_info, line_range=(2, 3)),
    ]
    assert list(_merge_contexts(contexts)) == [
        _DiagnosticContext(file_info=file_info, line_range=(1, 4)),
        _DiagnosticContext(file_info=file_info, line_range=None),
        _DiagnosticContext(file_info=file_info, line_range=(2, 3)),
    ]
