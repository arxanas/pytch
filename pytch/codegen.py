"""Generate Python code from Pytch code.

Generates the AST for the Pytch code, then emits code for that AST.
"""
import contextlib


class Scope(object):
    """A scope for variables.

    A scope is a map from variable names to information about those variables.
    As we descend into the AST, we make scopes that may, for example, shadow
    variables from outer scopes.
    """
    def __init__(self, parent):
        """Initialize the scope with its parent scope.

        :param Scope|None parent: The parent scope of this scope. This is the
            scope that is used to look up variables if a given variable is not
            found in this scope.
        """
        self._symbols = {}
        self._parent = parent

    def make_symbol(self, preferred_name):
        """Produce a unique variable name.

        A variable name is "unique" if it is not the same as any variable in
        the current scope or in any parent scope.

        :param str preferred_name: The preferred name of the variable.
        :returns str: The preferred name, potentially suffixed with something
            if there is a name clash.
        """
        name = next(i for i in self._suggestions_for_name(preferred_name)
                    if not self._is_symbol_in_use(i))
        # TODO: Maybe associate information with that variable here.
        self._symbols[name] = None
        return name

    def _suggestions_for_name(self, name):
        yield name
        i = 1
        while True:
            yield "{}{}".format(name, i)

    def _is_symbol_in_use(self, name):
        if name in self._symbols:
            return True
        if self._parent:
            return self._parent._is_symbol_in_use(name)
        return False


class Env(object):
    def __init__(self):
        self.global_scope = Scope(parent=None)
        self.scopes = [self.global_scope]

    @property
    def current_scope(self):
        assert self.scopes
        return self.scopes[-1]

    @contextlib.contextmanager
    def scope(self):
        scope = Scope(parent=self.current_scope)
        self.scopes.append(scope)
        yield scope
        self.scopes.pop()


def compile_ast(filename, ast):
    ast = Program.from_node(ast)
    env = Env()
    code = ast.emit(env)
    lines_of_code = code.setup + code.code
    return "".join(i + "\n" for i in lines_of_code)


class Code(object):
    """The generated code corresponding to an AST node.

    :ivar Node node: The node that generated this code.
    :ivar list setup: The list of lines of code that should be inserted at the
        beginning of this scope.
    :ivar list code: The list of lines of code that should be inserted at the
        current position.
    :ivar str|None expr: A Python code snippet to execute that evaluates to the
        value of this code block, if any.
    """
    def __init__(self, node, setup, code, expr):
        self.node = node
        self.setup = setup
        self.code = code
        self.expr = expr

    def __repr__(self):
        return ("<Code node={node} setup={setup} code={code} expr={expr}>"
                .format(
                    node=repr(self.node),
                    setup=repr(self.setup),
                    code=repr(self.code),
                    expr=repr(self.expr),
                ))

    @classmethod
    def no_code(cls, node):
        return Code(
            node=node,
            setup=[],
            code=[],
            expr=None,
        )


class AstNode(object):
    def __init__(self, node):
        self.node = node

    def __repr__(self):
        raise NotImplementedError("__repr__ not implemented: '{}'"
                                  .format(self.__class__))

    def emit(self, env):
        raise NotImplementedError("emit not implemented: '{}'"
                                  .format(self.__class__))

    @classmethod
    def from_node(cls, node):
        raise NotImplementedError("from_node not implemented: '{}'"
                                  .format(cls.__name__))


class Program(AstNode):
    def __init__(self, node, statements):
        super(Program, self).__init__(node)
        self.statements = statements

    def __repr__(self):
        children = " ".join(repr(i) for i in self.statements)
        return "(Program {})".format(children)

    def emit(self, env):
        code = [i.emit(env) for i in self.statements]
        return Code(
            node=self,
            setup=_sum_lists(i.setup for i in code),
            code=_sum_lists(i.code for i in code),
            expr=None,
        )

    @classmethod
    def from_node(cls, node):
        statements = [TopLevelStmt.from_node(i)
                      for i in _traverse(node)
                      if i.expr_name == "toplevel_stmt"]
        return cls(node, statements)


class TopLevelStmt(AstNode):
    @classmethod
    def from_node(cls, node):
        while node.expr_name not in ["val_stmt", "let_stmt"]:
            node = _filter_whitespace(node.children)[0]

        if node.expr_name == "val_stmt":
            return ValStmt.from_node(node)
        elif node.expr_name == "let_stmt":
            return LetStmt.from_node(node)
        else:
            assert False


