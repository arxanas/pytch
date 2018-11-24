from typing import Any, Iterator, List, Optional

import pytest
from utils import CaseInfo, CaseResult, find_tests, generate, get_syntax_tree

from pytch.binder import bind, GLOBAL_SCOPE as BINDER_GLOBAL_SCOPE
from pytch.containers import PVector
from pytch.cstquery import Query
from pytch.errors import Error, get_error_lines
from pytch.redcst import Expr, FunctionCallExpr
from pytch.typesystem import (
    FunctionTy,
    GLOBAL_SCOPE as TYPE_SYSTEM_GLOBAL_SCOPE,
    NONE_TY,
    typecheck,
    TyVar,
    UniversalTy,
)
from pytch.utils import FileInfo


BINDER_GLOBAL_SCOPE = dict(BINDER_GLOBAL_SCOPE)
BINDER_GLOBAL_SCOPE.update({"show_type": []})

show_type_ty_var = TyVar(name="T")
show_type_ty = FunctionTy(
    domain=PVector([UniversalTy(quantifier_ty=show_type_ty_var, ty=show_type_ty_var)]),
    codomain=NONE_TY,
)
TYPE_SYSTEM_GLOBAL_SCOPE = TYPE_SYSTEM_GLOBAL_SCOPE.set("show_type", show_type_ty)


def get_typesystem_tests() -> Iterator[CaseInfo]:
    return find_tests("typesystem", input_extension=".pytch", error_extension=".err")


def get_typesystem_test_ids() -> List[str]:
    return [test.name for test in get_typesystem_tests()]


def make_result(input_filename: str, source_code: str, capsys: Any) -> CaseResult:
    file_info = FileInfo(file_path=input_filename, source_code=source_code)
    (syntax_tree, syntax_errors) = get_syntax_tree(file_info=file_info)
    bindation = bind(
        file_info=file_info, syntax_tree=syntax_tree, global_scope=BINDER_GLOBAL_SCOPE
    )

    typeation = typecheck(
        syntax_tree=syntax_tree,
        bindation=bindation,
        global_scope=TYPE_SYSTEM_GLOBAL_SCOPE,
    )

    function_calls = Query(syntax_tree=syntax_tree).find_instances(FunctionCallExpr)
    show_type_exprs: List[Expr] = []
    for function_call in function_calls:
        n_callee = function_call.n_callee
        if n_callee is None:
            continue

        text = n_callee.text
        if text != "show_type":
            continue

        n_argument_list = function_call.n_argument_list
        assert n_argument_list is not None
        arguments = n_argument_list.arguments
        assert arguments is not None
        assert len(arguments) == 1
        argument = arguments[0].n_expr
        assert isinstance(argument, Expr)
        show_type_exprs.append(argument)

    output = ""
    for show_type_expr in show_type_exprs:
        line_num = (
            file_info.get_range_from_offset_range(
                show_type_expr.offset_range
            ).start.line
            + 1
        )
        type_info = typeation.ctx.get_infers(expr=show_type_expr)
        output += f"line {line_num}: {type_info!r}\n"

    error_lines = []
    errors: List[Error] = syntax_errors + bindation.errors + typeation.errors
    for i in errors:
        error_lines.extend(get_error_lines(i, ascii=True))

    error: Optional[str]
    if error_lines:
        error = "".join(line + "\n" for line in error_lines)
    else:
        error = None

    return CaseResult(output=output, error=error)


@pytest.mark.parametrize(
    "test_case_info", get_typesystem_tests(), ids=get_typesystem_test_ids()
)
def test_typesystem(test_case_info: CaseInfo) -> None:
    result = make_result(
        input_filename=test_case_info.input_filename,
        source_code=test_case_info.input,
        capsys=None,
    )
    assert test_case_info.output == result.output
    assert test_case_info.error == result.error


@pytest.mark.generate
def test_generate_typesystem_tests() -> None:
    generate(get_typesystem_tests(), make_result, capsys=None)
