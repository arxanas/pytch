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
from typing import (
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Pattern,
    Sequence,
    Tuple,
)

from . import FileInfo, OffsetRange
from .errors import Error, ErrorCode, Severity


class TriviumKind(Enum):
    WHITESPACE = "whitespace"
    NEWLINE = "newline"
    COMMENT = "comment"
    ERROR = "error"


class TokenKind(Enum):
    IDENTIFIER = "identifier"
    LET = "'let'"
    COMMA = "','"
    INT_LITERAL = "integer literal"
    EQUALS = "'='"
    LPAREN = "'('"
    RPAREN = "')'"

    ERROR = "error"
    """Any invalid token."""

    EOF = "the end of the file"
    """This token is a zero-width token denoting the end of the file.

    It's inserted by the pre-parser, so we can always expect there to be an
    EOF token in the token stream.
    """

    # Dummy tokens; inserted by the pre-parser.
    DUMMY_IN = "the end of a 'let' binding"


class Trivium:
    def __init__(self, kind: TriviumKind, text: str) -> None:
        self._kind = kind
        self._text = text

    def __repr__(self) -> str:
        return f"<Trivium kind={self.kind.name} text={self.text!r}>"

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Trivium):
            return False
        return self.kind == other.kind and self.text == other.text

    @property
    def kind(self) -> TriviumKind:
        return self._kind

    @property
    def text(self) -> str:
        return self._text

    @property
    def width(self) -> int:
        return len(self._text)


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

    def __repr__(self) -> str:
        r = f"<Token kind={self.kind.name}"
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
            and self.kind == other.kind
            and self.leading_trivia == other.leading_trivia
            and self.trailing_trivia == other.trailing_trivia
        )

    def update(
        self,
        kind: TokenKind = None,
        text: str = None,
        leading_trivia: List[Trivium] = None,
        trailing_trivia: List[Trivium] = None,
    ) -> "Token":
        if kind is None:
            kind = self._kind
        if text is None:
            text = self._text
        if leading_trivia is None:
            leading_trivia = self._leading_trivia
        if trailing_trivia is None:
            trailing_trivia = self._trailing_trivia
        return Token(
            kind=kind,
            text=text,
            leading_trivia=leading_trivia,
            trailing_trivia=trailing_trivia,
        )

    @property
    def kind(self) -> TokenKind:
        return self._kind

    @property
    def is_dummy(self):
        return (
            self.kind == TokenKind.EOF
            or self.kind.name.lower().startswith("dummy")
        )

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


class State:
    def __init__(
        self,
        file_info: FileInfo,
        offset: int,
    ) -> None:
        self.file_info = file_info
        self.offset = offset

    def update(
        self,
        offset: int = None,
    ):
        if offset is None:
            offset = self.offset
        return State(
            file_info=self.file_info,
            offset=offset,
        )

    def advance_offset(self, offset_delta: int) -> "State":
        assert offset_delta >= 0
        return self.update(offset=self.offset + offset_delta)


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
COMMA_RE = re.compile(",")
LPAREN_RE = re.compile("\(")
RPAREN_RE = re.compile("\)")

UNKNOWN_TOKEN_RE = re.compile("[^ \n\t\ra-zA-Z0-9]+")


