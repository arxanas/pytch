#!/bin/bash

main() {
    cd "$(dirname "$0")"/..
    rm -r fuzz
    mkdir -p fuzz

    mkdir -p fuzz/initial
    cp test/{lexer,parser}/*.pytch fuzz/initial

    cd fuzz
    py-afl-fuzz -m 400 -i initial -o results -- python -m pytch.fuzz @@
}

main
