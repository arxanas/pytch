"""Parses a series of tokens into a concrete syntax tree (CST).

The concrete syntax tree is not quite an abstract syntax tree: the tokens
contained therein are enough to reconstitute the source code. The
non-meaningful parts of the program are contained within "trivia" nodes. See
the lexer for more information.

The *green* CST is considered to be immutable and must not be modified.

The *red* CST is based off of the green syntax tree. It is also immutable,
but its nodes are generated lazily (since they contain `parent` pointers and
therefore reference cycles).
"""
from typing import Iterator, List, Optional, Tuple

import attr

from . import FileInfo, OffsetRange, Range
from .errors import Error, ErrorCode, Note, Severity
from .greencst import (
    Argument,
    ArgumentList,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IntLiteralExpr,
    LetExpr,
    Node,
    Pattern,
    SyntaxTree,
    VariablePattern,
)
from .lexer import Token, TokenKind, Trivium, TriviumKind


def walk_tokens(node: Node) -> Iterator[Token]:
    for child in node.children:
        if child is None:
            continue
        if isinstance(child, Token):
            yield child
        elif isinstance(child, Node):
            yield from walk_tokens(child)
        else:
            assert False, f"Unexpected node child type: {child!r}"


@attr.s(auto_attribs=True, frozen=True)
class Parsation:
    green_cst: SyntaxTree
    errors: List[Error]

    @property
    def is_buggy(self) -> bool:
        """Return whether the parse tree violates any known invariants."""
        assert ErrorCode.PARSED_LENGTH_MISMATCH.value == 9000
        return any(
            error.code.value >= ErrorCode.PARSED_LENGTH_MISMATCH.value
            for error in self.errors
        )


class ParseException(Exception):
    def __init__(self, error: Error) -> None:
        self.error = error


