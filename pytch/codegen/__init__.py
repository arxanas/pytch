import keyword
from typing import Dict, List, Optional, Set, Tuple

import attr

from .py3ast import (
    PyArgument,
    PyAssignmentStmt,
    PyBinaryExpr,
    PyExpr,
    PyExprStmt,
    PyFunctionCallExpr,
    PyFunctionStmt,
    PyIdentifierExpr,
    PyIfStmt,
    PyLiteralExpr,
    PyParameter,
    PyStmtList,
    PyUnavailableExpr,
)
from ..binder import Bindation
from ..errors import Error
from ..lexer import TokenKind
from ..redcst import (
    BinaryExpr,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IfExpr,
    IntLiteralExpr,
    LetExpr,
    Pattern,
    SyntaxTree,
    VariablePattern,
)
from ..typesystem import Typeation


@attr.s(auto_attribs=True, frozen=True)
class Scope:
    pytch_bindings: Dict[VariablePattern, str]
    python_bindings: Set[str]

    def update(self, **kwargs) -> "Scope":
        return attr.evolve(self, **kwargs)

    @staticmethod
    def empty() -> "Scope":
        return Scope(pytch_bindings={}, python_bindings=set())


@attr.s(auto_attribs=True, frozen=True)
class Env:
    """Environment for codegen with the Python 3 backend.

    We keep track of the emitted variable bindings here. We may need to emit
    extra variables that don't exist in the source code as temporaries, and
    we need to account for the differences in scoping between Pytch and
    Python (for example, function bindings aren't recursive by default in
    Pytch, but are in Python).
    """

    bindation: Bindation
    scopes: List[Scope]

    def _update(self, **kwargs) -> "Env":
        return attr.evolve(self, **kwargs)

    def push_scope(self) -> "Env":
        return self._update(scopes=self.scopes + [Scope.empty()])

    def pop_scope(self) -> "Env":
        assert self.scopes
        return self._update(scopes=self.scopes[:-1])

    def add_binding(
        self, variable_pattern: VariablePattern, preferred_name: str
    ) -> Tuple["Env", str]:
        """Add a binding for a variable that exists in the source code.

        `preferred_name` is used as the preferred Python variable name, but a
        non-colliding name will be generated if there is already such a name
        in the current Python scope.
        """
        python_name = self._get_name(preferred_name)
        current_pytch_bindings = dict(self.scopes[-1].pytch_bindings)
        current_pytch_bindings[variable_pattern] = python_name
        current_scope = self.scopes[-1].update(pytch_bindings=current_pytch_bindings)
        return (self._update(scopes=self.scopes[:-1] + [current_scope]), python_name)

    def make_temporary(self, preferred_name: str) -> Tuple["Env", str]:
        python_name = self._get_name(preferred_name)
        current_python_bindings = set(self.scopes[-1].python_bindings)
        assert python_name not in current_python_bindings
        current_python_bindings.add(python_name)
        current_scope = self.scopes[-1].update(python_bindings=current_python_bindings)
        return (self._update(scopes=self.scopes[:-1] + [current_scope]), python_name)

    def lookup_binding(self, variable_pattern: VariablePattern) -> Optional[str]:
        for scope in reversed(self.scopes):
            if variable_pattern in scope.pytch_bindings:
                return scope.pytch_bindings[variable_pattern]
        return None

    def _get_name(self, preferred_name: str) -> str:
        for suggested_name in self._suggest_names(preferred_name):
            if (
                not keyword.iskeyword(suggested_name)
                and suggested_name not in self.scopes[-1].python_bindings
                and suggested_name not in self.scopes[-1].pytch_bindings.values()
            ):
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
        return "".join(line + "\n" for line in compiled_output_lines)


def compile_expr(
    env: Env, expr: Expr
) -> Tuple[
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
    # In this case, the expression `helper` would be the `PyExpr` above, and
    # the definition of the helper function would be the `PyStmtList`.
    PyStmtList,
]:
    if isinstance(expr, LetExpr):
        return compile_let_expr(env, expr)
    elif isinstance(expr, IfExpr):
        return compile_if_expr(env, expr)
    elif isinstance(expr, FunctionCallExpr):
        return compile_function_call_expr(env, expr)
    elif isinstance(expr, BinaryExpr):
        return compile_binary_expr(env, expr)
    elif isinstance(expr, IdentifierExpr):
        return compile_identifier_expr(env, expr)
    elif isinstance(expr, IntLiteralExpr):
        return compile_int_literal_expr(env, expr)
    else:
        assert False, f"Unhandled expr type {expr.__class__.__name__}"


PY_EXPR_NO_TARGET = PyUnavailableExpr("should have been directly stored already")


