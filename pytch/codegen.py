from .ast import (
    FunctionCallExpr,
    Ident,
    IntLiteral,
    LetFuncStmt,
    LetInExpr,
    LetPlainStmt,
    Program,
    StringLiteral,
    TypeStmt,
    ValStmt,
)


class Scope:
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

    def __getitem__(self, name):
        return self._names[name]

    def __setitem__(self, name):
        self._names[name] = name

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


class Env:
    def __init__(self):
        self.naming_scope = Scope(parent=None)
        self.emit_scope = Scope(parent=None)
        self.references = {}


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


def compile_ast(ast):
    env = Env()
    naming(env, ast)
    code = emit(env, ast)
    lines_of_code = code.setup + code.code
    return "".join(i + "\n" for i in lines_of_code)


def naming(env, node):
    def recurse(node):
        return emit(env, node)

    if isinstance(node, Program):
        for statement in node.statements:
            recurse(statement)

    elif isinstance(node, ValStmt):
        env.current_scope[node.ident.value] = node

    elif isinstance(node, TypeStmt):
        env.current_scope[node.ident.value] = node

    elif isinstance(node, LetPlainStmt):
        env.current_scope[node.ident.value] = node

    elif isinstance(node, LetFuncStmt):
        env.current_scope[node.ident.value] = node

    else:
        assert False, "unhandled naming: {}".format(node.__class__.__name__)


def emit(env, node):
    def recurse(node):
        return emit(env, node)

    if isinstance(node, Program):
        code = [recurse(statement) for statement in node.statements]
        return Code(
            node=node,
            setup=_sum_lists(i.setup for i in code),
            code=_sum_lists(i.code for i in code),
            expr=None,
        )

    elif (
        isinstance(node, ValStmt) or
        isinstance(node, TypeStmt)
    ):
        return Code.no_code(node)

    elif isinstance(node, LetPlainStmt):
        name = recurse(node.ident)
        value = recurse(node.value)
        code = ["{} = {}".format(name.expr, value.expr)]
        return Code(
            node=node,
            setup=_sum_lists([
                name.setup,
                name.code,
                value.setup,
                value.code,
            ]),
            code=code,
            expr=name.expr,
        )

    elif isinstance(node, LetFuncStmt):
        name = recurse(node.ident)
        idents = [recurse(param) for param in node.params]
        body = recurse(node.value)
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
            node=node,
            setup=setup,
            code=code,
            expr=name.expr,
        )

    elif isinstance(node, LetInExpr):
        let_stmt = recurse(node.let_stmt)
        expr = recurse(node.expr)
        setup = let_stmt.setup + expr.setup
        code = let_stmt.code + expr.code
        return Code(
            node=node,
            setup=setup,
            code=code,
            expr=expr.expr,
        )

    elif isinstance(node, FunctionCallExpr):
        name = recurse(node.ident)
        args = [recurse(arg) for arg in node.args]
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
            node=node,
            setup=setup,
            code=[],
            expr=expr,
        )

    elif isinstance(node, Ident):
        return Code(
            node=node,
            setup=[],
            code=[],
            expr=node.value,
        )

    elif isinstance(node, IntLiteral):
        return Code(
            node=node,
            setup=[],
            code=[],
            expr=repr(node.value),
        )

    elif isinstance(node, StringLiteral):
        return Code(
            node=node,
            setup=[],
            code=[],
            expr=repr(node.value),
        )

    else:
        assert False, "unhandled emit: {}".format(node.__class__.__name__)


def _indent(string):
    return "\n".join("    " + i for i in string.split("\n"))


def _sum_lists(lists):
    ret = []
    for i in lists:
        ret.extend(i)
    return ret
