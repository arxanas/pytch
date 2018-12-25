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
from typing import Iterable, Iterator, List, Mapping, Optional, Pattern, Tuple

import attr

from .errors import Error, ErrorCode, Severity
from .utils import FileInfo, OffsetRange


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

    IF = "'if'"
    THEN = "'then'"
    ELSE = "'else'"

    PLUS = "'+'"
    MINUS = "'-'"
    OR = "'or'"
    AND = "'and'"

    ERROR = "error"
    """Any invalid token."""

    EOF = "the end of the file"
    """This token is a zero-width token denoting the end of the file.

    It's inserted by the pre-parser, so we can always expect there to be an
    EOF token in the token stream.
    """

    # Dummy tokens; inserted by the pre-parser.
    DUMMY_IN = "the end of a 'let' binding"
    DUMMY_SEMICOLON = "the end of a statement"
    DUMMY_ENDIF = "the end of an 'if' expression"


class Associativity(Enum):
    LEFT = "left"
    RIGHT = "right"


BINARY_OPERATORS: Mapping[
    TokenKind, Tuple[int, Associativity]  # Precedence: higher binds more tightly.
] = {
    TokenKind.PLUS: (4, Associativity.LEFT),
    TokenKind.MINUS: (4, Associativity.LEFT),
    TokenKind.AND: (3, Associativity.LEFT),
    TokenKind.OR: (2, Associativity.LEFT),
    TokenKind.DUMMY_SEMICOLON: (1, Associativity.RIGHT),
}

BINARY_OPERATOR_PRECEDENCES = set(
    precedence for precedence, associativity in BINARY_OPERATORS.values()
)
assert all(precedence > 0 for precedence in BINARY_OPERATOR_PRECEDENCES)
assert BINARY_OPERATOR_PRECEDENCES == set(
    range(min(BINARY_OPERATOR_PRECEDENCES), max(BINARY_OPERATOR_PRECEDENCES) + 1)
)

BINARY_OPERATOR_KINDS = list(BINARY_OPERATORS.keys())


@attr.s(auto_attribs=True, frozen=True)
class Trivium:
    kind: TriviumKind
    text: str

    @property
    def width(self) -> int:
        return len(self.text)


@attr.s(auto_attribs=True, frozen=True)
class Token:
    kind: TokenKind
    text: str
    leading_trivia: List[Trivium]
    trailing_trivia: List[Trivium]

    def update(self, **kwargs) -> "Token":
        return attr.evolve(self, **kwargs)

    @property
    def is_dummy(self):
        return self.kind == TokenKind.EOF or self.kind.name.lower().startswith("dummy")

    @property
    def full_text(self) -> str:
        return self.leading_text + self.text + self.trailing_text

    @property
    def width(self) -> int:
        return len(self.text)

    @property
    def full_width(self) -> int:
        """The width of the token, including leading and trailing trivia."""
        return self.leading_width + self.width + self.trailing_width

    @property
    def leading_width(self) -> int:
        return sum(trivium.width for trivium in self.leading_trivia)

    @property
    def leading_text(self) -> str:
        return "".join(trivium.text for trivium in self.leading_trivia)

    @property
    def trailing_width(self) -> int:
        return sum(trivium.width for trivium in self.trailing_trivia)

    @property
    def trailing_text(self) -> str:
        return "".join(trivium.text for trivium in self.trailing_trivia)

    @property
    def is_followed_by_newline(self) -> bool:
        return any(
            trivium.kind == TriviumKind.NEWLINE for trivium in self.trailing_trivia
        )


@attr.s(auto_attribs=True, frozen=True)
class State:
    file_info: FileInfo
    offset: int

    def update(self, **kwargs):
        return attr.evolve(self, **kwargs)

    def advance_offset(self, offset_delta: int) -> "State":
        assert offset_delta >= 0
        return self.update(offset=self.offset + offset_delta)


@attr.s(auto_attribs=True, frozen=True)
class Lexation:
    tokens: List[Token]
    errors: List[Error]

    @property
    def full_width(self) -> int:
        return sum(token.full_width for token in self.tokens)


