"""Binds name references to variable declarations in the AST.

In a valid program, every `IdentifierExpr` refers to at least one
`VariablePattern` somewhere. (In a pattern-match, there may be more than one
source `VariablePattern`.)
"""
from typing import List, Mapping, Optional, Tuple

import attr
import distance

from . import FileInfo, Range
from .errors import Error, ErrorCode, Note, Severity
from .redcst import (
    IdentifierExpr,
    LetExpr,
    Node,
    Pattern,
    SyntaxTree,
    VariablePattern,
)


GLOBAL_SCOPE: Mapping[str, List[VariablePattern]] = {
    "map": [],
    "filter": [],
    "print": [],
}


@attr.s(auto_attribs=True, frozen=True)
class Bindation:
    bindings: Mapping[IdentifierExpr, List[VariablePattern]]
    errors: List[Error]

    def get(
        self,
        node: IdentifierExpr,
    ) -> Optional[List[VariablePattern]]:
        return self.bindings.get(node)


def get_names_bound_by_node(
    node: Node,
) -> Mapping[str, List[VariablePattern]]:
    if isinstance(node, LetExpr):
        n_pattern = node.n_pattern
        return get_names_bound_by_pattern(n_pattern)
    else:
        return {}


def get_names_bound_by_pattern(
    pattern: Optional[Pattern],
) -> Mapping[str, List[VariablePattern]]:
    if pattern is None:
        return {}

    if isinstance(pattern, VariablePattern):
        t_identifier = pattern.origin.t_identifier
        if t_identifier is None:
            return {}
        name = t_identifier.text
        return {name: [pattern]}
    else:
        assert False, f"Unhandled pattern type: {pattern.__class__.__name__}"


def bind(file_info: FileInfo, syntax_tree: SyntaxTree) -> Bindation:
    def bind_node(
        node: Node,
        names_in_scope: Mapping[str, List[VariablePattern]],
    ) -> Tuple[Mapping[IdentifierExpr, List[VariablePattern]], List[Error]]:
        names_in_scope = {**names_in_scope, **get_names_bound_by_node(node)}

        bindings = {}
        errors = []
        if isinstance(node, IdentifierExpr):
            node_identifier = node.t_identifier
            if node_identifier is not None:
                name = node_identifier.text
                binding = names_in_scope.get(name)
                if binding is not None:
                    bindings[node] = binding
                else:
                    suggestions = [
                        candidate
                        for candidate in names_in_scope
                        if distance.levenshtein(name, candidate) <= 2
                    ]
                    notes = []
                    for suggestion in suggestions:
                        suggestion_nodes = names_in_scope.get(suggestion)
                        range: Optional[Range]
                        if suggestion_nodes:
                            range = file_info.get_range_from_offset_range(
                                suggestion_nodes[0].offset_range,
                            )
                            location = ", defined here"
                        else:
                            range = None
                            location = " (a builtin)"
                        notes.append(Note(
                            file_info=file_info,
                            message=f"Did you mean `{suggestion}`{location}?",
                            range=range,
                        ))

                    errors.append(Error(
                        file_info=file_info,
                        code=ErrorCode.UNBOUND_NAME,
                        severity=Severity.ERROR,
                        message=(
                            f"I couldn't find a variable " +
                            f"in the current scope with the name `{name}`."
                        ),
                        notes=notes,
                        range=file_info.get_range_from_offset_range(
                            node.offset_range,
                        )
                    ))

        for child in node.children:
            if isinstance(child, Node):
                (child_bindings, child_errors) = \
                    bind_node(node=child, names_in_scope=names_in_scope)
                bindings.update(child_bindings)
                errors.extend(child_errors)

        return (bindings, errors)

    (bindings, errors) = bind_node(
        node=syntax_tree,
        names_in_scope=GLOBAL_SCOPE,
    )
    return Bindation(
        bindings=bindings,
        errors=errors,
    )
