from pygments.lexer import RegexLexer
import pygments.token as token


class PytchLexer(RegexLexer):
    name = "pytch"
    filenames = ["*.pytch"]

    tokens = {
        "root__0": [('\\"', token.String, "#pop"), (".", token.String)],
        "root": [
            ("\\s+", token.Whitespace),
            ("\\#[^\\n]*", token.Comment),
            ("and|else|if|let|or|then", token.Keyword),
            ("[a-zA-Z_][a-zA-Z0-9_]*", token.Name),
            ("[0-9]+", token.Number),
            ("=|,|\\+|\\-|\\(|\\)", token.Punctuation),
            (".", token.String, "root__0"),
        ],
    }


def setup(app) -> None:
    from sphinx.highlighting import lexers

    lexers["pytch"] = PytchLexer()