WHITESPACE_RE = re.compile(r"[ \t]+")
NEWLINE_RE = re.compile(r"\n")
IDENTIFIER_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
INT_LITERAL_RE = re.compile(r"[0-9]+")
EQUALS_RE = re.compile(r"=")
LET_RE = re.compile(r"let")
COMMA_RE = re.compile(r",")
LPAREN_RE = re.compile(r"\(")
RPAREN_RE = re.compile(r"\)")
IF_RE = re.compile(r"if")
THEN_RE = re.compile(r"then")
ELSE_RE = re.compile(r"else")
PLUS_RE = re.compile(r"\+")
MINUS_RE = re.compile(r"-")
OR_RE = re.compile(r"or")
AND_RE = re.compile(r"and")

UNKNOWN_TOKEN_RE = re.compile(r"[^ \n\t\ra-zA-Z0-9]+")


class Lexer:
    def lex(self, file_info: FileInfo) -> Lexation:
        state = State(file_info=file_info, offset=0)
        errors = []
        tokens = []
        while True:
            last_offset = state.offset
            (state, token) = self.lex_token(state)
            tokens.append(token)
            if token.kind == TokenKind.ERROR:
                errors.append(
                    Error(
                        file_info=file_info,
                        code=ErrorCode.INVALID_TOKEN,
                        severity=Severity.ERROR,
                        message=f"Invalid token '{token.text}'.",
                        notes=[],
                        range=file_info.get_range_from_offset_range(
                            OffsetRange(
                                start=state.offset - token.trailing_width - token.width,
                                end=state.offset - token.trailing_width,
                            )
                        ),
                    )
                )

            if token.kind == TokenKind.EOF:
                break
            assert state.offset >= last_offset, "No progress made in lexing"

        return Lexation(tokens=tokens, errors=errors)

    def lex_leading_trivia(self, state: State) -> Tuple[State, List[Trivium]]:
        leading_trivia = self.lex_next_trivia_by_patterns(
            state, {TriviumKind.WHITESPACE: WHITESPACE_RE}
        )
        state = state.advance_offset(sum(trivium.width for trivium in leading_trivia))
        return (state, leading_trivia)

    def lex_trailing_trivia(self, state: State) -> Tuple[State, List[Trivium]]:
        trailing_trivia = self.lex_next_trivia_by_patterns(
            state,
            {TriviumKind.WHITESPACE: WHITESPACE_RE, TriviumKind.NEWLINE: NEWLINE_RE},
        )
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
        state = state.advance_offset(sum(trivium.width for trivium in trailing_trivia))
        return (state, trailing_trivia)

    def lex_next_trivia_by_patterns(
        self, state: State, trivia_patterns: Mapping[TriviumKind, Pattern]
    ) -> List[Trivium]:
        trivia: List[Trivium] = []
        offset = state.offset
        while True:
            matches = [
                (trivium_kind, regex.match(state.file_info.source_code, pos=offset))
                for trivium_kind, regex in trivia_patterns.items()
            ]
            filtered_matches = [
                (trivium_kind, match)
                for trivium_kind, match in matches
                if match is not None
            ]
            if not filtered_matches:
                return trivia
            assert (
                len(filtered_matches) == 1
            ), "More than one possible type of trivia found"
            trivium_kind, match = filtered_matches[0]

            trivium = Trivium(kind=trivium_kind, text=match.group())
            trivia.append(trivium)
            offset += trivium.width

    def lex_token(self, state: State) -> Tuple[State, Token]:
        (state, leading_trivia) = self.lex_leading_trivia(state)
        token_info = None

        if token_info is None:
            (maybe_state, token_info) = self.lex_next_token_by_patterns(
                state,
                {
                    TokenKind.INT_LITERAL: INT_LITERAL_RE,
                    TokenKind.EQUALS: EQUALS_RE,
                    TokenKind.LET: LET_RE,
                    TokenKind.COMMA: COMMA_RE,
                    TokenKind.LPAREN: LPAREN_RE,
                    TokenKind.RPAREN: RPAREN_RE,
                    TokenKind.IF: IF_RE,
                    TokenKind.THEN: THEN_RE,
                    TokenKind.ELSE: ELSE_RE,
                    TokenKind.PLUS: PLUS_RE,
                    TokenKind.MINUS: MINUS_RE,
                    TokenKind.OR: OR_RE,
                    TokenKind.AND: AND_RE,
                    TokenKind.IDENTIFIER: IDENTIFIER_RE,
                },
            )
            if token_info is not None:
                state = maybe_state

        if token_info is None:
            (maybe_state, token_info) = self.lex_next_token_by_patterns(
                state, {TokenKind.ERROR: UNKNOWN_TOKEN_RE}
            )
            if token_info is not None:
                state = maybe_state

        if token_info is None:
            # We can't find any match at all? Then there must be only
            # trivia remaining in the stream, so just produce the EOF
            # token.
            token_info = (TokenKind.EOF, "")

        (state, trailing_trivia) = self.lex_trailing_trivia(state)
        (token_kind, token_text) = token_info
        return (
            state,
            Token(
                kind=token_kind,
                text=token_text,
                leading_trivia=leading_trivia,
                trailing_trivia=trailing_trivia,
            ),
        )

    def lex_next_token_by_patterns(
        self, state: State, token_patterns: Mapping[TokenKind, Pattern]
    ) -> Tuple[State, Optional[Tuple[TokenKind, str]]]:
        matches = [
            (token_kind, regex.match(state.file_info.source_code, pos=state.offset))
            for token_kind, regex in token_patterns.items()
        ]
        filtered_matches = [
            (token_kind, match) for token_kind, match in matches if match is not None
        ]
        if not filtered_matches:
            return (state, None)

        (kind, match) = max(filtered_matches, key=lambda x: len(x[1].group()))
        token_text = match.group()
        state = state.advance_offset(len(token_text))
        return (state, (kind, token_text))


