from utils import get_syntax_tree

from pytch import FileInfo
from pytch.cstquery import Query
from pytch.redcst import LetExpr


def test_cst_query() -> None:
    file_info = FileInfo(
        file_path="dummy.pytch",
        source_code="""\
let foo =
  let bar = 3
  bar
""",
    )
    syntax_tree = get_syntax_tree(file_info)

    let_exprs = list(Query(syntax_tree).find_instances(LetExpr))
    assert len(let_exprs) == 2
