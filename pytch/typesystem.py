"""Type inference and typechecking.

The Pytch type system is a bidirectional typechecking system, based off of
the system described in [Dunfield 2013] (see Figures 9-11 for the algorithmic
typing rules for the system). A standard Hindley-Milner type system would be
difficult to reconcile in the presence of subtyping, which will naturally
occur when interfacing with Python code.

  [Dunfield 2013]: https://www.cl.cam.ac.uk/~nk480/bidir.pdf

Terminology used in this file:

  * `ty`: "type".
  * `ctx`: "context".
  * `env`: "environment". This only refers to the usual sort of global
  configuration that's passed around, rather than a typing environment (Γ),
  which is called a "context" instead.
  * `var`: "variable", specifically a type variable of some sort.
  * The spelling "judgment" is preferred over "judgement".

"""
from typing import List, Optional, Tuple

import attr

from .binder import Bindation
from .containers import find, PMap, PVector, take_while
from .errors import Error
from .lexer import TokenKind
from .redcst import (
    Argument,
    BinaryExpr,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IfExpr,
    IntLiteralExpr,
    LetExpr,
    Parameter,
    Pattern,
    SyntaxTree,
    VariablePattern,
)


class Ty:
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
class ExistentialVariableHasTy(TypingJudgment):
    existential_ty_var: ExistentialTyVar
    ty: Ty


@attr.s(auto_attribs=True, frozen=True)
class ExistentialVariableMarkerJudgment(TypingJudgment):
    """Creates a new 'scope' in which to solve existential type variables."""

    existential_ty_var: ExistentialTyVar


@attr.s(auto_attribs=True, frozen=True)
class Env:
    bindation: Bindation
    global_scope: PMap[str, Ty]
    errors: PVector[Error]


@attr.s(auto_attribs=True, frozen=True)
class TypingContext:
    judgments: PVector[TypingJudgment]
    inferred_tys: PMap[Expr, Ty]

    def add_judgment(self, judgment: TypingJudgment) -> "TypingContext":
        return attr.evolve(self, judgments=self.judgments.append(judgment))

    def take_until_before_judgment(self, judgment: TypingJudgment) -> "TypingContext":
        judgments = PVector(take_while(self.judgments, lambda x: x != judgment))
        assert len(judgments) < len(
            self.judgments
        ), f"take_until_before_judgment: expected to find judgment {judgment!r} in context {self.judgments!r}"
        return attr.evolve(self, judgments=judgments)

    def apply_as_substitution(self, ty: Ty) -> Ty:
        """See Dunfield 2013 Figure 7."""
        if isinstance(ty, MonoTy):
            return ty
        elif isinstance(ty, BaseTy):
            return ty
        elif isinstance(ty, ExistentialTyVar):

            def is_substitution_for_existential_ty_variable(
                judgment: TypingJudgment
            ) -> bool:
                if isinstance(judgment, ExistentialVariableHasTy):
                    return judgment.existential_ty_var == ty
                else:
                    return False

            existential_ty_variable_substitution = find(
                self.judgments, is_substitution_for_existential_ty_variable
            )
            if existential_ty_variable_substitution is not None:
                assert isinstance(
                    existential_ty_variable_substitution, ExistentialTyVar
                )
                return existential_ty_variable_substitution.ty
            else:
                return ty
        elif isinstance(ty, FunctionTy):
            domain = ty.domain.map(self.apply_as_substitution)
            codomain = self.apply_as_substitution(ty.codomain)
            return FunctionTy(domain=domain, codomain=codomain)
        elif isinstance(ty, UniversalTy):
            return UniversalTy(
                quantifier_ty=ty.quantifier_ty, ty=self.apply_as_substitution(ty)
            )
        else:
            assert (
                False
            ), f"Unhandled case for typing context substitution: {ty.__class__.__name__}"

    def instantiate_existential(
        self, existential_ty_var: ExistentialTyVar, to: Ty
    ) -> "TypingContext":
        def f(x: TypingJudgment) -> TypingJudgment:
            if isinstance(x, DeclareExistentialVarJudgment):
                if x.existential_ty_var == existential_ty_var:
                    return ExistentialVariableHasTy(
                        existential_ty_var=existential_ty_var, ty=to
                    )
            return x

        return attr.evolve(self, judgments=self.judgments.map(f))

    def record_infers(self, expr: Expr, ty: Ty) -> "TypingContext":
        return attr.evolve(self, inferred_tys=self.inferred_tys.set(expr, ty))

    def get_infers(self, expr: Expr) -> Optional[Ty]:
        return self.inferred_tys.get(expr)

    def add_pattern_ty(self, pattern: VariablePattern, ty: Ty) -> "TypingContext":
        judgment = PatternHasTyJudgment(pattern=pattern, ty=ty)
        return attr.evolve(self, judgments=self.judgments.append(judgment))

    def get_pattern_ty(self, pattern: VariablePattern) -> Optional[Ty]:
        for judgment in self.judgments:
            if isinstance(judgment, PatternHasTyJudgment):
                if judgment.pattern is pattern:
                    return judgment.ty
        return None

    def push_existential_ty_var_marker(
        self, existential_ty_var: ExistentialTyVar
    ) -> "TypingContext":
        return attr.evolve(
            self,
            judgments=self.judgments.append(
                ExistentialVariableMarkerJudgment(existential_ty_var=existential_ty_var)
            ),
        )

    def pop_existential_ty_var_marker(
        self, existential_ty_var: ExistentialTyVar
    ) -> "TypingContext":
        raise NotImplementedError("pop existential ty var not implemented")