class ValStmt(AstNode):
    def __init__(self, node, ident, type_sig):
        super(ValStmt, self).__init__(node)
        self.ident = ident
        self.type_sig = type_sig

    def __repr__(self):
        return "(Val {} {})".format(repr(self.ident), repr(self.type_sig))

    def emit(self, env):
        return Code.no_code(self.node)

    @classmethod
    def from_node(cls, node):
        _, ident, _, type_sig = _filter_whitespace(node.children)
        return cls(node, Ident.from_node(ident), TypeSig.from_node(type_sig))


class LetStmt(AstNode):
    @classmethod
    def from_node(cls, node):
        stmt = node.children[0]
        stmt_types = {
            "plain_let_stmt": PlainLetStmt,
            "func_let_stmt": FuncLetStmt,
            "let_in_stmt": LetInStmt,
        }
        return stmt_types[stmt.expr_name].from_node(stmt)


class PlainLetStmt(AstNode):
    def __init__(self, node, name, value):
        super(PlainLetStmt, self).__init__(node)
        self.name = name
        self.value = value

    def __repr__(self):
        return "(PlainLet {} {})".format(repr(self.name), repr(self.value))

    def emit(self, env):
        name = self.name.emit(env)
        value = self.value.emit(env)
        code = ["{} = {}".format(name.expr, value.expr)]
        return Code(
            node=self,
            setup=_sum_lists([
                name.setup,
                name.code,
                value.setup,
                value.code,
            ]),
            code=code,
            expr=name.expr,
        )

    @classmethod
    def from_node(cls, node):
        children = _filter_whitespace(node.children)
        _, name, _, value = children
        return cls(node, Ident.from_node(name), Expr.from_node(value))


class FuncLetStmt(AstNode):
    def __init__(self, node, name, params, value):
        super(FuncLetStmt, self).__init__(node)
        self.name = name
        self.params = params
        self.value = value

    def __repr__(self):
        return "(FuncLet {} {} {})".format(
            repr(self.name),
            repr(self.params),
            repr(self.value),
        )

    def emit(self, env):
        name = self.name.emit(env)
        with env.scope():
            idents = [i.emit(env) for i in self.params]
            body = self.value.emit(env)
            body_code = body.code + ["return {}".format(body.expr)]
            setup = (
                name.setup
                + _sum_lists(i.setup for i in idents)
                + body.setup
            )
            code = name.code + ["def {}({}):".format(
                name.expr,
                ", ".join(i.expr for i in idents),
            )] + [_indent(i) for i in body_code]
        return Code(
            node=self,
            setup=setup,
            code=code,
            expr=name.expr,
        )

    @classmethod
    def from_node(cls, node):
        children = _filter_whitespace(node.children)
        _, name, params, _, value = children
        return cls(
            node,
            Ident.from_node(name),
            Params.from_node(params),
            Expr.from_node(value),
        )


class LetInStmt(AstNode):
    def __init__(self, node, let_stmt, expr):
        super(LetInStmt, self).__init__(node)
        self.let_stmt = let_stmt
        self.expr = expr

    def __repr__(self):
        return "(LetInStmt {} {})".format(
            repr(self.let_stmt),
            repr(self.expr),
        )

    def emit(self, env):
        let_stmt = self.let_stmt.emit(env)
        expr = self.expr.emit(env)
        setup = let_stmt.setup + expr.setup
        code = let_stmt.code + expr.code
        return Code(
            node=self,
            setup=setup,
            code=code,
            expr=expr.expr,
        )

    @classmethod
    def from_node(cls, node):
        children = _filter_whitespace(node.children)
        let_stmt, _, expr = children
        return cls(
            node,
            LetStmt.from_node(let_stmt),
            Expr.from_node(expr),
        )


class TypeSig(AstNode):
    def __init__(self, node, type_decls):
        super(TypeSig, self).__init__(node)
        self.type_decls = type_decls

    def __repr__(self):
        type_decls = " ".join(repr(i) for i in self.type_decls)
        return "(TypeSig {})".format(type_decls)

    @classmethod
    def from_node(cls, node):
        type_decls = [TypeDecl.from_node(i)
                      for i in _filter_whitespace(node.children)]
        return cls(node, type_decls)


