class AstNode:
    def __init__(self, text, location, tokens):
        """Save the information about the PyParsing token.

        TODO: As it is, it seems that every token saves the same `text`. If we
        want to actually get the text corresponding to a given AST node, we
        need to build it up by looking at the offsets and lengths of all the
        child tokens. This probably needs to be built up recursively, by
        specifying the length of the lowest level tokens (such as Idents) and
        then calculating the lengths of the AST nodes that consist of these
        tokens.

        :param str text: The full text of the source code.
        :param int location: The offset into the source code where this token
            started.
        :param list token: The list of tokens composing this token. They should
            have already been converted to AST nodes by this point.
        """
        self._text = text
        self._location = location
        self._tokens = tokens

    def __repr__(self):
        return "({} {})".format(
            self.__class__.__name__,
            " ".join(repr(i) for i in self._tokens),
        )


class Program(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.statements = tokens


class ValStmt(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        ident, type_expr = tokens
        self.ident = ident
        self.type_expr = type_expr


class FunctionCallExpr(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.ident, *self.args = tokens


class LetPlainStmt(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.ident, self.value = tokens


class LetFuncStmt(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.ident, *self.params, self.value = tokens


class LetInExpr(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.let_stmt, self.expr = tokens


class TypeStmt(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        if isinstance(tokens[0], Ident):
            self.ident, self.type_expr = tokens
        else:
            raise NotImplementedError(
                "not implemented: TypeExprAtom.__init__ for {}"
                .format(tokens)
            )


class TypeExprAtom(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.ident, = tokens


class FunctionTypeExpr(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        *self.params, self.return_type = tokens


class RecordTypeExpr(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.fields = tokens

    def __repr__(self):
        return "({} {})".format(
            self.__class__.__name__,
            " ".join(
                "(RecordField {} {})".format(*i)
                for i in self.fields
            ),
        )


class TupleTypeExpr(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.elements = tokens


class Ident(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.value, = tokens


class IntLiteral(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.value, = tokens
        self.value = int(self.value)

    def __repr__(self):
        return "(IntLiteral {})".format(repr(self.value))


class StringLiteral(AstNode):
    def __init__(self, text, location, tokens):
        super().__init__(text, location, tokens)
        self.value, = tokens

        # TODO: Handle backslash escape sequences.

        # Remove leading and trailing quotes. NOTE: This depends on the type of
        # the string being a double-quoted string.
        assert self.value[0] == "\""
        assert self.value[-1] == "\""
        self.value = self.value[1:-1]

    def __repr__(self):
        return "(StringLiteral {})".format(repr(self.value))
