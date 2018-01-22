"""Parses a series of tokens into a syntax tree.

The syntax tree is not quite an abstract syntax tree: the tokens contained
therein are enough to reconstitute the source code. The non-meaningful parts
of the program are contained within "trivia" nodes. See the lexer for more
information.

The syntax tree is considered to be immutable and must not be modified.
Therefore, its nodes and tokens can be checked for referential equality and
used as keys into maps.
"""
from enum import Enum
from typing import List, Optional, Tuple, Union

from pytch.errors import Error, Severity
from . import FileInfo, OffsetRange
from .ast import (
    Ast,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IntLiteralExpr,
    LetStatement,
    Pattern,
    VariablePattern,
)
from .lexer import Token, TokenKind


class ErrorCode(Enum):
    UNEXPECTED_TOKEN = 1000
    EXPECTED_EXPRESSION = 1001
    EXPECTED_LPAREN = 1002
    EXPECTED_RPAREN = 1003


class Parsation:
    def __init__(self, ast: Ast, errors: List[Error]) -> None:
        self.ast = ast
        self.errors = errors


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
    ) -> None:
        # TODO: Remove this?
        # We accept `token_index == len(tokens)` because that's the state we
        # would be in when we've consumed all the tokens.
        assert token_index <= len(tokens)

        self.file_info = file_info
        self.tokens = tokens
        self.token_index = token_index
        self.offset = offset
        self.errors = errors

    @property
    def previous_token(self) -> Optional[Token]:
        if 0 <= self.token_index - 1 < len(self.tokens):
            return self.tokens[self.token_index - 1]
        return None

    @property
    def current_token(self) -> Optional[Token]:
        if 0 <= self.token_index < len(self.tokens):
            return self.tokens[self.token_index]
        return None

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
        return State(
            file_info=file_info,
            tokens=tokens,
            token_index=token_index,
            offset=offset,
            errors=errors,
        )

    def add_error(self, error: Error) -> "State":
        return self.update(errors=self.errors + [error])

    def consume_token(self, token: Token) -> "State":
        return self.update(
            token_index=self.token_index + 1,
            offset=self.offset + token.full_width,
        )


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
        )
        top_level_stmts = []
        last_index = -1
        while state.token_index < len(state.tokens):
            assert state.token_index > last_index, (
                f"Didn't make progress in parsing "
                f"at token {state.token_index}"
            )
            last_index = state.token_index
            (state, stmt_let) = self.parse_stmt_let(state)
            top_level_stmts.append(stmt_let)
        ast = Ast(n_statements=top_level_stmts)
        return Parsation(ast=ast, errors=state.errors)

    def parse_stmt_let(self, state: State) -> Tuple[State, LetStatement]:
        (state, t_let) = self.expect_token(state, [TokenKind.LET])
        (state, n_pattern) = self.parse_pattern(state)
        (state, t_equals) = self.expect_token(state, [TokenKind.EQUALS])
        (state, n_value) = self.parse_expr_with_left_recursion(state)
        return (state, LetStatement(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
        ))

    def parse_pattern(self, state: State) -> Tuple[State, Optional[Pattern]]:
        # TODO: Parse more kinds of patterns.
        (state, t_identifier) = self.expect_token(state, [TokenKind.IDENTIFIER])
        return (state, VariablePattern(t_identifier=t_identifier))

    def parse_expr_with_left_recursion(
        self,
        state: State,
    ) -> Tuple[State, Optional[Expr]]:
        """Parse an expression, even if that parse involves left-recursion."""
        (state, n_expr) = self.parse_expr(state)
        while n_expr is not None:
            token = state.current_token
            if token is None:
                break
            if token.kind == TokenKind.LPAREN:
                (state, n_expr) = self.parse_function_call(
                    state,
                    current_token=token,
                    n_receiver=n_expr,
                )
            else:
                break
        return (state, n_expr)

    def add_error_and_recover(self, state: State, error: Error) -> State:
        raise NotImplementedError()

    def parse_expr(self, state: State) -> Tuple[State, Optional[Expr]]:
        # TODO: Parse more kinds of expressions.
        token = state.current_token
        if token is None:
            previous_token = state.previous_token
            assert previous_token is not None
            state = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                severity=Severity.ERROR,
                title="Expected expression.",
                code=ErrorCode.EXPECTED_EXPRESSION.value,
                message=(
                    "I was expecting an expression " +
                    "but instead reached the end of the file."
                ),
                offset_range=OffsetRange(
                    start=(
                        state.offset
                        - (previous_token.width + previous_token.trailing_width)
                    ),
                    end=state.offset,
                ),
                notes=[],
            ))
            return (state, None)
        if token.kind == TokenKind.IDENTIFIER:
            # TODO: Potentially look ahead to parse a bigger expression.
            return self.parse_identifier(state)
        elif token.kind == TokenKind.INT_LITERAL:
            return self.parse_int_literal(state)
        raise ValueError(
            f"tried to parse expression of unsupported token kind {token.kind}"
        )

    def parse_function_call(
        self,
        state: State,
        current_token: Token,
        n_receiver: Expr,
    ) -> Tuple[State, Optional[FunctionCallExpr]]:
        (state, t_lparen) = self.expect_token(state, [TokenKind.LPAREN])
        if t_lparen is not None:
            (state, arguments) = self.parse_function_call_arguments(state)
        else:
            state = state.add_error(Error(
                file_info=state.file_info,
                title="Expected '('",
                code=ErrorCode.EXPECTED_LPAREN.value,
                severity=Severity.ERROR,
                message=(
                    "I expected a '(' to indicate the start of a " +
                    "function argument list, but instead got " +
                    self.describe_token_kind(current_token) +
                    "."
                ),
                notes=[],
                offset_range=self.get_offset_range_from_token(
                    state,
                    current_token,
                ),
            ))
            arguments = []
        if arguments is not None:
            (state, t_rparen) = self.expect_token(state, [TokenKind.RPAREN])
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
                if token is None or token.kind == TokenKind.RPAREN:
                    break

                (state, t_comma) = self.expect_token(state, [TokenKind.COMMA])
                if t_comma is None:
                    arguments = None
                    break

            # If we see an rparen here (or end-of-file), that means that we're
            # done parsing arguments and must return.
            token = state.current_token
            if token is None or token.kind == TokenKind.RPAREN:
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
        (state, t_identifier) = self.expect_token(state, [TokenKind.IDENTIFIER])
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
        possible_tokens: List[TokenKind],
    ) -> Tuple[State, Optional[Token]]:
        token = state.current_token
        if token is not None and token.kind in possible_tokens:
            return (state.consume_token(token), token)

        if token is not None:
            message = (
                f"I expected one of {possible_tokens!r}, " +
                f"but instead got " +
                self.describe_token_kind(token) +
                "."
            )
            offset_range = self.get_offset_range_from_token(state, token)
        else:
            message = (
                f"I expected one of {possible_tokens!r}, " +
                f"but instead reached the end of the file."
            )

        state = self.add_error_and_recover(state, Error(
            file_info=state.file_info,
            title="Unexpected token.",
            code=ErrorCode.UNEXPECTED_TOKEN.value,
            severity=Severity.ERROR,
            message=message,
            notes=[],
            offset_range=offset_range,
        ))
        token = None
        return (state, token)

    def get_offset_range_from_token(
        self,
        state: State,
        token: Token,
    ) -> OffsetRange:
        return OffsetRange(
            start=state.offset,
            end=state.offset + token.width,
        )

    def describe_token_kind(self, token: Token) -> str:
        vowels = ["a", "e", "i", "o", "u"]
        if any(token.kind.value.startswith(vowel) for vowel in vowels):
            return f"an {token.kind}"
        else:
            return f"a {token.kind}"


def parse(file_info: FileInfo, tokens: List[Token]) -> Parsation:
    parser = Parser(file_info=file_info, tokens=tokens)
    return parser.parse()


__all__ = ["parse"]
