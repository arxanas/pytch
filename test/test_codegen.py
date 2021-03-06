from typing import Any, Iterator, Optional

import pytest

from pytch.__main__ import compile_file
from pytch.errors import get_error_lines
from pytch.utils import FileInfo
from .utils import CaseInfo, CaseResult, find_tests, generate


def get_codegen_tests() -> Iterator["pytest.mark.structures.ParameterSet[CaseInfo]"]:
    return find_tests("codegen", input_extension=".pytch", error_extension=".err")


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    (compiled_output, errors) = compile_file(
        FileInfo(file_path=input_filename, source_code=source_code)
    )

    if compiled_output is None:
        compiled_output = ""

    error_lines = []
    for i in errors:
        error_lines.extend(get_error_lines(i, ascii=True))

    error: Optional[str]
    if error_lines:
        error = "".join(line + "\n" for line in error_lines)
    else:
        error = None

    return CaseResult(output=compiled_output, error=error)


@pytest.mark.parametrize("test_case_info", get_codegen_tests())
def test_codegen(test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input, None)
    assert test_case_info.error == result.error
    assert test_case_info.output == result.output


@pytest.mark.generate
def test_generate_codegen_tests() -> None:
    generate(get_codegen_tests(), make_result, capsys=None)
