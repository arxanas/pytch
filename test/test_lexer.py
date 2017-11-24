from typing import List

import pytest

from pytch.lexer import lex, Token, TokenKind, Trivium, TriviumKind


class Tr:
    def __init__(self, text: str, kind: TriviumKind) -> None:
        self.text = text
        self.kind = kind


class T:
    def __init__(
        self,
        text: str,
        kind: TokenKind,
        leading: List[Tr] = None,
        trailing: List[Tr] = None,
    ) -> None:
        self.text = text
        self.kind = kind
        self.leading = leading or []
        self.trailing = trailing or []


def reconstruct(tokens: List[T]) -> List[Token]:
    result = []
    for token in tokens:
        leading = reconstruct_trivia(token.leading)
        token_width = len(token.text)
        trailing = reconstruct_trivia(token.trailing)

        result.append(Token(
            kind=token.kind,
            width=token_width,
            leading_trivia=leading,
            trailing_trivia=trailing,
        ))
    return result


def reconstruct_trivia(trivia: List[Tr]) -> List[Trivium]:
    return [
        Trivium(kind=trivium.kind, width=len(trivium.text))
        for trivium in trivia
    ]


@pytest.mark.parametrize("source_code, tokens", [(
    """foo""",
    reconstruct([
        T("foo", TokenKind.IDENTIFIER),
    ]),
), (
    """  foo\n""",
    reconstruct([
        T(
            "foo",
            TokenKind.IDENTIFIER,
            leading=[Tr("  ", TriviumKind.WHITESPACE)],
            trailing=[Tr("\n", TriviumKind.NEWLINE)]
        ),
    ]),
), (
    """let foo = 1  \nlet bar=2""",
    reconstruct([
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
    ])
), (
    """print(1)""",
    reconstruct([
        T("print", TokenKind.IDENTIFIER),
        T("(", TokenKind.LPAREN),
        T("1", TokenKind.INT_LITERAL),
        T(")", TokenKind.RPAREN),
    ]),
)])
def test_lexer(source_code: str, tokens: List[Token]):
    lexation = lex(source_code)
    assert lexation.tokens == tokens
