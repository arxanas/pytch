from utils import get_red_cst

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
"""
    )
    red_cst = get_red_cst(file_info)

    let_exprs = list(Query(red_cst).find_instances(LetExpr))
    assert len(let_exprs) == 2
