from typing import Any, Iterator, List, Optional

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch.errors import Error, get_error_lines
from pytch.lexer import lex
from pytch.parser import dump_syntax_tree, parse
from pytch.utils import FileInfo


def get_parser_tests() -> Iterator[CaseInfo]:
    return find_tests("parser", input_extension=".pytch", error_extension=".err")


def get_parser_test_ids() -> List[str]:
    return [test.name for test in get_parser_tests()]


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    file_info = FileInfo(file_path=input_filename, source_code=source_code)
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    offset, rendered_st_lines = dump_syntax_tree(source_code, parsation.green_cst)
    output = "".join(line + "\n" for line in rendered_st_lines)

    error_lines = []
    errors: List[Error] = lexation.errors + parsation.errors
    for i in errors:
        error_lines.extend(get_error_lines(i, ascii=True))

    error: Optional[str]
    if error_lines:
        error = "".join(line + "\n" for line in error_lines)
    else:
        error = None

    return CaseResult(output=output, error=error)


@pytest.mark.parametrize(
    "test_case_info", get_parser_tests(), ids=get_parser_test_ids()
)
def test_parser(test_case_info: CaseInfo) -> None:
    result = make_result(
        input_filename=test_case_info.input_filename,
        source_code=test_case_info.input,
        capsys=None,
    )
    assert test_case_info.output == result.output
    assert test_case_info.error == result.error


@pytest.mark.generate
def test_generate_parser_tests() -> None:
    generate(get_parser_tests(), make_result, capsys=None)
