import attr

from pytch.redcst import Pattern
from .types import ExistentialTyVar, Ty, TyVar


class TypingJudgment:
    """Abstract base class for typing judgments.

    See Dunfield 2013 Figure 6 for the list of possible judgments.
    """

    pass


@attr.s(auto_attribs=True, frozen=True)
class DeclareVarJudgment(TypingJudgment):
    variable: TyVar


@attr.s(auto_attribs=True, frozen=True)
class PatternHasTyJudgment(TypingJudgment):
    pattern: Pattern
    ty: Ty


@attr.s(auto_attribs=True, frozen=True)
class DeclareExistentialVarJudgment(TypingJudgment):
    existential_ty_var: ExistentialTyVar


@attr.s(auto_attribs=True, frozen=True)
class ExistentialVariableHasTyJudgment(TypingJudgment):
    existential_ty_var: ExistentialTyVar
    ty: Ty


@attr.s(auto_attribs=True, frozen=True)
class ExistentialVariableMarkerJudgment(TypingJudgment):
    """Creates a new 'scope' in which to solve existential type variables."""

    existential_ty_var: ExistentialTyVar
