#!/usr/bin/env python3
"""Generate the AST data structures from the description in pytch/ast.txt.

Run `generate_ast.sh` rather than this script directly.
"""
import sys
import textwrap
from typing import Dict, Iterable, List, Mapping, Optional

INDENT = " " * 4
PREAMBLE = """\
\"\"\"NOTE: This file auto-generated from ast.txt.

Run `bin/generate_ast.sh` to re-generate. Do not edit!
\"\"\"
from typing import List, Optional, Sequence, Union

from .lexer import Token


"""


class NodeType:
    def __init__(self, name: str, supertype: Optional[str]) -> None:
        self.name = name
        self.supertype = supertype

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NodeType):
            return False
        return self.name == other.name

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, NodeType)
        return self.name < other.name

    def __hash__(self) -> int:
        return hash(self.name)

    @property
    def is_top_type(self) -> bool:
        return self.supertype is None


class Child:
    def __init__(self, name: str, type: str) -> None:
        self.name = name
        self.type = type

    @property
    def is_sequence_type(self) -> bool:
        return (
            self.type.startswith("List[")
            or self.type.startswith("Sequence[")
        )

    @property
    def is_optional_sequence_type(self) -> bool:
        return (
            self.type.startswith("Optional[List[")
            or self.type.startswith("Optional[Sequence[")
        )


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


def get_node_types(lines: List[str]) -> Mapping[NodeType, List[Child]]:
    sections: Dict[NodeType, List[Child]] = {}
    current_node_type = None
    for line in lines:
        if not line:
            continue

        if not line.startswith(" "):
            current_node_type = get_node_type_from_header(line)
            assert current_node_type not in sections, \
                f"Duplicate node type: {current_node_type.name}"
            sections[current_node_type] = []
            continue

        line = line.lstrip()
        if line.startswith("#"):
            # Comment, skip this line.
            continue

        child = get_child(line)
        assert current_node_type is not None, \
            f"Child has no associated node type: {line}"
        sections[current_node_type].append(child)
    return sections


def get_node_type_from_header(header: str) -> NodeType:
    if "(" in header:
        name, supertype = header.split("(", 1)
        assert supertype.endswith(")")
        supertype = supertype.rstrip(")")
        return NodeType(name=name, supertype=supertype)
    return NodeType(name=header, supertype=None)


def get_child(line: str) -> Child:
    name, type = line.split(": ", 1)
    return Child(name=name, type=type)


def get_class_def(node_type: NodeType, children: List[Child]) -> str:
    class_header = f"class {node_type.name}"
    if node_type.supertype:
        class_header += f"({node_type.supertype})"
    class_header += ":\n"

    if not children:
        class_body = textwrap.indent("pass\n", prefix=INDENT)
        return class_header + class_body

    init_header = "def __init__(\n"
    init_header += "    self,\n"
    for child in children:
        init_header += f"    {child.name}: {child.type},\n"
    init_header += ") -> None:\n"
    init_header = textwrap.indent(init_header, prefix=INDENT)
    class_header += init_header

    init_body = ""
    if not node_type.is_top_type:
        init_body += "super().__init__([\n"
        for child in children:
            super_arg = ""
            if child.is_sequence_type:
                super_arg += f"*{child.name}"
            elif child.is_optional_sequence_type:
                super_arg += (
                    f"*({child.name} if {child.name} is not None else [])"
                )
            else:
                super_arg += child.name
            super_arg += ",\n"
            init_body += textwrap.indent(super_arg, prefix=INDENT)
        init_body += "])\n"
    for child in children:
        init_body += f"self._{child.name} = {child.name}\n"
    init_body = textwrap.indent(init_body, prefix=INDENT * 2)
    class_header += init_body

    class_body = ""
    for child in children:
        property_body = "\n"
        property_body += "@property\n"
        property_body += f"def {child.name}(self) -> {child.type}:\n"
        property_body += f"    return self._{child.name}\n"
        class_body += textwrap.indent(property_body, prefix=INDENT)

    return class_header + class_body


def get_exports(node_types: Iterable[NodeType]) -> str:
    sorted_exports = sorted(node_types)
    exports = "[\n" + "".join(
        textwrap.indent(f'"{export.name}",\n', prefix=INDENT)
        for export in sorted_exports
    ) + "]"
    return "__all__ = " + exports


if __name__ == "__main__":
    main()
