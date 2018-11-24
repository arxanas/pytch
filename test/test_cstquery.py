from utils import get_syntax_tree

from pytch.cstquery import Query
from pytch.redcst import LetExpr
from pytch.utils import FileInfo


def test_cst_query() -> None:
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="""\
let foo =
  let bar = 3
  bar
""",
    )
    (syntax_tree, errors) = get_syntax_tree(file_info)
    assert not errors

    let_exprs = list(Query(syntax_tree).find_instances(LetExpr))
    assert len(let_exprs) == 2


def test_cst_query_errors() -> None:
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="""\
let foo =
""",
    )
    (syntax_tree, errors) = get_syntax_tree(file_info)
    assert errors
