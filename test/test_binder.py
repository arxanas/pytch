from pytch.binder import bind, GLOBAL_SCOPE
from pytch.cstquery import Query
from pytch.errors import Error, ErrorCode, Note, Severity
from pytch.redcst import DefExpr, IdentifierExpr, LetExpr, VariablePattern
from pytch.utils import FileInfo, Position, Range
from .utils import get_syntax_tree


def test_binder() -> None:
    file_info = FileInfo(
        file_path="<stdin>",
        source_code="""\
let foo =
  let bar = 3
  bar
""",
    )
    (syntax_tree, errors) = get_syntax_tree(file_info)
    assert not errors
    bindation = bind(
        file_info=file_info, syntax_tree=syntax_tree, global_scope=GLOBAL_SCOPE
    )
    [outer_let, inner_let] = Query(syntax_tree).find_instances(LetExpr)
    [bar_ident] = Query(syntax_tree).find_instances(IdentifierExpr)
    assert bar_ident.t_identifier is not None
    assert bar_ident.t_identifier.text == "bar"
    assert bindation.get(bar_ident) == [inner_let.n_pattern]


def test_binder_error() -> None:
    file_info = FileInfo(
        file_path="<stdin>",
        source_code="""\
let foo =
  let bar = 3
  baz
""",
    )
    (syntax_tree, errors) = get_syntax_tree(file_info)
    assert not errors
    bindation = bind(
        file_info=file_info, syntax_tree=syntax_tree, global_scope=GLOBAL_SCOPE
    )
    assert bindation.errors == [
        Error(
            file_info=file_info,
            code=ErrorCode.UNBOUND_NAME,
            severity=Severity.ERROR,
            message=(
                "I couldn't find a binding in the current scope "
                + "with the name 'baz'."
            ),
            range=Range(
                start=Position(line=2, character=2), end=Position(line=2, character=5)
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
                        start=Position(line=1, character=6),
                        end=Position(line=1, character=9),
                    ),
                ),
            ],
        )
    ]


def test_binding_defs() -> None:
    file_info = FileInfo(
        file_path="<stdin>",
        source_code="""\
def foo(bar) =>
    bar + baz
bar
""",
    )
    (syntax_tree, errors) = get_syntax_tree(file_info)
    assert not errors
    bindation = bind(
        file_info=file_info, syntax_tree=syntax_tree, global_scope=GLOBAL_SCOPE
    )
    [containing_def] = Query(syntax_tree).find_instances(DefExpr)
    [_, bar_ident_definition] = Query(syntax_tree).find_instances(VariablePattern)
    [bar_ident_use, _, _] = Query(syntax_tree).find_instances(IdentifierExpr)
    assert bar_ident_use.t_identifier is not None
    assert bar_ident_use.t_identifier.text == "bar"
    assert bindation.get(bar_ident_use) == [bar_ident_definition]
    assert bindation.errors == [
        Error(
            file_info=file_info,
            code=ErrorCode.UNBOUND_NAME,
            severity=Severity.ERROR,
            message=(
                "I couldn't find a binding in the current scope "
                + "with the name 'baz'."
            ),
            range=Range(
                start=Position(line=1, character=10), end=Position(line=1, character=13)
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
                        start=Position(line=0, character=8),
                        end=Position(line=0, character=11),
                    ),
                ),
            ],
        ),
        Error(
            file_info=file_info,
            code=ErrorCode.UNBOUND_NAME,
            severity=Severity.ERROR,
            message=(
                "I couldn't find a binding in the current scope "
                + "with the name 'bar'."
            ),
            range=Range(
                start=Position(line=2, character=0), end=Position(line=2, character=3)
            ),
            notes=[
                Note(
                    file_info=file_info,
                    message="Did you mean 'map' (a builtin)?",
                    range=None,
                )
            ],
        ),
    ]
