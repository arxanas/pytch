from typing import Sequence

from pytch import FileInfo, OffsetRange
from pytch.errors import Error, get_error_lines, Note, Severity


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
        title="LOOK_INTO_THIS",
        code=1234,
        severity=Severity.ERROR,
        message="Look into this",
        offset_range=OffsetRange(start=9, end=15),
        notes=[Note(
            file_info=file_info,
            message="This is an additional point of interest",
            offset_range=OffsetRange(start=0, end=5),
        )],
    )
    lines = lines_to_string(get_error_lines(error, ascii=True))
    assert lines == """\
In dummy.pytch, line 2, character 4:
LOOK_INTO_THIS[1234]: Look into this
   +-----------------------------------------------+
   | Error: Look into this                         |
   +-----------------------------------------------+
   | dummy.pytch                                   |
 1 | line1                                         |
 2 |   line2                                       |
   |    ^~~~                                       |
 3 |   line3                                       |
   |   ~~                                          |
 4 |   line4                                       |
   +-----------------------------------------------+
   | Note: This is an additional point of interest |
   +-----------------------------------------------+
   | dummy.pytch                                   |
 1 | line1                                         |
   | ^~~~~                                         |
 2 |   line2                                       |
   +-----------------------------------------------+
"""
