from typing import List, Optional, Tuple

import attr

from pytch.binder import Bindation
from pytch.containers import find, PMap, PVector, take_while
from pytch.errors import Error, ErrorCode, Note, Severity
from pytch.lexer import TokenKind
from pytch.redcst import (
    Argument,
    BinaryExpr,
    Expr,
    FunctionCallExpr,
    IdentifierExpr,
    IfExpr,
    IntLiteralExpr,
    LetExpr,
    Node,
    Parameter,
    SyntaxTree,
    VariablePattern,
)
from pytch.utils import FileInfo, Range
from .builtins import ERR_TY, INT_TY, NONE_TY, OBJECT_TY, TOP_TY, VOID_TY
from .judgments import (
    DeclareExistentialVarJudgment,
    DeclareVarJudgment,
    ExistentialVariableHasTyJudgment,
    ExistentialVariableMarkerJudgment,
    PatternHasTyJudgment,
    TypingJudgment,
)
from .reason import (
    EqualTysReason,
    InstantiateExistentialReason,
    InvalidSyntaxReason,
    NoneIsSubtypeOfVoidReason,
    Reason,
    SubtypeOfObjectReason,
    SubtypeOfUnboundedGenericReason,
    TodoReason,
)
from .types import BaseTy, ExistentialTyVar, FunctionTy, MonoTy, Ty, TyVar, UniversalTy


@attr.s(auto_attribs=True, frozen=True)
class Env:
    file_info: FileInfo
    bindation: Bindation
    global_scope: PMap[str, Ty]
    errors: PVector[Error]

    def get_range_for_node(self, node: Node) -> Range:
        """Get the range corresponding to node.

        Note that for `let`-expressions, we don't want to flag the entire
        range. Instead, we only want to flag the innermost `let`-expression
        body.
        """
        while isinstance(node, LetExpr):
            n_body = node.n_body
            if n_body is None:
                break
            else:
                node = n_body
        return self.file_info.get_range_from_offset_range(node.offset_range)

    def add_error(
        self,
        code: ErrorCode,
        severity: Severity,
        message: str,
        notes: List[Note] = None,
        range: Range = None,
    ) -> "Env":
        error = Error(
            file_info=self.file_info,
            code=code,
            severity=severity,
            message=message,
            notes=notes if notes is not None else [],
            range=range,
        )
        return attr.evolve(self, errors=self.errors.append(error))


