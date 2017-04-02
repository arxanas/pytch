## Development

### Setup

The Pytch compiler is currently written in Python 3.6.

To install the development packages, run

```sh
$ pip install -r requirements-dev.txt
```

### Creating parser tests

The grammar can be found in `pytch/grammar.py`. Most parser changes are changes
to the grammar, so this is where they would go.

Tests for the parser are in `test/parse/`. A parser test is a `.pytch` file with
a corresponding `.out` file that contains the AST of the `.pytch` file. When you
add a `.pytch` file, you can generate a `.out` file by running

```sh
py.test -G
```

You can also delete any `.out` file and regenerate it from the current grammar
in this way.
