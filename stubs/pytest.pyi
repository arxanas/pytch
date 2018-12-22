from typing import Any, Callable, Generic, Iterable, Tuple, TypeVar, Union

T = TypeVar("T")

class Xfail:
    pass

class mark:
    @staticmethod
    def parametrize(
        name: str, cases: Iterable[Any], ids: Iterable[Any] = None
    ) -> Callable[[Callable[..., None]], Callable[..., None]]: ...
    # `pytch`-specific mark, not defined in `pytest`.
    @staticmethod
    def generate(t: T) -> T: ...
    @staticmethod
    def xfail(strict: bool = True) -> Xfail: ...
    class structures:
        class ParameterSet(Generic[T]):
            values: Tuple[T]

def param(
    value: T, id: str = None, marks: Union[Xfail] = None
) -> mark.structures.ParameterSet[T]: ...
