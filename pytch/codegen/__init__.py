from typing import Dict, List, Optional, Tuple

import attr

from .py3ast import (
    PyArgument,
    PyAssignmentStmt,
    PyExpr,
    PyExprStmt,
    PyFunctionCallExpr,
    PyIdentifierExpr,
    PyLiteralExpr,
    PyStmtList,
    PyUnavailableExpr,
)
from ..binder import Bindation
from ..errors import Error
from ..redcst import (
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IntLiteralExpr,
    LetExpr,
    SyntaxTree,
    VariablePattern,
)


@attr.s(auto_attribs=True, frozen=True)
class Env:
    bindation: Bindation
    scopes: List[Dict[VariablePattern, str]]

    def _update(self, **kwargs) -> "Env":
        return attr.evolve(self, **kwargs)

    def push_scope(self) -> "Env":
        return self._update(scopes=self.scopes + [{}])

    def pop_scope(self) -> "Env":
        assert self.scopes
        return self._update(scopes=self.scopes[:-1])

    def add_binding(
        self,
        variable_pattern: VariablePattern,
        preferred_name: str,
    ) -> Tuple["Env", str]:
        python_name = self._get_name(preferred_name)
        current_scope = dict(self.scopes[-1])
        current_scope[variable_pattern] = python_name
        return (
            self._update(scopes=self.scopes[:-1] + [current_scope]),
            python_name,
        )

    def lookup_binding(
        self,
        variable_pattern: VariablePattern,
    ) -> Optional[str]:
        for scope in reversed(self.scopes):
            if variable_pattern in scope:
                return scope[variable_pattern]
        return None

    def _get_name(self, preferred_name: str) -> str:
        for suggested_name in self._suggest_names(preferred_name):
            if suggested_name not in self.scopes[-1].values():
                return suggested_name
        assert False, "`suggest_names` should loop forever"

    def _suggest_names(self, preferred_name: str):
        yield preferred_name
        i = 2
        while True:
            yield preferred_name + str(i)
            i += 1


@attr.s(auto_attribs=True, frozen=True)
class Codegenation:
    statements: PyStmtList
    errors: List[Error]

    def get_compiled_output(self) -> str:
        compiled_output_lines = []
        for statement in self.statements:
            compiled_output_lines.extend(statement.compile())
        return "".join(
            line + "\n"
            for line in compiled_output_lines
        )


def compile_expr(env: Env, expr: Expr) -> Tuple[
    Env,

    # A Python expression that evaluates to its corresponding Pytch expression.
    PyExpr,

    # Any setup code that needs to be run in order to evaluate the Python
    # expression (since not everything is an expression in Python). For example,
    #
    #     def helper(x):
    #         foo()
    #         return x + 1
    #
    # could later be used in the expression
    #
    #     map(helper, some_list)
    #
    # In this case, `helper` would be the `PyExpr` above, and the definition of
    # `helper` would be the `PyStmtList`.
    PyStmtList,
]:
    if isinstance(expr, LetExpr):
        return compile_let_expr(env, expr)
    elif isinstance(expr, FunctionCallExpr):
        return compile_function_call_expr(env, expr)
    elif isinstance(expr, IdentifierExpr):
        return compile_identifier_expr(env, expr)
    elif isinstance(expr, IntLiteralExpr):
        return compile_int_literal_expr(env, expr)
    else:
        assert False, f"Unhandled expr type {expr.__class__.__name__}"


def compile_let_expr(
    env: Env,
    let_expr: LetExpr,
) -> Tuple[Env, PyExpr, PyStmtList]:
    pattern = let_expr.n_pattern
    value = let_expr.n_value
    py_binding_statements: PyStmtList = []
    if pattern is not None and value is not None:
        assert isinstance(pattern, VariablePattern), \
            f"Unhandled pattern type {pattern.__class__.__name__}"

        t_identifier = pattern.t_identifier
        if t_identifier is not None:
            (env, name) = env.add_binding(
                pattern,
                preferred_name=t_identifier.text,
            )
            (env, value_expr, value_statements) = compile_expr(env, value)
            py_binding_statements = [
                *value_statements,
                PyAssignmentStmt(
                    lhs=PyIdentifierExpr(name=name),
                    rhs=value_expr,
                )
            ]

    if let_expr.n_body is not None:
        (env, body_expr, body_statements) = compile_expr(env, let_expr.n_body)
    else:
        body_expr = PyUnavailableExpr("missing let-expr body")
        body_statements = []

    return (env, body_expr, py_binding_statements + body_statements)


def compile_function_call_expr(
    env: Env,
    function_call_expr: FunctionCallExpr,
) -> Tuple[Env, PyExpr, PyStmtList]:
    n_callee = function_call_expr.n_callee
    if n_callee is not None:
        (env, py_callee_expr, py_receiver_statements) = \
            compile_expr(env, n_callee)
    else:
        return (env, PyUnavailableExpr("missing function callee"), [])

    n_argument_list = function_call_expr.n_argument_list
    if n_argument_list is None or n_argument_list.arguments is None:
        return (env, PyUnavailableExpr("missing function argument list"), [])

    py_arguments = []
    py_argument_list_statements: PyStmtList = []
    for argument in n_argument_list.arguments:
        if argument.n_expr is None:
            return (env, PyUnavailableExpr("missing argument"), [])
        (env, py_argument_expr, py_argument_statements) = \
            compile_expr(env, argument.n_expr)
        py_arguments.append(PyArgument(
            value=py_argument_expr,
        ))
        py_argument_list_statements.extend(py_argument_list_statements)

    py_function_call_expr = PyFunctionCallExpr(
        callee=py_callee_expr,
        arguments=py_arguments,
    )
    return (
        env,
        py_function_call_expr,
        py_receiver_statements + py_argument_list_statements,
    )


def compile_identifier_expr(
    env: Env,
    identifier_expr: IdentifierExpr,
) -> Tuple[Env, PyExpr, PyStmtList]:
    sources = env.bindation.get(identifier_expr)
    if not sources:
        t_identifier = identifier_expr.t_identifier
        if t_identifier is not None:
            return (env, PyIdentifierExpr(name=t_identifier.text), [])
        else:
            return (env, PyUnavailableExpr(
                f"unknown identifier",
            ), [])

    python_identifiers = []
    for source in sources:
        python_identifier = env.lookup_binding(source)
        assert python_identifier is not None
        python_identifiers.append(python_identifier)

    assert all(
        python_identifier == python_identifiers[0]
        for python_identifier in python_identifiers
    )
    return (env, PyIdentifierExpr(name=python_identifiers[0]), [])


def compile_int_literal_expr(
    env: Env,
    int_literal_expr: IntLiteralExpr,
) -> Tuple[Env, PyExpr, PyStmtList]:
    t_int_literal = int_literal_expr.t_int_literal
    if t_int_literal is None:
        return (env, PyUnavailableExpr("missing int literal"), [])
    else:
        value = int(t_int_literal.text)
        return (env, PyLiteralExpr(value=str(value)), [])


def codegen(syntax_tree: SyntaxTree, bindation: Bindation) -> Codegenation:
    env = Env(bindation=bindation, scopes=[{}])
    if syntax_tree.n_expr is None:
        return Codegenation(statements=[], errors=[])
    (env, expr, statements) = compile_expr(env, syntax_tree.n_expr)
    return Codegenation(
        statements=statements + [PyExprStmt(expr=expr)],
        errors=[],
    )


__all__ = ["codegen"]
