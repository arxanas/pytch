"""NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
"""
from typing import List, Optional, Sequence, Union

import pytch.greencst as greencst
from .lexer import Token


class Node:
    def __init__(
        self,
        parent: Optional["Node"],
    ) -> None:
        self._parent = parent

    @property
    def parent(self) -> Optional["Node"]:
        return self._parent

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        raise NotImplementedError("should be implemented by children")


class Expr(Node):
    pass


class SyntaxTree(Node):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.SyntaxTree,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def n_expr(self) -> Optional[Expr]:
        return Optional[Expr](
            parent=self,
            origin=self.origin.n_expr
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.n_expr,
        ]


class Pattern(Node):
    pass


class VariablePattern(Pattern):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.VariablePattern,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def t_identifier(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_identifier
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_identifier,
        ]


class LetExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.LetExpr,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def t_let(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_let
        )

    @property
    def n_pattern(self) -> Optional[Pattern]:
        return Optional[Pattern](
            parent=self,
            origin=self.origin.n_pattern
        )

    @property
    def t_equals(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_equals
        )

    @property
    def n_value(self) -> Optional[Expr]:
        return Optional[Expr](
            parent=self,
            origin=self.origin.n_value
        )

    @property
    def n_body(self) -> Optional[Expr]:
        return Optional[Expr](
            parent=self,
            origin=self.origin.n_body
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_let,
            self.n_pattern,
            self.t_equals,
            self.n_value,
            self.n_body,
        ]


class IdentifierExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.IdentifierExpr,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def t_identifier(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_identifier
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_identifier,
        ]


class IntLiteralExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.IntLiteralExpr,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def t_int_literal(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_int_literal
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_int_literal,
        ]


class FunctionCallExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.FunctionCallExpr,
    ) -> None:
        super().__init__(parent)
        self.origin = origin

    @property
    def n_receiver(self) -> Optional[Expr]:
        return Optional[Expr](
            parent=self,
            origin=self.origin.n_receiver
        )

    @property
    def t_lparen(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_lparen
        )

    @property
    def arguments(self) -> Optional[List[Union[Expr, Token]]]:
        return Optional[List[Union[Expr, Token]]](
            parent=self,
            origin=self.origin.arguments
        )

    @property
    def t_rparen(self) -> Optional[Token]:
        return Optional[Token](
            parent=self,
            origin=self.origin.t_rparen
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.n_receiver,
            self.t_lparen,
            *(self.arguments if self.arguments is not None else []),
            self.t_rparen,
        ]


__all__ = [
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
