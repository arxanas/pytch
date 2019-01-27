from pygments import token
from pygments.lexer import RegexLexer
from sphinx.highlighting import lexers


class EbnfLexer(RegexLexer):
    name = "ebnf"

    tokens = {
        "root": [
            (r"\s+", token.Whitespace),
            (r"[$a-zA-Z-]+", token.Keyword),
            (r"::=", token.Operator),
            (r"\(", token.Punctuation),
            (r"\)", token.Punctuation),
            (r"\[", token.Punctuation),
            (r"\]", token.Punctuation),
            (r"\.\.\.", token.Operator),
            (r"\|", token.Operator),
            (r"\*", token.Operator),
            (r"\+", token.Operator),
            (r"'[^']*'", token.String),
            (r'"[^"]*"', token.String),
            (r"<", token.Text, "angle-bracket-descriptor"),
            (r"#.*", token.Comment),
        ],
        "angle-bracket-descriptor": [
            (r"\s+", token.Whitespace),
            (r"[a-zA-Z-]+", token.Text),
            (r"'[^']*'", token.String),
            (r'"[^"]*"', token.String),
            (r">", token.Text, "#pop"),
        ],
    }


def setup(app) -> None:
    lexers["ebnf"] = EbnfLexer()
