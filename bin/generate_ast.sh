#!/bin/sh
set -euo pipefail

readonly CURRENT_DIR=$(dirname "$0")
readonly RELATIVE_PATH_TO_AST='../pytch/ast.txt'
readonly RELATIVE_PATH_TO_OUTPUT='../pytch'

cd "$(dirname "$0")"

<"$RELATIVE_PATH_TO_AST" './generate_greenast.py' >"$RELATIVE_PATH_TO_OUTPUT/greenast.py"
<"$RELATIVE_PATH_TO_AST" './generate_redast.py' >"$RELATIVE_PATH_TO_OUTPUT/redast.py"
