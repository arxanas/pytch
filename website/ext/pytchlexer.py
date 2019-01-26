from pygments.lexer import RegexLexer
import pygments.token as token


class PytchLexer(RegexLexer):
    name = "pytch"
    filenames = ["*.pytch"]

    tokens = {
        "single-quoted-string__0": [
            ("(\\\\'|[^'])", token.String.Single),
            ("'", token.String.Single, "#pop"),
        ],
        "double-quoted-string__1": [
            ('(\\\\"|[^"])', token.String.Double),
            ('"', token.String.Double, "#pop"),
        ],
        "root": [
            ("\\s+", token.Whitespace),
            ("\\#[^\\n]*", token.Comment),
            ("and|def|else|if|let|or|then", token.Keyword),
            ("[a-zA-Z_][a-zA-Z0-9_]*", token.Name),
            ("[0-9]+", token.Number),
            ("=|=>|,|\\+|\\-|\\(|\\)", token.Punctuation),
            ("'", token.String.Single, "single-quoted-string__0"),
            ('"', token.String.Double, "double-quoted-string__1"),
        ],
    }


def setup(app) -> None:
    from sphinx.highlighting import lexers

    lexers["pytch"] = PytchLexer()