class Lexer:
    def lex(self, file_info: FileInfo) -> Lexation:
        state = State(file_info=file_info, offset=0)
        errors = []
        error_tokens = []
        tokens = []
        while True:
            last_offset = state.offset
            (state, token) = self.lex_token(state)
            tokens.append(token)
            if token.kind == TokenKind.ERROR:
                error_tokens.append(token)
                errors.append(Error(
                    file_info=file_info,
                    code=ErrorCode.INVALID_TOKEN,
                    severity=Severity.ERROR,
                    message=f"Invalid token '{token.text}'.",
                    notes=[],
                    range=file_info.get_range_from_offset_range(OffsetRange(
                        start=state.offset - token.trailing_width - token.width,
                        end=state.offset - token.trailing_width,
                    )),
                ))

            if token.kind == TokenKind.EOF:
                break
            assert state.offset >= last_offset, "No progress made in lexing"

        return Lexation(tokens=tokens, errors=errors)

    def lex_leading_trivia(self, state: State) -> Tuple[State, List[Trivium]]:
        leading_trivia = self.lex_next_trivia_by_patterns(state, {
            TriviumKind.WHITESPACE: WHITESPACE_RE,
        })
        state = state.advance_offset(sum(
            trivium.width for trivium in leading_trivia,
        ))
        return (state, leading_trivia)

    def lex_trailing_trivia(self, state: State) -> Tuple[State, List[Trivium]]:
        trailing_trivia = self.lex_next_trivia_by_patterns(state, {
            TriviumKind.WHITESPACE: WHITESPACE_RE,
            TriviumKind.NEWLINE: NEWLINE_RE,
        })
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
        state = state.advance_offset(
            sum(trivium.width for trivium in trailing_trivia),
        )
        return (state, trailing_trivia)

    def lex_next_trivia_by_patterns(
        self,
        state: State,
        trivia_patterns: Mapping[TriviumKind, Pattern],
    ) -> List[Trivium]:
        trivia: List[Trivium] = []
        offset = state.offset
        while True:
            matches = [
                (trivium_kind, regex.match(
                    state.file_info.source_code,
                    pos=offset,
                ))
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

    def lex_token(self, state: State) -> Tuple[State, Token]:
        (maybe_state, token) = self.lex_next_token_by_patterns(state, {
            TokenKind.INT_LITERAL: INT_LITERAL_RE,
            TokenKind.EQUALS: EQUALS_RE,
            TokenKind.LET: LET_RE,
            TokenKind.COMMA: COMMA_RE,
            TokenKind.LPAREN: LPAREN_RE,
            TokenKind.RPAREN: RPAREN_RE,
            TokenKind.IDENTIFIER: IDENTIFIER_RE,
        })

        if token is not None:
            state = maybe_state
        else:
            (maybe_state, token) = self.lex_next_token_by_patterns(state, {
                TokenKind.ERROR: UNKNOWN_TOKEN_RE,
            })

        if token is not None:
            state = maybe_state
        else:
            # We can't find any match at all? Then there must be only
            # trivia remaining in the stream, so just produce the EOF
            # token.
            (state, leading_trivia) = self.lex_leading_trivia(state)
            (state, trailing_trivia) = self.lex_trailing_trivia(state)
            token = Token(
                kind=TokenKind.EOF,
                text='',
                leading_trivia=leading_trivia,
                trailing_trivia=trailing_trivia,
            )

        return (state, token)

    def lex_next_token_by_patterns(
        self,
        state: State,
        token_patterns: Mapping[TokenKind, Pattern],
    ) -> Tuple[State, Optional[Token]]:
        (state, leading_trivia) = self.lex_leading_trivia(state)
        matches = [
            (token_kind, regex.match(
                state.file_info.source_code,
                pos=state.offset,
            ))
            for token_kind, regex in token_patterns.items()
        ]
        matches = [
            (token_kind, match)
            for token_kind, match in matches
            if match is not None
        ]
        if not matches:
            return (state, None)

        (kind, match) = max(matches, key=lambda x: len(x[1].group()))
        token_text = match.group()
        state = state.advance_offset(len(token_text))
        (state, trailing_trivia) = self.lex_trailing_trivia(state)
        token = Token(
            kind=kind,
            text=token_text,
            leading_trivia=leading_trivia,
            trailing_trivia=trailing_trivia,
        )
        return (state, token)


def with_indentation_levels(
    tokens: Iterable[Token],
) -> Iterator[Tuple[int, Token]]:
    indentation_level = 0
    is_first_token_on_line = True
    for token in tokens:
        if is_first_token_on_line:
            indentation_level = token.leading_width
            is_first_token_on_line = False
        if token.is_followed_by_newline:
            is_first_token_on_line = True
        yield (indentation_level, token)


def preparse(tokens: Iterable[Token]) -> Iterator[Token]:
    """Insert dummy tokens for lightweight constructs into the token stream.

    This technique is based off of the "pre-parsing" step as outlined in the
    F# 4.0 spec, section 15: Lightweight Syntax:
    http://fsharp.org/specs/language-spec/4.0/FSharpSpec-4.0-latest.pdf

    The pre-parser inserts dummy tokens into the token stream where we would
    expect the token to go in the non-lightweight token stream. For example,
    it might convert this:

        let foo = 1
        foo

    into this:

        let foo = 1 $in
        foo

    We do the same thing, although with significantly fewer restrictions on
    the source code's indentation.
    """
    stack: List[Tuple[int, int, Token]] = []
    eof_token = None
    current_line = 0
    for indentation_level, token in with_indentation_levels(tokens):
        if stack:
            (top_indentation_level, top_line, top_token) = stack[-1]
            if (
                indentation_level <= top_indentation_level
                and current_line > top_line
            ):
                if top_token.kind == TokenKind.LET:
                    yield Token(
                        kind=TokenKind.DUMMY_IN,
                        text="",
                        leading_trivia=[],
                        trailing_trivia=[],
                    )
                    stack.pop()

        if token.kind == TokenKind.LET:
            stack.append((indentation_level, current_line, token))

        if token.kind != TokenKind.EOF:
            yield token
        else:
            eof_token = token

        current_line += sum(
            len(trivium.text)
            for trivium in token.trailing_trivia
            if trivium.kind == TriviumKind.NEWLINE
        )

    while stack:
        (_, _, top_token) = stack.pop()
        if top_token.kind == TokenKind.LET:
            yield Token(
                kind=TokenKind.DUMMY_IN,
                text="",
                leading_trivia=[],
                trailing_trivia=[],
            )
        else:
            assert False, \
                f"Unexpected token kind in pre-parser: {token.kind.value}"

    assert eof_token is not None
    yield eof_token


def lex(file_info: FileInfo) -> Lexation:
    lexer = Lexer()
    lexation = lexer.lex(file_info=file_info)

    tokens = list(preparse(lexation.tokens))
    errors = lexation.errors

    source_code_length = len(file_info.source_code)
    tokens_length = sum(token.full_width for token in lexation.tokens)
    if source_code_length != tokens_length:
        errors.append(Error(
            file_info=file_info,
            code=ErrorCode.PARSED_LENGTH_MISMATCH,
            severity=Severity.WARNING,
            message=(
                f"Mismatch between source code length ({source_code_length}) " +
                f"and total length of parsed tokens ({tokens_length}). " +
                f"The parse tree for this file is probably incorrect. " +
                f"This is a bug. Please report it!"
            ),
            notes=[],
        ))

    return Lexation(tokens=tokens, errors=errors)


__all__ = ["lex", "Lexation", "Token", "TokenKind", "Trivium", "TriviumKind"]
