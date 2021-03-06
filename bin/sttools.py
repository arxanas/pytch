"""Tools for generating syntax trees."""
from typing import Dict, List, Mapping, Optional


class NodeType:
    def __init__(self, name: str, supertype: Optional[str]) -> None:
        self.name = name
        self.supertype = supertype

    def __repr__(self) -> str:
        return f"<NodeType name={self.name} supertype={self.supertype}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NodeType):
            return False
        return self.name == other.name and self.supertype == other.supertype

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, NodeType)
        return self.name < other.name

    def __hash__(self) -> int:
        return hash(self.name)


TOKEN_TYPE = NodeType(name="Token", supertype=None)


class Child:
    def __init__(self, name: str, type: NodeType) -> None:
        self.name = name
        self.type = type

    @property
    def base_type(self) -> NodeType:
        assert self.type.name.startswith("Optional[")
        assert self.type.name.endswith("]")
        name = self.type.name[len("Optional[") : -len("]")]

        if name.startswith("List["):
            name = name[len("List[") : -len("]")]
        if name.startswith("Sequence["):
            name = name[len("Sequence[") : -len("]")]

        return NodeType(name=name, supertype=None)

    @property
    def is_sequence_type(self) -> bool:
        return self.type.name.startswith("List[") or self.type.name.startswith(
            "Sequence["
        )

    @property
    def is_optional_sequence_type(self) -> bool:
        return self.type.name.startswith("Optional[List[") or self.type.name.startswith(
            "Optional[Sequence["
        )


def get_node_type_from_header(header: str) -> NodeType:
    if "(" in header:
        name, supertype = header.split("(", 1)
        assert supertype.endswith(")")
        supertype = supertype.rstrip(")")
        return NodeType(name=name, supertype=supertype)
    return NodeType(name=header, supertype=None)


def get_child(line: str) -> Child:
    name, child_type = line.split(": ", 1)
    type = NodeType(name=child_type, supertype=None)
    return Child(name=name, type=type)


def get_node_types(lines: List[str]) -> Mapping[NodeType, List[Child]]:
    sections: Dict[NodeType, List[Child]] = {}
    current_node_type = None
    for line in lines:
        if not line:
            continue

        if not line.startswith(" "):
            current_node_type = get_node_type_from_header(line)
            assert (
                current_node_type not in sections
            ), f"Duplicate node type: {current_node_type.name}"
            sections[current_node_type] = []
            continue

        line = line.lstrip()
        if line.startswith("#"):
            # Comment, skip this line.
            continue

        child = get_child(line)
        assert (
            current_node_type is not None
        ), f"Child has no associated node type: {line}"
        sections[current_node_type].append(child)
    return sections
