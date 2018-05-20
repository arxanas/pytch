from typing import List

import attr


CompiledOutput = List[str]


class PyExpr:
    def compile(self) -> str:
        raise NotImplementedError(
            f"`PyExpr.compile` not implemented by {self.__class__.__name__}",
        )


@attr.s(auto_attribs=True, frozen=True)
class PyUnavailableExpr(PyExpr):
    """Indicates a value deriving from malformed source code."""
    reason: str

    def compile(self) -> str:
        return f'"<pytch unavailable expr: {self.reason}>"'


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


class PyStmt:
    def compile(self) -> CompiledOutput:
        raise NotImplementedError(
            f"`PyStmt.compile` not implemented by {self.__class__.__name__}",
        )


@attr.s(auto_attribs=True, frozen=True)
class PyAssignmentStmt(PyStmt):
    lhs: PyIdentifierExpr
    rhs: PyExpr

    def compile(self) -> CompiledOutput:
        return [
            f"{self.lhs.compile()} = {self.rhs.compile()}"
        ]


@attr.s(auto_attribs=True, frozen=True)
class PyExprStmt(PyStmt):
    expr: PyExpr

    def compile(self) -> CompiledOutput:
        if isinstance(self.expr, PyUnavailableExpr):
            return []
        return [
            f"{self.expr.compile()}"
        ]


PyStmtList = List[PyStmt]


__all__ = [
    "PyAssignmentStmt",
    "PyExpr",
    "PyExprStmt",
    "PyLiteralExpr",
    "PyStmtList",
    "PyUnavailableExpr",
]
