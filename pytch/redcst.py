"""NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
"""
from typing import List, Optional, Sequence, Union

import pytch.greencst as greencst
from .lexer import Token
from .utils import OffsetRange


class Node:
    def __init__(self, parent: Optional["Node"]) -> None:
        self._parent = parent

    @property
    def parent(self) -> Optional["Node"]:
        return self._parent

    @property
    def text(self) -> str:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `text`"
        )

    @property
    def full_text(self) -> str:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `full_text`"
        )

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `children`"
        )

    @property
    def full_width(self) -> int:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `full_width`"
        )

    @property
    def offset_range(self) -> OffsetRange:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `offset_range`"
        )


class Expr(Node):
    pass


class SyntaxTree(Node):
    def __init__(
        self, parent: Optional[Node], origin: greencst.SyntaxTree, offset: int
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
        offset = self.offset
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_expr.__class__](
            parent=self, origin=self.origin.n_expr, offset=offset
        )
        self._n_expr = result
        return result

    @property
    def t_eof(self) -> Optional[Token]:
        return self.origin.t_eof

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.n_expr, self.t_eof]


class Pattern(Node):
    pass


class VariablePattern(Pattern):
    def __init__(
        self, parent: Optional[Node], origin: greencst.VariablePattern, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_identifier(self) -> Optional[Token]:
        return self.origin.t_identifier

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.t_identifier]


class Parameter(Node):
    def __init__(
        self, parent: Optional[Node], origin: greencst.Parameter, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_pattern: Optional[Pattern] = None

    @property
    def n_pattern(self) -> Optional[Pattern]:
        if self.origin.n_pattern is None:
            return None
        if self._n_pattern is not None:
            return self._n_pattern
        offset = self.offset
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_pattern.__class__](
            parent=self, origin=self.origin.n_pattern, offset=offset
        )
        self._n_pattern = result
        return result

    @property
    def t_comma(self) -> Optional[Token]:
        return self.origin.t_comma

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.n_pattern, self.t_comma]


class ParameterList(Node):
    def __init__(
        self, parent: Optional[Node], origin: greencst.ParameterList, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._parameters: Optional[List[Parameter]] = None

    @property
    def t_lparen(self) -> Optional[Token]:
        return self.origin.t_lparen

    @property
    def parameters(self) -> Optional[List[Parameter]]:
        if self.origin.parameters is None:
            return None
        if self._parameters is not None:
            return self._parameters
        offset = self.offset + (
            self.t_lparen.full_width if self.t_lparen is not None else 0
        )
        result = []
        for child in self.origin.parameters:
            result.append(Parameter(parent=self, origin=child, offset=offset))
            offset += child.full_width
        self._parameters = result
        return result

    @property
    def t_rparen(self) -> Optional[Token]:
        return self.origin.t_rparen

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_lparen,
            *(self.parameters if self.parameters is not None else []),
            self.t_rparen,
        ]


class LetExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.LetExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_pattern: Optional[Pattern] = None
        self._n_parameter_list: Optional[ParameterList] = None
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
        offset = self.offset + (self.t_let.full_width if self.t_let is not None else 0)
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_pattern.__class__](
            parent=self, origin=self.origin.n_pattern, offset=offset
        )
        self._n_pattern = result
        return result

    @property
    def n_parameter_list(self) -> Optional[ParameterList]:
        if self.origin.n_parameter_list is None:
            return None
        if self._n_parameter_list is not None:
            return self._n_parameter_list
        offset = (
            self.offset
            + (self.t_let.full_width if self.t_let is not None else 0)
            + (self.n_pattern.full_width if self.n_pattern is not None else 0)
        )
        result = ParameterList(
            parent=self, origin=self.origin.n_parameter_list, offset=offset
        )
        self._n_parameter_list = result
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
            + (self.t_let.full_width if self.t_let is not None else 0)
            + (self.n_pattern.full_width if self.n_pattern is not None else 0)
            + (
                self.n_parameter_list.full_width
                if self.n_parameter_list is not None
                else 0
            )
            + (self.t_equals.full_width if self.t_equals is not None else 0)
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_value.__class__](
            parent=self, origin=self.origin.n_value, offset=offset
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
            + (self.t_let.full_width if self.t_let is not None else 0)
            + (self.n_pattern.full_width if self.n_pattern is not None else 0)
            + (
                self.n_parameter_list.full_width
                if self.n_parameter_list is not None
                else 0
            )
            + (self.t_equals.full_width if self.t_equals is not None else 0)
            + (self.n_value.full_width if self.n_value is not None else 0)
            + (self.t_in.full_width if self.t_in is not None else 0)
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_body.__class__](
            parent=self, origin=self.origin.n_body, offset=offset
        )
        self._n_body = result
        return result

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_let,
            self.n_pattern,
            self.n_parameter_list,
            self.t_equals,
            self.n_value,
            self.t_in,
            self.n_body,
        ]


class IfExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.IfExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_if_expr: Optional[Expr] = None
        self._n_then_expr: Optional[Expr] = None
        self._n_else_expr: Optional[Expr] = None

    @property
    def t_if(self) -> Optional[Token]:
        return self.origin.t_if

    @property
    def n_if_expr(self) -> Optional[Expr]:
        if self.origin.n_if_expr is None:
            return None
        if self._n_if_expr is not None:
            return self._n_if_expr
        offset = self.offset + (self.t_if.full_width if self.t_if is not None else 0)
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_if_expr.__class__](
            parent=self, origin=self.origin.n_if_expr, offset=offset
        )
        self._n_if_expr = result
        return result

    @property
    def t_then(self) -> Optional[Token]:
        return self.origin.t_then

    @property
    def n_then_expr(self) -> Optional[Expr]:
        if self.origin.n_then_expr is None:
            return None
        if self._n_then_expr is not None:
            return self._n_then_expr
        offset = (
            self.offset
            + (self.t_if.full_width if self.t_if is not None else 0)
            + (self.n_if_expr.full_width if self.n_if_expr is not None else 0)
            + (self.t_then.full_width if self.t_then is not None else 0)
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_then_expr.__class__](
            parent=self, origin=self.origin.n_then_expr, offset=offset
        )
        self._n_then_expr = result
        return result

    @property
    def t_else(self) -> Optional[Token]:
        return self.origin.t_else

    @property
    def n_else_expr(self) -> Optional[Expr]:
        if self.origin.n_else_expr is None:
            return None
        if self._n_else_expr is not None:
            return self._n_else_expr
        offset = (
            self.offset
            + (self.t_if.full_width if self.t_if is not None else 0)
            + (self.n_if_expr.full_width if self.n_if_expr is not None else 0)
            + (self.t_then.full_width if self.t_then is not None else 0)
            + (self.n_then_expr.full_width if self.n_then_expr is not None else 0)
            + (self.t_else.full_width if self.t_else is not None else 0)
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_else_expr.__class__](
            parent=self, origin=self.origin.n_else_expr, offset=offset
        )
        self._n_else_expr = result
        return result

    @property
    def t_endif(self) -> Optional[Token]:
        return self.origin.t_endif

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_if,
            self.n_if_expr,
            self.t_then,
            self.n_then_expr,
            self.t_else,
            self.n_else_expr,
            self.t_endif,
        ]


class IdentifierExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.IdentifierExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_identifier(self) -> Optional[Token]:
        return self.origin.t_identifier

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.t_identifier]


class IntLiteralExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.IntLiteralExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset

    @property
    def t_int_literal(self) -> Optional[Token]:
        return self.origin.t_int_literal

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.t_int_literal]


class BinaryExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.BinaryExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_lhs: Optional[Expr] = None
        self._n_rhs: Optional[Expr] = None

    @property
    def n_lhs(self) -> Optional[Expr]:
        if self.origin.n_lhs is None:
            return None
        if self._n_lhs is not None:
            return self._n_lhs
        offset = self.offset
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_lhs.__class__](
            parent=self, origin=self.origin.n_lhs, offset=offset
        )
        self._n_lhs = result
        return result

    @property
    def t_operator(self) -> Optional[Token]:
        return self.origin.t_operator

    @property
    def n_rhs(self) -> Optional[Expr]:
        if self.origin.n_rhs is None:
            return None
        if self._n_rhs is not None:
            return self._n_rhs
        offset = (
            self.offset
            + (self.n_lhs.full_width if self.n_lhs is not None else 0)
            + (self.t_operator.full_width if self.t_operator is not None else 0)
        )
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_rhs.__class__](
            parent=self, origin=self.origin.n_rhs, offset=offset
        )
        self._n_rhs = result
        return result

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.n_lhs, self.t_operator, self.n_rhs]


class Argument(Node):
    def __init__(
        self, parent: Optional[Node], origin: greencst.Argument, offset: int
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
        offset = self.offset
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_expr.__class__](
            parent=self, origin=self.origin.n_expr, offset=offset
        )
        self._n_expr = result
        return result

    @property
    def t_comma(self) -> Optional[Token]:
        return self.origin.t_comma

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.n_expr, self.t_comma]


class ArgumentList(Node):
    def __init__(
        self, parent: Optional[Node], origin: greencst.ArgumentList, offset: int
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
        offset = self.offset + (
            self.t_lparen.full_width if self.t_lparen is not None else 0
        )
        result = []
        for child in self.origin.arguments:
            result.append(Argument(parent=self, origin=child, offset=offset))
            offset += child.full_width
        self._arguments = result
        return result

    @property
    def t_rparen(self) -> Optional[Token]:
        return self.origin.t_rparen

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [
            self.t_lparen,
            *(self.arguments if self.arguments is not None else []),
            self.t_rparen,
        ]


class FunctionCallExpr(Expr):
    def __init__(
        self, parent: Optional[Node], origin: greencst.FunctionCallExpr, offset: int
    ) -> None:
        super().__init__(parent)
        self.origin = origin
        self.offset = offset
        self._n_callee: Optional[Expr] = None
        self._n_argument_list: Optional[ArgumentList] = None

    @property
    def n_callee(self) -> Optional[Expr]:
        if self.origin.n_callee is None:
            return None
        if self._n_callee is not None:
            return self._n_callee
        offset = self.offset
        result = GREEN_TO_RED_NODE_MAP[self.origin.n_callee.__class__](
            parent=self, origin=self.origin.n_callee, offset=offset
        )
        self._n_callee = result
        return result

    @property
    def n_argument_list(self) -> Optional[ArgumentList]:
        if self.origin.n_argument_list is None:
            return None
        if self._n_argument_list is not None:
            return self._n_argument_list
        offset = self.offset + (
            self.n_callee.full_width if self.n_callee is not None else 0
        )
        result = ArgumentList(
            parent=self, origin=self.origin.n_argument_list, offset=offset
        )
        self._n_argument_list = result
        return result

    @property
    def text(self) -> str:
        return self.origin.text

    @property
    def full_text(self) -> str:
        return self.origin.full_text

    @property
    def full_width(self) -> int:
        return self.origin.full_width

    @property
    def offset_range(self) -> OffsetRange:
        start = self.offset + self.origin.leading_width
        return OffsetRange(start=start, end=start + self.origin.width)

    @property
    def children(self) -> List[Optional[Union[Token, Node]]]:
        return [self.n_callee, self.n_argument_list]


GREEN_TO_RED_NODE_MAP = {
    greencst.Expr: Expr,
    greencst.SyntaxTree: SyntaxTree,
    greencst.Pattern: Pattern,
    greencst.VariablePattern: VariablePattern,
    greencst.Parameter: Parameter,
    greencst.ParameterList: ParameterList,
    greencst.LetExpr: LetExpr,
    greencst.IfExpr: IfExpr,
    greencst.IdentifierExpr: IdentifierExpr,
    greencst.IntLiteralExpr: IntLiteralExpr,
    greencst.BinaryExpr: BinaryExpr,
    greencst.Argument: Argument,
    greencst.ArgumentList: ArgumentList,
    greencst.FunctionCallExpr: FunctionCallExpr,
}
