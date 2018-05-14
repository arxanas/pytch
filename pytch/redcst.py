"""NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
"""
from typing import List, Optional, Sequence, Union

import pytch.greencst as greencst
from . import OffsetRange
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
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `children`",
        )

    @property
    def full_width(self) -> int:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `full_width`",
        )


class Expr(Node):
    pass


class SyntaxTree(Node):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.SyntaxTree,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_expr: Optional[Expr] = None

    @property
    def n_expr(self) -> Optional[Expr]:
        if self.origin.n_expr is None:
            return None
        if self._n_expr is not None:
            return self._n_expr
        offset = (
            self.offset
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_expr.__class__](
            parent=self,
            origin=self.origin.n_expr,
            offset=offset,
        )
        self._n_expr = result
        return result

    @property
    def t_eof(self) -> Optional[Token]:
        return self.origin.t_eof

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.n_expr,
            self.t_eof,
        ]


class Pattern(Node):
    pass


class VariablePattern(Pattern):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.VariablePattern,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_identifier(self) -> Optional[Token]:
        return self.origin.t_identifier

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
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
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_pattern: Optional[Pattern] = None
        self._n_value: Optional[Expr] = None
        self._n_body: Optional[Expr] = None

    @property
    def t_let(self) -> Optional[Token]:
        return self.origin.t_let

    @property
    def n_pattern(self) -> Optional[Pattern]:
        if self.origin.n_pattern is None:
            return None
        if self._n_pattern is not None:
            return self._n_pattern
        offset = (
            self.offset
            + (
                self.t_let.full_width
                if self.t_let is not None else
                0
            )
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_pattern.__class__](
            parent=self,
            origin=self.origin.n_pattern,
            offset=offset,
        )
        self._n_pattern = result
        return result

    @property
    def t_equals(self) -> Optional[Token]:
        return self.origin.t_equals

    @property
    def n_value(self) -> Optional[Expr]:
        if self.origin.n_value is None:
            return None
        if self._n_value is not None:
            return self._n_value
        offset = (
            self.offset
            + (
                self.t_let.full_width
                if self.t_let is not None else
                0
            )
            + (
                self.n_pattern.full_width
                if self.n_pattern is not None else
                0
            )
            + (
                self.t_equals.full_width
                if self.t_equals is not None else
                0
            )
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_value.__class__](
            parent=self,
            origin=self.origin.n_value,
            offset=offset,
        )
        self._n_value = result
        return result

    @property
    def t_in(self) -> Optional[Token]:
        return self.origin.t_in

    @property
    def n_body(self) -> Optional[Expr]:
        if self.origin.n_body is None:
            return None
        if self._n_body is not None:
            return self._n_body
        offset = (
            self.offset
            + (
                self.t_let.full_width
                if self.t_let is not None else
                0
            )
            + (
                self.n_pattern.full_width
                if self.n_pattern is not None else
                0
            )
            + (
                self.t_equals.full_width
                if self.t_equals is not None else
                0
            )
            + (
                self.n_value.full_width
                if self.n_value is not None else
                0
            )
            + (
                self.t_in.full_width
                if self.t_in is not None else
                0
            )
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_body.__class__](
            parent=self,
            origin=self.origin.n_body,
            offset=offset,
        )
        self._n_body = result
        return result

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_let,
            self.n_pattern,
            self.t_equals,
            self.n_value,
            self.t_in,
            self.n_body,
        ]


class IdentifierExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.IdentifierExpr,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_identifier(self) -> Optional[Token]:
        return self.origin.t_identifier

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
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
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_int_literal(self) -> Optional[Token]:
        return self.origin.t_int_literal

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_int_literal,
        ]


class Argument(Node):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.Argument,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_expr: Optional[Expr] = None

    @property
    def n_expr(self) -> Optional[Expr]:
        if self.origin.n_expr is None:
            return None
        if self._n_expr is not None:
            return self._n_expr
        offset = (
            self.offset
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_expr.__class__](
            parent=self,
            origin=self.origin.n_expr,
            offset=offset,
        )
        self._n_expr = result
        return result

    @property
    def t_comma(self) -> Optional[Token]:
        return self.origin.t_comma

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.n_expr,
            self.t_comma,
        ]


class ArgumentList(Node):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.ArgumentList,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._arguments: Optional[List[Argument]] = None

    @property
    def t_lparen(self) -> Optional[Token]:
        return self.origin.t_lparen

    @property
    def arguments(self) -> Optional[List[Argument]]:
        if self.origin.arguments is None:
            return None
        if self._arguments is not None:
            return self._arguments
        offset = (
            self.offset
            + (
                self.t_lparen.full_width
                if self.t_lparen is not None else
                0
            )
        )
        result = []
        for child in self.origin.arguments:
            result.append(Argument(
                parent=self,
                origin=child,
                offset=offset,
            ))
            offset += child.full_width
        self._arguments = result
        return result

    @property
    def t_rparen(self) -> Optional[Token]:
        return self.origin.t_rparen

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_lparen,
            *(self.arguments if self.arguments is not None else []),
            self.t_rparen,
        ]


class FunctionCallExpr(Expr):
    def __init__(
        self,
        parent: Optional[Node],
        origin: greencst.FunctionCallExpr,
        offset: int,
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_receiver: Optional[Expr] = None
        self._n_argument_list: Optional[ArgumentList] = None

    @property
    def n_receiver(self) -> Optional[Expr]:
        if self.origin.n_receiver is None:
            return None
        if self._n_receiver is not None:
            return self._n_receiver
        offset = (
            self.offset
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_receiver.__class__](
            parent=self,
            origin=self.origin.n_receiver,
            offset=offset,
        )
        self._n_receiver = result
        return result

    @property
    def n_argument_list(self) -> Optional[ArgumentList]:
        if self.origin.n_argument_list is None:
            return None
        if self._n_argument_list is not None:
            return self._n_argument_list
        offset = (
            self.offset
            + (
                self.n_receiver.full_width
                if self.n_receiver is not None else
                0
            )
        )
        result = ArgumentList(
            parent=self,
            origin=self.origin.n_argument_list,
            offset=offset,
        )
        self._n_argument_list = result
        return result

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(
            start=start,
            end=start + self.origin.width,
        )

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.n_receiver,
            self.n_argument_list,
        ]


GREEN_TO_RED_NODE_MAP = {
    greencst.Expr: Expr,
    greencst.SyntaxTree: SyntaxTree,
    greencst.Pattern: Pattern,
    greencst.VariablePattern: VariablePattern,
    greencst.LetExpr: LetExpr,
    greencst.IdentifierExpr: IdentifierExpr,
    greencst.IntLiteralExpr: IntLiteralExpr,
    greencst.Argument: Argument,
    greencst.ArgumentList: ArgumentList,
    greencst.FunctionCallExpr: FunctionCallExpr,
}


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
