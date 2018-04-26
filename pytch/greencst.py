"""NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
"""
from typing import List, Optional, Sequence, Union

from .lexer import Token


class Node:
    def __init__(
        self,
        children: Sequence[Union["Node", Optional["Token"]]],
    ) -> None:
        self._children = children

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        return self._children

    @property
    def full_width(self) -> int:
        return sum(
            child.full_width if child is not None else 0
            for child in self.children
        )


class Expr(Node):
    pass


class SyntaxTree(Node):
    def __init__(
        self,
        n_expr: Optional[Expr],
        t_eof: Optional[Token],
    ) -> None:
        super().__init__([
            n_expr,
            t_eof,
        ])
        self._n_expr = n_expr
        self._t_eof = t_eof

    @property
    def n_expr(self) -> Optional[Expr]:
        return self._n_expr

    @property
    def t_eof(self) -> Optional[Token]:
        return self._t_eof


class Pattern(Node):
    pass


class VariablePattern(Pattern):
    def __init__(
        self,
        t_identifier: Optional[Token],
    ) -> None:
        super().__init__([
            t_identifier,
        ])
        self._t_identifier = t_identifier

    @property
    def t_identifier(self) -> Optional[Token]:
        return self._t_identifier


class LetExpr(Expr):
    def __init__(
        self,
        t_let: Optional[Token],
        n_pattern: Optional[Pattern],
        t_equals: Optional[Token],
        n_value: Optional[Expr],
        n_body: Optional[Expr],
    ) -> None:
        super().__init__([
            t_let,
            n_pattern,
            t_equals,
            n_value,
            n_body,
        ])
        self._t_let = t_let
        self._n_pattern = n_pattern
        self._t_equals = t_equals
        self._n_value = n_value
        self._n_body = n_body

    @property
    def t_let(self) -> Optional[Token]:
        return self._t_let

    @property
    def n_pattern(self) -> Optional[Pattern]:
        return self._n_pattern

    @property
    def t_equals(self) -> Optional[Token]:
        return self._t_equals

    @property
    def n_value(self) -> Optional[Expr]:
        return self._n_value

    @property
    def n_body(self) -> Optional[Expr]:
        return self._n_body


class IdentifierExpr(Expr):
    def __init__(
        self,
        t_identifier: Optional[Token],
    ) -> None:
        super().__init__([
            t_identifier,
        ])
        self._t_identifier = t_identifier

    @property
    def t_identifier(self) -> Optional[Token]:
        return self._t_identifier


class IntLiteralExpr(Expr):
    def __init__(
        self,
        t_int_literal: Optional[Token],
    ) -> None:
        super().__init__([
            t_int_literal,
        ])
        self._t_int_literal = t_int_literal

    @property
    def t_int_literal(self) -> Optional[Token]:
        return self._t_int_literal


class Argument(Node):
    def __init__(
        self,
        n_expr: Optional[Expr],
        t_comma: Optional[Token],
    ) -> None:
        super().__init__([
            n_expr,
            t_comma,
        ])
        self._n_expr = n_expr
        self._t_comma = t_comma

    @property
    def n_expr(self) -> Optional[Expr]:
        return self._n_expr

    @property
    def t_comma(self) -> Optional[Token]:
        return self._t_comma


class ArgumentList(Node):
    def __init__(
        self,
        t_lparen: Optional[Token],
        arguments: Optional[List[Argument]],
        t_rparen: Optional[Token],
    ) -> None:
        super().__init__([
            t_lparen,
            *(arguments if arguments is not None else []),
            t_rparen,
        ])
        self._t_lparen = t_lparen
        self._arguments = arguments
        self._t_rparen = t_rparen

    @property
    def t_lparen(self) -> Optional[Token]:
        return self._t_lparen

    @property
    def arguments(self) -> Optional[List[Argument]]:
        return self._arguments

    @property
    def t_rparen(self) -> Optional[Token]:
        return self._t_rparen


class FunctionCallExpr(Expr):
    def __init__(
        self,
        n_receiver: Optional[Expr],
        n_argument_list: Optional[ArgumentList],
    ) -> None:
        super().__init__([
            n_receiver,
            n_argument_list,
        ])
        self._n_receiver = n_receiver
        self._n_argument_list = n_argument_list

    @property
    def n_receiver(self) -> Optional[Expr]:
        return self._n_receiver

    @property
    def n_argument_list(self) -> Optional[ArgumentList]:
        return self._n_argument_list


__all__ = [
    "Argument",
    "ArgumentList",
    "Expr",
    "FunctionCallExpr",
    "IdentifierExpr",
    "IntLiteralExpr",
    "LetExpr",
    "Node",
    "Pattern",
    "SyntaxTree",
    "VariablePattern",
]
