#!/usr/bin/env python3
"""Generate the syntax tree data structures from their spec.

Run `generate_syntax_trees.sh` rather than this script directly.
"""
import sys
import textwrap
from typing import List, Mapping, Optional

from sttools import Child, get_exports, get_node_types, NodeType, TOKEN_TYPE


PREAMBLE = """\
\"\"\"NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
\"\"\"
from typing import List, Optional, Sequence, Union

import pytch.greencst as greencst
from .lexer import Token


class Node:
    def __init__(
        self,
        parent: Optional["Node"],
    ) -> None:
        self._parent = parent

    @property
    def parent(self) -> Optional["Node"]:
        return self._parent

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `children`",
        )

    @property
    def full_width(self) -> int:
        raise NotImplementedError(
            f"class {self.__class__.__name__} should implement `full_width`",
        )


"""


def main() -> None:
    lines = sys.stdin.read().splitlines()
    sections = get_node_types(lines)
    class_defs = [
        get_class_def(name, sections, children)
        for name, children
        in sections.items()
    ]
    exports = get_exports(sections.keys())
    sys.stdout.write(PREAMBLE)
    sys.stdout.write("\n\n".join(class_defs) + "\n\n")
    sys.stdout.write(get_green_to_red_node_map(sections) + "\n\n")
    sys.stdout.write(exports)


def get_green_to_red_node_map(
    node_types: Mapping[NodeType, List[Child]],
) -> str:
    map = "GREEN_TO_RED_NODE_MAP = {\n"
    for node_type in node_types:
        node_class = node_type.name
        map += f"    greencst.{node_class}: {node_class},\n"
    map += "}\n"
    return map


def get_class_def(
    node_type: NodeType,
    node_types: Mapping[NodeType, List[Child]],
    children: List[Child],
) -> str:
    node_types = {
        NodeType(name=k.name, supertype=None): v
        for k, v in node_types.items()
    }

    def get_leaf_children(base_type: NodeType) -> Optional[List[Child]]:
        children = node_types.get(base_type, [])
        if len(children) > 0:
            return children
        return None

    # class name
    class_header = f"class {node_type.name}"
    if node_type.supertype:
        class_header += f"({node_type.supertype})"
    class_header += ":\n"

    if not children:
        class_body = textwrap.indent("pass\n", prefix="    ")
        return class_header + class_body

    # __init__
    init_header = "def __init__(\n"
    init_header += f"    self,\n"
    init_header += f"    parent: Optional[Node],\n"
    init_header += f"    origin: greencst.{node_type.name},\n"
    init_header += f"    offset: int,\n"
    init_header += f") -> None:\n"
    init_header = textwrap.indent(init_header, prefix="    ")
    class_header += init_header

    # __init__ body
    init_body = "super().__init__(parent)\n"
    init_body += "self.origin = origin\n"
    init_body += "self.offset = offset\n"
    for child in children:
        if child.base_type != TOKEN_TYPE:
            init_body += f"self._{child.name}: {child.type.name} = None\n"
    init_body = textwrap.indent(init_body, prefix="    " * 2)
    class_header += init_body

    # class body
    class_body = ""
    for i, child in enumerate(children):
        property_body = "\n"
        property_body += "@property\n"
        property_body += f"def {child.name}(self) -> {child.type.name}:\n"

        leaf_children = get_leaf_children(child.base_type)
        if child.base_type == TOKEN_TYPE:
            # Tokens don't need to construct a new red node.
            property_body += f"    return self.origin.{child.name}\n"
        else:
            property_body += f"    if self.origin.{child.name} is None:\n"
            property_body += f"        return None\n"

            property_body += f"    if self._{child.name} is not None:\n"
            property_body += f"        return self._{child.name}\n"

            property_body += f"    offset = (\n"
            property_body += f"        self.offset\n"
            for previous_child in children[:i]:
                child_width = (
                    "+ (\n"
                    + f"    self.{previous_child.name}.full_width\n"
                    + f"    if self.{previous_child.name} is not None else\n"
                    + f"    0\n"
                    + ")\n"
                )
                property_body += textwrap.indent(child_width, "    " * 2)
            property_body += f"    )\n"

            if leaf_children is not None:
                # A specific class to construct, like `FunctionCallExpr`.
                property_body += f"    result = {child.base_type.name}(\n"
                property_body += f"        parent=self,\n"
                property_body += f"        origin=self.origin.{child.name},\n"
                property_body += f"        offset=offset,\n"
                property_body += f"    )\n"
            else:
                # An abstract class to construct, like `Expr`, whose concrete
                # implementation could be one of many subclasses.
                property_body += f"    result = GREEN_TO_RED_NODE_MAP[" + \
                    f"self.origin.{child.name}.__class__](\n"
                property_body += f"        parent=self,\n"
                property_body += f"        origin=self.origin.{child.name},\n"
                property_body += f"        offset=offset,\n"
                property_body += f"    )\n"

            property_body += f"    self._{child.name} = result\n"
            property_body += f"    return result\n"

        class_body += textwrap.indent(property_body, prefix="    ")

    children_prop_body = "\n"
    children_prop_body += "@property\n"
    children_prop_body += "def full_width(self) -> int:\n"
    children_prop_body += "    return self.origin.full_width\n"

    children_prop_body += "\n"
    children_prop_body += f"@property\n"
    children_prop_body += \
        f"def children(self) -> List[Optional[Union[Token, Node]]]:\n"
    children_prop_body += f"    return [\n"
    for child in children:
        if child.is_sequence_type:
            children_prop_body += f"        *self.{child.name},\n"
        elif child.is_optional_sequence_type:
            children_prop_body += (
                f"        *(self.{child.name} " +
                f"if self.{child.name} is not None else []),\n"
            )
        else:
            children_prop_body += f"        self.{child.name},\n"
    children_prop_body += "    ]\n"
    class_body += textwrap.indent(children_prop_body, prefix="    ")

    return class_header + class_body


if __name__ == "__main__":
    main()
