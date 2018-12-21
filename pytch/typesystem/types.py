import attr

from pytch.containers import PVector
import pytch.typesystem.reason


@attr.s(auto_attribs=True, frozen=True)
class Ty:
    reason: "pytch.typesystem.reason.Reason"

    def __eq__(self, other: object) -> bool:
        # TODO: does this work? Do we need to assign types unique IDs instead?
        return self is other

    def __neq__(self, other: object) -> bool:
        return not (self == other)


class MonoTy(Ty):
    pass


@attr.s(auto_attribs=True, frozen=True)
class BaseTy(MonoTy):
    name: str


@attr.s(auto_attribs=True, frozen=True)
class FunctionTy(MonoTy):
    domain: PVector[Ty]
    codomain: Ty


@attr.s(auto_attribs=True, frozen=True)
class TyVar(MonoTy):
    """Type variable.

    This represents an indeterminate type which is to be symbolically
    manipulated, such as in a universally-quantified type. We don't
    instantiate it to a concrete type during typechecking.

    Usually type variables are denoted by Greek letters, such as "α" rather
    than "a".
    """

    name: str


@attr.s(auto_attribs=True, frozen=True)
class UniversalTy(Ty):
    """Universally-quantified type.

    For example, the type

        ∀α. α → unit

    is a function type which takes a value of any type and returns the unit
    value.
    """

    quantifier_ty: TyVar
    ty: Ty


@attr.s(auto_attribs=True, frozen=True)
class ExistentialTyVar(Ty):
    """Existential type variable.

    This represents an unsolved type that should be solved during type
    inference. The rules for doing so are covered in Dunfield 2013 Figure 10.
    """

    name: str
