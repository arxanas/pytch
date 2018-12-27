from typing import List, Optional

import attr

from pytch import ISSUE_TRACKER_URL


CompiledOutput = List[str]


class PyExpr:
    def compile(self) -> str:
        raise NotImplementedError(
            f"`PyExpr.compile` not implemented by {self.__class__.__name__}"
        )


@attr.s(auto_attribs=True, frozen=True)
class PyUnavailableExpr(PyExpr):
    """Indicates a value deriving from malformed source code."""

    reason: str

    def compile(self) -> str:
        return (
            f'"<Bug in Pytch compilation -- '
            + f"please report it at {ISSUE_TRACKER_URL} ! "
            + f'Message: unavailable expr: {self.reason}>"'
        )


@attr.s(auto_attribs=True, frozen=True)
class PyIdentifierExpr(PyExpr):
    name: str

    def compile(self) -> str:
        return self.name


@attr.s(auto_attribs=True, frozen=True)
class PyLiteralExpr(PyExpr):
    value: str

    def compile(self) -> str:
        return self.value


@attr.s(auto_attribs=True, frozen=True)
class PyArgument:
    value: PyExpr

    def compile(self) -> str:
        return self.value.compile()


@attr.s(auto_attribs=True, frozen=True)
class PyFunctionCallExpr(PyExpr):
    callee: PyExpr
    arguments: List[PyArgument]

    def compile(self) -> str:
        compiled_arguments = []
        for argument in self.arguments:
            compiled_arguments.append(argument.compile())
        compiled_arguments_str = ", ".join(compiled_arguments)
        return f"{self.callee.compile()}({compiled_arguments_str})"


@attr.s(auto_attribs=True, frozen=True)
class PyBinaryExpr(PyExpr):
    lhs: PyExpr
    operator: str
    rhs: PyExpr

    def compile(self) -> str:
        return f"{self.lhs.compile()} {self.operator} {self.rhs.compile()}"


class PyStmt:
    def compile(self) -> CompiledOutput:
        raise NotImplementedError(
            f"`PyStmt.compile` not implemented by {self.__class__.__name__}"
        )


PyStmtList = List[PyStmt]


@attr.s(auto_attribs=True, frozen=True)
class PyIndentedStmt:
    statement: PyStmt

    def compile(self) -> CompiledOutput:
        return ["    " + line for line in self.statement.compile()]


@attr.s(auto_attribs=True, frozen=True)
class PyAssignmentStmt(PyStmt):
    lhs: PyIdentifierExpr
    rhs: PyExpr

    def compile(self) -> CompiledOutput:
        return [f"{self.lhs.compile()} = {self.rhs.compile()}"]


@attr.s(auto_attribs=True, frozen=True)
class PyReturnStmt(PyStmt):
    expr: PyExpr

    def compile(self) -> CompiledOutput:
        return [f"return {self.expr.compile()}"]


@attr.s(auto_attribs=True, frozen=True)
class PyIfStmt(PyStmt):
    if_expr: PyExpr  # noqa: E701
    then_statements: PyStmtList
    else_statements: Optional[PyStmtList]  # noqa: E701

    def compile(self) -> CompiledOutput:
        if_statements = [f"if {self.if_expr.compile()}:"]
        for statement in self.then_statements:
            if_statements.extend(PyIndentedStmt(statement=statement).compile())

        else_statements = []
        if self.else_statements is not None:
            assert self.else_statements
            else_statements.append("else:")
            for statement in self.else_statements:
                else_statements.extend(PyIndentedStmt(statement=statement).compile())
        return if_statements + else_statements


@attr.s(auto_attribs=True, frozen=True)
class PyParameter:
    name: str

    def compile(self) -> str:
        return self.name


@attr.s(auto_attribs=True, frozen=True)
class PyFunctionStmt(PyStmt):
    name: str
    parameters: List[PyParameter]
    body_statements: PyStmtList
    return_expr: PyExpr

    def compile(self) -> CompiledOutput:
        parameters = ", ".join(parameter.compile() for parameter in self.parameters)
        body_statements = []
        for statement in self.body_statements:
            body_statements.extend(PyIndentedStmt(statement=statement).compile())

        return_statement = PyIndentedStmt(statement=PyReturnStmt(expr=self.return_expr))
        body_statements.extend(return_statement.compile())

        return [f"def {self.name}({parameters}):", *body_statements]


@attr.s(auto_attribs=True, frozen=True)
class PyExprStmt(PyStmt):
    expr: PyExpr

    def compile(self) -> CompiledOutput:
        if isinstance(self.expr, PyUnavailableExpr):
            return []
        return [f"{self.expr.compile()}"]
