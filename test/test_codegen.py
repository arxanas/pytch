import importlib.util

import pytest

from utils import find_tests, generate

from pytch.codegen import compile_ast
from pytch.grammar import parse


def _get_codegen_tests():
    return find_tests("codegen")


def _make_code(file_contents, capsys, tmpdir):
    code = compile_ast(parse(file_contents))
    temp_file = tmpdir.join("test.py")
    temp_file.write(code)

    # http://stackoverflow.com/a/67692/344643
    spec = importlib.util.spec_from_file_location("test", str(temp_file))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    out, _ = capsys.readouterr()
    return out


@pytest.mark.parametrize(
    "input_filename,output_filename",
    _get_codegen_tests(),
)
def test_codegen(capsys, tmpdir, input_filename, output_filename):
    with open(input_filename) as input_file:
        input = input_file.read()
    with open(output_filename) as output_file:
        output = output_file.read()
    assert _make_code(input, capsys, tmpdir) == output


@pytest.mark.generate
def test_generate_code_output(capsys, tmpdir):
    def make_code(file_contents):
        return _make_code(file_contents, capsys, tmpdir)
    generate(_get_codegen_tests(), make_code)
