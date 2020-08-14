"""Patch callables (functions and methods).

Our perfmon system using this to patch in perf_timers, but this can be used
for any type of patching. See patch_callables() below as the main entrypoint.
"""

import types
from importlib import import_module
from typing import Callable, List, Set, Tuple, Union

# The parent of a callable is a module or a class, class is of type "type".
CallableParent = Union[types.ModuleType, type]

# An example PatchFunction is:
# def _patch_perf_timer(parent, callable: str, label: str) -> None
PatchFunction = Callable[[CallableParent, str, str], None]


class PatchError(Exception):
    """Failed to patch target, config file error?"""

    def __init__(self, message):
        self.message = message


def _patch_attribute(
    module: types.ModuleType, attribute_str: str, patch_func: PatchFunction
):
    """Patch the module's callable pointed to by the attribute string.

    Parameters
    ----------
    module : types.ModuleType
        The module to patch.
    attribute_str : str
        An attribute in the module like "function" or "class.method".
    patch_func : PatchFunction
        This function is called to perform the patch.

    """
    # We expect attribute_str is <function> or <class>.<method>. We could
    # allow nested classes and functions if we wanted to extend this some.
    if attribute_str.count('.') > 1:
        raise PatchError(f"Nested attribute not found: {attribute_str}")

    if '.' in attribute_str:
        # Assume attribute_str is <class>.<method>
        class_str, callable_str = attribute_str.split('.')
        try:
            parent = getattr(module, class_str)
        except AttributeError:
            raise PatchError(
                f"Module {module.__name__} has no attribute {attribute_str}"
            )
        parent_str = class_str
    else:
        # Assume attribute_str is <function>.
        class_str = None
        parent = module
        parent_str = module.__name___
        callable_str = attribute_str

    try:
        getattr(parent, callable_str)
    except AttributeError:
        raise PatchError(
            f"Parent {parent_str} has no attribute {callable_str}"
        )

    label = (
        callable_str if class_str is None else f"{class_str}.{callable_str}"
    )

    # Patch it with the user-provided patch_func.
    print(f"Patcher: patching {module.__name__}.{label}")
    patch_func(parent, callable_str, label)


def _import_module(target_str: str) -> Tuple[types.ModuleType, str]:
    """Import the module portion of this target string.

    Try importing successively longer segments of the target_str. For example
    with "napari.utils.chunk_loader.ChunkLoader.load_chunk" we will import:
        napari (success)
        napari.utils (success)
        napari.utils.chunk_loader (success)
        napari.utils.chunk_loader.ChunkLoader (failure)

    The last one fails because ChunkLoader is a class not a module.

    Parameters
    ----------
    target_str : str
        The fully qualified callable such as "module1.module2.function".

    Returns
    -------
    Tuple[types.ModuleType, str]
        Where the module is the inner most imported module, and the string
        is the rest of target_str that was not modules.
    """
    parts = target_str.split('.')
    module = None  # Inner-most module imported so far.

    # Progressively try to import longer and longer segments of the path.
    for i in range(1, len(target_str)):
        module_path = '.'.join(parts[:i])
        try:
            module = import_module(module_path)
        except ModuleNotFoundError:
            if module is None:
                # The very first top-level module import failed!
                raise PatchError(f"Module not found: {module_path}")

            # We successfully imported part of the target_str but then
            # we got a failure. Usually this is because we tried
            # importing a class or function. Return the inner-most
            # module we did successfuly import. And return the rest of
            # the module_path we didn't use.
            attribute_str = '.'.join(parts[i - 1 :])
            return module, attribute_str


def patch_callables(callables: List[str], patch_func: PatchFunction) -> None:
    """Patch the given list of callables.

    Parameters
    ----------
    callables : List[str]
        Patch all of these callables (functions or methods).
    patch_func : PatchFunction
        Called on every callable to patch it.

    Notes
    -----
    The callables list should look like:
    [
        "module.module.ClassName.method_name",
        "module.function_name"
        ...
    ]

    Nested classes and methods not allowed, but support could be added.

    An example patch_func is::

        import wrapt
        def _my_patcher(parent: CallableParent, callable: str, label: str):
            @wrapt.patch_function_wrapper(parent, callable)
            def my_announcer(wrapped, instance, args, kwargs):
                print(f"Announce {label}")
                return wrapped(*args, **kwargs)
    """
    patched: Set[str] = set()

    for target_str in callables:
        if target_str in patched:
            # Ignore duplicated targets in the config file.
            print(f"Patcher: [WARN] skipping duplicate {target_str}")
            continue

        # Patch the target and note that we did.
        try:
            module, attribute_str = _import_module(target_str)
            _patch_attribute(module, attribute_str, patch_func)
        except PatchError as exc:
            # We don't stop on error because if you switch around branches
            # but keep the same config file, it's easy for your config
            # file to contain targets that aren't in the code.
            print(f"Patcher: [ERROR] {exc}")

        patched.add(target_str)
