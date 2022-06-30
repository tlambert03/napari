from __future__ import annotations

from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
)

import in_n_out as ino

C = TypeVar("C", bound=Callable)
T = TypeVar("T")

if TYPE_CHECKING:
    from in_n_out._inject import RaiseWarnReturnIgnore

__all__ = [
    'provider',
    'get_provider',
    'get_processor',
    'inject_napari_dependencies',
    'set_providers',
    'set_processors',
]


@lru_cache(maxsize=1)
def _napari_names() -> Dict[str, object]:
    """Napari names to inject into local namespace when evaluating type hints."""
    import napari
    from napari import components, layers, viewer

    def _public_types(module):
        return {
            name: val
            for name, val in vars(module).items()
            if not name.startswith('_')
            and isinstance(val, type)
            and getattr(val, '__module__', '_').startswith('napari')
        }

    return {
        'napari': napari,
        **_public_types(components),
        **_public_types(layers),
        **_public_types(viewer),
    }


_STORE = ino.Store.create('napari')
_STORE.namespace = _napari_names


def inject_napari_dependencies(
    func: Callable[..., C],
    *,
    localns: Optional[dict] = None,
    on_unresolved_required_args: RaiseWarnReturnIgnore = "raise",
    on_unannotated_required_args: RaiseWarnReturnIgnore = "warn",
) -> Callable[..., C]:
    """Decorator returns func that can access/process napari objects based on type hints.

    This is form of dependency injection, and result processing.  It does 2 things:

    1. If `func` includes a parameter that has a type with a registered provider
    (e.g. `Viewer`, or `Layer`), then this decorator will return a new version of
    the input function that can be called *without* that particular parameter.

    2. If `func` has a return type with a registered processor (e.g. `ImageData`),
    then this decorator will return a new version of the input function that, when
    called, will have the result automatically processed by the current processor
    for that type (e.g. in the case of `ImageData`, it will be added to the viewer.)

    Parameters
    ----------
    func : Callable
        A function with napari type hints.

    Returns
    -------
    Callable
        A function with napari dependencies injected
    """
    return ino.inject_dependencies(
        func,
        localns=localns,
        store=_STORE,
        on_unresolved_required_args=on_unresolved_required_args,
        on_unannotated_required_args=on_unannotated_required_args,
    )


def provider(func: C) -> C:
    return ino.provider(func, store=_STORE)


def processor(func: C) -> C:
    return ino.processor(func, store=_STORE)


def get_provider(
    type_: Union[object, Type[T]]
) -> Union[Callable[[], T], Callable[[], Optional[T]], None]:
    return ino.get_provider(type_, store=_STORE)


def get_processor(type_: Type[T]) -> Optional[Callable[[T], Any]]:
    return ino.get_processor(type_, store=_STORE)


def set_providers(
    mapping: Dict[Type[T], Union[T, Callable[[], T]]], *, clobber: bool = False
) -> None:
    return ino.set_providers(mapping, store=_STORE, clobber=clobber)


def set_processors(
    mapping: Dict[Type[T], Union[T, Callable[[], T]]], *, clobber: bool = False
) -> None:
    return ino.set_processors(mapping, store=_STORE, clobber=clobber)