@attr.s(auto_attribs=True, frozen=True)
class Typeation:
    ctx: TypingContext
    errors: List[Error]


ERR_TY = BaseTy(name="<error>")
"""Error type.

Produced when there is a typechecking error, in order to prevent cascading
failure messages.
"""


NONE_TY = BaseTy(name="None")
"""None type, corresponding to Python's `None` value."""


INT_TY = BaseTy(name="int")
"""Integer type, corresponding to Python's `int` type."""


def tys_equal(lhs: Ty, rhs: Ty) -> bool:
    return lhs == rhs


def _make_print() -> FunctionTy:
    quantifier_ty = TyVar(name="T")
    domain: PVector[Ty] = PVector(
        [UniversalTy(quantifier_ty=quantifier_ty, ty=quantifier_ty)]
    )
    codomain = NONE_TY
    return FunctionTy(domain=domain, codomain=codomain)


# TODO: add the Python builtins to the global scope.
GLOBAL_SCOPE: PMap[str, Ty] = PMap({"print": _make_print()})


def do_infer(env: Env, ctx: TypingContext, expr: Expr) -> Tuple[Env, TypingContext, Ty]:
    if isinstance(expr, IntLiteralExpr):
        return (env, ctx, INT_TY)
    elif isinstance(expr, LetExpr):
        raise ValueError("should not be trying to infer the type of a let-expr (?)")
    elif isinstance(expr, FunctionCallExpr):
        # Γ ⊢ e1 ⇒ A ⊣ Θ   Θ ⊢ [Θ]A•e2 ⇒⇒ C ⊣ ∆
        # --------------------------------------  →E
        #            Γ ⊢ e1 e2 ⇒ C ⊣ ∆
        n_callee = expr.n_callee
        if n_callee is None:
            raise NotImplementedError("TODO(missing): handle missing callee")

        (env, ctx, callee_ty) = infer(env, ctx=ctx, expr=n_callee)

        n_argument_list = expr.n_argument_list
        if n_argument_list is None:
            raise NotImplementedError("TODO(missing): handle missing argument list")
        arguments = n_argument_list.arguments
        if arguments is None:
            raise NotImplementedError("TODO(missing): handle missing argument list")

        callee_ty = ctx.apply_as_substitution(callee_ty)
        return function_application_infer(
            env, ctx=ctx, ty=callee_ty, arguments=PVector(arguments)
        )
    elif isinstance(expr, IdentifierExpr):
        target = env.bindation.get(expr)
        if target is None:
            raise NotImplementedError("TODO: handle absent type for identifier")

        if len(target) == 0:
            # Binding exists, but there is no definition. It must be a global
            # binding.
            result_ty = env.global_scope.get(expr.text)
            if result_ty is not None:
                return (env, ctx, result_ty)
            raise NotImplementedError(
                f"TODO: handle absent global variable type for {expr.text}"
            )

        elif len(target) == 1:
            pattern = target[0]
            result_ty = ctx.get_pattern_ty(pattern)
            if result_ty is None:
                raise NotImplementedError("TODO: handle absent type for expr")
            return (env, ctx, result_ty)

        else:
            raise NotImplementedError(
                "TODO: handle multiple possible source definitions"
            )
    elif isinstance(expr, BinaryExpr):
        t_operator = expr.t_operator
        if t_operator is None:
            raise NotImplementedError(
                "TODO(missing): handle missing operator in binary expression"
            )

        if t_operator.kind == TokenKind.DUMMY_SEMICOLON:
            n_lhs = expr.n_lhs
            if n_lhs is not None:
                (env, ctx, checks) = check(env, ctx, expr=n_lhs, ty=NONE_TY)
                if not checks:
                    raise NotImplementedError(
                        "TODO: raise error/warning for non-None LHS of binary expression"
                    )
            n_rhs = expr.n_rhs
            if n_rhs is not None:
                return infer(env, ctx, expr=n_rhs)
            else:
                return (env, ctx, ERR_TY)
        elif t_operator.kind == TokenKind.PLUS:
            # TODO: do something more sophisticated.
            n_lhs = expr.n_lhs
            if n_lhs is not None:
                (env, ctx, checks) = check(env, ctx, expr=n_lhs, ty=INT_TY)
                if not checks:
                    raise NotImplementedError("TODO: handle + on non-int LHS operand")
            n_rhs = expr.n_rhs
            if n_rhs is not None:
                (env, ctx, checks) = check(env, ctx, expr=n_rhs, ty=INT_TY)
                if not checks:
                    raise NotImplementedError("TODO: handle + on non-int RHS operand")
            return (env, ctx, INT_TY)
        else:
            raise NotImplementedError(
                f"`infer` not yet implemented for binary expression operator kind {t_operator.kind}"
            )
    elif isinstance(expr, IfExpr):
        # TODO: should we actually mint a new existential type variable, then
        # infer it against the two clauses?
        n_else_expr = expr.n_else_expr
        if n_else_expr is None:
            result_ty = NONE_TY
        else:
            (env, ctx, result_ty) = infer(env, ctx, n_else_expr)

        n_then_expr = expr.n_then_expr
        if n_then_expr is None:
            return (env, ctx, ERR_TY)
        (env, ctx, checks) = check(env, ctx, n_then_expr, result_ty)
        if not checks:
            raise NotImplementedError(
                "TODO: `if`-clause without `else`-clause shouldn't check against None"
            )

        return (env, ctx, result_ty)
    else:
        raise NotImplementedError(
            f"TODO: `infer` not yet implemented for expression type: {expr.__class__.__name__}"
        )