@attr.s(auto_attribs=True, frozen=True)
class TypingContext:
    judgments: PVector[TypingJudgment]
    inferred_tys: PMap[Expr, Ty]

    def add_judgment(self, judgment: TypingJudgment) -> "TypingContext":
        return attr.evolve(self, judgments=self.judgments.append(judgment))

    def ty_to_string(self, ty: Ty) -> str:
        if isinstance(ty, BaseTy):
            return ty.name
        else:
            raise NotImplementedError(f"ty_to_string not implemented for type: {ty!r}")

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
                if isinstance(judgment, ExistentialVariableHasTyJudgment):
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
            return FunctionTy(domain=domain, codomain=codomain, reason=ty.reason)
        elif isinstance(ty, UniversalTy):
            return UniversalTy(
                quantifier_ty=ty.quantifier_ty,
                ty=self.apply_as_substitution(ty),
                reason=ty.reason,
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
                    return ExistentialVariableHasTyJudgment(
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


def tys_equal(lhs: Ty, rhs: Ty) -> bool:
    return lhs == rhs


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
                (env, ctx, _reason) = check(env, ctx, expr=n_lhs, ty=TOP_TY)

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
        n_then_expr = expr.n_then_expr
        if n_then_expr is None:
            return (env, ctx, ERR_TY)

        # TODO: should we actually mint a new existential type variable, then
        # infer it against the two clauses? We could also mint two existential
        # type variables, and then produce the union of them.
        n_else_expr = expr.n_else_expr
        if n_else_expr is None:
            result_ty = VOID_TY
        else:
            (env, ctx, result_ty) = infer(env, ctx, n_else_expr)

        (env, ctx, _reason) = check(env, ctx, n_then_expr, result_ty)
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
            (env, ctx, _reason) = check(env, ctx, expr=n_expr, ty=argument_ty)
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
        parameter_ty = ExistentialTyVar(
            name=f"param_{i}", reason=TodoReason(todo="parameter ty")
        )
        parameter_tys.append(parameter_ty)
        judgment = DeclareExistentialVarJudgment(existential_ty_var=parameter_ty)
        ctx = ctx.add_judgment(judgment)
        ctx = ctx.add_pattern_ty(pattern=n_pattern, ty=parameter_ty)

        if until_judgment is None:
            until_judgment = judgment

    return_ty = ExistentialTyVar(name="return", reason=TodoReason(todo="return ty"))
    return_judgment = DeclareExistentialVarJudgment(existential_ty_var=return_ty)
    if until_judgment is None:
        until_judgment = return_judgment
    ctx = ctx.add_judgment(return_judgment)

    env, ctx, checks = check(env, ctx=ctx, expr=body, ty=return_ty)
    ctx = ctx.take_until_before_judgment(judgment=until_judgment)

    function_ty = FunctionTy(
        domain=PVector(parameter_tys),
        codomain=return_ty,
        reason=TodoReason(todo="infer_lambda"),
    )
    return (env, ctx, function_ty)


def check(
    env: Env, ctx: TypingContext, expr: Expr, ty: Ty
) -> Tuple[Env, TypingContext, Optional[Reason]]:
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
            return (env, ctx, InvalidSyntaxReason())

        if expr.n_parameter_list is None:
            n_value = expr.n_value
            if n_value is None:
                return (env, ctx, InvalidSyntaxReason())
            (env, ctx, value_ty) = infer(env, ctx, n_value)
            if not isinstance(n_pattern, VariablePattern):
                raise NotImplementedError(
                    "TODO: patterns other than VariablePattern not supported"
                )
            ctx = ctx.add_pattern_ty(n_pattern, value_ty)
            if tys_equal(value_ty, VOID_TY):
                env = env.add_error(
                    code=ErrorCode.CANNOT_BIND_TO_VOID,
                    severity=Severity.ERROR,
                    message=(
                        f"This expression has type {ctx.ty_to_string(VOID_TY)}, "
                        + "so it cannot be bound to a variable."
                    ),
                    range=env.get_range_for_node(n_value),
                    notes=[
                        Note(
                            file_info=env.file_info,
                            message="This is the variable it's being bound to.",
                            range=env.get_range_for_node(n_pattern),
                        )
                    ],
                )

            n_body = expr.n_body
            if n_body is None:
                return (env, ctx, InvalidSyntaxReason())

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
        (env, ctx, reason) = check_subtype(env, ctx, lhs=actual_ty, rhs=ty)
        if reason is not None:
            return (env, ctx, reason)
        else:
            env = env.add_error(
                code=ErrorCode.INCOMPATIBLE_TYPES,
                severity=Severity.ERROR,
                message=(
                    f"I was expecting this expression to have type {ctx.ty_to_string(ty)}, "
                    + f"but it actually had type {ctx.ty_to_string(actual_ty)}."
                ),
                range=env.get_range_for_node(expr),
            )
            return (env, ctx, reason)


def check_subtype(
    env: Env, ctx: TypingContext, lhs: Ty, rhs: Ty
) -> Tuple[Env, TypingContext, Optional[Reason]]:
    if tys_equal(lhs, rhs):
        return (env, ctx, EqualTysReason(lhs=lhs, rhs=rhs))
    elif isinstance(lhs, UniversalTy):
        # TODO: implement
        return (env, ctx, TodoReason(todo="UniversalTy"))
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
        return (env, ctx, SubtypeOfUnboundedGenericReason())
    elif tys_equal(rhs, VOID_TY):
        assert lhs != VOID_TY, "should be handled in tys_equal case"
        (env, ctx, reason) = check_subtype(env, ctx, lhs=lhs, rhs=NONE_TY)
        if reason is not None:
            return (env, ctx, NoneIsSubtypeOfVoidReason())
        else:
            return (env, ctx, None)
    elif tys_equal(rhs, OBJECT_TY):
        if tys_equal(lhs, VOID_TY):
            return (env, ctx, None)
        else:
            return (env, ctx, SubtypeOfObjectReason())
    elif isinstance(lhs, BaseTy) and isinstance(rhs, BaseTy):
        assert not tys_equal(lhs, rhs), "should have been handled in tys_equal case"
        return (env, ctx, None)
    elif isinstance(lhs, FunctionTy) or isinstance(rhs, FunctionTy):
        if not isinstance(lhs, FunctionTy):
            raise NotImplementedError(
                f"TODO: handle subtype failure for non-function type {lhs!r} and function type {rhs!r}"
            )
        if not isinstance(rhs, FunctionTy):
            raise NotImplementedError(
                f"TODO: handle subtype failure for function type {lhs!r} and non-function type {rhs!r}"
            )
        raise NotImplementedError("TODO: implement subtype checking for functions")

    # TODO: implement the rest of the subtyping from Figure 9.
    raise NotImplementedError(
        f"TODO: subtype checking for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def instantiate_lhs_existential(
    env: Env, ctx: TypingContext, lhs: ExistentialTyVar, rhs: Ty
) -> Tuple[Env, TypingContext, Reason]:
    if isinstance(rhs, (MonoTy, ExistentialTyVar)):
        ctx = ctx.instantiate_existential(existential_ty_var=lhs, to=rhs)
        return (env, ctx, InstantiateExistentialReason(existential_ty_var=lhs, to=rhs))

    raise NotImplementedError(
        f"TODO: LHS existential instantiation for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def instantiate_rhs_existential(
    env: Env, ctx: TypingContext, lhs: Ty, rhs: ExistentialTyVar
) -> Tuple[Env, TypingContext, Reason]:
    if isinstance(lhs, MonoTy):
        ctx = ctx.instantiate_existential(existential_ty_var=rhs, to=lhs)
        return (env, ctx, InstantiateExistentialReason(existential_ty_var=rhs, to=lhs))

    raise NotImplementedError(
        f"TODO: RHS existential instantiation for lhs {lhs!r} and rhs {rhs!r} not implemented"
    )


def typecheck(
    file_info: FileInfo,
    syntax_tree: SyntaxTree,
    bindation: Bindation,
    global_scope: PMap[str, Ty],
) -> Typeation:
    ctx = TypingContext(judgments=PVector(), inferred_tys=PMap())
    if syntax_tree.n_expr is None:
        return Typeation(ctx, errors=[])

    env = Env(
        file_info=file_info,
        bindation=bindation,
        global_scope=global_scope,
        errors=PVector(),
    )
    (env, ctx, checks) = check(env, ctx, expr=syntax_tree.n_expr, ty=TOP_TY)
    assert checks, "The program should always check against the top type"
    return Typeation(ctx=ctx, errors=list(env.errors))
