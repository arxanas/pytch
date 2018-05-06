from typing import Iterator, List, Optional, Tuple, Union

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate

from pytch import FileInfo
from pytch.errors import Error, get_error_lines
from pytch.greencst import Node
from pytch.lexer import lex, Token, TokenKind
from pytch.parser import parse


def render_syntax_tree(
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
            offset += trivium.width
            lines.append(f"Leading {trivium.text!r}")

        offset += token.width
        if token.is_dummy or token.kind == TokenKind.EOF:
            lines.append(f"Token {token.kind.name} {token.text!r}")
        else:
            lines.append(f"Token {token.text!r}")

        for trivium in token.trailing_trivia:
            offset += trivium.width
            lines.append(f"Trailing {trivium.text!r}")

        return (offset, lines)
    else:
        lines = [f"{ast_node.__class__.__name__}"]
        for child in ast_node.children:
            (offset, rendered_child) = \
                render_syntax_tree(source_code, child, offset)
            lines.extend(
                f"    {subline}"
                for subline in rendered_child
            )
        return (offset, lines)


def get_parser_tests() -> Iterator[CaseInfo]:
    return find_tests(
        "parser",
        input_extension=".pytch",
        error_extension=".err",
    )


def get_parser_test_ids() -> List[str]:
    return [test.name for test in get_parser_tests()]


def make_result(input_filename: str, source_code: str) -> CaseResult:
    file_info = FileInfo(
        file_path=input_filename,
        source_code=source_code,
    )
    lexation = lex(file_info=file_info)
    parsation = parse(file_info=file_info, tokens=lexation.tokens)
    offset, rendered_st_lines = render_syntax_tree(
        source_code,
        parsation.green_cst,
    )
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
    "test_case_info",
    get_parser_tests(),
    ids=get_parser_test_ids(),
)
def test_parser(test_case_info: CaseInfo) -> None:
    result = make_result(test_case_info.input_filename, test_case_info.input)
    assert test_case_info.error == result.error
    assert test_case_info.output == result.output


@pytest.mark.generate
def test_generate_parser_tests():
    generate(get_parser_tests(), make_result)
