from typing import Any, Iterator, Optional, cast


class PropertyView:
    """Proxy object that wraps the return value of a property.

    This allows any changes to the return value of a property to be redirected
    to the property setter (therefore changing the parent object)

    Parameters
    ----------
    viewed : Any
        The return value from an @property
    parent : Union[Any, PropertyView]
        The object that return `viewed`.  Or, if this `PropertyView` was the
        result of a __getitem__ call, the original `PropertyView` that returned
        this `PropertyView` instance.
    key : Any
        If this `PropertyView` was the result of a __getitem__ call, the key
        that was passed to `__getitem__`.  By default, `None`.
    prop : property, optional
        If this `PropertyView` was *not* the result of a __getitem__ call,
        the property instance whose `fget` function returned `viewed`,
        by default `None`.
    """

    def __init__(
        self,
        viewed: Any,
        parent: Any,
        key: Any = None,
        prop: Optional[property] = None,
    ):
        self._viewed = viewed
        self._parent = parent
        self._key = key
        self._prop = prop

    def _call_setter(self) -> None:
        # this won't fire for nested views, so only the top level does something
        if self._prop is not None:
            self._prop.fset(self._parent, self._viewed)

    def __getattribute__(self, name: str) -> Any:
        # proxy as much as possible
        if name in {'_viewed', '_key', '_prop', '_parent', '_call_setter'}:
            return super().__getattribute__(name)
        return getattr(self._viewed, name)

    def __getitem__(self, k: Any) -> 'PropertyView':
        # recursively return views so you can index as deep as you want
        return PropertyView(self._viewed[k], self, key=k)

    def __setitem__(self, k: Any, v: Any) -> None:
        self._viewed[k] = v
        if self._prop is None:
            parent = cast(PropertyView, self._parent)
            # if nested, update the *parent*.
            # (directly the viewed object to avoid recursion)
            parent._viewed[self._key][k] = v
            parent._call_setter()
        else:
            # call directly setter
            self._call_setter()

    def __iter__(self) -> Iterator:
        yield from self._viewed

    def __repr__(self) -> str:
        return f'View({repr(self._viewed)})'

    # more proxy methods


class property_view(property):
    def __get__(self, obj: object, objtype: Optional[type] = None):
        prop_return_value = super().__get__(obj, objtype)
        return PropertyView(prop_return_value, parent=obj, prop=self)
