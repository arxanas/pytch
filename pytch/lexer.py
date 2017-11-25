from enum import Enum
import re
from typing import List, Mapping, Optional, Pattern, Sequence

from typing_extensions import Protocol


class TriviumKind(Enum):
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    COMMENT = "comment"


class TokenKind(Enum):
    IDENTIFIER = "identifier"
    LET = "let"
    INT_LITERAL = "int_literal"
    EQUALS = "="
    LPAREN = "("
    RPAREN = ")"


class Item(Protocol):
    @property
    def width(self) -> int:
        ...


class Trivium:
    def __init__(self, kind: TriviumKind, text: str) -> None:
        self._kind = kind
        self._text = text

    @property
    def kind(self) -> TriviumKind:
        return self._kind

    @property
    def text(self) -> str:
        return self._text

    @property
    def width(self) -> int:
        return len(self._text)

    def __repr__(self) -> str:
        return f"<Trivium kind={self.kind} text={self.text}>"

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Trivium):
            return False
        return self.kind == other.kind and self.text == other.text


class Token:
    def __init__(
        self,
        kind: TokenKind,
        text: str,
        leading_trivia: List[Trivium],
        trailing_trivia: List[Trivium]
    ) -> None:
        self._kind = kind
        self._text = text
        self._leading_trivia = leading_trivia
        self._trailing_trivia = trailing_trivia

    @property
    def kind(self) -> TokenKind:
        return self._kind

    @property
    def text(self) -> str:
        return self._text

    @property
    def width(self) -> int:
        return len(self._text)

    @property
    def full_width(self) -> int:
        """The width of the token, including leading and trailing trivia."""
        leading_width = sum(trivium.width for trivium in self.leading_trivia)
        trailing_width = sum(trivium.width for trivium in self.trailing_trivia)
        return leading_width + self.width + trailing_width

    @property
    def leading_trivia(self) -> Sequence[Trivium]:
        return self._leading_trivia

    @property
    def trailing_trivia(self) -> Sequence[Trivium]:
        return self._trailing_trivia

    def __repr__(self) -> str:
        r = f"<Token text={self.text!r}"
        if self.leading_trivia:
            r += f" leading={self.leading_trivia!r}"
        if self.trailing_trivia:
            r += f" trailing={self.trailing_trivia!r}"
        r += ">"
        return r

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Token):
            return False
        return (
            self.text == other.text
            and self.leading_trivia == other.leading_trivia
            and self.trailing_trivia == other.trailing_trivia
        )


class Error:
    def __init__(self, offset: int, message: str) -> None:
        self.offset = offset
        self.message = message


class Lexation:
    def __init__(self, tokens: List[Token], errors: List[Error]) -> None:
        self.tokens = tokens
        self.errors = errors


WHITESPACE_RE = re.compile("[ \t]+")
NEWLINE_RE = re.compile("\n")
IDENTIFIER_RE = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")
INT_LITERAL_RE = re.compile("[0-9]+")
EQUALS_RE = re.compile("=")
LET_RE = re.compile("let")
LPAREN_RE = re.compile("\(")
RPAREN_RE = re.compile("\)")


class Lexer:
    def __init__(self, source_code: str) -> None:
        self._source_code = source_code
        self._offset = 0

    def lex(self) -> Lexation:
        tokens = []
        # TODO: Shouldn't need type annotation.
        errors: List[Error] = []
        while self._offset < len(self._source_code):
            leading_trivia = self._lex_leading_trivia()
            for trivium in leading_trivia:
                self._consume_item(trivium)

            token = self._lex_next_token()
            self._consume_item(token)

            trailing_trivia = self._lex_trailing_trivia()
            if not any(
                trivium.kind == TriviumKind.NEWLINE
                for trivium in trailing_trivia
            ):
                # If we're not about to consume the end of the line, let this
                # trivia be the leading trivia of the next token instead.
                trailing_trivia = []
            for trivium in trailing_trivia:
                self._consume_item(trivium)

            tokens.append(Token(
                kind=token.kind,
                text=token.text,
                leading_trivia=leading_trivia,
                trailing_trivia=trailing_trivia,
            ))
        return Lexation(tokens=tokens, errors=errors)

    def _consume_item(self, item: Item) -> None:
        self._offset += item.width

    def _lex_leading_trivia(self) -> List[Trivium]:
        return self._lex_next_trivia_by_patterns({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
        })

    def _lex_trailing_trivia(self) -> List[Trivium]:
        return self._lex_next_trivia_by_patterns({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
            TriviumKind.NEWLINE: NEWLINE_RE,
        })

    def _lex_next_trivia_by_patterns(
        self,
        trivia_patterns: Mapping[TriviumKind, Pattern],
    ) -> List[Trivium]:
        trivia: List[Trivium] = []
        offset = self._offset
        while True:
            matches = [
                (trivium_kind, regex.match(self._source_code, pos=offset))
                for trivium_kind, regex in trivia_patterns.items()
            ]
            matches = [
                (trivium_kind, match)
                for trivium_kind, match in matches
                if match is not None
            ]
            if not matches:
                return trivia
            assert len(matches) == 1, \
                "More than one possible type of trivia found"
            trivium_kind, match = matches[0]

            trivium = Trivium(
                kind=trivium_kind,
                text=match.group(),
            )
            trivia.append(trivium)
            offset += trivium.width

    def _lex_next_token(self) -> Token:
        try:
            token = self._lex_next_token_by_patterns({
                TokenKind.INT_LITERAL: INT_LITERAL_RE,
                TokenKind.EQUALS: EQUALS_RE,
                TokenKind.LET: LET_RE,
                TokenKind.LPAREN: LPAREN_RE,
                TokenKind.RPAREN: RPAREN_RE,
            })
        except ValueError:
            token = self._lex_next_token_by_patterns({
                TokenKind.IDENTIFIER: IDENTIFIER_RE,
            })
        return token

    def _lex_next_token_by_patterns(
        self,
        token_patterns: Mapping[TokenKind, Pattern],
    ) -> Token:
        matches = [
            (token_kind, regex.match(self._source_code, pos=self._offset))
            for token_kind, regex in token_patterns.items()
        ]
        matches = [
            (token_kind, match)
            for token_kind, match in matches
            if match is not None
        ]
        if not matches:
            # TODO: This should be a formal lexing error.
            raise ValueError(
                "no match: '" +
                self._source_code[self._offset:self._offset + 5] +
                "'",
            )
        longest_match = max(matches, key=lambda x: len(x[1].group()))
        kind, match = longest_match
        return Token(
            kind=kind,
            text=match.group(),
            leading_trivia=[],
            trailing_trivia=[],
        )

    def _lex_next_identifier(self) -> Optional[Token]:
        match = IDENTIFIER_RE.match(self._source_code, pos=self._offset)
        if match is None:
            return None
        return Token(
            kind=TokenKind.IDENTIFIER,
            text=match.group(),
            leading_trivia=[],
            trailing_trivia=[],
        )


def lex(source_code: str) -> Lexation:
    lexer = Lexer(source_code=source_code)
    return lexer.lex()


__all__ = ["lex", "Lexation", "Token", "TokenKind", "Trivium", "TriviumKind"]
