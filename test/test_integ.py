from typing import Any, Iterator

import pytest

from pytch.__main__ import run_file
from pytch.utils import FileInfo
from .utils import CaseInfo, CaseResult, find_tests, generate


def get_integ_tests() -> Iterator["pytest.mark.structures.ParameterSet[CaseInfo]"]:
    return find_tests("integ", input_extension=".pytch", error_extension=".err")


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    run_file(FileInfo(file_path=input_filename, source_code=source_code))
    (output, error) = capsys.readouterr()
    if not error:
        error = None
    return CaseResult(output=output, error=error)


@pytest.mark.parametrize("test_case_info", get_integ_tests())
def test_integ(capsys: Any, test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input, capsys)
    assert test_case_info.error == result.error
    assert test_case_info.output == result.output


@pytest.mark.generate
def test_generate_integ_tests(capsys: Any) -> None:
    generate(get_integ_tests(), make_result, capsys=capsys)
