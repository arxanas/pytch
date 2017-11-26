import textwrap
from typing import List, Tuple, Union

import pytest

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


@pytest.mark.parametrize("source_code, output", [
    (
        """let foo = 1""",
        """
        Ast
            LetStatement
                Token 'let'
                VariablePattern
                    Leading ' '
                    Token 'foo'
                Leading ' '
                Token '='
                IntLiteralExpr
                    Leading ' '
                    Token '1'
        """,
    ), (
        """let foo = print(1)""",
        """
        Ast
            LetStatement
                Token 'let'
                VariablePattern
                    Leading ' '
                    Token 'foo'
                Leading ' '
                Token '='
                FunctionCallExpr
                    IdentifierExpr
                        Leading ' '
                        Token 'print'
                    Token '('
                    IntLiteralExpr
                        Token '1'
                    Token ')'
        """
    )
])
def test_parser(source_code: str, output: str) -> None:
    tokens = lex(source_code).tokens
    ast = parse(source_code=source_code, tokens=tokens)
    offset, rendered_ast_lines = render_ast(source_code, ast)
    assert offset == len(source_code)
    rendered_ast = "\n".join(rendered_ast_lines)

    output = "\n".join(output.split("\n")[1:-1])
    output = textwrap.dedent(output)
    output = output.strip()
    assert rendered_ast == output
