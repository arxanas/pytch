import pytest

from utils import find_tests, generate

from pytch.grammar import parse


def _get_parse_tests():
    return find_tests("parse")


def _make_parse(file_contents):
    return _pretty_print_ast(parse(file_contents))


def _pretty_print_ast(ast):
    ast = repr(ast)
    printed = ""
    indent_level = -1
    # Assumes that there are no parentheses in strings, for example.
    for c in ast:
        if c == "(":
            printed = printed.rstrip()
            if indent_level >= 0:
                printed += "\n"
            indent_level += 1
            printed += "  " * indent_level
        elif c == ")":
            printed = printed.rstrip()
            indent_level -= 1
        printed += c
    printed += "\n"
    return printed


@pytest.mark.parametrize("input_filename,output_filename", _get_parse_tests())
def test_parse(input_filename, output_filename):
    with open(input_filename) as input_file:
        input = input_file.read()
    with open(output_filename) as output_file:
        output = output_file.read()
    assert _make_parse(input) == output


@pytest.mark.generate
def test_generate_parse_output():
    generate(_get_parse_tests(), _make_parse)
