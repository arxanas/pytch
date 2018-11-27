"""Binds name references to variable declarations in the AST.

In a valid program, every `IdentifierExpr` refers to at least one
`VariablePattern` somewhere. (In a pattern-match, there may be more than one
source `VariablePattern`.)
"""
from typing import Dict, List, Mapping, Optional, Tuple

import attr
import distance

from .errors import Error, ErrorCode, Note, Severity
from .redcst import IdentifierExpr, LetExpr, Node, Pattern, SyntaxTree, VariablePattern
from .utils import FileInfo, Range


GLOBAL_SCOPE: Mapping[str, List[VariablePattern]] = {
    "map": [],
    "filter": [],
    "print": [],
    "True": [],
    "False": [],
    "None": [],
}


@attr.s(auto_attribs=True, frozen=True)
class Bindation:
    bindings: Mapping[IdentifierExpr, List[VariablePattern]]
    errors: List[Error]

    def get(self, node: IdentifierExpr) -> Optional[List[VariablePattern]]:
        return self.bindings.get(node)


def get_names_bound_for_let_expr_value(
    n_let_expr: LetExpr,
) -> Mapping[str, List[VariablePattern]]:
    """Get the names bound in a let-expression's value.

    That is, for function let expressions, get the names of the parameters
    that should be bound inside the function's definition. For example:

        let foo(bar, baz) =
          bar + baz  # bar and baz should be bound here...
        foo(1, 2) # ...but not here.

    TODO: Additionally, if the function is marked as `rec`, bind the function
    name itself inside the function body.
    """
    n_parameter_list = n_let_expr.n_parameter_list
    if n_parameter_list is None:
        return {}

    parameters = n_parameter_list.parameters
    if parameters is None:
        return {}

    bindings: Dict[str, List[VariablePattern]] = {}
    for parameter in parameters:
        n_pattern = parameter.n_pattern
        if n_pattern is not None:
            # TODO: warn about overlapping name-bindings.
            bindings.update(get_names_bound_by_pattern(n_pattern))
    return bindings


def get_names_bound_for_let_expr_body(
    n_let_expr: LetExpr,
) -> Mapping[str, List[VariablePattern]]:
    if n_let_expr.n_pattern is None:
        return {}
    return get_names_bound_by_pattern(n_let_expr.n_pattern)


def get_names_bound_by_pattern(
    n_pattern: Pattern,
) -> Mapping[str, List[VariablePattern]]:
    if isinstance(n_pattern, VariablePattern):
        t_identifier = n_pattern.origin.t_identifier
        if t_identifier is None:
            return {}
        name = t_identifier.text
        return {name: [n_pattern]}
    else:
        assert False, f"Unhandled pattern type: {n_pattern.__class__.__name__}"


def bind(
    file_info: FileInfo,
    syntax_tree: SyntaxTree,
    global_scope: Mapping[str, List[VariablePattern]],
) -> Bindation:
    def get_binding_referred_to_by_name(
        node: Node, name: str, names_in_scope: Mapping[str, List[VariablePattern]]
    ) -> Tuple[Optional[List[VariablePattern]], List[Error]]:
        binding = names_in_scope.get(name)
        if binding is not None:
            return (binding, [])

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
                    suggestion_nodes[0].offset_range
                )
                location = ", defined here"
            else:
                range = None
                location = " (a builtin)"
            notes.append(
                Note(
                    file_info=file_info,
                    message=f"Did you mean '{suggestion}'{location}?",
                    range=range,
                )
            )

        errors = [
            Error(
                file_info=file_info,
                code=ErrorCode.UNBOUND_NAME,
                severity=Severity.ERROR,
                message=(
                    f"I couldn't find a binding "
                    + f"in the current scope with the name '{name}'."
                ),
                notes=notes,
                range=file_info.get_range_from_offset_range(node.offset_range),
            )
        ]
        return (None, errors)

    def bind_node(
        node: Node, names_in_scope: Mapping[str, List[VariablePattern]]
    ) -> Tuple[Mapping[IdentifierExpr, List[VariablePattern]], List[Error]]:
        bindings = {}
        errors = []
        if isinstance(node, IdentifierExpr):
            node_identifier = node.t_identifier
            if node_identifier is not None:
                name = node_identifier.text
                (
                    identifier_binding,
                    identifier_errors,
                ) = get_binding_referred_to_by_name(
                    node=node, name=name, names_in_scope=names_in_scope
                )
                if identifier_binding is not None:
                    bindings[node] = identifier_binding
                errors.extend(identifier_errors)

        if isinstance(node, LetExpr):
            if node.n_value is not None:
                value_names_in_scope = {
                    **names_in_scope,
                    **get_names_bound_for_let_expr_value(node),
                }
                (value_bindings, value_errors) = bind_node(
                    node=node.n_value, names_in_scope=value_names_in_scope
                )
                bindings.update(value_bindings)
                errors.extend(value_errors)

            if node.n_body is not None:
                body_names_in_scope = {
                    **names_in_scope,
                    **get_names_bound_for_let_expr_body(node),
                }
                (body_bindings, body_errors) = bind_node(
                    node=node.n_body, names_in_scope=body_names_in_scope
                )
                bindings.update(body_bindings)
                errors.extend(body_errors)
        else:
            for child in node.children:
                if isinstance(child, Node):
                    (child_bindings, child_errors) = bind_node(
                        node=child, names_in_scope=names_in_scope
                    )
                    bindings.update(child_bindings)
                    errors.extend(child_errors)

        return (bindings, errors)

    (bindings, errors) = bind_node(node=syntax_tree, names_in_scope=global_scope)
    return Bindation(bindings=bindings, errors=errors)
