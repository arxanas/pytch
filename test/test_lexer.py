from typing import Any, Iterator, List, Optional

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.errors import Error, get_error_lines
from pytch.lexer import lex, Token


def render_token_stream(tokens: List[Token]) -> str:
    output_lines = []
    for token in tokens:
        for trivium in token.leading_trivia:
            output_lines.append(f"leading {trivium.kind.value} {trivium.text!r}")

        if not token.text or token.kind.value == repr(token.text):
            output_lines.append(token.kind.value)
        else:
            output_lines.append(f"{token.kind.value} {token.text!r}")

        for trivium in token.trailing_trivia:
            output_lines.append(f"trailing {trivium.kind.value} {trivium.text!r}")
    return "".join(line + "\n" for line in output_lines)


def get_lexer_tests() -> Iterator[CaseInfo]:
    return find_tests("lexer", input_extension=".pytch", error_extension=".err")


def get_lexer_test_ids() -> List[str]:
    return [test.name for test in get_lexer_tests()]


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    file_info = FileInfo(file_path=input_filename, source_code=source_code)
    lexation = lex(file_info=file_info)
    output = render_token_stream(lexation.tokens)

    error_lines = []
    errors: List[Error] = lexation.errors
    for i in errors:
        error_lines.extend(get_error_lines(i, ascii=True))

    error: Optional[str]
    if error_lines:
        error = "".join(line + "\n" for line in error_lines)
    else:
        error = None

    return CaseResult(output=output, error=error)


@pytest.mark.parametrize("test_case_info", get_lexer_tests(), ids=get_lexer_test_ids())
def test_lexer(test_case_info: CaseInfo) -> None:
    result = make_result(
        input_filename=test_case_info.input_filename,
        source_code=test_case_info.input,
        capsys=None,
    )
    assert test_case_info.output == result.output
    assert test_case_info.error == result.error


@pytest.mark.generate
def test_generate_lexer_tests() -> None:
    generate(get_lexer_tests(), make_result, capsys=None)
