"""Nestable MutableSequence that emits events when altered.

see module docstring of evented_list.py for more details
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import (
    DefaultDict,
    Generator,
    Iterable,
    NewType,
    Tuple,
    Union,
    cast,
    overload,
)

from ..event import Event
from ..types import SupportsEvents
from ._evented_list import _T, EventedList, Index

logger = logging.getLogger(__name__)

NestedIndex = Tuple[Index, ...]
MaybeNestedIndex = Union[Index, NestedIndex]
ParentIndex = NewType('ParentIndex', Tuple[int, ...])


def ensure_tuple_index(index: MaybeNestedIndex) -> NestedIndex:
    """Return index as a tuple of ints or slices.

    Parameters
    ----------
    index : Tuple[Union[int, slice], ...] or int or slice
        An index as an int, tuple, or slice

    Returns
    -------
    NestedIndex
        The index, guaranteed to be a tuple.

    Raises
    ------
    TypeError
        If the input ``index`` is not an ``int``, ``slice``, or ``tuple``.
    """
    if isinstance(index, (slice, int)):
        return (index,)  # single integer inserts to self
    elif isinstance(index, tuple):
        return index
    raise TypeError(f"Invalid nested index: {index}. Must be an int or tuple")


def split_nested_index(index: MaybeNestedIndex) -> tuple[ParentIndex, Index]:
    """Given a nested index, return (nested_parent_index, row).

    Parameters
    ----------
    index : MaybeNestedIndex
        An index as an int, tuple, or slice

    Returns
    -------
    Tuple[NestedIndex, Index]
        A tuple of ``parent_index``, ``row``

    Raises
    ------
    ValueError
        If any of the items in the returned ParentIndex tuple are not ``int``.

    Examples
    --------
    >>> split_nested_index((1, 2, 3, 4))
    ((1, 2, 3), 4)
    >>> split_nested_index(1)
    ((), 1)
    >>> split_nested_index(())
    ((), -1)
    """
    index = ensure_tuple_index(index)
    if index:
        *first, last = index
        if any(not isinstance(p, int) for p in first):
            raise ValueError('The parent index must be a tuple of int')
        return cast(ParentIndex, tuple(first)), last
    return ParentIndex(()), -1  # empty tuple appends to self


class NestableEventedList(EventedList[_T]):
    """Nestable Mutable Sequence that emits recursive events when altered.

    ``NestableEventedList`` instances can be indexed with a ``tuple`` of
    ``int`` (e.g. ``mylist[0, 2, 1]``) to retrieve nested child objects.

    A key property of this class is that when new mutable sequences are added
    to the list, they are themselves converted to a ``NestableEventedList``,
    and all of the ``EventEmitter`` objects in the child are connect to the
    parent object's ``_reemit_nested_event`` method (assuming the child has
    an attribute called ``events`` that is an instance of ``EmitterGroup``).
    When ``_reemit_nested_event`` receives an event from a child object, it
    remits the event, but changes any ``index`` keys in the event to a
    ``NestedIndex`` (a tuple of ``int``) such that indices emitted by any given
    ``NestableEventedList`` are always relative to itself.


    Parameters
    ----------
    data : iterable, optional
        Elements to initialize the list with. by default None.
    basetype : type or sequence of types, optional
        Type of the elements in the list.
    lookup : dict of Type[L] : function(object) -> L
        Mapping between a type, and a function that converts items in the list
        to that type.

    Events
    ------
    types used:
        Index = Union[int, Tuple[int, ...]]

    inserting (index: Index)
        emitted before an item is inserted at ``index``
    inserted (index: Index, value: T)
        emitted after ``value`` is inserted at ``index``
    removing (index: Index)
        emitted before an item is removed at ``index``
    removed (index: Index, value: T)
        emitted after ``value`` is removed at ``index``
    moving (index: Index, new_index: Index)
        emitted before an item is moved from ``index`` to ``new_index``
    moved (index: Index, new_index: Index, value: T)
        emitted after ``value`` is moved from ``index`` to ``new_index``
    changed (index: Index, old_value: T, value: T)
        emitted when ``index`` is set from ``old_value`` to ``value``
    changed <OVERLOAD> (index: slice, old_value: list[_T], value: list[_T])
        emitted when slice ``index`` is set from ``old_value`` to ``value``
    reordered (value: self)
        emitted when the list is reordered (eg. moved/reversed).
    """

    # WAIT!! ... Read the ._list module docs before reimplement these classes
    # def append(self, item): ...
    # def clear(self): ...
    # def pop(self, index=-1): ...
    # def extend(self, value: Iterable[_T]): ...
    # def remove(self, value: T): ...

    @overload  # type: ignore
    def __getitem__(self, key: int) -> Union[_T, 'NestableEventedList[_T]']:
        ...  # pragma: no cover

    @overload
    def __getitem__(self, key: ParentIndex) -> 'NestableEventedList[_T]':
        ...  # pragma: no cover

    @overload
    def __getitem__(self, key: slice) -> 'NestableEventedList[_T]':  # noqa
        ...  # pragma: no cover

    @overload
    def __getitem__(
        self, key: NestedIndex
    ) -> Union[_T, 'NestableEventedList[_T]']:
        ...  # pragma: no cover

    def __getitem__(self, key: MaybeNestedIndex):
        if isinstance(key, tuple):
            item: NestableEventedList[_T] = self
            for idx in key:
                item = item[idx]  # type: ignore
            return item
        return super().__getitem__(key)

    @overload
    def __setitem__(self, key: Union[int, NestedIndex], value: _T):
        ...  # pragma: no cover

    @overload
    def __setitem__(self, key: slice, value: Iterable[_T]):
        ...  # pragma: no cover

    def __setitem__(self, key: MaybeNestedIndex, value):
        # NOTE: if we check isinstance(..., MutableList), then we'll actually
        # clobber object of specialized classes being inserted into the list
        # (for instance, subclasses of NestableEventedList)
        # this check is more conservative, but will miss some "nestable" things
        if isinstance(value, list):
            value = self.__class__(value)
        if isinstance(key, tuple):
            parent_i, index = split_nested_index(key)
            self[parent_i].__setitem__(index, value)
            return
        self._connect_child_emitters(value)
        super().__setitem__(key, value)

    def _delitem_indices(
        self, key: MaybeNestedIndex
    ) -> Iterable[tuple[EventedList[_T], int]]:
        if isinstance(key, tuple):
            parent_i, index = split_nested_index(key)
            if isinstance(index, slice):
                indices = sorted(
                    range(*index.indices(len(parent_i))), reverse=True
                )
            else:
                indices = [index]
            return [
                (cast(NestableEventedList[_T], self[parent_i]), i)
                for i in indices
            ]
        return super()._delitem_indices(key)

    def __delitem__(self, key):
        for parent, index in self._delitem_indices(key):
            self._disconnect_child_emitters(parent[index])
        super().__delitem__(key)

    def insert(self, index: int, value: _T):
        """Insert object before index."""
        # this is delicate, we want to preserve the evented list when nesting
        # but there is a high risk here of clobbering attributes of a special
        # child class
        if isinstance(value, list):
            value = self.__newlike__(value)
        super().insert(index, value)
        self._connect_child_emitters(value)

    def _reemit_nested_event(self, event: Event):
        source_index = self.index(event.source)
        for attr in ('index', 'new_index'):
            if hasattr(event, attr):
                src_index = ensure_tuple_index(event.index)
                setattr(event, attr, (source_index,) + src_index)
        if not hasattr(event, 'index'):
            setattr(event, 'index', source_index)

        # reemit with this object's EventEmitter of the same type if present
        # otherwise just emit with the EmitterGroup itself
        getattr(self.events, event.type, self.events)(event)

    def _disconnect_child_emitters(self, child: _T):
        """Disconnect all events from the child from the reemitter."""
        if isinstance(child, SupportsEvents):
            child.events.disconnect(self._reemit_nested_event)

    def _connect_child_emitters(self, child: _T):
        """Connect all events from the child to be reemitted."""
        if isinstance(child, SupportsEvents):
            # make sure the event source has been set on the child
            if child.events.source is None:
                child.events.source = child
            child.events.connect(self._reemit_nested_event)

    def _non_negative_index(
        self, parent_index: ParentIndex, dest_index: Index
    ) -> Index:
        """Make sure dest_index is a positive index inside parent_index."""
        destination_group = cast(NestableEventedList[_T], self[parent_index])
        # not handling slice indexes
        if isinstance(dest_index, int):
            if dest_index < 0:
                dest_index += len(destination_group) + 1
        return dest_index

    def _nested_move_plan(
        self, sources: Iterable[NestedIndex], dest_index: NestedIndex
    ) -> Generator[tuple[NestedIndex, NestedIndex], None, None]:

        dest_par, dest_i = split_nested_index(dest_index)
        if isinstance(dest_i, slice):
            raise ValueError("Destination index may not be a slice")
        dest_i = cast(int, self._non_negative_index(dest_par, dest_i))

        # need to update indices as we pop, so we keep track of the indices
        # we have previously popped
        popped: DefaultDict[NestedIndex, list[int]] = defaultdict(list)
        dumped: list[int] = []

        # we iterate indices from the end first, so pop() always works
        for idx in sorted(sources, reverse=True):
            if idx == ():
                raise IndexError("Group cannot move itself")

            # i.e. we need to increase the (src_par, ...) by 1 for each time
            # we have previously inserted items in front of the (src_par, ...)
            if len(idx) > len(dest_par):
                z = idx[len(dest_par)]
                _idx: list[Index] = list(idx)
                if isinstance(_idx[len(dest_par)], slice):
                    raise NotImplementedError(
                        "Can't yet deal with slice source indices in multimove"
                    )
                _idx[len(dest_par)] += sum(map(lambda x: x <= z, dumped))  # type: ignore
                idx = tuple(_idx)

            src_par, src_i = split_nested_index(idx)
            if isinstance(src_i, slice):
                raise ValueError("Terminal source index may not be a slice")
            src_i = cast(int, src_i)
            if src_i < 0:
                src_i += len(self[src_par])

            # we need to decrement the src_i by 1 for each time we have
            # previously pulled items out from in front of the src_i
            src_i -= sum(map(lambda x: x <= src_i, popped.get(src_par, [])))

            # we need to decrement the dest_i by 1 for each time we have
            # previously pulled items out from in front of the dest_i
            ddec = sum(map(lambda x: x <= dest_i, popped.get(dest_par, [])))

            # skip noop
            if src_par == dest_par and src_i == dest_i - ddec:
                continue

            yield src_par + (src_i,), dest_par + (dest_i - ddec,)
            popped[src_par].append(src_i)
            dumped.append(dest_i - ddec)

    def move_multiple(
        self, sources: Iterable[NestedIndex], dest_index: NestedIndex
    ) -> int:
        """Move a batch of nested indices, to a single destination."""
        logger.debug(
            f"move_multiple(sources={sources}, dest_index={dest_index})"
        )

        # calling list here makes sure that there are no index errors up front
        move_plan = list(self._nested_move_plan(sources, dest_index))

        # more complicated when moving multiple objects.
        # don't assume index adjacency ... so move one at a time
        with self.events.reordered.blocker():
            for src, dest in move_plan:
                self.move(src, dest)

        self.events.reordered(value=self)
        return len(move_plan)

    def move(
        self,
        src_index: Union[int, NestedIndex],
        dest_index: Union[int, NestedIndex] = (0,),
    ) -> bool:
        """Move a single item from ``src_index`` to ``dest_index``.

        Parameters
        ----------
        src_index : Union[int, NestedIndex]
            The index of the object to move
        dest_index : Union[int, NestedIndex], optional
            The destination.  Object will be inserted before ``dest_index.``,
            by default, will insert at the front of the root list.

        Returns
        -------
        bool
            Whether the operation completed successfully

        Raises
        ------
        ValueError
            If the terminal source is a slice, or if the source is this root
            object
        """
        logger.debug(f"move(src_index={src_index}, dest_index={dest_index})")
        src_par_i, src_i = split_nested_index(src_index)
        dest_par_i, dest_i = split_nested_index(dest_index)
        dest_i = self._non_negative_index(dest_par_i, dest_i)
        dest_index = dest_par_i + (dest_i,)

        if isinstance(src_i, slice):
            raise ValueError("Terminal source index may not be a slice")
        if isinstance(dest_i, slice):
            raise ValueError("Destination index may not be a slice")
        if src_i == ():
            raise ValueError("Group cannot move itself")

        if src_par_i == dest_par_i:
            if isinstance(dest_i, int):
                if dest_i > src_i:
                    dest_i -= 1
                if src_i == dest_i:
                    return False

        self.events.moving(index=src_index, new_index=dest_index)
        with self.events.blocker_all():
            dest_par = self[dest_par_i]  # grab this before popping src_i
            value = self[src_par_i].pop(src_i)
            dest_par.insert(dest_i, value)

        self.events.moved(index=src_index, new_index=dest_index, value=value)
        self.events.reordered(value=self)
        return True

    def _type_check(self, e) -> _T:
        if isinstance(e, list):
            return self.__newlike__(e)
        if self._basetypes:
            _types = set(self._basetypes) | {NestableEventedList}
            if not any(isinstance(e, t) for t in _types):
                raise TypeError(
                    f'Cannot add object with type {type(e)!r} to '
                    f'TypedList expecting type {_types!r}'
                )
        return e
