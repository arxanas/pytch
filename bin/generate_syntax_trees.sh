#!/bin/sh
set -euo pipefail

readonly CURRENT_DIR=$(dirname "$0")
readonly RELATIVE_PATH_TO_SYNTAX_TREE_SPEC='../pytch/syntax_tree.txt'
readonly RELATIVE_PATH_TO_OUTPUT='../pytch'

cd "$(dirname "$0")"

<"$RELATIVE_PATH_TO_SYNTAX_TREE_SPEC" './generate_greencst.py' >"$RELATIVE_PATH_TO_OUTPUT/greencst.py"
poetry run black "$RELATIVE_PATH_TO_OUTPUT/greencst.py"
<"$RELATIVE_PATH_TO_SYNTAX_TREE_SPEC" './generate_redcst.py' >"$RELATIVE_PATH_TO_OUTPUT/redcst.py"
poetry run black "$RELATIVE_PATH_TO_OUTPUT/redcst.py"
