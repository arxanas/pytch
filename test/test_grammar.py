from pytch.grammar import grammar


def test_grammar():
    ast = grammar.parse("""
val foo : int
let foo = 3
""")
    assert ast
