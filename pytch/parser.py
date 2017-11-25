from typing import List, Sequence, Union

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


class IntLiteralExpr(Expr):
    def __init__(self, t_int_literal: Token) -> None:
        super().__init__(children=[t_int_literal])
        self.t_int_literal = t_int_literal


class ExprFunctionCall(Expr):
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


class Parser:
    def __init__(self, source_code: str, tokens: List[Token]) -> None:
        self.source_code = source_code
        self.tokens = tokens
        self.token_index = 0
        self.offset = 0

    def parse(self) -> Ast:
        top_level_stmts = []
        last_index = -1
        while self.token_index < len(self.tokens):
            assert self.token_index > last_index, \
                f"Didn't make progress in parsing at token {self.token_index}"
            last_index = self.token_index
            stmt_let = self._parse_stmt_let()
            top_level_stmts.append(stmt_let)
        return Ast(n_statements=top_level_stmts)

    def _parse_stmt_let(self) -> LetStatement:
        t_let = self._expect_token([TokenKind.LET])
        n_pattern = self._parse_pattern()
        t_equals = self._expect_token([TokenKind.EQUALS])
        n_value = self._parse_expr()
        return LetStatement(
            t_let=t_let,
            n_pattern=n_pattern,
            t_equals=t_equals,
            n_value=n_value,
        )

    def _parse_pattern(self) -> Pattern:
        # TODO: Parse more kinds of patterns.
        t_identifier = self._expect_token([TokenKind.IDENTIFIER])
        return VariablePattern(t_identifier=t_identifier)

    def _parse_expr(self) -> Expr:
        # TODO: Parse more kinds of expressions.
        int_literal = self._parse_int_literal()
        return int_literal

    def _parse_int_literal(self) -> IntLiteralExpr:
        t_int_literal = self._expect_token([TokenKind.INT_LITERAL])
        return IntLiteralExpr(t_int_literal=t_int_literal)

    def _expect_token(self, possible_tokens: List[TokenKind]) -> Token:
        token = self._current_token()
        if token.kind in possible_tokens:
            return self._consume_token()
        raise ValueError(
            f"expected one of {possible_tokens!r}, got {token.kind}",
        )

    def _current_token(self) -> Token:
        return self.tokens[self.token_index]

    def _consume_token(self) -> Token:
        token = self.tokens[self.token_index]
        self.token_index += 1
        self.offset += token.full_width
        return token


def parse(source_code: str, tokens: List[Token]) -> Ast:
    parser = Parser(source_code=source_code, tokens=tokens)
    return parser.parse()


__all__ = ["Node", "parse"]
