"""NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
"""
from typing import List, Optional, Sequence, Union

from .lexer import Token


class Node:
    def __init__(self, children: Sequence[Union["Node", Optional["Token"]]]) -> None:
        self._children = children

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        return self._children

    @property
    def leading_text(self) -> str:
        first_child = self.first_present_child
        if first_child is None:
            return ""
        else:
            return first_child.leading_text

    @property
    def text(self) -> str:
        if len(self._children) == 0:
            return ""
        elif len(self._children) == 1:
            child = self._children[0]
            if child is None:
                return ""
            else:
                return child.text
        else:
            text = ""
            [first, *middle, last] = self._children
            if first is not None:
                text += first.text + first.trailing_text
            for child in middle:
                if child is not None:
                    text += child.full_text
            if last is not None:
                text += last.leading_text + last.text
            return text

    @property
    def trailing_text(self) -> str:
        last_child = self.last_present_child
        if last_child is None:
            return ""
        else:
            return last_child.trailing_text

    @property
    def full_text(self) -> str:
        return "".join(child.full_text for child in self._children if child is not None)

    @property
    def first_present_child(self) -> Optional[Union["Node", "Token"]]:
        for child in self.children:
            if child is None:
                continue
            if isinstance(child, Token):
                if not child.is_dummy:
                    return child
            else:
                child_first_present_child = child.first_present_child
                if child_first_present_child is not None:
                    return child_first_present_child
        return None

    @property
    def last_present_child(self) -> Optional[Union["Node", "Token"]]:
        for child in reversed(self.children):
            if child is None:
                continue
            if isinstance(child, Token):
                if not child.is_dummy:
                    return child
            else:
                child_last_present_child = child.last_present_child
                if child_last_present_child is not None:
                    return child_last_present_child
        return None

    @property
    def leading_width(self) -> int:
        child = self.first_present_child
        if child is None:
            return 0
        return child.leading_width

    @property
    def trailing_width(self) -> int:
        child = self.last_present_child
        if child is None:
            return 0
        return child.trailing_width

    @property
    def width(self) -> int:
        if not self.children:
            return 0
        return self.full_width - self.leading_width - self.trailing_width

    @property
    def full_width(self) -> int:
        return sum(
            child.full_width if child is not None else 0 for child in self.children
        )


class Expr(Node):
    pass


class SyntaxTree(Node):
    def __init__(self, n_expr: Optional[Expr], t_eof: Optional[Token]) -> None:
        super().__init__([n_expr, t_eof])
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
    def __init__(self, t_identifier: Optional[Token]) -> None:
        super().__init__([t_identifier])
        self._t_identifier = t_identifier

    @property
    def t_identifier(self) -> Optional[Token]:
        return self._t_identifier


class Parameter(Node):
    def __init__(self, n_pattern: Optional[Pattern], t_comma: Optional[Token]) -> None:
        super().__init__([n_pattern, t_comma])
        self._n_pattern = n_pattern
        self._t_comma = t_comma

    @property
    def n_pattern(self) -> Optional[Pattern]:
        return self._n_pattern

    @property
    def t_comma(self) -> Optional[Token]:
        return self._t_comma


class ParameterList(Node):
    def __init__(
        self,
        t_lparen: Optional[Token],
        parameters: Optional[List[Parameter]],
        t_rparen: Optional[Token],
    ) -> None:
        super().__init__(
            [t_lparen, *(parameters if parameters is not None else []), t_rparen]
        )
        self._t_lparen = t_lparen
        self._parameters = parameters
        self._t_rparen = t_rparen

    @property
    def t_lparen(self) -> Optional[Token]:
        return self._t_lparen

    @property
    def parameters(self) -> Optional[List[Parameter]]:
        return self._parameters

    @property
    def t_rparen(self) -> Optional[Token]:
        return self._t_rparen


