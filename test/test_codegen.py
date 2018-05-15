from typing import Any, Iterator, List

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.__main__ import do_compile


def get_codegen_tests() -> Iterator[CaseInfo]:
    return find_tests(
        "codegen",
        input_extension=".pytch",
        error_extension=".err",
    )


def get_codegen_test_ids() -> List[str]:
    return [test.name for test in get_codegen_tests()]


def make_result(
    input_filename: str,
    source_code: str,
    capsys: Any,
) -> CaseResult:
    compiled_output = do_compile(FileInfo(
        file_path=input_filename,
        source_code=source_code,
    ))
    exec(compiled_output)
    (output, error) = capsys.readouterr()
    if not error:
        error = None
    return CaseResult(
        output=output,
        error=error,
    )


@pytest.mark.parametrize(
    "test_case_info",
    get_codegen_tests(),
    ids=get_codegen_test_ids(),
)
def test_codegen(capsys: Any, test_case_info: CaseInfo) -> None:
    result = make_result(
        test_case_info.input_filename,
        test_case_info.input,
        capsys,
    )
    assert test_case_info.error == result.error
    assert test_case_info.output == result.output


@pytest.mark.generate
def test_generate_parser_tests(capsys: Any) -> None:
    generate(get_codegen_tests(), make_result, capsys=capsys)
