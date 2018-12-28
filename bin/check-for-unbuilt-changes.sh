#!/bin/bash
set -euo pipefail

make clean
make
if [[ "$(git status --porcelain | grep -E -v '\.doctree$')" != '' ]]; then
    tput bold
    tput setaf 1
    echo 'Error: There were unbuilt changes in this commit.'
    echo 'Note: changes to *.doctree files are ignored for this purpose, although they may be present in the diff below.'
    echo 'Git diff:'
    tput sgr0
    git diff
    exit 1
fi
