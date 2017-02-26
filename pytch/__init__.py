import os.path

from pytch.codegen import compile_ast
from pytch.grammar import grammar

PYTCH_EXTENSION = ".pytch"
PYTHON_EXTENSION = ".py"


def compile_files(files):
    asts = {
        i: get_ast(i)
        for i in gather_files(files)
    }
    for filename, ast in asts.items():
        out_filename = get_compiled_filename(filename)
        compiled_code = compile_ast(filename, ast)
        with open(out_filename, "w") as f:
            f.write(compiled_code)


def gather_files(files):
    def recurse_on_filename(filename):
        if not os.path.isdir(filename):
            yield filename
            return
        for root, dirs, files in os.walk(filename):
            for i in files:
                yield os.path.join(root, i)

    for i in files:
        for filename in recurse_on_filename(i):
            if filename.endswith(PYTCH_EXTENSION):
                yield filename


def get_ast(filename):
    with open(filename) as f:
        return grammar.parse(f.read())


def get_compiled_filename(filename):
    assert filename.endswith(PYTCH_EXTENSION)
    return filename[:-len(PYTCH_EXTENSION)] + PYTHON_EXTENSION
