import os.path

import pytest

from pytch.grammar import parse


def _get_parse_tests():
    current_dir = os.path.dirname(__file__)
    tests_dir = os.path.join(current_dir, "parse")
    tests = set(os.path.splitext(filename)[0]
                for filename in os.listdir(tests_dir)
                if filename.endswith(".pytch"))
    for test in tests:
        input_filename = os.path.join(tests_dir, f"{test}.pytch")
        output_filename = os.path.join(tests_dir, f"{test}.out")
        yield (input_filename, output_filename)


@pytest.mark.parametrize("input_filename,output_filename", _get_parse_tests())
def test_parse(input_filename, output_filename):
    with open(input_filename) as input_file:
        input = input_file.read()
    with open(output_filename) as output_file:
        output = output_file.read()

    ast = parse(input)
    assert _pretty_print_ast(ast) == output


@pytest.mark.generate
def test_generate_parse_output():
    # Don't parametrize so as not to clog up the test matrix with a bunch of
    # skipped tests.
    for input_filename, output_filename in _get_parse_tests():
        with open(input_filename) as input_file:
            input = input_file.read()
        print(f"parsing {input_filename}")
        ast = parse(input)
        ast = _pretty_print_ast(ast)
        if not os.path.exists(output_filename):
            with open(output_filename, "w") as output_file:
                output_file.write(ast)
        else:
            print(f"file exists, not generating: {output_filename}")


def _pretty_print_ast(ast):
    ast = repr(ast)
    printed = ""
    indent_level = -1
    # Assumes that there are no parentheses in strings, for example.
    for c in ast:
        if c == "(":
            # Remove trailing spaces.
            printed = printed.rstrip()
            if indent_level >= 0:
                printed += "\n"
            indent_level += 1
            printed += "  " * indent_level
        elif c == ")":
            indent_level -= 1
        printed += c
    printed += "\n"
    return printed
