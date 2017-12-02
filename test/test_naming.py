from pytch import FileInfo
from pytch.lexer import lex
from pytch.naming import name
from pytch.parser import parse


def test_naming():
    # Not sure of a good way to test this, so I'll just test that this doesn't
    # throw an exception.
    source_code = """let foo = 1
let bar = foo"""
    file_info = FileInfo(file_path="dummy.pytch", source_code=source_code)
    tokens = lex(file_info=file_info).tokens
    ast = parse(file_info=file_info, tokens=tokens)
    name(ast)
