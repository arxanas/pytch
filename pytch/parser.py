"""Parses a series of tokens into a concrete syntax tree (CST).

The concrete syntax tree is not quite an abstract syntax tree: the tokens
contained therein are enough to reconstitute the source code. The
non-meaningful parts of the program are contained within "trivia" nodes. See
the lexer for more information.

The *green* CST is considered to be immutable and must not be modified.
Therefore, its nodes and tokens can be checked for referential equality and
used as keys into maps.

The *red* CST is based off of the green syntax tree. It is also immutable,
but its nodes are generated lazily (since they contain `parent` pointers and
therefore reference cycles). The object identity of its nodes and tokens must
*not* be relied on, although their corresponding nodes in
the green CST (their "origins") can be.
"""
from typing import Iterator, List, Optional, Tuple, Union

from . import FileInfo, OffsetRange, Range, warn_if
from .errors import Error, ErrorCode, Note, Severity
from .greencst import (
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


SyncTokenKind = TokenKind
"""The kind of token that we synchronized to during error-recovery.

During error-recovery, we skip ahead to the next synchronizing token.
Sometimes, we want to know what kind of token that was, to know how to
proceed with error-recovery. This could be a dummy token kind like `DUMMY_IN`
or just `EOF`.
"""


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


class Parsation:
    def __init__(self, green_cst: SyntaxTree, errors: List[Error]) -> None:
        self.green_cst = green_cst
        self.errors = errors

    @property
    def full_width(self) -> int:
        return sum(token.full_width for token in walk_tokens(self.green_cst))


class ParseException(Exception):
    def __init__(self, error: Error) -> None:
        self.error = error


class State:
    def __init__(
        self,
        file_info: FileInfo,
        tokens: List[Token],
        token_index: int,
        offset: int,
        errors: List[Error],
        error_tokens: List[Token],
    ) -> None:
        assert len(tokens) > 0, "Expected at least one token (the EOF token)."
        assert tokens[-1].kind == TokenKind.EOF, \
            "Token stream must end with an EOF token."
        assert token_index < len(tokens)

        self.file_info = file_info
        self.tokens = tokens
        self.token_index = token_index
        self.offset = offset
        self.errors = errors

        self.error_tokens: List[Token] = []

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
            Trivium(kind=TriviumKind.ERROR, text=error_token.text)
            for error_token in self.error_tokens
        ]
        return token.update(
            leading_trivia=[*error_trivia, *token.leading_trivia],
        )

    @property
    def current_token_offset_range(self) -> OffsetRange:
        current_token = self.current_token
        if current_token.kind == TokenKind.EOF:
            start = len(self.file_info.source_code)
            end = start
        else:
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
                end = start
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
        file_info: FileInfo = None,
        tokens: List[Token] = None,
        token_index: int = None,
        offset: int = None,
        errors: List[Error] = None,
        error_tokens: List[Token] = None
    ) -> "State":
        if file_info is None:
            file_info = self.file_info
        if tokens is None:
            tokens = self.tokens
        if token_index is None:
            token_index = self.token_index
        if offset is None:
            offset = self.offset
        if errors is None:
            errors = self.errors
        if error_tokens is None:
            error_tokens = self.error_tokens
        return State(
            file_info=file_info,
            tokens=tokens,
            token_index=token_index,
            offset=offset,
            errors=errors,
            error_tokens=error_tokens,
        )

    def add_error(self, error: Error) -> "State":
        return self.update(errors=self.errors + [error])

    def consume_token(self, token: Token) -> "State":
        assert self.current_token.kind != TokenKind.EOF, \
            "Tried to consume the EOF token."
        return self.update(
            token_index=self.token_index + 1,
            offset=self.offset + token.full_width,
        )

    def consume_error_token(self, token: Token) -> "State":
        assert self.current_token.kind != TokenKind.EOF, \
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
                print(self._state)
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
    def __init__(self, file_info: FileInfo, tokens: List[Token]) -> None:
        self.file_info_UPDATE_ME = file_info
        self.tokens_UPDATE_ME = tokens

    def parse(self) -> Parsation:
        state = State(
            file_info=self.file_info_UPDATE_ME,
            tokens=self.tokens_UPDATE_ME,
            token_index=0,
            offset=0,
            errors=[],
            error_tokens=[],
        )
        try:
            (state, n_expr) = self.parse_expr_with_left_recursion(
                state,
                allow_naked_lets=True,
            )
            ast = SyntaxTree(n_expr=n_expr)
            return Parsation(green_cst=ast, errors=state.errors)
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
        (state, t_let, _sync) = self.expect_token(state, [TokenKind.LET])
        if not t_let:
            return (state, None)
        let_note = Note(
            file_info=state.file_info,
            message="This is the beginning of the let-binding.",
            range=t_let_range,
        )
        notes = [let_note]

        (state, n_let_expr, sync_token_kind) = self.parse_let_expr_binding(
            state=state,
            allow_naked_lets=allow_naked_lets,
            t_let=t_let,
            notes=notes,
        )

        if n_let_expr is None:
            return (state, None)

        if sync_token_kind is None:
            (state, t_dummy_in, _sync) = self.expect_token(
                state,
                [TokenKind.DUMMY_IN],
                notes=notes,
            )
            if not t_dummy_in:
                return (state, None)

        (body_state, n_body) = self.parse_expr_with_left_recursion(
            state,
            allow_naked_lets=allow_naked_lets,
        )
        if not n_body and not allow_naked_lets:
            state = state.add_error(Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_LET_EXPRESSION,
                severity=Severity.ERROR,
                message="I was expecting an expression to follow " +
                        "the previous let-binding.",
                notes=notes,
                range=state.current_token_range,
            ))
            return (state, None)
        elif n_body:
            state = body_state

        return (state, LetExpr(
            t_let=t_let,
            n_pattern=n_let_expr.n_pattern,
            t_equals=n_let_expr.t_equals,
            n_value=n_let_expr.n_value,
            n_body=n_body,
        ))

    def parse_let_expr_binding(
        self,
        state: State,
        allow_naked_lets: bool,
        t_let: Token,
        notes: List[Note],
    ) -> Tuple[State, Optional[LetExpr], Optional[SyncTokenKind]]:
        sync_token_kind: Optional[SyncTokenKind]

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
            (pattern_state, n_pattern) = self.parse_pattern(state)
            if not n_pattern:
                (state, sync_token_kind) = self.add_error_and_recover(
                    state,
                    Error(
                        file_info=state.file_info,
                        code=ErrorCode.EXPECTED_PATTERN,
                        severity=Severity.ERROR,
                        message="I was expecting a pattern after 'let'.",
                        notes=notes,
                        range=state.current_token_range,
                    ),
                )
                if state.current_token.kind != TokenKind.EQUALS:
                    return (state, LetExpr(
                        t_let=t_let,
                        n_pattern=None,
                        t_equals=None,
                        n_value=None,
                        n_body=None,
                    ), sync_token_kind)
            state = pattern_state

        (state, t_equals, sync_token_kind) = self.expect_token(
            state,
            [TokenKind.EQUALS],
            notes=notes,
        )
        if not t_equals:
            return (state, LetExpr(
                t_let=t_let,
                n_pattern=n_pattern,
                t_equals=None,
                n_value=None,
                n_body=None,
            ), sync_token_kind)

        (expr_state, n_value) = self.parse_expr_with_left_recursion(
            state,
            allow_naked_lets=False,
        )
        if not n_value:
            (state, sync_token_kind) = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_EXPRESSION,
                severity=Severity.ERROR,
                message="I was expecting a value after the " +
                        "'=' in this let-binding.",
                notes=notes,
                range=state.current_token_range,
            ))
            return (state, LetExpr(
                t_let=t_let,
                n_pattern=n_pattern,
                t_equals=t_equals,
                n_value=None,
                n_body=None,  # TODO: Maybe recover next let-expression.
            ), sync_token_kind)
        state = expr_state

        return (state, LetExpr(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
            n_body=None,  # Parsed by caller.
        ), None)

    def parse_pattern(self, state: State) -> Tuple[State, Optional[Pattern]]:
        # TODO: Parse more kinds of patterns.
        (identifier_state, t_identifier, _sync) = \
            self.expect_token(state, [TokenKind.IDENTIFIER])
        if not t_identifier:
            return (state, None)
        state = identifier_state
        return (state, VariablePattern(t_identifier=t_identifier))

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
                    n_receiver=n_expr,
                )
            else:
                break
        return (state, n_expr)

    def add_error_and_recover(
        self,
        state: State,
        error: Error,
    ) -> Tuple[State, SyncTokenKind]:
        synchronization_token_kinds = [TokenKind.DUMMY_IN]
        state = state.add_error(error)
        while state.current_token.kind != TokenKind.EOF:
            current_token = state.current_token
            state = state.consume_error_token(state.current_token)
            if current_token.kind in synchronization_token_kinds:
                return (state, current_token.kind)
        return (state, TokenKind.EOF)

    def parse_expr(
        self,
        state: State,
        allow_naked_lets: bool = False,
    ) -> Tuple[State, Optional[Expr]]:
        token = state.current_token
        if token.kind == TokenKind.EOF:
            # TODO: Maybe this shouldn't be here, and the caller should
            # manually check for EOF.
            (state, _sync) = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                severity=Severity.ERROR,
                code=ErrorCode.EXPECTED_EXPRESSION,
                message=(
                    "I was expecting an expression " +
                    "but instead reached the end of the file."
                ),
                range=state.current_token_range,
                notes=[],
            ))
            return (state, None)
        elif token.kind == TokenKind.IDENTIFIER:
            return self.parse_identifier(state)
        elif token.kind == TokenKind.INT_LITERAL:
            return self.parse_int_literal(state)
        elif token.kind == TokenKind.LET:
            return self.parse_let_expr(state, allow_naked_lets=allow_naked_lets)
        elif token.kind == TokenKind.DUMMY_IN:
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
        n_receiver: Expr,
    ) -> Tuple[State, Optional[FunctionCallExpr]]:
        (state, t_lparen, _sync) = self.expect_token(state, [TokenKind.LPAREN])
        if t_lparen is not None:
            (state, arguments) = self.parse_function_call_arguments(state)
        else:
            state = state.add_error(Error(
                file_info=state.file_info,
                code=ErrorCode.EXPECTED_LPAREN,
                severity=Severity.ERROR,
                message=(
                    "I was expecting a '(' to indicate the start of a " +
                    "function argument list, but instead got " +
                    self.describe_token_kind(current_token.kind) +
                    "."
                ),
                notes=[],
                range=self.get_range_from_token(state, current_token),
            ))
            arguments = []
        if arguments is not None:
            (state, t_rparen, _sync) = \
                self.expect_token(state, [TokenKind.RPAREN])
        else:
            t_rparen = None
        n_function_call_expr = FunctionCallExpr(
            n_receiver=n_receiver,
            t_lparen=t_lparen,
            arguments=arguments,
            t_rparen=t_rparen,
        )
        return (state, n_function_call_expr)

    def parse_function_call_arguments(
        self,
        state: State,
    ) -> Tuple[State, Optional[List[Union[Expr, Token]]]]:
        is_first = True
        arguments: Optional[List[Union[Expr, Token]]] = []
        while arguments is not None:
            # Consume a mandatory comma separating arguments.
            if not is_first:
                token = state.current_token
                if token.kind in [TokenKind.EOF, TokenKind.RPAREN]:
                    break

                (state, t_comma, _sync) = \
                    self.expect_token(state, [TokenKind.COMMA])
                if t_comma is None:
                    arguments = None
                    break

            # If we see an rparen here (or end-of-file), that means that we're
            # done parsing arguments and must return.
            token = state.current_token
            if token.kind in [TokenKind.EOF, TokenKind.RPAREN]:
                break

            # Consume the argument.
            (state, expr) = self.parse_expr_with_left_recursion(state)
            if expr is None:
                arguments = None
                break
            else:
                arguments.append(expr)
        return (state, arguments)

    def parse_identifier(
        self,
        state: State,
    ) -> Tuple[State, Optional[IdentifierExpr]]:
        (state, t_identifier, _sync) = self.expect_token(
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
        (state, t_int_literal, _sync) = \
            self.expect_token(state, [TokenKind.INT_LITERAL])
        if t_int_literal is None:
            return (state, None)
        return (state, IntLiteralExpr(t_int_literal=t_int_literal))

    def expect_token(
        self,
        state: State,
        possible_tokens: List[TokenKind],
        *,
        notes: List[Note] = [],
    ) -> Tuple[State, Optional[Token], Optional[SyncTokenKind]]:
        token = state.current_token
        if token.kind in possible_tokens:
            return (state.consume_token(token), token, None)

        assert possible_tokens
        possible_tokens_str = self.describe_token_kind(possible_tokens[0])
        if len(possible_tokens) > 1:
            possible_tokens_str += ", ".join(
                token.value for token in possible_tokens[0:-1]
            )
            possible_tokens_str += " or " + possible_tokens[-1].value

        message = (
            f"I was expecting {possible_tokens_str}, " +
            f"but instead got {self.describe_token_kind(token.kind)}."
        )
        (state, sync_token_kind) = self.add_error_and_recover(state, Error(
            file_info=state.file_info,
            code=ErrorCode.UNEXPECTED_TOKEN,
            severity=Severity.ERROR,
            message=message,
            notes=[],
            range=self.get_range_from_token(state, token),
        ))
        return (state, None, sync_token_kind)

    def get_range_from_token(
        self,
        state: State,
        token: Token,
    ) -> Range:
        return state.file_info.get_range_from_offset_range(OffsetRange(
            start=state.offset,
            end=state.offset + token.width,
        ))

    def describe_token_kind(self, token_kind: TokenKind) -> str:
        if token_kind.value.startswith("the "):
            return token_kind.value

        vowels = ["a", "e", "i", "o", "u"]
        if any(token_kind.value.startswith(vowel) for vowel in vowels):
            return f"an {token_kind.value}"
        else:
            return f"a {token_kind.value}"


def parse(file_info: FileInfo, tokens: List[Token]) -> Parsation:
    parser = Parser(file_info=file_info, tokens=tokens)
    parsation = parser.parse()

    source_code_length = len(file_info.source_code)
    tokens_length = parsation.full_width
    warn_if(
        source_code_length != tokens_length,
        f"Mismatch between source code length ({source_code_length}) " +
        f"and total length of parsed tokens ({tokens_length}) " +
        f"in file {file_info.file_path}.\n" +
        f"The parse tree for this file is probably incorrect.\n" +
        f"This is a bug. Please report it!",
    )

    return parsation


__all__ = ["parse"]