class LetExpr(Expr):
    def __init__(
        self,
        t_let: Optional[Token],
        n_pattern: Optional[Pattern],
        n_parameter_list: Optional[ParameterList],
        t_equals: Optional[Token],
        n_value: Optional[Expr],
        t_in: Optional[Token],
        n_body: Optional[Expr],
    ) -> None:
        super().__init__(
            [t_let, n_pattern, n_parameter_list, t_equals, n_value, t_in, n_body]
        )
        self._t_let = t_let
        self._n_pattern = n_pattern
        self._n_parameter_list = n_parameter_list
        self._t_equals = t_equals
        self._n_value = n_value
        self._t_in = t_in
        self._n_body = n_body

    @property
    def t_let(self) -> Optional[Token]:
        return self._t_let

    @property
    def n_pattern(self) -> Optional[Pattern]:
        return self._n_pattern

    @property
    def n_parameter_list(self) -> Optional[ParameterList]:
        return self._n_parameter_list

    @property
    def t_equals(self) -> Optional[Token]:
        return self._t_equals

    @property
    def n_value(self) -> Optional[Expr]:
        return self._n_value

    @property
    def t_in(self) -> Optional[Token]:
        return self._t_in

    @property
    def n_body(self) -> Optional[Expr]:
        return self._n_body


class IfExpr(Expr):
    def __init__(
        self,
        t_if: Optional[Token],
        n_if_expr: Optional[Expr],
        t_then: Optional[Token],
        n_then_expr: Optional[Expr],
        t_else: Optional[Token],
        n_else_expr: Optional[Expr],
        t_endif: Optional[Token],
    ) -> None:
        super().__init__(
            [t_if, n_if_expr, t_then, n_then_expr, t_else, n_else_expr, t_endif]
        )
        self._t_if = t_if
        self._n_if_expr = n_if_expr
        self._t_then = t_then
        self._n_then_expr = n_then_expr
        self._t_else = t_else
        self._n_else_expr = n_else_expr
        self._t_endif = t_endif

    @property
    def t_if(self) -> Optional[Token]:
        return self._t_if

    @property
    def n_if_expr(self) -> Optional[Expr]:
        return self._n_if_expr

    @property
    def t_then(self) -> Optional[Token]:
        return self._t_then

    @property
    def n_then_expr(self) -> Optional[Expr]:
        return self._n_then_expr

    @property
    def t_else(self) -> Optional[Token]:
        return self._t_else

    @property
    def n_else_expr(self) -> Optional[Expr]:
        return self._n_else_expr

    @property
    def t_endif(self) -> Optional[Token]:
        return self._t_endif


class IdentifierExpr(Expr):
    def __init__(self, t_identifier: Optional[Token]) -> None:
        super().__init__([t_identifier])
        self._t_identifier = t_identifier

    @property
    def t_identifier(self) -> Optional[Token]:
        return self._t_identifier


class IntLiteralExpr(Expr):
    def __init__(self, t_int_literal: Optional[Token]) -> None:
        super().__init__([t_int_literal])
        self._t_int_literal = t_int_literal

    @property
    def t_int_literal(self) -> Optional[Token]:
        return self._t_int_literal


class BinaryExpr(Expr):
    def __init__(
        self, n_lhs: Optional[Expr], t_operator: Optional[Token], n_rhs: Optional[Expr]
    ) -> None:
        super().__init__([n_lhs, t_operator, n_rhs])
        self._n_lhs = n_lhs
        self._t_operator = t_operator
        self._n_rhs = n_rhs

    @property
    def n_lhs(self) -> Optional[Expr]:
        return self._n_lhs

    @property
    def t_operator(self) -> Optional[Token]:
        return self._t_operator

    @property
    def n_rhs(self) -> Optional[Expr]:
        return self._n_rhs


class Argument(Node):
    def __init__(self, n_expr: Optional[Expr], t_comma: Optional[Token]) -> None:
        super().__init__([n_expr, t_comma])
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
        super().__init__(
            [t_lparen, *(arguments if arguments is not None else []), t_rparen]
        )
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
        self, n_callee: Optional[Expr], n_argument_list: Optional[ArgumentList]
    ) -> None:
        super().__init__([n_callee, n_argument_list])
        self._n_callee = n_callee
        self._n_argument_list = n_argument_list

    @property
    def n_callee(self) -> Optional[Expr]:
        return self._n_callee

    @property
    def n_argument_list(self) -> Optional[ArgumentList]:
        return self._n_argument_list
