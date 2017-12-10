"""Parses a series of tokens into a syntax tree.

The syntax tree is not quite an abstract syntax tree: the tokens contained
therein are enough to reconstitute the source code. The non-meaningful parts
of the program are contained within "trivia" nodes. See the lexer for more
information.

The syntax tree is considered to be immutable and must not be modified.
Therefore, its nodes and tokens can be checked for referential equality and
used as keys into maps.
"""
from typing import List, Optional, Union

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


class Parsation:
    def __init__(self, ast: Ast, errors: List[Error]) -> None:
        self.ast = ast
        self.errors = errors


class ParseException(Exception):
    def __init__(self, error: Error) -> None:
        self.error = error


class Parser:
    def __init__(self, file_info: FileInfo, tokens: List[Token]) -> None:
        self.file_info = file_info
        self.tokens = tokens
        self.token_index = 0
        self.offset = 0

    def parse(self) -> Parsation:
        errors = []
        top_level_stmts = []
        last_index = -1
        while self.token_index < len(self.tokens):
            try:
                assert self.token_index > last_index, (
                    f"Didn't make progress in parsing "
                    f"at token {self.token_index}"
                )
                last_index = self.token_index
                stmt_let = self.parse_stmt_let()
                top_level_stmts.append(stmt_let)
            except ParseException as e:
                errors.append(e.error)
        ast = Ast(n_statements=top_level_stmts)
        return Parsation(ast=ast, errors=errors)

    def parse_stmt_let(self) -> LetStatement:
        t_let = self.expect_token([TokenKind.LET])
        n_pattern = self.parse_pattern()
        t_equals = self.expect_token([TokenKind.EQUALS])
        n_value = self.parse_expr_with_left_recursion()
        return LetStatement(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
        )

    def parse_pattern(self) -> Pattern:
        # TODO: Parse more kinds of patterns.
        t_identifier = self.expect_token([TokenKind.IDENTIFIER])
        return VariablePattern(t_identifier=t_identifier)

    def parse_expr_with_left_recursion(self) -> Expr:
        """Parse an expression, even if that parse involves left-recursion.

        To overcome left-recursion issues, simply parse an expression, and
        then look ahead one token. If the token is appropriate, continue
        parsing an expression.
        """
        n_expr = self.parse_expr()
        while True:
            token = self.current_token()
            if token is None:
                break
            if token.kind == TokenKind.LPAREN:
                t_lparen = self.expect_token([TokenKind.LPAREN])
                arguments = self.parse_function_call_arguments()
                t_rparen = self.expect_token([TokenKind.RPAREN])
                n_expr = FunctionCallExpr(
                    n_receiver=n_expr,
                    t_lparen=t_lparen,
                    arguments=arguments,
                    t_rparen=t_rparen,
                )
            else:
                break
        return n_expr

    def parse_expr(self) -> Expr:
        # TODO: Parse more kinds of expressions.
        token = self.current_token()
        if token is None:
            previous_token = self.previous_token()
            assert previous_token is not None
            raise ParseException(Error(
                file_info=self.file_info,
                severity=Severity.ERROR,
                title="Expected expression.",
                code=1001,
                message=(
                    "I was expecting an expression but " +
                    "instead got to end-of-file."
                ),
                offset_range=OffsetRange(
                    start=(
                        self.offset
                        - (previous_token.width + previous_token.trailing_width)
                    ),
                    end=self.offset,
                ),
                notes=[],
            ))
        if token.kind == TokenKind.IDENTIFIER:
            # TODO: Potentially look ahead to parse a bigger expression.
            return self.parse_identifier()
        elif token.kind == TokenKind.INT_LITERAL:
            return self.parse_int_literal()
        raise ValueError(
            f"tried to parse expression of unsupported token kind {token.kind}"
        )

    def parse_function_call_arguments(self) -> List[Union[Token, Expr]]:
        is_first = True
        arguments: List[Union[Token, Expr]] = []
        while True:
            token = self.current_token()
            if token is None:
                raise ValueError("expected ')'")
            if token.kind == TokenKind.RPAREN:
                break
            if not is_first:
                arguments.append(self.expect_token([TokenKind.COMMA]))
                is_first = False

            token = self.current_token()
            if token is None:
                raise ValueError("expected ')'")
            if token.kind == TokenKind.RPAREN:
                # We had a trailing comma.
                break
            arguments.append(self.parse_expr_with_left_recursion())
        return arguments

    def parse_identifier(self) -> IdentifierExpr:
        t_identifier = self.expect_token([TokenKind.IDENTIFIER])
        return IdentifierExpr(t_identifier=t_identifier)

    def parse_int_literal(self) -> IntLiteralExpr:
        t_int_literal = self.expect_token([TokenKind.INT_LITERAL])
        return IntLiteralExpr(t_int_literal=t_int_literal)

    def expect_token(self, possible_tokens: List[TokenKind]) -> Token:
        token = self.current_token()
        if token is not None and token.kind in possible_tokens:
            return self.consume_token()

        if token is not None:
            raise ValueError(
                f"expected one of {possible_tokens!r}, got {token.kind}",
            )
        else:
            raise ValueError(
                f"expected one of {possible_tokens!r}, got end-of-file",
            )

    def previous_token(self) -> Optional[Token]:
        if self.token_index > 0:
            return self.tokens[self.token_index - 1]
        else:
            return None

    def current_token(self) -> Optional[Token]:
        try:
            return self.tokens[self.token_index]
        except IndexError:
            return None

    def consume_token(self) -> Token:
        token = self.tokens[self.token_index]
        self.token_index += 1
        self.offset += token.full_width
        return token


def parse(file_info: FileInfo, tokens: List[Token]) -> Parsation:
    parser = Parser(file_info=file_info, tokens=tokens)
    return parser.parse()


__all__ = ["parse"]
