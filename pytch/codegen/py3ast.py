from typing import List


CompiledOutput = List[str]


class PyExpr:
    def compile(self) -> str:
        raise NotImplementedError(
            f"`PyExpr.compile` not implemented by {self.__class__.__name__}",
        )


class PyUnavailableExpr(PyExpr):
    """Indicates a value deriving from malformed source code."""
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def compile(self) -> str:
        return f'"<pytch unavailable expr: {self.reason}>"'


class PyIdentifierExpr(PyExpr):
    def __init__(self, name: str) -> None:
        self.name = name

    def compile(self) -> str:
        return self.name


class PyLiteralExpr(PyExpr):
    def __init__(self, value: str) -> None:
        self.value = value

    def compile(self) -> str:
        return self.value


class PyArgument:
    def __init__(self, value: PyExpr) -> None:
        self.value = value

    def compile(self) -> str:
        return self.value.compile()


class PyFunctionCallExpr(PyExpr):
    def __init__(self, receiver: PyExpr, arguments: List[PyArgument]) -> None:
        self.receiver = receiver
        self.arguments = arguments

    def compile(self) -> str:
        compiled_arguments = []
        for argument in self.arguments:
            compiled_arguments.append(argument.compile())
        compiled_arguments_str = ", ".join(compiled_arguments)
        return f"{self.receiver.compile()}({compiled_arguments_str})"


class PyStmt:
    def compile(self) -> CompiledOutput:
        raise NotImplementedError(
            f"`PyStmt.compile` not implemented by {self.__class__.__name__}",
        )


class PyAssignmentStmt(PyStmt):
    def __init__(self, lhs: PyIdentifierExpr, rhs: PyExpr) -> None:
        self.lhs = lhs
        self.rhs = rhs

    def compile(self) -> CompiledOutput:
        return [
            f"{self.lhs.compile()} = {self.rhs.compile()}"
        ]


class PyExprStmt(PyStmt):
    def __init__(self, expr: PyExpr) -> None:
        self.expr = expr

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
