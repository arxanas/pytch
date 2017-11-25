from typing import List

import pytest

from pytch.lexer import lex, Token, TokenKind, Trivium, TriviumKind


def T(
    text: str,
    kind: TokenKind,
    leading: List[Trivium] = None,
    trailing: List[Trivium] = None,
):
    return Token(
        kind=kind,
        text=text,
        leading_trivia=leading or [],
        trailing_trivia=trailing or [],
    )


def Tr(text: str, kind: TriviumKind) -> Trivium:
    return Trivium(
        kind=kind,
        text=text,
    )


@pytest.mark.parametrize("source_code, tokens", [(
    """foo""",
    [
        T("foo", TokenKind.IDENTIFIER),
    ],
), (
    """  foo\n""",
    [
        T(
            "foo",
            TokenKind.IDENTIFIER,
            leading=[Tr("  ", TriviumKind.WHITESPACE)],
            trailing=[Tr("\n", TriviumKind.NEWLINE)],
        ),
    ],
), (
    """let foo = 1  \nlet bar=2""",
    [
        T("let", TokenKind.LET),
        T("foo", TokenKind.IDENTIFIER,
          leading=[Tr(" ", TriviumKind.WHITESPACE)]),
        T("=", TokenKind.EQUALS, leading=[Tr(" ", TriviumKind.WHITESPACE)]),
        T(
            "1",
            TokenKind.INT_LITERAL,
            leading=[Tr(" ", TriviumKind.WHITESPACE)],
            trailing=[
                Tr("  ", TriviumKind.WHITESPACE),
                Tr("\n", TriviumKind.NEWLINE),
            ],
        ),
        T("let", TokenKind.LET),
        T("bar", TokenKind.IDENTIFIER,
          leading=[Tr(" ", TriviumKind.WHITESPACE)]),
        T("=", TokenKind.EQUALS),
        T("2", TokenKind.INT_LITERAL),
    ],
), (
    """print(1)""",
    [
        T("print", TokenKind.IDENTIFIER),
        T("(", TokenKind.LPAREN),
        T("1", TokenKind.INT_LITERAL),
        T(")", TokenKind.RPAREN),
    ],
)])
def test_lexer(source_code: str, tokens: List[Token]):
    lexation = lex(source_code)
    assert lexation.tokens == tokens
