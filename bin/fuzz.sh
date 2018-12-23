#!/bin/bash

main() {
    cd "$(dirname "$0")"/..
    mkdir -p fuzz/initial
    cp test/{lexer,parser}/*.pytch fuzz/initial

    cd fuzz
    poetry run py-afl-fuzz -m 400 -i initial -o results -- python -m pytch.fuzz @@
}

main
