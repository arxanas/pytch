#!/usr/bin/env python3
"""Generate the syntax tree data structures from their spec.

Run `generate_syntax_trees.sh` rather than this script directly.
"""
import sys
import textwrap
from typing import List, Sequence

from sttools import Child, get_node_types, NodeType


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

    @property
    def leading_text(self) -> str:
        first_child = self.first_present_child
        if first_child is None:
            return ""
        else:
            return first_child.leading_text

    @property
    def text(self) -> str:
        if len(self._children) == 0:
            return ""
        elif len(self._children) == 1:
            child = self._children[0]
            if child is None:
                return ""
            else:
                return child.text
        else:
            text = ""
            [first, *middle, last] = self._children
            if first is not None:
                text += first.text + first.trailing_text
            for child in middle:
                if child is not None:
                    text += child.full_text
            if last is not None:
                text += last.leading_text + last.text
            return text

    @property
    def trailing_text(self) -> str:
        last_child = self.last_present_child
        if last_child is None:
            return ""
        else:
            return last_child.trailing_text

    @property
    def full_text(self) -> str:
        return "".join(
            child.full_text
            for child in self._children
            if child is not None
        )

    @property
    def first_present_child(self) -> Optional[Union["Node", "Token"]]:
        for child in self.children:
            if child is None:
                continue
            if isinstance(child, Token):
                if not child.is_dummy:
                    return child
            else:
                child_first_present_child = child.first_present_child
                if child_first_present_child is not None:
                    return child_first_present_child
        return None

    @property
    def last_present_child(self) -> Optional[Union["Node", "Token"]]:
        for child in reversed(self.children):
            if child is None:
                continue
            if isinstance(child, Token):
                if not child.is_dummy:
                    return child
            else:
                child_last_present_child = child.last_present_child
                if child_last_present_child is not None:
                    return child_last_present_child
        return None

    @property
    def leading_width(self) -> int:
        child = self.first_present_child
        if child is None:
            return 0
        return child.leading_width

    @property
    def trailing_width(self) -> int:
        child = self.last_present_child
        if child is None:
            return 0
        return child.trailing_width

    @property
    def width(self) -> int:
        if not self.children:
            return 0
        return (
            self.full_width
            - self.leading_width
            - self.trailing_width
        )

    @property
    def full_width(self) -> int:
        return sum(
            child.full_width if child is not None else 0
            for child in self.children
        )


"""


def main() -> None:
    lines = sys.stdin.read().splitlines()
    sections = get_node_types(lines)
    class_defs = [get_class_def(name, children) for name, children in sections.items()]
    sys.stdout.write(PREAMBLE)
    sys.stdout.write("\n\n".join(class_defs))


def get_children_parameter_list(children: Sequence[Child]) -> str:
    parameter = "[\n"
    for child in children:
        list_elem = ""
        if child.is_sequence_type:
            list_elem += f"*{child.name}"
        elif child.is_optional_sequence_type:
            list_elem += f"*({child.name} if {child.name} is not None else [])"
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
        init_header += f"    {child.name}: {child.type.name},\n"
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

    # children
    for child in children:
        property_body = "\n"
        property_body += "@property\n"
        property_body += f"def {child.name}(self) -> {child.type.name}:\n"
        property_body += f"    return self._{child.name}\n"
        class_body += textwrap.indent(property_body, prefix="    ")

    return class_header + class_body


if __name__ == "__main__":
    main()
