from typing import Iterator, List, Optional, Tuple, Union

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.ast import Node
from pytch.errors import Error, get_error_lines
from pytch.lexer import lex, Token
from pytch.parser import parse


def render_ast(
    source_code: str,
    ast_node: Union[Node, Token, None],
    offset: int = 0,
) -> Tuple[int, List[str]]:
    if ast_node is None:
        return (offset, ["<missing>"])
    elif isinstance(ast_node, Token):
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


def get_parser_test_ids() -> List[str]:
    return [test.name for test in get_parser_tests()]


def make_result(input_filename: str, source_code: str) -> CaseResult:
    file_info = FileInfo(
        file_path=input_filename,
        source_code=source_code,
    )
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    offset, rendered_ast_lines = render_ast(source_code, parsation.ast)
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


@pytest.mark.parametrize(
    "test_case_info",
    get_parser_tests(),
    ids=get_parser_test_ids(),
)
def test_parser(test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input)
    assert result.output == test_case_info.output
    assert result.error == test_case_info.error


@pytest.mark.generate
def test_generate_parser_tests():
    generate(get_parser_tests(), make_result)