@attr.s(auto_attribs=True, frozen=True)
class State:
    file_info: FileInfo
    tokens: List[Token] = attr.ib()
    """The list of tokens that make up the file."""

    @tokens.validator
    def check(self, attribute, value) -> None:
        assert len(self.tokens) > 0, \
            "Expected at least one token (the EOF token)."
        assert self.tokens[-1].kind == TokenKind.EOF, \
            "Token stream must end with an EOF token."

    token_index: int
    """The index into the token list indicating where we currently are in the
    process of parsing."""

    offset: int
    """The offset into the source file. Must be kept in sync
    with `token_index`."""

    errors: List[Error]
    """A list of errors that have occurred during parsing so far."""

    is_recovering: bool
    """Whether or not we are in the process of recovering from a parser
    error. While recovering, we'll consume tokens blindly until we find a
    token of a kind that we're expecting (a synchronization token), and
    resume parsing from there."""

    error_tokens: List[Token]
    """A list of tokens that have been consumed during error recovery."""

    sync_token_kinds: List[List[TokenKind]]
    """A stack of collections of tokens. Some callers will push a set of
    tokens into this stack. This set indicates tokens that can be
    synchronized to. If a function deeper in the stack encounters an error,
    then parsing will synchronize to the next token that appears somewhere in
    this stack, and unwind to the its caller."""
    # assert token_index < len(tokens)

    @property
    def end_of_file_offset_range(self) -> OffsetRange:
        last_offset = len(self.file_info.source_code)
        last_non_empty_token = next(
            (token for token in reversed(self.tokens)
             if token.full_width > 0),
            None,
        )

        if last_non_empty_token is None:
            start = 0
            end = 0
        else:
            first_trailing_newline_index = 0
            for trivium in last_non_empty_token.trailing_trivia:
                if trivium.kind == TriviumKind.NEWLINE:
                    break
                first_trailing_newline_index += 1
            trailing_trivia_up_to_newline = \
                last_non_empty_token.trailing_trivia[
                    :first_trailing_newline_index + 1
                ]
            trailing_trivia_up_to_newline_length = sum(
                trivium.width
                for trivium in trailing_trivia_up_to_newline
            )
            start = last_offset - trailing_trivia_up_to_newline_length
            end = start
        return OffsetRange(start=start, end=end)

    @property
    def current_token(self) -> Token:
        assert 0 <= self.token_index < len(self.tokens)
        token = self.tokens[self.token_index]
        error_trivia = [
            Trivium(kind=TriviumKind.ERROR, text=error_token.full_text)
            for error_token in self.error_tokens
        ]
        return token.update(
            leading_trivia=[*error_trivia, *token.leading_trivia],
        )

    @property
    def current_token_offset_range(self) -> OffsetRange:
        current_token = self.tokens[self.token_index]

        # We usually don't want to point to a dummy token, so rewind until
        # we find a non-dummy token.
        token_index = self.token_index
        offset = self.offset
        did_rewind = False
        while token_index > 0 and current_token.is_dummy:
            did_rewind = True
            token_index -= 1
            current_token = self.tokens[token_index]
            offset -= current_token.full_width

        start = offset + current_token.leading_width
        end = start + current_token.width

        if did_rewind:
            # If we rewound, point to the location immediately after the
            # token we rewound to, rather than that token itself.
            start = end
        return OffsetRange(start=start, end=end)

    @property
    def current_token_range(self) -> Range:
        return self.file_info.get_range_from_offset_range(
            self.current_token_offset_range,
        )

    @property
    def next_token(self) -> Optional[Token]:
        if 0 <= self.token_index + 1 < len(self.tokens):
            return self.tokens[self.token_index + 1]
        return None

    def update(
        self,
        **kwargs,
    ) -> "State":
        return attr.evolve(self, **kwargs)

    def add_error(self, error: Error) -> "State":
        return self.update(errors=self.errors + [error])

    def assert_(
        self,
        condition: bool,
        code: ErrorCode,
        message: str,
    ) -> "State":
        if not condition:
            return self.add_error(Error(
                file_info=self.file_info,
                code=code,
                severity=Severity.WARNING,
                message=f"Assertion failure -- please report this! {message}",
                notes=[],
            ))
        return self

    def start_recovery(self) -> "State":
        assert not self.is_recovering, \
            "Tried to start parser error recovery while already recovering"
        return self.update(is_recovering=True)

    def finish_recovery(self) -> "State":
        assert self.is_recovering, \
            "Tried to finish parser error recovery while not recovering"
        return self.update(is_recovering=False)

    def push_sync_token_kinds(self, token_kinds: List[TokenKind]) -> "State":
        return self.update(
            sync_token_kinds=self.sync_token_kinds + [token_kinds],
        )

    def pop_sync_token_kinds(self) -> "State":
        assert self.sync_token_kinds
        return self.update(
            sync_token_kinds=self.sync_token_kinds[:-1]
        )

    def consume_token(self, token: Token) -> "State":
        assert self.current_token.kind != TokenKind.EOF, \
            "Tried to consume the EOF token."

        # We may have added leading error tokens as trivia, but we don't want
        # to double-count their width, since they've already been consumed.
        full_width_without_errors = (
            token.width
            + sum(
                trivium.width
                for trivium in token.leading_trivia
                if trivium.kind != TriviumKind.ERROR
            )
            + sum(
                trivium.width
                for trivium in token.trailing_trivia
                if trivium.kind != TriviumKind.ERROR
            )
        )
        return self.update(
            token_index=self.token_index + 1,
            offset=self.offset + full_width_without_errors,
            error_tokens=[],
        )

    def consume_error_token(self, token: Token) -> "State":
        # Make sure not to use `self.current_token`, since that would duplicate
        # the error tokens.
        assert 0 <= self.token_index < len(self.tokens)
        token = self.tokens[self.token_index]
        assert token.kind != TokenKind.EOF, \
            "Tried to consume the EOF token as an error token."
        return self.update(
            token_index=self.token_index + 1,
            offset=self.offset + token.full_width,
            error_tokens=self.error_tokens + [token],
        )


