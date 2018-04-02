#!/usr/bin/env python3
"""Generate the syntax tree data structures from their spec.

Run `generate_syntax_trees.sh` rather than this script directly.
"""
import sys
import textwrap
from typing import List, Sequence

from sttools import Child, get_exports, get_node_types, NodeType


PREAMBLE = """\
\"\"\"NOTE: This file auto-generated from ast.txt.

Run `bin/generate_syntax_trees.sh` to re-generate. Do not edit!
\"\"\"
from typing import List, Optional, Sequence, Union

from .lexer import Token


class Node:
    def __init__(
        self,
        children: Sequence[Union["Node", Optional["Token"]]],
    ) -> None:
        self._children = children

    @property
    def children(self) -> Sequence[Union["Node", Optional["Token"]]]:
        return self._children


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


def get_children_parameter_list(children: Sequence[Child]) -> str:
    parameter = "[\n"
    for child in children:
        list_elem = ""
        if child.is_sequence_type:
            list_elem += f"*{child.name}"
        elif child.is_optional_sequence_type:
            list_elem += (
                f"*({child.name} if {child.name} is not None else [])"
            )
        else:
            list_elem += child.name
        list_elem += ",\n"
        parameter += textwrap.indent(list_elem, prefix="    ")
    parameter += "]"
    return parameter


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
    init_header += "    self,\n"
    for child in children:
        init_header += f"    {child.name}: {child.type},\n"
    init_header += ") -> None:\n"
    init_header = textwrap.indent(init_header, prefix="    ")
    class_header += init_header

    # __init__ body
    init_body = f"super().__init__({get_children_parameter_list(children)})\n"
    for child in children:
        init_body += f"self._{child.name} = {child.name}\n"
    init_body = textwrap.indent(init_body, prefix="    " * 2)
    class_header += init_body

    # class body
    class_body = ""
    for child in children:
        property_body = "\n"
        property_body += "@property\n"
        property_body += f"def {child.name}(self) -> {child.type}:\n"
        property_body += f"    return self._{child.name}\n"
        class_body += textwrap.indent(property_body, prefix="    ")

    return class_header + class_body


if __name__ == "__main__":
    main()
