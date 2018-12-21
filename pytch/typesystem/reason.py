import attr


class Reason:
    def __str__(self) -> str:
        raise NotImplementedError(
            f"__str__ not implemented for reason class {self.__class__.__name__}"
        )


@attr.s(auto_attribs=True, frozen=True)
class NoneReason(Reason):
    def __str__(self) -> str:
        return "<none>"


@attr.s(auto_attribs=True, frozen=True)
class TodoReason(Reason):
    todo: str

    def __str__(self) -> str:
        return f"reason not implemented for case {self.todo}"


@attr.s(auto_attribs=True, frozen=True)
class BuiltinReason(Reason):
    name: str

    def __str__(self) -> str:
        return f"{self.name} is a built-in"
