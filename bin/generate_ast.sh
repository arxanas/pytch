#!/bin/sh
set -euo pipefail

readonly CURRENT_DIR=$(dirname "$0")
readonly GENERATE_SCRIPT='./generate_ast.py'
readonly RELATIVE_PATH_TO_AST='../pytch/ast.txt'
readonly RELATIVE_PATH_TO_OUTPUT='../pytch/ast.py'

cd "$(dirname "$0")"
<"$RELATIVE_PATH_TO_AST" "$GENERATE_SCRIPT" >"$RELATIVE_PATH_TO_OUTPUT"