class TypeDecl(AstNode):
    def __init__(self, node, ident=None, type_sig=None):
        super(TypeDecl, self).__init__(node)
        self.ident = ident
        self.type_sig = type_sig

    def __repr__(self):
        return "(TypeDecl {})".format(repr(self.ident))

    @classmethod
    def from_node(cls, node):
        if node.children[0].expr_name == "ident":
            node = node.children[0]
            return cls(node, ident=Ident.from_node(node))
        else:
            raise NotImplementedError(
                    "type decl for non-ident types not implemented: '{}'"
                    .format(node.expr_name))


class Ident(AstNode):
    def __init__(self, node, value):
        super(Ident, self).__init__(node)
        self.value = value

    def __repr__(self):
        return "(Ident {})".format(repr(self.value))

    def emit(self, env):
        return Code(
            node=self,
            setup=[],
            code=[],
            expr=self.value,
        )

    @classmethod
    def from_node(cls, node):
        assert node.expr_name == "ident"
        return cls(node, node.text)


class Params(AstNode):
    @staticmethod
    def from_node(node):
        return [Ident.from_node(i)
                for i in _traverse(node)
                if i.expr_name == "ident"]


class Expr(AstNode):
    def __init__(self, node):
        super(Expr, self).__init__(node)

    @classmethod
    def from_node(cls, node):
        child = _first_non_trivial_node(node.children)
        expr_types = {
            "int_literal": IntLiteral,
            "string_literal": StringLiteral,
            "ident": Ident,
            "function_call": FunctionCall,
            "expr": Expr,
            "let_in_stmt": LetInStmt,
        }
        try:
            expr_type = expr_types[child.expr_name]
        except KeyError:
            raise NotImplementedError("expr not implemented: '{}'"
                                      .format(child.expr_name))
        return expr_type.from_node(child)


class IntLiteral(AstNode):
    def __init__(self, node, value):
        super(IntLiteral, self).__init__(node)
        self.value = value

    def __repr__(self):
        return "(IntLiteral {})".format(repr(self.value))

    def emit(self, env):
        return Code(
            node=self,
            setup=[],
            code=[],
            expr=repr(self.value),
        )

    @classmethod
    def from_node(cls, node):
        value = int(node.text)
        return cls(node, value)


class StringLiteral(AstNode):
    def __init__(self, node, value):
        super(StringLiteral, self).__init__(node)
        self.value = value

    def __repr__(self):
        return "(StringLiteral {})".format(repr(self.value))

    def emit(self, env):
        return Code(
            node=self,
            setup=[],
            code=[],
            expr=repr(self.value),
        )

    @classmethod
    def from_node(cls, node):
        # Get node in between quotes.
        node = node.children[1]
        value = node.text
        return cls(node, value)


class FunctionCall(AstNode):
    def __init__(self, node, name, args):
        super(FunctionCall, self).__init__(node)
        self.name = name
        self.args = args

    def __repr__(self):
        return "(FunctionCall {} {})".format(
            repr(self.name),
            " ".join(repr(i) for i in self.args),
        )

    def emit(self, env):
        name = self.name.emit(env)
        args = [i.emit(env) for i in self.args]
        setup = name.setup + _sum_lists(i.setup for i in args)
        assert not any(i.code for i in args), (
            "Not implemented: we need to store args into temporary " +
            "variables if they generate any appreciable amount of code."
        )
        expr = "{}({})".format(
            name.expr,
            ", ".join(i.expr for i in args),
        )
        return Code(
            node=self,
            setup=setup,
            code=[],
            expr=expr,
        )

    @classmethod
    def from_node(cls, node):
        children = _filter_whitespace(node.children)
        name = Ident.from_node(children[0])
        args = [Expr.from_node(i) for i in children[1:]]
        return FunctionCall(node, name, args)


def _indent(string):
    return "\n".join("    " + i for i in string.split("\n"))


def _traverse(node):
    yield node
    for i in node.children:
        yield from _traverse(i)


def _first_non_trivial_node(nodes):
    queue = list(nodes)
    while queue:
        node = queue.pop()
        if node.expr_name and node.expr_name != "_":
            return node
        queue.extend(node.children)
    assert False, "no non-trivial node underneath node: {}".format(node)


def _filter_whitespace(children):
    return [i for i in children
            if i.expr_name != "_"
            if i.text]


def _lines_to_str(lines):
    return "".join(i + "\n" for i in lines)


def _sum_lists(lists):
    ret = []
    for i in lists:
        ret.extend(i)
    return ret