class UnhandledParserException(Exception):
    def __init__(self, state: State) -> None:
        self._state = state

    def __str__(self) -> str:
        file_contents = ""
        for i, token in enumerate(self._state.tokens):
            if i == self._state.token_index:
                file_contents += "<HERE>"
            file_contents += token.full_text

        error_messages = "\n".join(
            f"{error.code.name}[{error.code.value}]: {error.message}"
            for error in self._state.errors
        )
        return f"""All tokens:
{self._state.tokens}

Parser location:
{file_contents}

There are {len(self._state.tokens)} tokens total,
and we are currently at token #{self._state.token_index},
which is: {self._state.current_token}.

Errors so far:
{error_messages or "<none>"}

Original exception:
{self.__cause__.__class__.__name__}: {self.__cause__}
"""


class Parser:
    def parse(self, file_info: FileInfo, tokens: List[Token]) -> Parsation:
        state = State(
            file_info=file_info,
            tokens=tokens,
            token_index=0,
            offset=0,
            errors=[],
            is_recovering=False,
            error_tokens=[],
            sync_token_kinds=[[TokenKind.EOF]],
        )

        # File with only whitespace.
        if state.current_token.kind == TokenKind.EOF:
            syntax_tree = SyntaxTree(
                n_expr=None,
                t_eof=state.current_token,
            )
            return Parsation(green_cst=syntax_tree, errors=state.errors)

        try:
            (state, n_expr) = self.parse_expr_with_left_recursion(
                state,
                allow_naked_lets=True,
            )
            t_eof = state.current_token
            syntax_tree = SyntaxTree(n_expr=n_expr, t_eof=t_eof)

            state = state.assert_(
                t_eof.kind == TokenKind.EOF,
                code=ErrorCode.SHOULD_END_WITH_EOF,
                message=(
                    "Expected the last token to be parsed "
                    + "to be the EOF token, "
                    + f"but instead it was of kind {t_eof.kind.name!r} "
                    + f"at index {state.token_index} "
                    + f"(zero-indexed, out of {len(state.tokens)})."
                ),
            )

            source_code_length = len(file_info.source_code)
            tokens_length = sum(
                token.full_width
                for token in walk_tokens(syntax_tree)
            )
            state = state.assert_(
                source_code_length == tokens_length,
                code=ErrorCode.PARSED_LENGTH_MISMATCH,
                message=(
                    f"Mismatch between source code length " +
                    f"({source_code_length}) " +
                    f"and total length of parsed tokens " +
                    f"({tokens_length}). " +
                    f"The parse tree for this file is probably incorrect."
                ),
            )

            return Parsation(green_cst=syntax_tree, errors=state.errors)
        except UnhandledParserException:
            raise
        except Exception as e:
            raise UnhandledParserException(state) from e

    def parse_let_expr(
        self,
        state: State,
        allow_naked_lets=False,
    ) -> Tuple[State, Optional[LetExpr]]:
        t_let_range = state.current_token_range
        (state, t_let) = self.expect_token(state, [TokenKind.LET])
        if not t_let:
            return (state, None)

        state = state.push_sync_token_kinds([TokenKind.DUMMY_IN])
        let_note = Note(
            file_info=state.file_info,
            message="This is the beginning of the let-binding.",
            range=t_let_range,
        )
        notes = [let_note]

        (state, n_let_expr) = self.parse_let_expr_binding(
            state,
            allow_naked_lets=allow_naked_lets,
            t_let=t_let,
            notes=notes,
        )
        (state, t_in) = self.expect_token(
            state,
            [TokenKind.DUMMY_IN],
            notes=notes,
        )
        if allow_naked_lets and state.current_token.kind == TokenKind.EOF:
            n_body = None
        else:
            (state, n_body) = self.parse_expr_with_left_recursion(
                state,
                allow_naked_lets=allow_naked_lets,
            )

        n_pattern = n_let_expr.n_pattern if n_let_expr is not None else None
        t_equals = n_let_expr.t_equals if n_let_expr is not None else None
        n_value = n_let_expr.n_value if n_let_expr is not None else None
        state = state.pop_sync_token_kinds()
        return (state, LetExpr(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
            t_in=t_in,
            n_body=n_body,
        ))

    def parse_let_expr_binding(
        self,
        state: State,
        allow_naked_lets: bool,
        t_let: Token,
        notes: List[Note],
    ) -> Tuple[State, Optional[LetExpr]]:
        if state.current_token.kind == TokenKind.EQUALS:
            # If the token is an equals sign, assume that the name is missing
            # (e.g. during editing, the user is renaming the variable), but
            # that the rest of the let-binding is present.
            n_pattern = None
            state = state.add_error(Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_PATTERN,
                severity=Severity.ERROR,
                message="I was expecting a pattern after 'let'.",
                notes=notes,
                range=state.current_token_range,
            ))
        else:
            (state, n_pattern) = self.parse_pattern(
                state,
                error=Error(
                    file_info=state.file_info,
                    code=ErrorCode.EXPECTED_PATTERN,
                    severity=Severity.ERROR,
                    message="I was expecting a pattern after 'let'.",
                    notes=notes,
                    range=state.current_token_range,
                ),
            )
        (state, t_equals) = self.expect_token(
            state,
            [TokenKind.EQUALS],
            notes=notes,
        )
        (state, n_value) = self.parse_expr_with_left_recursion(
            state,
            allow_naked_lets=False,
        )

        return (state, LetExpr(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
            t_in=None,  # Parsed by caller.
            n_body=None,  # Parsed by caller.
        ))

    def parse_pattern(
        self,
        state: State,
        error: Error,
    ) -> Tuple[State, Optional[Pattern]]:
        (state, t_identifier) = self.expect_token(
            state,
            [TokenKind.IDENTIFIER],
            error=error,
        )
        if t_identifier:
            return (state, VariablePattern(t_identifier=t_identifier))
        else:
            return (state, None)

    def parse_expr_with_left_recursion(
        self,
        state: State,

        # Set when we allow let-bindings without associated expressions. For
        # example, this at the top-level:
        #
        #     # Non-naked let; has the expression `let bar = 2`
        #     let foo =
        #       # Non-naked let; has the expression `bar`
        #       let bar = 2
        #       bar
        #
        #     # Naked let: no expression for this let-binding.
        #     let bar = 2
        allow_naked_lets: bool = False,
    ) -> Tuple[State, Optional[Expr]]:
        """Parse an expression, even if that parse involves left-recursion."""
        (state, n_expr) = self.parse_expr(
            state,
            allow_naked_lets=allow_naked_lets,
        )
        while n_expr is not None:
            token = state.current_token
            if token.kind == TokenKind.EOF:
                break
            elif token.kind == TokenKind.LPAREN:
                (state, n_expr) = self.parse_function_call(
                    state,
                    current_token=token,
                    n_callee=n_expr,
                )
            else:
                break
        return (state, n_expr)

    def skip_past(self, state: State, kind: TokenKind) -> State:
        while state.current_token.kind != kind:
            state = state.consume_error_token(state.current_token)
        state = state.consume_error_token(state.current_token)
        return state

    def add_error_and_recover(
        self,
        state: State,
        error: Error,
    ) -> State:
        if state.is_recovering:
            return state
        state = state.start_recovery()

        sync_token_kinds = set(
            token_kind
            for sync_token_kinds in state.sync_token_kinds
            for token_kind in sync_token_kinds
        )
        state = state.add_error(error)
        while state.current_token.kind != TokenKind.EOF:
            current_token = state.current_token

            if current_token.kind == TokenKind.LET:
                # 'let' is *always* paired with a dummy 'in', thanks to the
                # pre-parser, so make sure to synchronize past that 'in'.
                # Otherwise we end up with too many 'in's for our 'let's
                state = self.skip_past(state, TokenKind.DUMMY_IN)
                continue

            if current_token.kind in sync_token_kinds:
                return state
            state = state.consume_error_token(state.current_token)
        return state

    def parse_expr(
        self,
        state: State,
        allow_naked_lets: bool = False,
    ) -> Tuple[State, Optional[Expr]]:
        token = state.current_token
        if token.kind == TokenKind.IDENTIFIER:
            return self.parse_identifier(state)
        elif token.kind == TokenKind.INT_LITERAL:
            return self.parse_int_literal(state)
        elif token.kind == TokenKind.LET:
            return self.parse_let_expr(state, allow_naked_lets=allow_naked_lets)
        else:
            state = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                severity=Severity.ERROR,
                code=ErrorCode.EXPECTED_EXPRESSION,
                message=(
                    "I was expecting an expression, but instead got " +
                    self.describe_token(state.current_token) +
                    "."
                ),
                range=state.current_token_range,
                notes=[],
            ))
            return (state, None)
        raise UnhandledParserException(
            state,
        ) from ValueError(
            f"tried to parse expression of unsupported token kind {token.kind}"
        )

    def parse_function_call(
        self,
        state: State,
        current_token: Token,
        n_callee: Expr,
    ) -> Tuple[State, Optional[FunctionCallExpr]]:
        (state, n_argument_list) = self.parse_argument_list(state)
        return (state, FunctionCallExpr(
            n_callee=n_callee,
            n_argument_list=n_argument_list,
        ))

    def parse_argument_list(
        self,
        state: State,
    ) -> Tuple[State, Optional[ArgumentList]]:
        t_lparen_range = state.current_token_range
        (state, t_lparen) = self.expect_token(state, [TokenKind.LPAREN])
        if t_lparen is None:
            state = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_LPAREN,
                severity=Severity.ERROR,
                message=(
                    "I was expecting a '(' to indicate the start of a " +
                    "function argument list, but instead got " +
                    self.describe_token(state.current_token) +
                    "."
                ),
                notes=[],
                range=state.current_token_range,
            ))
            return (state, None)

        state = state.push_sync_token_kinds([TokenKind.RPAREN])
        arguments: List[Argument] = []
        while state.current_token.kind not in [TokenKind.RPAREN, TokenKind.EOF]:
            (state, n_argument) = self.parse_argument(state)
            if n_argument is None:
                break
            arguments.append(n_argument)
        state = state.pop_sync_token_kinds()

        (state, t_rparen) = self.expect_token(
            state,
            [TokenKind.RPAREN],
            error=Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_RPAREN,
                severity=Severity.ERROR,
                message=(
                    "I was expecting a ')' to indicate the end of this " +
                    "function argument list, but instead got " +
                    self.describe_token(state.current_token) +
                    "."
                ),
                notes=[Note(
                    file_info=state.file_info,
                    message="The beginning of the argument list is here.",
                    range=t_lparen_range,
                )],
                range=state.current_token_range,
            ),
        )
        return (state, ArgumentList(
            t_lparen=t_lparen,
            arguments=arguments,
            t_rparen=t_rparen,
        ))

    def parse_argument(self, state: State) -> Tuple[State, Optional[Argument]]:
        argument_start_offset = state.offset
        (state, n_expr) = self.parse_expr_with_left_recursion(state)
        if n_expr is None:
            return (state, None)

        token = state.current_token
        if token.kind == TokenKind.RPAREN:
            return (state, Argument(
                n_expr=n_expr,
                t_comma=None,
            ))

        if token.kind == TokenKind.COMMA:
            (state, t_comma) = self.expect_token(state, [TokenKind.COMMA])
            return (state, Argument(
                n_expr=n_expr,
                t_comma=t_comma,
            ))

        argument_end_offset = (
            argument_start_offset
            + n_expr.leading_width
            + n_expr.width
        )
        # The end offset is exclusive, so when the position is used as the
        # start offset, it's one character after the argument (where you
        # would expect the comma to go).
        argument_position = state.file_info.get_position_for_offset(
            argument_end_offset,
        )
        expected_comma_range = Range(
            start=argument_position,
            end=argument_position,
        )

        error = Error(
            file_info=state.file_info,
            code=ErrorCode.EXPECTED_COMMA,
            severity=Severity.ERROR,
            message=(
                "I was expecting a ',' after the previous argument."
            ),
            notes=[],
            range=expected_comma_range,
        )
        (state, t_comma) = self.expect_token(
            state,
            [TokenKind.COMMA],
            error=error,
        )

        return (state, Argument(
            n_expr=n_expr,
            t_comma=t_comma,
        ))

    def parse_identifier(
        self,
        state: State,
    ) -> Tuple[State, Optional[IdentifierExpr]]:
        (state, t_identifier) = self.expect_token(
            state,
            [TokenKind.IDENTIFIER],
        )
        if t_identifier is None:
            return (state, None)
        return (state, IdentifierExpr(t_identifier=t_identifier))

    def parse_int_literal(
        self,
        state: State,
    ) -> Tuple[State, Optional[IntLiteralExpr]]:
        (state, t_int_literal) = \
            self.expect_token(state, [TokenKind.INT_LITERAL])
        if t_int_literal is None:
            return (state, None)
        return (state, IntLiteralExpr(t_int_literal=t_int_literal))

    def expect_token(
        self,
        state: State,
        possible_token_kinds: List[TokenKind],
        *,
        notes: List[Note] = [],
        error: Error = None,
    ) -> Tuple[State, Optional[Token]]:
        token = state.current_token
        if token.kind in possible_token_kinds:
            if state.is_recovering:
                state = state.finish_recovery()
            state = state.consume_token(token)
            return (state, token)

        if state.is_recovering:
            return (state, None)

        assert len(possible_token_kinds) > 0
        if len(possible_token_kinds) == 1:
            possible_tokens_str = self.describe_token_kind(
                possible_token_kinds[0],
            )
        elif len(possible_token_kinds) == 2:
            possible_tokens_str = " or ".join([
                self.describe_token_kind(possible_token_kinds[0]),
                possible_token_kinds[1].value,
            ])
        else:
            possible_tokens_str = ", ".join(
                token.value
                for token in possible_token_kinds[:-1]
            )
            possible_tokens_str += ", or " + possible_token_kinds[-1].value

        if error is None:
            message = (
                f"I was expecting {possible_tokens_str}, " +
                f"but instead got {self.describe_token(token)}."
            )
            error = Error(
                file_info=state.file_info,
                code=ErrorCode.UNEXPECTED_TOKEN,
                severity=Severity.ERROR,
                message=message,
                notes=[],
                range=state.current_token_range,
            )
        state = self.add_error_and_recover(state, error)

        token = state.current_token
        if token.kind in possible_token_kinds:
            # We recovered to a token that the caller happens to be able to
            # handle, so return it directly.
            state = state.consume_token(token)
            state = state.finish_recovery()
            return (state, token)
        return (state, None)

    def describe_token(self, token: Token) -> str:
        if token.kind == TokenKind.ERROR:
            return f"the invalid token '{token.text}'"
        return self.describe_token_kind(token.kind)

    def describe_token_kind(self, token_kind: TokenKind) -> str:
        if token_kind.value.startswith("the "):
            return token_kind.value

        vowels = ["a", "e", "i", "o", "u"]
        if any(token_kind.value.startswith(vowel) for vowel in vowels):
            return f"an {token_kind.value}"
        else:
            return f"a {token_kind.value}"


def parse(file_info: FileInfo, tokens: List[Token]) -> Parsation:
    parser = Parser()
    return parser.parse(file_info=file_info, tokens=tokens)


__all__ = ["parse"]
