#!/bin/bash

if [[ ! -d 'docs' ]]; then
    echo 'Docs must be built (try running `make`)'
    exit 1
fi

readonly FILES_WITH_SYNTAX_ERRORS=$(grep '<span class="err">' -R docs -l)
if [[ "$FILES_WITH_SYNTAX_ERRORS" != '' ]]; then
    tput bold
    tput setaf 1
    echo 'Error: There were documentation pages with syntax-highlighting errors:'
    tput sgr0
    echo "$FILES_WITH_SYNTAX_ERRORS"
    exit 1
fi
