import contextlib


class Scope(object):
    def __init__(self, parent):
        self.symbols = {}
        self.code = ""
        self.parent = parent

    def make_symbol(self, preferred_name):
        name = next(i for i in self._suggestions_for_name(preferred_name)
                    if not self._is_symbol_in_use(i))
        self.symbols[name] = None
        return name

    def _suggestions_for_name(self, name):
        yield name
        i = 1
        while True:
            yield "{}{}".format(name, i)

    def _is_symbol_in_use(self, name):
        if name in self.symbols:
            return True
        if self.parent:
            return self.parent._is_symbol_in_use(name)
        return False


class Env(object):
    """The environment in which the code is generated.

    This lets generated code define variables local to the current scope, for
    example.
    """
    def __init__(self):
        self.global_scope = Scope(parent=None)
        self.scopes = [self.global_scope]

    @property
    def current_scope(self):
        assert self.scopes
        return self.scopes[-1]

    def add_code(self, code):
        self.current_scope.code += code.code
        return code

    @contextlib.contextmanager
    def scope(self):
        scope = Scope(parent=self.current_scope)
        self.scopes.append(scope)
        yield scope
        self.scopes.pop()
        self.current_scope.code += scope.code


def compile_ast(filename, ast):
    ast = Program.from_node(ast)
    env = Env()
    ast.emit(env)
    return env.global_scope.code


class Code(object):
    """The generated code corresponding to an AST node.

    :ivar str code: The generated Python code.
    :ivar str expr: A Python code snippet to execute that evaluates to the
        value of this code block.
    :ivar Node node: The node that generated this code.
    """
    def __init__(self, code, expr, node):
        self.code = code
        self.node = node
        self.expr = expr


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
        super().__init__(node)
        self.statements = statements

    def __repr__(self):
        children = " ".join(repr(i) for i in self.statements)
        return "(Program {})".format(children)

    def emit(self, env):
        for i in self.statements:
            i.emit(env)

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
        super().__init__(node)
        self.ident = ident
        self.type_sig = type_sig

    def __repr__(self):
        return "(Val {} {})".format(repr(self.ident), repr(self.type_sig))

    def emit(self, env):
        return

    @classmethod
    def from_node(cls, node):
        _, ident, _, type_sig = _filter_whitespace(node.children)
        return cls(node, Ident.from_node(ident), TypeSig.from_node(type_sig))


class LetStmt(AstNode):
    @classmethod
    def from_node(cls, node):
        stmt = node.children[0]
        assert stmt.expr_name in ["plain_let_stmt", "func_let_stmt"]
        if stmt.expr_name == "plain_let_stmt":
            return PlainLetStmt.from_node(stmt)
        elif stmt.expr_name == "func_let_stmt":
            return FuncLetStmt.from_node(stmt)


class PlainLetStmt(AstNode):
    def __init__(self, node, name, value):
        super().__init__(node)
        self.name = name
        self.value = value

    def __repr__(self):
        return "(PlainLet {} {})".format(repr(self.name), repr(self.value))

    def emit(self, env):
        name = self.name.emit(env).expr
        v = self.value.emit(env)
        code = v.code
        value = v.expr
        code += "{} = {}\n".format(name, value)
        code = Code(code=code, expr=name, node=self)
        return env.add_code(code)

    @classmethod
    def from_node(cls, node):
        children = _filter_whitespace(node.children)
        _, name, _, value = children
        return cls(node, Ident.from_node(name), Expr.from_node(value))


class FuncLetStmt(AstNode):
    def __init__(self, node, name, params, value):
        super().__init__(node)
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
        name = self.name.emit(env).expr
        with env.scope():
            params = self.params.emit(env)
            code = "def {}{}:\n".format(name, params.code)
            body = self.value.emit(env)
            code += _indent("return {}".format(body.expr)) + "\n"
        return env.add_code(Code(code=code, expr=name, node=self))

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


class TypeSig(AstNode):
    def __init__(self, node, type_decls):
        super().__init__(node)
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
        super().__init__(node)
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
        super().__init__(node)
        self.value = value

    def __repr__(self):
        return "(Ident {})".format(repr(self.value))

    def emit(self, env):
        return Code(code="", expr=self.value, node=self)

    @classmethod
    def from_node(cls, node):
        assert node.expr_name == "ident"
        return cls(node, node.text)


class Params(AstNode):
    def __init__(self, node, params):
        super().__init__(node)
        self.params = params

    def __repr__(self):
        params = " ".join(repr(i) for i in self.params)
        return "(Params {})".format(params)

    def emit(self, env):
        code = "({})".format(", ".join(i.emit(env).expr for i in self.params))
        return Code(code=code, expr="", node=self)

    @classmethod
    def from_node(cls, node):
        params = [Ident.from_node(i)
                  for i in _traverse(node)
                  if i.expr_name == "ident"]
        return cls(node, params)


class Expr(AstNode):
    def __init__(self, node):
        super().__init__(node)

    @classmethod
    def from_node(cls, node):
        child = _first_non_trivial_node(node.children)
        if child.expr_name == "int_literal":
            return IntLiteral.from_node(child)
        elif child.expr_name == "string_literal":
            return StringLiteral.from_node(child)
        elif child.expr_name == "ident":
            return Ident.from_node(child)
        elif child.expr_name == "function_call":
            return FunctionCall.from_node(child)
        elif child.expr_name == "expr":
            return Expr.from_node(child)
        else:
            raise NotImplementedError("expr not implemented: '{}'"
                                      .format(child.expr_name))


class IntLiteral(AstNode):
    def __init__(self, node, value):
        super().__init__(node)
        self.value = value

    def __repr__(self):
        return "(IntLiteral {})".format(repr(self.value))

    def emit(self, env):
        return Code(code="", expr=repr(self.value), node=self)

    @classmethod
    def from_node(cls, node):
        value = int(node.text)
        return cls(node, value)


class StringLiteral(AstNode):
    def __init__(self, node, value):
        super().__init__(node)
        self.value = value

    def __repr__(self):
        return "(StringLiteral {})".format(repr(self.value))

    def emit(self, env):
        return Code(code="", expr=repr(self.value), node=self)

    @classmethod
    def from_node(cls, node):
        # Get node in between quotes.
        node = node.children[1]
        value = node.text
        return cls(node, value)


class FunctionCall(AstNode):
    def __init__(self, node, name, args):
        super().__init__(node)
        self.name = name
        self.args = args

    def __repr__(self):
        return "(FunctionCall {} {})".format(
            repr(self.name),
            " ".join(repr(i) for i in self.args),
        )

    def emit(self, env):
        args = ", ".join("{}".format(i.emit(env).expr) for i in self.args)
        func_name = self.name.emit(env).expr
        code = "{}({})".format(func_name, args)
        return Code(code="", expr=code, node=self)

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
