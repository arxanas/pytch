from pytch.lexer import lex
from pytch.naming import name
from pytch.parser import parse


def test_naming():
    # Not sure of a good way to test this, so I'll just test that this doesn't
    # throw an exception.
    source_code = """let foo = 1
let bar = foo"""
    tokens = lex(source_code=source_code).tokens
    ast = parse(source_code=source_code, tokens=tokens)
    name(ast)
