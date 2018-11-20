from typing import (
    AbstractSet,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    overload,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import pyrsistent as p
from pyrsistent import pmap, pset, pvector


Tk = TypeVar("Tk")
Tv = TypeVar("Tv")
Tv_in = TypeVar("Tv_in")
Tv_out = TypeVar("Tv_out")


class PSet(AbstractSet[Tk]):
    def __init__(self, iterable: Iterable[Tk] = None) -> None:
        if iterable is not None:
            self._container: p.PSet = pset(iterable)
        else:
            self._container: p.PSet = pset()

    # TODO: tighten up `__contains__` to only accept `Tk`.
    def __contains__(self, key: object) -> bool:
        return key in self._container

    def __iter__(self) -> Iterator[Tk]:
        return iter(self._container)

    def __len__(self) -> int:
        return len(self._container)

    def __repr__(self) -> str:
        elements = ", ".join(repr(element) for element in self._container)
        return f"PSet([{elements}])"

    def add(self, key: Tk) -> "PSet[Tk]":
        return self._container.add(key)


class PVector(Sequence[Tv]):
    def __init__(self, iterable: Iterable[Tv] = None) -> None:
        if iterable is not None:
            self._container: p.PVector = pvector(iterable)
        else:
            self._container: p.PVector = pvector()

    @overload
    def __getitem__(self, item: int) -> Tv:
        pass

    @overload  # noqa: F811
    def __getitem__(self, item: slice) -> Sequence[Tv]:
        pass

    def __getitem__(  # noqa: F811
        self, index: Union[int, slice]
    ) -> Union[Tv, Sequence[Tv]]:
        return self._container[index]

    def __len__(self) -> int:
        return len(self._container)

    def __repr__(self) -> str:
        elements = ", ".join(repr(element) for element in self._container)
        return f"PVector([{elements}])"

    def append(self, element: Tv) -> "PVector[Tv]":
        return PVector(self._container.append(element))

    def map(self, f: Callable[[Tv_in], Tv_out]) -> "PVector[Tv_out]":
        return PVector(self._container.transform(None, f))


class PMap(Mapping[Tk, Tv]):
    def __init__(self, mapping: Mapping[Tk, Tv] = None) -> None:
        if mapping is not None:
            self._container: p.PMap = pmap(mapping.items())
        else:
            self._container: p.PMap = pmap()

    @classmethod
    def of_entries(cls, iterable: Iterable[Tuple[Tk, Tv]] = None) -> "PMap[Tk, Tv]":
        container: PMap[Tk, Tv] = cls()
        container._container = pmap(iterable)
        return container

    def __getitem__(self, index: Tk) -> Tv:
        return self._container[index]

    def __iter__(self) -> Iterator[Tk]:
        return iter(self._container)

    def __len__(self) -> int:
        return len(self._container)

    def __repr__(self) -> str:
        elements = ", ".join(f"{k!r}: {v!r}" for k, v in self._container.items())
        return f"PMap({{{elements}}})"

    def set(self, key: Tk, value: Tv) -> "PMap[Tk, Tv]":
        return PMap(self._container.set(key, value))

    def update(self, bindings: Mapping[Tk, Tv]) -> "PMap[Tk, Tv]":
        return PMap(self._container.update(bindings))


def find(iterable: Iterable[Tv], pred: Callable[[Tv], bool]) -> Optional[Tv]:
    for i in iterable:
        if pred(i):
            return i
    return None


def take_while(iterable: Iterable[Tv], pred: Callable[[Tv], bool]) -> Iterator[Tv]:
    for i in iterable:
        if pred(i):
            yield i
        else:
            return