def compile_expr_target(
    env: Env, expr: Expr, target: PyIdentifierExpr, preferred_name: str
) -> Tuple[Env, PyStmtList]:
    """Like `compile_expr`, but store the result in the given target.

    This cleans up the generated code by avoiding temporary stores that make
    it hard to read. For example, this code:

    ```
    let foo =
      if True
      then 1
      else 2
    print(foo)
    ```

    May compile into this, if we don't elide intermediate stores:

    ```
    if True:
        _tmp_if = 1
    else:
        _tmp_if = 2
    foo = _tmp_if
    print(foo)
    ```

    But we can write this more succinctly by noting that the result of the
    `if`-expression should be directly assigned to `foo`:

    ```
    if True:
        foo = 1
    else:
        foo = 2
    print(foo)
    ```
    """
    if isinstance(expr, LetExpr):
        (env, _py_expr, statements) = compile_let_expr(
            env, let_expr=expr, target=target
        )
        return (env, statements)
    elif isinstance(expr, IfExpr):
        (env, _py_expr, statements) = compile_if_expr(env, if_expr=expr, target=target)
        return (env, statements)
    elif isinstance(expr, IntLiteralExpr):
        (env, _py_expr, statements) = compile_int_literal_expr(env, expr, target=target)
        return (env, statements)
    else:
        (env, py_expr, statements) = compile_expr(env, expr)
        statements = statements + [PyAssignmentStmt(lhs=target, rhs=py_expr)]
        return (env, statements)


def compile_let_expr(
    env: Env, let_expr: LetExpr, target: PyIdentifierExpr = None
) -> Tuple[Env, PyExpr, PyStmtList]:
    n_pattern = let_expr.n_pattern
    n_value = let_expr.n_value
    py_binding_statements: PyStmtList
    if n_pattern is not None and n_value is not None:
        n_parameter_list = None
        if let_expr.n_parameter_list is not None:
            n_parameter_list = let_expr.n_parameter_list.parameters

        if n_parameter_list is None:
            if target is not None:
                (env, py_binding_statements) = compile_expr_target(
                    env, n_value, target=target, preferred_name="_tmp_let"
                )
            else:
                (env, py_binding_statements) = compile_assign_to_pattern(
                    env, expr=n_value, pattern=n_pattern
                )
        else:
            assert isinstance(
                n_pattern, VariablePattern
            ), f"Bad pattern type {n_pattern.__class__.__name__} for function"

            t_identifier = n_pattern.t_identifier
            if t_identifier is None:
                return (env, PyUnavailableExpr("missing let-binding function name"), [])

            function_name = t_identifier.text

            env = env.push_scope()
            py_parameters = []
            for n_parameter in n_parameter_list:
                n_parameter_pattern = n_parameter.n_pattern
                if n_parameter_pattern is None:
                    continue

                assert isinstance(n_parameter_pattern, VariablePattern), (
                    f"Unhandled pattern type "
                    + f"{n_parameter_pattern.__class__.__name__}"
                )
                t_pattern_identifier = n_parameter_pattern.t_identifier
                if t_pattern_identifier is None:
                    continue

                parameter_name = t_pattern_identifier.text
                (env, parameter_name) = env.add_binding(
                    variable_pattern=n_parameter_pattern, preferred_name=parameter_name
                )
                py_parameters.append(PyParameter(name=parameter_name))

            (
                env,
                py_function_body_return_expr,
                py_function_body_statements,
            ) = compile_expr(env, n_value)
            env = env.pop_scope()
            (env, actual_function_name) = env.add_binding(
                n_pattern, preferred_name=function_name
            )
            py_binding_statements = [
                PyFunctionStmt(
                    name=actual_function_name,
                    parameters=py_parameters,
                    body_statements=py_function_body_statements,
                    return_expr=py_function_body_return_expr,
                )
            ]

    if let_expr.n_body is not None:
        (env, body_expr, body_statements) = compile_expr(env, let_expr.n_body)
    else:
        body_expr = PyUnavailableExpr("missing let-expr body")
        body_statements = []

    return (env, body_expr, py_binding_statements + body_statements)


def compile_if_expr(
    env: Env, if_expr: IfExpr, target: PyIdentifierExpr = None
) -> Tuple[Env, PyExpr, PyStmtList]:
    n_if_expr = if_expr.n_if_expr
    n_then_expr = if_expr.n_then_expr
    n_else_expr = if_expr.n_else_expr

    if n_if_expr is None:
        return (env, PyUnavailableExpr("missing if condition"), [])
    (env, py_if_expr, py_if_statements) = compile_expr(env, n_if_expr)

    # Check `n_then_expr` here to avoid making a temporary and not using it.
    if target is None and n_then_expr is not None:
        (env, target_name) = env.make_temporary("_tmp_if")
        target = PyIdentifierExpr(name=target_name)

    # Compile the `then`-clause.
    if n_then_expr is None:
        return (env, PyUnavailableExpr("missing then expression"), [])
    if n_else_expr is not None:
        assert target is not None
        (env, py_then_statements) = compile_expr_target(
            env, n_then_expr, target=target, preferred_name="_tmp_if"
        )
    else:
        # Avoid storing the result of the `then`-clause into anything if there is no corresponding `else`-clause. This makes code like this:
        #
        #     if True
        #     then print(1)
        #
        # produce code like this:
        #
        #     if True:
        #         print(1)
        #
        # instead of code like this:
        #
        #     if True:
        #         _tmp_if = print(1)
        #     else:
        #         _tmp_if = None
        #     _tmp_if
        (env, py_body_expr, py_then_statements) = compile_expr(env, n_then_expr)
        py_then_statements = py_then_statements + [PyExprStmt(expr=py_body_expr)]
        target = None

    py_else_statements: Optional[PyStmtList] = None
    if n_else_expr is not None:
        assert target is not None
        (env, py_else_statements) = compile_expr_target(
            env, n_else_expr, target=target, preferred_name="_tmp_if"
        )

    statements = py_if_statements + [
        PyIfStmt(
            if_expr=py_if_expr,
            then_statements=py_then_statements,
            else_statements=py_else_statements,
        )
    ]
    if isinstance(target, PyIdentifierExpr):
        return (env, target, statements)
    else:
        return (env, PY_EXPR_NO_TARGET, statements)


