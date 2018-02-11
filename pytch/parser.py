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
from typing import Iterator, List, Optional, Tuple, Union

from pytch.errors import Error, Severity
from . import FileInfo, OffsetRange
from .ast import (
    Ast,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IntLiteralExpr,
    LetStatement,
    Node,
    Pattern,
    VariablePattern,
)
from .lexer import Token, TokenKind


class ErrorCode(Enum):
    UNEXPECTED_TOKEN = 1000
    EXPECTED_EXPRESSION = 1001
    EXPECTED_LPAREN = 1002
    EXPECTED_RPAREN = 1003
    EXPECTED_INDENT = 1004
    EXPECTED_DEDENT = 1005


def walk_tokens(node: Node) -> Iterator[Token]:
    for child in node.children:
        if isinstance(child, Token):
            yield child
        elif isinstance(child, Node):
            yield from walk_tokens(child)
        else:
            assert False


class Parsation:
    def __init__(self, ast: Ast, errors: List[Error]) -> None:
        self.ast = ast
        self.errors = errors

    @property
    def full_width(self) -> int:
        return sum(token.full_width for token in walk_tokens(self.ast))


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
            f"[{error.code}] {error.title}: {error.message}"
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
        )
        try:
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
        except UnhandledParserException:
            raise
        except Exception as e:
            raise UnhandledParserException(state) from e

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
        state = state.add_error(error)
        while (
            state.current_token is not None
            and state.current_token.kind != TokenKind.DEDENT
        ):
            state = state.consume_token(state.current_token)
        return state

    def parse_expr(self, state: State) -> Tuple[State, Optional[Expr]]:
        # TODO: Parse more kinds of expressions.
        token = state.current_token
        if token is None:
            previous_token = state.previous_token
            assert previous_token is not None
            state = self.add_error_and_recover(state, Error(
                file_info=state.file_info,
                severity=Severity.ERROR,
                title="Expected expression",
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
        if token.kind == TokenKind.INDENT:
            return self.parse_indented_expr(state)
        elif token.kind == TokenKind.DEDENT:
            # The caller should already be handling an indented block, so just
            # leave it to them to consume the dedent token as well.
            return (state, None)
        elif token.kind == TokenKind.IDENTIFIER:
            # TODO: Potentially look ahead to parse a bigger expression.
            return self.parse_identifier(state)
        elif token.kind == TokenKind.INT_LITERAL:
            return self.parse_int_literal(state)
        raise UnhandledParserException(
            state,
        ) from ValueError(
            f"tried to parse expression of unsupported token kind {token.kind}"
        )

    def parse_indented_expr(
        self,
        state: State,
    ) -> Tuple[State, Optional[Expr]]:
        (state, t_indent) = self.expect_token(state, [TokenKind.INDENT])
        if t_indent is None:
            state = state.add_error(Error(
                file_info=state.file_info,
                title="Expected indent",
                code=ErrorCode.EXPECTED_INDENT.value,
                severity=Severity.ERROR,
                message="I was expecting an indent and then an expression.",
                notes=[],
            ))
            return (state, None)
        (state, n_expr) = self.parse_expr_with_left_recursion(state)
        if n_expr is None:
            return (state, None)
        (state, t_dedent) = self.expect_token(state, [TokenKind.DEDENT])
        if t_dedent is None:
            state = state.add_error(Error(
                file_info=state.file_info,
                title="Expected dedent",
                code=ErrorCode.EXPECTED_DEDENT.value,
                severity=Severity.ERROR,
                message="I was expecting a dedent after this indented block.",
                # TODO: Perhaps show the start of the indented block.
                notes=[],
            ))
            return (state, None)
        return (state, n_expr)

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
                    "I was expecting a '(' to indicate the start of a " +
                    "function argument list, but instead got " +
                    self.describe_token_kind(current_token.kind) +
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

        assert possible_tokens
        possible_tokens_str = self.describe_token_kind(possible_tokens[0])
        if len(possible_tokens) > 1:
            possible_tokens_str += ", ".join(
                token.value for token in possible_tokens[0:-1]
            )
            possible_tokens_str += " or " + possible_tokens[-1].value

        offset_range: Optional[OffsetRange]
        if token is not None:
            message = (
                f"I was expecting {possible_tokens_str}, " +
                f"but instead got " +
                self.describe_token_kind(token.kind) +
                "."
            )
            offset_range = self.get_offset_range_from_token(state, token)
        else:
            message = (
                f"I was expecting {possible_tokens_str}, " +
                f"but instead reached the end of the file."
            )
            offset_range = None

        state = self.add_error_and_recover(state, Error(
            file_info=state.file_info,
            title="Unexpected token",
            code=ErrorCode.UNEXPECTED_TOKEN.value,
            severity=Severity.ERROR,
            message=message,
            notes=[],
            offset_range=offset_range,
        ))
        return (state, None)

    def get_offset_range_from_token(
        self,
        state: State,
        token: Token,
    ) -> OffsetRange:
        return OffsetRange(
            start=state.offset,
            end=state.offset + token.width,
        )

    def describe_token_kind(self, token_kind: TokenKind) -> str:
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
    assert source_code_length == tokens_length, (
        f"Mismatch between source code length ({source_code_length}) "
        f"and total length of parsed tokens ({tokens_length})"
    )

    return parsation


__all__ = ["parse"]
