"""Run the naming phase on the syntax tree.

In the naming phase, we essentially attach a `scope` to every node in the
syntax tree. The node can then look up names in that scope. Most scopes are
empty. Some constructs, such as `let`-expressions, introduce new names into
their scopes.

The scopes form a tree mirroring the structure of the AST. When looking up a
name in a scope, if it is not found in the current scope, we search upward in
the scope hierarchy until the name is found or until we reach the top of the
tree.

Each name is associated with the AST node that introduced it.

Scopes are immutable.
"""
from typing import Dict, Mapping, Optional

from .parser import Ast, LetExpr, LetStatement, Node, VariablePattern


class Scope:
    def __init__(
        self,
        parent: Optional["Scope"],
        names: Mapping[str, Node],
    ) -> None:
        self._parent = parent
        self._names = names

    def lookup(self, name: str) -> Optional[Node]:
        if name in self._names:
            return self._names[name]
        if self._parent:
            return self._parent.lookup(name)
        return None


def get_names_declared_by(node: Node) -> Mapping[str, Node]:
    raise NotImplementedError()
    if isinstance(node, VariablePattern):
        return node.t_identifier
    else:
        raise ValueError(f"Node of type {type(node)} does not declare names")


def name_node(parent: Optional[Node], node: Node) -> Mapping[Node, Scope]:
    scope_map = {}

    if isinstance(node, Ast):
        names: Dict[str, Node] = {}
        for child in node.children:
            assert isinstance(child, LetStatement)
            # TODO: Raise an error when duplicate names are found.
            names.update(get_names_declared_by(child.n_pattern))
        scope = Scope(parent=None, names=names)
        for child in node.children:
            if isinstance(child, Node):
                scope_map[child] = scope

    elif isinstance(node, LetExpr):
        pass

    return scope_map


def name(ast: Ast) -> Mapping[Node, Scope]:
    pass


__all__ = ["name", "Scope"]
