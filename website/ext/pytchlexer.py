from pygments import token
from pygments.lexer import RegexLexer
from sphinx.highlighting import lexers


# From https://stackoverflow.com/a/16470058
# Mostly just until we have a real syntax highlighter in place.
class PytchLexer(RegexLexer):
    name = "pytch"

    tokens = {"root": [(r".+", token.Text)]}


def setup(app) -> None:
    lexers["pytch"] = PytchLexer()