def compile_assign_to_pattern(
    env: Env, expr: Expr, pattern: Pattern
) -> Tuple[Env, PyStmtList]:
    if isinstance(pattern, VariablePattern):
        t_identifier = pattern.t_identifier
        if t_identifier is None:
            return (
                env,
                [
                    PyExprStmt(
                        expr=PyUnavailableExpr(
                            "missing identifier for variable pattern"
                        )
                    )
                ],
            )

        preferred_name = t_identifier.text
        (env, name) = env.add_binding(pattern, preferred_name=preferred_name)
        target = PyIdentifierExpr(name=name)
        return compile_expr_target(
            env, expr=expr, target=target, preferred_name=preferred_name
        )
    else:
        assert False, f"unimplemented pattern: {pattern.__class__.__name__}"


def compile_function_call_expr(
    env: Env, function_call_expr: FunctionCallExpr
) -> Tuple[Env, PyExpr, PyStmtList]:
    n_callee = function_call_expr.n_callee
    if n_callee is not None:
        (env, py_callee_expr, py_receiver_statements) = compile_expr(env, n_callee)
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
        (env, py_argument_expr, py_argument_statements) = compile_expr(
            env, argument.n_expr
        )
        py_arguments.append(PyArgument(value=py_argument_expr))
        py_argument_list_statements.extend(py_argument_statements)

    py_function_call_expr = PyFunctionCallExpr(
        callee=py_callee_expr, arguments=py_arguments
    )
    return (
        env,
        py_function_call_expr,
        py_receiver_statements + py_argument_list_statements,
    )


def compile_binary_expr(
    env: Env, binary_expr: BinaryExpr
) -> Tuple[Env, PyExpr, PyStmtList]:
    n_lhs = binary_expr.n_lhs
    if n_lhs is None:
        return (env, PyUnavailableExpr("missing lhs"), [])

    t_operator = binary_expr.t_operator
    if t_operator is None:
        return (env, PyUnavailableExpr("missing operator"), [])

    n_rhs = binary_expr.n_rhs
    if n_rhs is None:
        return (env, PyUnavailableExpr("missing rhs"), [])

    (env, py_lhs_expr, lhs_statements) = compile_expr(env, expr=n_lhs)
    (env, py_rhs_expr, rhs_statements) = compile_expr(env, expr=n_rhs)

    if t_operator.kind == TokenKind.DUMMY_SEMICOLON:
        statements = lhs_statements + [PyExprStmt(expr=py_lhs_expr)] + rhs_statements
        return (env, py_rhs_expr, statements)
    else:
        assert not t_operator.is_dummy
        return (
            env,
            PyBinaryExpr(lhs=py_lhs_expr, operator=t_operator.text, rhs=py_rhs_expr),
            lhs_statements + rhs_statements,
        )


def compile_identifier_expr(
    env: Env, identifier_expr: IdentifierExpr
) -> Tuple[Env, PyExpr, PyStmtList]:
    sources = env.bindation.get(identifier_expr)
    if not sources:
        t_identifier = identifier_expr.t_identifier
        if t_identifier is not None:
            return (env, PyIdentifierExpr(name=t_identifier.text), [])
        else:
            return (env, PyUnavailableExpr(f"unknown identifier"), [])

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
    env: Env, int_literal_expr: IntLiteralExpr, target: PyIdentifierExpr = None
) -> Tuple[Env, PyExpr, PyStmtList]:
    t_int_literal = int_literal_expr.t_int_literal
    if t_int_literal is None:
        return (env, PyUnavailableExpr("missing int literal"), [])

    value = t_int_literal.text
    py_expr = PyLiteralExpr(value=str(value))
    if target is None:
        return (env, py_expr, [])
    else:
        statements: PyStmtList = [PyAssignmentStmt(lhs=target, rhs=py_expr)]
        return (env, PY_EXPR_NO_TARGET, statements)


def codegen(
    syntax_tree: SyntaxTree, bindation: Bindation, typeation: Typeation
) -> Codegenation:
    env = Env(bindation=bindation, scopes=[Scope.empty()])
    if syntax_tree.n_expr is None:
        return Codegenation(statements=[], errors=[])
    (env, expr, statements) = compile_expr(env, syntax_tree.n_expr)
    return Codegenation(statements=statements + [PyExprStmt(expr=expr)], errors=[])
