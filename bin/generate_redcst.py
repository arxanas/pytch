#!/usr/bin/env python3
"""Generate the syntax tree data structures from their spec.

Run `generate_syntax_trees.sh` rather than this script directly.
"""
import sys
import textwrap
from typing import List

from sttools import Child, get_exports, get_node_types, NodeType


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
        raise NotImplementedError("should be implemented by children")


"""


def main() -> None:
    lines = sys.stdin.read().splitlines()
    sections = get_node_types(lines)
    class_defs = [
        get_class_def(name, children)
        for name, children
        in sections.items()
    ]
    exports = get_exports(sections.keys())
    sys.stdout.write(PREAMBLE)
    sys.stdout.write("\n\n".join(class_defs))
    sys.stdout.write("\n\n" + exports + "\n")


def get_class_def(node_type: NodeType, children: List[Child]) -> str:
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
    init_header += f") -> None:\n"
    init_header = textwrap.indent(init_header, prefix="    ")
    class_header += init_header

    # __init__ body
    init_body = "super().__init__(parent)\n"
    init_body += "self.origin = origin\n"
    init_body = textwrap.indent(init_body, prefix="    " * 2)
    class_header += init_body

    # class body
    class_body = ""
    for child in children:
        property_body = "\n"
        property_body += "@property\n"
        property_body += f"def {child.name}(self) -> {child.type}:\n"
        property_body += f"    return {child.type}(\n"
        property_body += f"        parent=self,\n"
        property_body += f"        origin=self.origin.{child.name}\n"
        property_body += f"    )\n"
        class_body += textwrap.indent(property_body, prefix="    ")

    children_prop_body = "\n"
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
