import attr

from .types import ExistentialTyVar, Ty


class Reason:
    def __str__(self) -> str:
        raise NotImplementedError(
            f"__str__ not implemented for reason class {self.__class__.__name__}"
        )


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


@attr.s(auto_attribs=True, frozen=True)
class InvalidSyntaxReason(Reason):
    def __str__(self) -> str:
        return (
            "there was invalid syntax, so I assumed "
            + "that bit of code typechecked and proceeded "
            + "with checking the rest of the program"
        )


@attr.s(auto_attribs=True, frozen=True)
class EqualTysReason(Reason):
    lhs: Ty
    rhs: Ty

    def __str__(self) -> str:
        return "because the two types were equal"


@attr.s(auto_attribs=True, frozen=True)
class InstantiateExistentialReason(Reason):
    existential_ty_var: ExistentialTyVar
    to: Ty

    def __str__(self) -> str:
        return "because the type was determined to be the other type"


@attr.s(auto_attribs=True, frozen=True)
class SubtypeOfObjectReason(Reason):
    def __str__(self) -> str:
        return "all types are subtypes of object"


@attr.s(auto_attribs=True, frozen=True)
class SubtypeOfUnboundedGenericReason(Reason):
    def __str__(self) -> str:
        return "it was checked to be the subtype of an generic type parameter"


@attr.s(auto_attribs=True, frozen=True)
class NoneIsSubtypeOfVoidReason(Reason):
    def __str__(self) -> str:
        return "None is the only value that can be used where no value is expected"
