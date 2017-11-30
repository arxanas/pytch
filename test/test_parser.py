from typing import Iterator, List, Optional, Tuple, Union

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch.errors import Error, get_error_lines
from pytch.lexer import lex, Token
from pytch.parser import Node, parse


def render_ast(
    source_code: str,
    ast_node: Union[Node, Token],
    offset: int = 0,
) -> Tuple[int, List[str]]:
    if isinstance(ast_node, Token):
        token = ast_node
        lines = []
        for trivium in token.leading_trivia:
            content = source_code[offset:offset + trivium.width]
            offset += trivium.width
            lines.append(f"Leading {content!r}")

        content = source_code[offset:offset + token.width]
        offset += token.width
        lines.append(f"Token {content!r}")

        for trivium in token.trailing_trivia:
            content = source_code[offset:offset + trivium.width]
            offset += trivium.width
            lines.append(f"Trailing {content!r}")

        return (offset, lines)
    else:
        lines = [f"{ast_node.__class__.__name__}"]
        for child in ast_node.children:
            (offset, rendered_child) = render_ast(source_code, child, offset)
            lines.extend(
                f"    {subline}"
                for subline in rendered_child
            )
        return (offset, lines)


def get_parser_tests() -> Iterator[CaseInfo]:
    return find_tests("parser", input_extension=".pytch")


def make_result(source_code: str) -> CaseResult:
    lexation = lex(source_code)
    parsation = parse(source_code=source_code, tokens=lexation.tokens)
    offset, rendered_ast_lines = render_ast(source_code, parsation.ast)
    assert offset == len(source_code)
    output = "".join(line + "\n" for line in rendered_ast_lines)

    error_lines = []
    errors: List[Error] = lexation.errors + parsation.errors  # type: ignore
    for i in errors:
        error_lines.extend(get_error_lines(i, ascii=True))

    error: Optional[str]
    if error_lines:
        error = "".join(line + "\n" for line in error_lines)
    else:
        error = None

    return CaseResult(output=output, error=error)


@pytest.mark.parametrize("test_case_info", get_parser_tests())
def test_parser(test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input)
    assert result.output == test_case_info.output
    assert result.error == test_case_info.error


@pytest.mark.generate
def test_generate_parser_tests():
    generate(get_parser_tests(), make_result)
