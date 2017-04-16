import os.path

from pyparsing import ParseException, ParseSyntaxException

from pytch.codegen import compile_ast
from pytch.grammar import parse

PYTCH_EXTENSION = ".pytch"
PYTHON_EXTENSION = ".py"


class SourceCodeError(Exception):
    def __init__(
        self,
        message,
        file_path,
        line_no,
        column_no,
        line_contents,
        error_span,
    ):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.line_no = line_no
        self.column_no = column_no
        self.line_contents = line_contents
        self.error_span = error_span


def compile_files(files):
    all_files = set(gather_files(files))
    asts = {
        file_path: get_ast(file_path)
        for file_path in all_files
    }

    for filename, ast in asts.items():
        out_filename = get_compiled_filename(filename)
        compiled_code = compile_ast(ast)
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


def get_ast(file_path):
    with open(file_path) as f:
        file_contents = f.read()

    try:
        return parse(file_contents)
    except (ParseException, ParseSyntaxException) as e:
        lines = file_contents.split("\n")
        line_contents = lines[e.lineno - 1]
        column_index = e.column - 1
        error_span = (column_index, column_index + 1)
        raise SourceCodeError(
            message=e.msg,
            file_path=file_path,
            line_no=e.lineno,
            column_no=e.column,
            line_contents=line_contents,
            error_span=error_span,
        )


def get_compiled_filename(filename):
    assert filename.endswith(PYTCH_EXTENSION)
    return filename[:-len(PYTCH_EXTENSION)] + PYTHON_EXTENSION
