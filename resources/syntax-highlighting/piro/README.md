# About

Piro is a syntax highlighter generator written in Python, inspired by
[Iro](https://eeyo.io/iro/). It's used in Pytch to generate Pygments and
Textmate grammars from a base specification.

# Usage

Install the package, then run

```sh
piro path/to/input.yaml -o pygments
```

to generate a Pygments lexer (written to stdout).

Much of the concepts used in the input YAML file are similar to Iro, so you
can consult its documentation. See `pytch-grammar.yaml` for an example.
