from typing import Iterator, List

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.lexer import lex, Token


def render_token_stream(tokens: List[Token]) -> str:
    output_lines = []
    for token in tokens:
        for trivium in token.leading_trivia:
            output_lines.append(
                f"leading {trivium.kind.value} {trivium.text!r}"
            )

        if not token.text or token.kind.value == repr(token.text):
            output_lines.append(token.kind.value)
        else:
            output_lines.append(f"{token.kind.value} {token.text!r}")

        for trivium in token.trailing_trivia:
            output_lines.append(
                f"trailing {trivium.kind.value} {trivium.text!r}"
            )
    return "".join(line + "\n" for line in output_lines)


def get_lexer_tests() -> Iterator[CaseInfo]:
    return find_tests("lexer", input_extension=".pytch")


def get_lexer_test_ids() -> List[str]:
    return [test.name for test in get_lexer_tests()]


def make_result(input_filename: str, source_code: str) -> CaseResult:
    file_info = FileInfo(
        file_path=input_filename,
        source_code=source_code,
    )
    lexation = lex(file_info=file_info)
    actual_result = render_token_stream(lexation.tokens)
    return CaseResult(output=actual_result, error=None)


@pytest.mark.parametrize(
    "test_case_info",
    get_lexer_tests(),
    ids=get_lexer_test_ids(),
)
def test_lexer(test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input)
    assert result.output == test_case_info.output


@pytest.mark.generate
def test_generate_lexer_tests():
    generate(get_lexer_tests(), make_result)