def infer(env: Env, ctx: TypingContext, expr: Expr) -> Tuple[Env, TypingContext, Ty]:
    (env, ctx, ty) = do_infer(env, ctx, expr)
    ctx = ctx.record_infers(expr, ty)
    return (env, ctx, ty)


def infer_function_definition(
    env: Env, ctx: TypingContext, expr: LetExpr
) -> Tuple[Env, TypingContext, Ty]:
    def error(ctx: TypingContext):
        function_ty = ERR_TY
        n_pattern = expr.n_pattern
        assert isinstance(
            n_pattern, VariablePattern
        ), "Function let-exprs should be VariablePatterns"
        ctx = ctx.add_pattern_ty(pattern=n_pattern, ty=function_ty)
        return (env, ctx, function_ty)

    n_parameter_list = expr.n_parameter_list
    if n_parameter_list is None:
        return error(ctx)

    parameter_list = n_parameter_list.parameters
    if parameter_list is None:
        return error(ctx)

    parameters: PVector[Optional[Parameter]] = PVector()
    for n_parameter in parameter_list:
        if n_parameter is None:
            return error(ctx)
        parameters = parameters.append(n_parameter)

    n_value = expr.n_value
    if n_value is None:
        return error(ctx)

    return infer_lambda(env, ctx, parameters=parameters, body=n_value)


def function_application_infer(
    env: Env, ctx: TypingContext, ty: Ty, arguments: PVector[Argument]
) -> Tuple[Env, TypingContext, Ty]:
    """The function-application relation ⇒⇒, discussed in Dunfield 2013."""
    if isinstance(ty, FunctionTy):
        if len(arguments) != len(ty.domain):
            raise NotImplementedError("TODO: handle argument number mismatch")

        # TODO: use `izip_longest` here instead (not known to Mypy?)
        for argument, argument_ty in zip(arguments, ty.domain):
            n_expr = argument.n_expr
            if n_expr is None:
                raise NotImplementedError("TODO(missing): handle missing argument")
            (env, ctx, checks) = check(env, ctx, expr=n_expr, ty=argument_ty)
            if not checks:
                raise NotImplementedError("TODO: handle argument type mismatch")
        return (env, ctx, ty.codomain)

    elif isinstance(ty, ExistentialTyVar):
        raise NotImplementedError()

    else:
        assert (
            False
        ), f"Unexpected function_application_infer type: {ty.__class__.__name__}"


