from typing import Iterable, Type, TypeVar, Union

from .redcst import Node, SyntaxTree, Token


T_node = TypeVar("T_node", bound=Node)


class Query:
    def __init__(self, red_cst: SyntaxTree) -> None:
        self._red_cst = red_cst

    def find_instances(self, node_type: Type[T_node]) -> Iterable[T_node]:
        for node in self._walk_all():
            if isinstance(node, node_type):
                yield node

    def _walk(self, node: Union[Node, Token]) -> Iterable[Union[Node, Token]]:
        yield node
        if isinstance(node, Node):
            for child in node.children:
                if child is not None:
                    yield from self._walk(child)

    def _walk_all(self) -> Iterable[Union[Node, Token]]:
        if self._red_cst.n_expr is not None:
            yield from self._walk(self._red_cst.n_expr)
        if self._red_cst.t_eof is not None:
            yield from self._walk(self._red_cst.t_eof)
