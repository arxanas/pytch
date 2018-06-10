from utils import get_red_cst

from pytch import FileInfo, Position, Range
from pytch.binder import bind
from pytch.cstquery import Query
from pytch.errors import Error, ErrorCode, Note, Severity
from pytch.redcst import IdentifierExpr, LetExpr


def test_binder() -> None:
    file_info = FileInfo(file_path="<stdin>", source_code="""\
let foo =
  let bar = 3
  bar
""")
    red_cst = get_red_cst(file_info)
    bindation = bind(file_info=file_info, syntax_tree=red_cst)
    [outer_let, inner_let] = Query(red_cst).find_instances(LetExpr)
    [bar_ident] = Query(red_cst).find_instances(IdentifierExpr)
    assert bar_ident.t_identifier is not None
    assert bar_ident.t_identifier.text == "bar"
    assert bindation.get(bar_ident) == [inner_let.n_pattern]


def test_binder_error() -> None:
    file_info = FileInfo(file_path="<stdin>", source_code="""\
let foo =
  let bar = 3
  baz
""")
    red_cst = get_red_cst(file_info)
    bindation = bind(file_info=file_info, syntax_tree=red_cst)
    assert bindation.errors == [Error(
        file_info=file_info,
        code=ErrorCode.UNBOUND_NAME,
        severity=Severity.ERROR,
        message=(
            "I couldn't find a binding in the current scope "
            + "with the name 'baz'."
        ),
        range=Range(
            start=Position(
                line=2,
                character=2,
            ),
            end=Position(
                line=2,
                character=5,
            ),
        ),
        notes=[
            Note(
                file_info=file_info,
                message="Did you mean 'map' (a builtin)?",
                range=None,
            ),
            Note(
                file_info=file_info,
                message="Did you mean 'bar', defined here?",
                range=Range(
                    start=Position(
                        line=1,
                        character=6,
                    ),
                    end=Position(
                        line=1,
                        character=9,
                    ),
                ),
            ),
        ],
    )]