def check_lambda():
    """Check the type of a lambda or function definition.

    The typing rule is

        Γ, x:A ⊢ e ⇐ B ⊣ ∆, x:A, Θ
        --------------------------  →I
            Γ ⊢ λx.e ⇐ A→B ⊣ ∆
    """
    raise NotImplementedError("check_lambda")


def infer_lambda(
    env: Env, ctx: TypingContext, parameters: PVector[Optional[Parameter]], body: Expr
) -> Tuple[Env, TypingContext, Ty]:
    """Infer the type of a lambda or function definition.

    The typing rule is

        Γ, â, bˆ, x:â ⊢ e ⇐ bˆ ⊣ ∆, x:â, Θ
        -----------------------------------  →I⇒
                Γ ⊢ λx.e ⇒ â→bˆ ⊣ ∆

    which must be generalized here to handle multiple parameters.
    """
    until_judgment = None
    parameter_tys = []
    for i, parameter in enumerate(parameters):
        if parameter is None:
            continue
        n_pattern = parameter.n_pattern
        if n_pattern is None:
            continue
        if not isinstance(n_pattern, VariablePattern):
            raise NotImplementedError(
                "TODO: patterns other than VariablePattern not supported"
            )
        parameter_ty = ExistentialTyVar(name=f"param_{i}")
        parameter_tys.append(parameter_ty)
        judgment = DeclareExistentialVarJudgment(existential_ty_var=parameter_ty)
        ctx = ctx.add_judgment(judgment)
        ctx = ctx.add_pattern_ty(pattern=n_pattern, ty=parameter_ty)

        if until_judgment is None:
            until_judgment = judgment

    return_ty = ExistentialTyVar(name="return")
    return_judgment = DeclareExistentialVarJudgment(existential_ty_var=return_ty)
    if until_judgment is None:
        until_judgment = return_judgment
    ctx = ctx.add_judgment(return_judgment)

    env, ctx, checks = check(env, ctx=ctx, expr=body, ty=return_ty)
    ctx = ctx.take_until_before_judgment(judgment=until_judgment)

    function_ty = FunctionTy(domain=PVector(parameter_tys), codomain=return_ty)
    return (env, ctx, function_ty)


def check(
    env: Env, ctx: TypingContext, expr: Expr, ty: Ty
) -> Tuple[Env, TypingContext, bool]:
    if isinstance(expr, LetExpr):
        # The typing rule for let-bindings is
        #
        #     Ψ ⊢ e ⇒ A   Ψ, x:A ⊢ e' ⇐ C
        #     ---------------------------  let
        #       Ψ ⊢ let x = e in e' ⇐ C
        #
        # Note that we have to adapt this for function definitions by also
        # using the rule for typing lambdas.
        n_pattern = expr.n_pattern
        if n_pattern is None:
            return (env, ctx, True)

        if expr.n_parameter_list is None:
            n_value = expr.n_value
            if n_value is None:
                return (env, ctx, True)
            (env, ctx, value_ty) = infer(env, ctx, n_value)
            if not isinstance(n_pattern, VariablePattern):
                raise NotImplementedError(
                    "TODO: patterns other than VariablePattern not supported"
                )
            ctx = ctx.add_pattern_ty(n_pattern, value_ty)

            n_body = expr.n_body
            if n_body is None:
                return (env, ctx, True)

            return check(env, ctx, expr=n_body, ty=ty)
        else:
            n_parameter_list = expr.n_parameter_list
            if n_parameter_list is None:
                return (env, ctx, True)

            parameters = n_parameter_list.parameters
            if parameters is None:
                raise NotImplementedError(
                    "TODO(missing): raise error for missing parameters"
                )

            (env, ctx, function_ty) = infer_function_definition(env, ctx, expr)
            n_body = expr.n_body
            if n_body is None:
                raise NotImplementedError(
                    "TODO(missing): raise error for missing function body"
                )

            # parameters_with_tys: PVector[CtxElemExprHasTy] = PVector()
            # for n_argument, argument_ty in zip(parameters, ty.domain):
            #     n_expr = n_argument.n_expr
            #     if n_expr is None:
            #         return (env, ctx, True)
            #     parameters_with_tys = parameters_with_tys.append(
            #         CtxElemExprHasTy(expr=n_expr, ty=argument_ty)
            #     )
            # ctx = ctx.add_elem(CtxElemExprsHaveTys(expr_tys=parameters_with_tys))

            assert isinstance(n_pattern, VariablePattern)
            ctx = ctx.add_pattern_ty(n_pattern, function_ty)
            return check(env, ctx, expr=n_body, ty=ty)
    else:
        (env, ctx, actual_ty) = infer(env, ctx, expr=expr)
        return check_subtype(env, ctx, lhs=actual_ty, rhs=ty)


