from enum import Enum
import re
from typing import List, Mapping, Match, Optional, Pattern

from typing_extensions import Protocol


class TriviumKind(Enum):
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    COMMENT = "comment"


class TokenKind(Enum):
    IDENTIFIER = "identifier"
    LET = "let"
    LPAREN = "("
    RPAREN = ")"


class Item(Protocol):
    @property
    def width(self) -> int:
        ...


class Trivium:
    def __init__(self, kind: TriviumKind, width: int) -> None:
        self.kind = kind
        self.width = width

    def __repr__(self) -> str:
        return f"<Trivium kind={self.kind} width={self.width}>"

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Trivium):
            return False
        return self.kind == other.kind and self.width == other.width


class Token:
    def __init__(
        self,
        kind: TokenKind,
        width: int,
        leading_trivia: List[Trivium],
        trailing_trivia: List[Trivium]
    ) -> None:
        self.kind = kind
        self.width = width
        self.leading_trivia = leading_trivia
        self.trailing_trivia = trailing_trivia

    def __repr__(self) -> str:
        r = f"<Token width={self.width}"
        if self.leading_trivia:
            r += f" leading={self.leading_trivia}"
        if self.trailing_trivia:
            r += f" trailing={self.trailing_trivia}"
        r += ">"
        return r

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Token):
            return False
        return (
            self.width == other.width
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
            for trivium in trailing_trivia:
                self._consume_item(trivium)

            token.leading_trivia = leading_trivia
            token.trailing_trivia = trailing_trivia
            tokens.append(token)
        return Lexation(tokens=tokens, errors=errors)

    def _match_width(self, match: Match) -> int:
        return match.end() - match.start()

    def _consume_item(self, item: Item) -> None:
        self._offset += item.width

    def _lex_leading_trivia(self) -> List[Trivium]:
        return self._lex_trivia({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
        })

    def _lex_trailing_trivia(self) -> List[Trivium]:
        return self._lex_trivia({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
            TriviumKind.NEWLINE: NEWLINE_RE,
        })

    def _lex_trivia(self, trivia_regexes: Mapping[TriviumKind, Pattern]
                    ) -> List[Trivium]:
        trivia: List[Trivium] = []
        offset = self._offset
        while True:
            matches = [
                (trivium_kind, regex.match(self._source_code, pos=offset))
                for trivium_kind, regex in trivia_regexes.items()
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
                width=self._match_width(match)
            )
            trivia.append(trivium)
            offset += trivium.width

    def _lex_next_token(self) -> Token:
        token = self._lex_next_identifier()
        assert token is not None, \
            "next: " + self._source_code[self._offset:self._offset + 5]
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
        longest_match = max(matches, key=lambda x: self._match_width(x[1]))
        kind, match = longest_match
        return Token(
            kind=kind,
            width=self._match_width(match),
            leading_trivia=[],
            trailing_trivia=[],
        )

    def _lex_next_identifier(self) -> Optional[Token]:
        match = IDENTIFIER_RE.match(self._source_code, pos=self._offset)
        if match is None:
            return None
        return Token(
            kind=TokenKind.IDENTIFIER,
            width=self._match_width(match),
            leading_trivia=[],
            trailing_trivia=[],
        )


def lex(source_code: str) -> Lexation:
    lexer = Lexer(source_code=source_code)
    return lexer.lex()


__all__ = ["lex", "Lexation", "Token", "TokenKind", "Trivium", "TriviumKind"]
