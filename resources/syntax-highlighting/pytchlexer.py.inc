def setup(app) -> None:
    from sphinx.highlighting import lexers
    lexers["pytch"] = PytchLexer()
