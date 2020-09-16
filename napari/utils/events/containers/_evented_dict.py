"""MutableMapping that emits events when altered.

Note For Developers
===================

Be cautious when re-implementing typical dict-like methods here (e.g. extend,
pop, clear, etc...).  By not re-implementing those methods, we force ALL "CRUD"
(create, read, update, delete) operations to go through a few key methods
defined by the abc.MutableMapping interface, where we can emit the necessary
events.

Specifically:

- ``__getitem__`` = retrieve the value of a key in the dict
- ``__setitem__`` = create/update the value of a key in the dict
- ``__delitem__`` = delete a key from the dict

All of the additional dict-like methods are provided by the MutableMapping
interface, and call one of those 2 methods.  So if you override a method, you
MUST make sure that all the appropriate events are emitted.  (Tests should
cover this in test_evented_dict.py)
"""

from typing import Any, Iterator, MutableMapping, TypeVar

from ..event import EmitterGroup

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class EventedDict(MutableMapping[_KT, _VT]):
    NOKEY = object()
    events: EmitterGroup

    def __init__(self, data: dict = None):

        _events = {
            'set': None,  # int
            'deleted': None,  # int
        }

        # For inheritance: If the mro already provides an EmitterGroup, add...
        if hasattr(self, 'events') and isinstance(self.events, EmitterGroup):
            self.events.add(**_events)
        else:
            # otherwise create a new one
            self.events = EmitterGroup(source=self, **_events)

        self._dict = dict(data) if data else {}

    def __getitem__(self, key: Any):
        return self._dict.__getitem__(key)

    def __setitem__(self, key: Any, value: Any):
        prev = self._dict.get(key, EventedDict.NOKEY)
        self._dict.__setitem__(key, value)
        if value != prev:
            self.events.set(value=(key, value, prev))

    def __delitem__(self, key: Any):
        value = self._dict.pop(key)
        self.events.deleted(value=(key, value))

    def __iter__(self) -> Iterator:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __repr__(self) -> str:
        return repr(self._dict)

    @classmethod
    def __newlike__(cls, data: dict):
        return cls(data)

    def copy(self) -> 'EventedDict[_KT, _VT]':
        """Return a shallow copy of the dict."""
        return self.__newlike__(self._dict)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        """Create a new EventedDict with keys from iterable.

        All values in the new dict will be set to ``value``.
        """
        return cls.__newlike__(dict.fromkeys(iterable, value))