def with_indentation_levels(tokens: Iterable[Token],) -> Iterator[Tuple[int, Token]]:
    indentation_level = 0
    is_first_token_on_line = True
    for token in tokens:
        if is_first_token_on_line:
            indentation_level = token.leading_width
            is_first_token_on_line = False
        if token.is_followed_by_newline:
            is_first_token_on_line = True
        yield (indentation_level, token)


def make_dummy_token(kind: TokenKind) -> Token:
    token = Token(kind=kind, text="", leading_trivia=[], trailing_trivia=[])
    assert token.is_dummy
    return token


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

    def unwind(
        indentation_level: int,
        unwind_statements: bool,
        kind: TokenKind = None,
        kind_indentation_level: int = None,
    ) -> Iterator[Token]:
        while stack:
            (top_indentation_level, top_line, top_token) = stack[-1]
            stack.pop()

            # If we're unwinding to a specific token kind, only stop once we've
            # reached that token kind.
            if kind is not None and top_token.kind == kind:
                if (
                    kind_indentation_level is None
                    or top_indentation_level <= kind_indentation_level
                ):
                    return

            can_be_followed_by_new_statement = True
            if top_token.kind == TokenKind.LET:
                # If we see something of the form
                #
                # ```
                # let foo = bar
                # baz
                # ```
                #
                # then no matter what, we will treat the following `baz` as the
                # `let` body, not a new statement.
                can_be_followed_by_new_statement = False
                yield make_dummy_token(TokenKind.DUMMY_IN)
            elif (
                top_token.kind == TokenKind.IF
                or top_token.kind == TokenKind.THEN
                or top_token.kind == TokenKind.ELSE
            ):
                yield make_dummy_token(TokenKind.DUMMY_ENDIF)

            if (
                unwind_statements
                and can_be_followed_by_new_statement
                and indentation_level == top_indentation_level
            ):
                yield make_dummy_token(TokenKind.DUMMY_SEMICOLON)

            if kind is None and top_indentation_level <= indentation_level:
                return

    is_first_token = True
    current_line = 0
    eof_token = None
    previous_line = None
    previous_token = None
    for indentation_level, token in with_indentation_levels(tokens):
        if token.kind == TokenKind.EOF:
            eof_token = token
            break

        if stack:
            (previous_indentation_level, _, _) = stack[-1]
        else:
            previous_indentation_level = 0

        maybe_expr_continuation = True
        maybe_new_statement = False
        if previous_line is not None:
            assert previous_line <= current_line
            if current_line > previous_line:
                maybe_new_statement = True
                if indentation_level <= previous_indentation_level:
                    maybe_expr_continuation = False

        is_part_of_binary_expr = token.kind in BINARY_OPERATOR_KINDS or (
            previous_token is not None and previous_token.kind in BINARY_OPERATOR_KINDS
        )
        has_comma = token.kind == TokenKind.COMMA or (
            previous_token is not None and previous_token.kind == TokenKind.COMMA
        )

        if token.kind == TokenKind.LPAREN:
            # Pass `0` as the indentation level to reset the indentation level
            # in the stack until we've exited the parenthesized tokens.
            stack.append((0, current_line, token))
        elif token.kind == TokenKind.RPAREN:
            yield from unwind(
                indentation_level, unwind_statements=False, kind=TokenKind.LPAREN
            )
        elif token.kind == TokenKind.LET:
            if not maybe_expr_continuation:
                yield from unwind(indentation_level, unwind_statements=False)
            stack.append((indentation_level, current_line, token))
        elif token.kind == TokenKind.IF:
            if not maybe_expr_continuation:
                yield from unwind(indentation_level, unwind_statements=True)
            stack.append((indentation_level, current_line, token))
        elif token.kind == TokenKind.THEN:
            yield from unwind(
                indentation_level, unwind_statements=False, kind=TokenKind.IF
            )
            stack.append((indentation_level, current_line, token))
        elif token.kind == TokenKind.ELSE:
            yield from unwind(
                indentation_level,
                unwind_statements=False,
                kind=TokenKind.THEN,
                kind_indentation_level=indentation_level,
            )
            stack.append((indentation_level, current_line, token))
        elif maybe_new_statement and not is_part_of_binary_expr and not has_comma:
            if indentation_level <= previous_indentation_level:
                yield from unwind(indentation_level, unwind_statements=True)
            stack.append((indentation_level, current_line, token))
        elif is_first_token:
            stack.append((indentation_level, current_line, token))

        yield token

        is_first_token = False
        previous_line = current_line
        previous_token = token
        current_line += sum(
            len(trivium.text)
            for trivium in token.trailing_trivia
            if trivium.kind == TriviumKind.NEWLINE
        )

    yield from unwind(indentation_level=-1, unwind_statements=False)

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
        errors.append(
            Error(
                file_info=file_info,
                code=ErrorCode.PARSED_LENGTH_MISMATCH,
                severity=Severity.WARNING,
                message=(
                    f"Mismatch between source code length ({source_code_length}) "
                    + f"and total length of parsed tokens ({tokens_length}). "
                    + f"The parse tree for this file is probably incorrect. "
                    + f"This is a bug. Please report it!"
                ),
                notes=[],
            )
        )

    num_lets = 0
    num_ins = 0
    for token in tokens:
        if token.kind == TokenKind.LET:
            num_lets += 1
        elif token.kind == TokenKind.DUMMY_IN:
            num_ins += 1
    if num_lets != num_ins:
        errors.append(
            Error(
                file_info=file_info,
                code=ErrorCode.LET_IN_MISMATCH,
                severity=Severity.WARNING,
                message=(
                    f"Mismatch between the number of 'let' bindings ({num_lets}) "
                    + f"and the number of inferred ends "
                    + f"of these 'let' bindings ({num_ins}). "
                    + f"The parse tree for this file is probably incorrect. "
                    + f"This is a bug. Please report it!"
                ),
                notes=[],
            )
        )

    num_ifs = 0
    num_endifs = 0
    for token in tokens:
        if token.kind == TokenKind.IF:
            num_ifs += 1
        elif token.kind == TokenKind.DUMMY_ENDIF:
            num_endifs += 1
    if num_ifs != num_endifs:
        errors.append(
            Error(
                file_info=file_info,
                code=ErrorCode.IF_ENDIF_MISMATCH,
                severity=Severity.WARNING,
                message=(
                    f"Mismatch between the number of 'if' expressions ({num_ifs}) "
                    + f"and the number of inferred ends "
                    + f"of these 'if' expressions ({num_endifs}). "
                    + f"The parse tree for this file is probably incorrect. "
                    + f"This is a bug. Please report it!"
                ),
                notes=[],
            )
        )

    return Lexation(tokens=tokens, errors=errors)
