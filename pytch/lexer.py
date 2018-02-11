"""Lexes the source code into a series of tokens.

The token design is roughly based on the tokens in Roslyn.

# Trivia

Each token has associated "trivia". Trivia accounts for whitespace in the
source code, so that we can apply modifications to the original source code
(such as autoformatting or refactorings) without losing data.

There are two types of trivia: leading and trailing. The leading trivia comes
before the token, and the trailing trivia comes after. Consider the following
code (the newline is explicitly written out):

    let foo = 1\n

This has four tokens:

    let:
        leading: []
        trailing: []
    foo:
        leading: [" "]
        trailing: []
    =:
        leading: [" "]
        trailing: []
    1:
        leading: [" "]
        trailing: ["\n"]

The basic rule is that if possible, a trivium is allocated to the leading
trivia of the next token rather than the trailing trivia of the previous
token.

Whitespace and comments are the types of trivia.

# Token fields

Tokens contain their kind, text, and trivia. They don't contain their
position: this allows us to potentially do incremental reparsing, since we
can modify tokens directly without having to adjust the positions of all the
following tokens.

# Kinds

The "kind" of a token indicates what kind of token it was. For example, each
keyword and symbol has its own kind, as well as things like identifiers and
strings.
"""
from enum import Enum
import re
from typing import List, Mapping, Optional, Pattern, Sequence

from typing_extensions import Protocol

from . import FileInfo


class TriviumKind(Enum):
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    COMMENT = "comment"


class TokenKind(Enum):
    INDENT = "indent"
    DEDENT = "dedent"

    IDENTIFIER = "identifier"
    LET = "'let'"
    COMMA = "','"
    INT_LITERAL = "integer literal"
    EQUALS = "'='"
    LPAREN = "'('"
    RPAREN = "')'"


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
        return f"<Trivium kind={self.kind.value} text='{self.text}'>"

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
        trailing_trivia: List[Trivium],
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
    def full_text(self) -> str:
        return (
            "".join(trivium.text for trivium in self.leading_trivia) +
            self.text +
            "".join(trivium.text for trivium in self.trailing_trivia)
        )

    @property
    def width(self) -> int:
        return len(self._text)

    @property
    def full_width(self) -> int:
        """The width of the token, including leading and trailing trivia."""
        return self.leading_width + self.width + self.trailing_width

    @property
    def leading_trivia(self) -> Sequence[Trivium]:
        return self._leading_trivia

    @property
    def leading_width(self) -> int:
        return sum(trivium.width for trivium in self.leading_trivia)

    @property
    def trailing_trivia(self) -> Sequence[Trivium]:
        return self._trailing_trivia

    @property
    def trailing_width(self) -> int:
        return sum(trivium.width for trivium in self.trailing_trivia)

    @property
    def is_followed_by_newline(self) -> bool:
        return any(
            trivium.kind == TriviumKind.NEWLINE
            for trivium in self.trailing_trivia
        )

    def __repr__(self) -> str:
        r = f"<Token"
        if self.kind not in [TokenKind.INDENT, TokenKind.DEDENT]:
            r += f" text={self.text!r}"
        else:
            r += f" kind={self.kind.value}"
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

    @property
    def full_width(self) -> int:
        return sum(token.full_width for token in self.tokens)


WHITESPACE_RE = re.compile("[ \t]+")
NEWLINE_RE = re.compile("\n")
IDENTIFIER_RE = re.compile("[a-zA-Z_][a-zA-Z0-9_]*")
INT_LITERAL_RE = re.compile("[0-9]+")
EQUALS_RE = re.compile("=")
LET_RE = re.compile("let")
LPAREN_RE = re.compile("\(")
RPAREN_RE = re.compile("\)")


class Lexer:
    def __init__(self, file_info: FileInfo) -> None:
        self.file_info = file_info
        self.offset = 0

    @property
    def source_code(self) -> str:
        return self.file_info.source_code

    def lex(self) -> Lexation:
        tokens: List[Token] = []
        errors: List[Error] = []
        while self.offset < len(self.source_code):
            leading_trivia = self.lex_leading_trivia()
            for trivium in leading_trivia:
                self.consume_item(trivium)

            token = self.lex_next_token()
            self.consume_item(token)

            trailing_trivia = self.lex_trailing_trivia()
            newline_indices = [
                i
                for (i, trivium) in enumerate(trailing_trivia)
                if trivium.kind == TriviumKind.NEWLINE
            ]
            if newline_indices:
                last_newline_index = newline_indices[-1] + 1
            else:
                last_newline_index = 0
            # Avoid consuming whitespace or other trivia, after the last
            # newline. We'll consume that as the leading trivia of the next
            # token.
            trailing_trivia = trailing_trivia[:last_newline_index]
            for trivium in trailing_trivia:
                self.consume_item(trivium)

            tokens.append(Token(
                kind=token.kind,
                text=token.text,
                leading_trivia=leading_trivia,
                trailing_trivia=trailing_trivia,
            ))
        return Lexation(tokens=tokens, errors=errors)

    def consume_item(self, item: Item) -> None:
        self.offset += item.width

    def lex_leading_trivia(self) -> List[Trivium]:
        return self.lex_next_trivia_by_patterns({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
        })

    def lex_trailing_trivia(self) -> List[Trivium]:
        return self.lex_next_trivia_by_patterns({
            TriviumKind.WHITESPACE: WHITESPACE_RE,
            TriviumKind.NEWLINE: NEWLINE_RE,
        })

    def lex_next_trivia_by_patterns(
        self,
        trivia_patterns: Mapping[TriviumKind, Pattern],
    ) -> List[Trivium]:
        trivia: List[Trivium] = []
        offset = self.offset
        while True:
            matches = [
                (trivium_kind, regex.match(self.source_code, pos=offset))
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

    def lex_next_token(self) -> Token:
        try:
            token = self.lex_next_token_by_patterns({
                TokenKind.INT_LITERAL: INT_LITERAL_RE,
                TokenKind.EQUALS: EQUALS_RE,
                TokenKind.LET: LET_RE,
                TokenKind.LPAREN: LPAREN_RE,
                TokenKind.RPAREN: RPAREN_RE,
            })
        except ValueError:
            token = self.lex_next_token_by_patterns({
                TokenKind.IDENTIFIER: IDENTIFIER_RE,
            })
        return token

    def lex_next_token_by_patterns(
        self,
        token_patterns: Mapping[TokenKind, Pattern],
    ) -> Token:
        matches = [
            (token_kind, regex.match(self.source_code, pos=self.offset))
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
                self.source_code[self.offset:self.offset + 5] +
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

    def lex_next_identifier(self) -> Optional[Token]:
        match = IDENTIFIER_RE.match(self.source_code, pos=self.offset)
        if match is None:
            return None
        return Token(
            kind=TokenKind.IDENTIFIER,
            text=match.group(),
            leading_trivia=[],
            trailing_trivia=[],
        )


def lex(file_info: FileInfo) -> Lexation:
    lexer = Lexer(file_info=file_info)
    lexation = lexer.lex()
    if not lexation.errors:
        source_code_length = len(file_info.source_code)
        tokens_length = lexation.full_width
        assert source_code_length == tokens_length, (
            f"Mismatch between source code length ({source_code_length}) "
            f"and total length of lexed tokens ({tokens_length})"
        )
    return lexation


__all__ = ["lex", "Lexation", "Token", "TokenKind", "Trivium", "TriviumKind"]
