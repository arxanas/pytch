"""Parses a series of tokens into a syntax tree.

The syntax tree is not quite an abstract syntax tree: the tokens contained
therein are enough to reconstitute the source code. The non-meaningful parts
of the program are contained within "trivia" nodes. See the lexer for more
information.

The syntax tree is considered to be immutable and must not be modified.
Therefore, its nodes and tokens can be checked for referential equality and
used as keys into maps.
"""
from typing import List, Optional, Sequence, Union

import pytch.errors
from . import FileInfo, OffsetRange
from .lexer import Token, TokenKind


class Node:
    def __init__(self, children: Sequence[Union["Node", Token]]) -> None:
        self.children = children


TopLevelStatement = Union["LetStatement"]


class Ast(Node):
    def __init__(self, n_statements: List[TopLevelStatement]) -> None:
        super().__init__(children=n_statements)
        self.n_statements = n_statements


# TODO
class Pattern(Node):
    pass


class VariablePattern(Pattern):
    def __init__(self, t_identifier: Token) -> None:
        super().__init__([t_identifier])
        self.t_identifier = t_identifier


class Expr(Node):
    pass


class LetStatement(Node):
    def __init__(
        self,
        t_let: Token,
        n_pattern: Pattern,
        t_equals: Token,
        n_value: Expr,
    ) -> None:
        super().__init__(children=[t_let, n_pattern, t_equals, n_value])
        self.t_let = t_let
        self.n_pattern = n_pattern
        self.t_equals = t_equals
        self.n_value = n_value


class LetExpr(Expr):
    def __init__(self, n_let_stmt: LetStatement, n_body: Expr) -> None:
        super().__init__(children=[n_let_stmt, n_body])
        self.n_let_stmt = n_let_stmt
        self.n_body = n_body


class IdentifierExpr(Expr):
    def __init__(self, t_identifier: Token) -> None:
        super().__init__(children=[t_identifier])
        self.t_identifier = t_identifier


class IntLiteralExpr(Expr):
    def __init__(self, t_int_literal: Token) -> None:
        super().__init__(children=[t_int_literal])
        self.t_int_literal = t_int_literal


class FunctionCallExpr(Expr):
    def __init__(
        self,
        n_receiver: Expr,
        t_lparen: Token,

        # This contains both the actual arguments and their interspersed commas.
        arguments: List[Union[Expr, Token]],

        t_rparen: Token
    ) -> None:
        super().__init__(children=[n_receiver, t_lparen, *arguments, t_rparen])
        self.n_receiver = n_receiver
        self.t_lparen = t_lparen
        self.arguments = arguments
        self.t_rparen = t_rparen


class Parsation:
    def __init__(self, ast: Ast, errors: List[pytch.errors.Error]) -> None:
        self.ast = ast
        self.errors = errors


class ParseException(Exception):
    def __init__(self, error: pytch.errors.Error) -> None:
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
            raise ParseException(pytch.errors.Error(
                file_info=self.file_info,
                severity=pytch.errors.Severity.ERROR,
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


__all__ = ["Node", "parse"]
