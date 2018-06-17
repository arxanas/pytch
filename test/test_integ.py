from typing import Any, Iterator, List

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.__main__ import run_file


def get_integ_tests() -> Iterator[CaseInfo]:
    return find_tests("integ", input_extension=".pytch", error_extension=".err")


def get_integ_test_ids() -> List[str]:
    return [test.name for test in get_integ_tests()]


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    run_file(FileInfo(file_path=input_filename, source_code=source_code))
    (output, error) = capsys.readouterr()
    if not error:
        error = None
    return CaseResult(output=output, error=error)


@pytest.mark.parametrize("test_case_info", get_integ_tests(), ids=get_integ_test_ids())
def test_integ(capsys: Any, test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input, capsys)
    assert test_case_info.error == result.error
    assert test_case_info.output == result.output


@pytest.mark.generate
def test_generate_parser_tests(capsys: Any) -> None:
    generate(get_integ_tests(), make_result, capsys=capsys)
