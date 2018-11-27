from typing import Any, Callable, Iterable, TypeVar

T = TypeVar("T")

class mark:
    @staticmethod
    def parametrize(
        name: str, cases: Iterable[Any], ids: Iterable[Any] = None
    ) -> Callable[[Callable[..., None]], Callable[..., None]]: ...
    # `pytch`-specific mark, not defined in `pytest`.
    @staticmethod
    def generate(t: T) -> T: ...