def check_subtype(
    env: Env, ctx: TypingContext, lhs: Ty, rhs: Ty
) -> Tuple[Env, TypingContext, bool]:
    if tys_equal(lhs, rhs):
        return (env, ctx, True)

    if isinstance(lhs, FunctionTy) or isinstance(rhs, FunctionTy):
        if not isinstance(lhs, FunctionTy):
            raise NotImplementedError(
                f"TODO: handle subtype failure for non-function type {lhs!r} and function type {rhs!r}"
            )
        if not isinstance(rhs, FunctionTy):
            raise NotImplementedError(
                f"TODO: handle subtype failure for function type {lhs!r} and non-function type {rhs!r}"
            )
        raise NotImplementedError("TODO: implement subtype checking for functions")

    if isinstance(lhs, UniversalTy):
        # TODO: implement
        return (env, ctx, True)
    elif isinstance(rhs, UniversalTy):
        judgment = DeclareVarJudgment(variable=rhs.quantifier_ty)
        ctx = ctx.add_judgment(judgment)
        (env, ctx, checks) = check_subtype(env, ctx, lhs=lhs, rhs=rhs.ty)
        ctx = ctx.take_until_before_judgment(judgment)
        return (env, ctx, checks)
    elif isinstance(lhs, ExistentialTyVar):
        # <:InstantiateL
        # TODO: check to see that the existential type variable is not in the
        # free variables of the right-hand side.
        return instantiate_lhs_existential(env, ctx, lhs=lhs, rhs=rhs)
    elif isinstance(rhs, ExistentialTyVar):
        # <:InstantiateR
        # TODO: check to see that the existential type variable is not in the
        # free variables of the right-hand side.
        return instantiate_rhs_existential(env, ctx, lhs=lhs, rhs=rhs)
    elif isinstance(rhs, TyVar):
        return (env, ctx, True)

    # TODO: implement the rest of the subtyping from Figure 9.
    raise NotImplementedError(
        f"TODO: subtype checking for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def instantiate_lhs_existential(
    env: Env, ctx: TypingContext, lhs: ExistentialTyVar, rhs: Ty
) -> Tuple[Env, TypingContext, bool]:
    if isinstance(rhs, (MonoTy, ExistentialTyVar)):
        ctx = ctx.instantiate_existential(existential_ty_var=lhs, to=rhs)
        return (env, ctx, True)

    raise NotImplementedError(
        f"TODO: LHS existential instantiation for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def instantiate_rhs_existential(
    env: Env, ctx: TypingContext, lhs: Ty, rhs: ExistentialTyVar
) -> Tuple[Env, TypingContext, bool]:
    if isinstance(lhs, MonoTy):
        ctx = ctx.instantiate_existential(existential_ty_var=rhs, to=lhs)
        return (env, ctx, True)

    raise NotImplementedError(
        f"TODO: RHS existential instantiation for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def typecheck(
    syntax_tree: SyntaxTree, bindation: Bindation, global_scope: PMap[str, Ty]
) -> Typeation:
    ctx = TypingContext(judgments=PVector(), inferred_tys=PMap())
    if syntax_tree.n_expr is None:
        return Typeation(ctx, errors=[])

    env = Env(bindation=bindation, global_scope=global_scope, errors=PVector())
    (env, ctx, checks) = check(env, ctx, expr=syntax_tree.n_expr, ty=NONE_TY)
    if not checks:
        raise NotImplementedError("TODO: handle module body not checking against None")
    return Typeation(ctx=ctx, errors=list(env.errors))
