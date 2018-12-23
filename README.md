[![Build Status](https://travis-ci.org/arxanas/pytch.svg?branch=master)](https://travis-ci.org/arxanas/pytch)

## Development

### Setup

The Pytch compiler is currently written in Python 3.7.

To install the development environment, run

```sh
$ poetry install
```

### Running

To launch the REPL:

```sh
$ poetry run pytch repl
```

To execute a file as a Pytch script:

```sh
$ poetry run pytch run file.pytch
```

### Updating the syntax trees

To modify the syntax tree node types, update `pytch/syntax_tree.txt`, then run:

```sh
$ ./bin/generate_syntax_trees.sh
```

### Fuzzing the parser

To run the fuzzer on the Pytch parser, first be sure that [the AFL
fuzzer][afl-fuzz] is installed (e.g. with `brew install afl-fuzz`). Next,
install the fuzzing dependencies:

  [afl-fuzz]: http://lcamtuf.coredump.cx/afl/

```sh
$ poetry install --extras fuzz
```

Then you can run:

```sh
$ ./bin/fuzz.sh
```
