from typing import Optional, List
from ..layers import Layer
from ..utils.naming import force_name_unique
from ..utils.list import ListModel
from ..utils.event_handler import call_on


def _add(event):
    """When a layer is added, set its name."""
    layers = event.source
    layer = event.item
    # Register layer event handler
    layer.event_handler.discover_connections(layers)
    # Coerce name into being unique in layer list
    layer.name = force_name_unique(layer.name, [l.name for l in layers[:-1]])
    # Unselect all other layers
    layers.unselect_all(ignore=layer)


class LayerList(ListModel):
    """List-like layer collection with built-in reordering and callback hooks.

    Parameters
    ----------
    iterable : iterable
        Iterable of napari.layer.Layer

    Attributes
    ----------
    events : vispy.util.event.EmitterGroup
        Event hooks:
            * added(item, index): whenever an item is added
            * removed(item): whenever an item is removed
            * reordered(): whenever the list is reordered
    """

    def __init__(self, iterable=()):
        super().__init__(
            basetype=Layer,
            iterable=iterable,
            lookup={str: lambda q, e: q == e.name},
        )

        self.events.added.connect(_add)

    def __newlike__(self, iterable):
        return ListModel(self._basetype, iterable, self._lookup)

    @call_on.name_unique
    def _on_name_unique_change(self, value):
        """Receive layer name tuple and update the name if is already in list.

        As the layer list can be indexed by name each layer must have a unique
        name to ensure that there is only one layer corresponding to every
        name. This method updates the name to be unique if it is not already.

        The name is made unique by appending an index to it, for example
        'Image' -> 'Image [1]' or adding to the index, say 'Image [2]'.

        Parameters
        ----------
        value : 2-tuple of str
            Tuple of old name and new name.
        """
        old_name, new_name = value
        unique_name = force_name_unique(new_name, [l.name for l in self])
        if new_name != unique_name:
            self[old_name].name = unique_name

    @property
    def selected(self):
        """List of selected layers."""
        return [layer for layer in self if layer.selected]

    def move_selected(self, index, insert):
        """Reorder list by moving the item at index and inserting it
        at the insert index. If additional items are selected these will
        get inserted at the insert index too. This allows for rearranging
        the list based on dragging and dropping a selection of items, where
        index is the index of the primary item being dragged, and insert is
        the index of the drop location, and the selection indicates if
        multiple items are being dragged. If the moved layer is not selected
        select it.

        Parameters
        ----------
        index : int
            Index of primary item to be moved
        insert : int
            Index that item(s) will be inserted at
        """
        total = len(self)
        indices = list(range(total))
        if not self[index].selected:
            self.unselect_all()
            self[index].selected = True
        selected = [i for i in range(total) if self[i].selected]

        # remove all indices to be moved
        for i in selected:
            indices.remove(i)
        # adjust offset based on selected indices to move
        offset = sum([i < insert and i != index for i in selected])
        # insert indices to be moved at correct start
        for insert_idx, elem_idx in enumerate(selected, start=insert - offset):
            indices.insert(insert_idx, elem_idx)
        # reorder list
        self[:] = self[tuple(indices)]

    def unselect_all(self, ignore=None):
        """Unselects all layers expect any specified in ignore.

        Parameters
        ----------
        ignore : Layer | None
            Layer that should not be unselected if specified.
        """
        for layer in self:
            if layer.selected and layer != ignore:
                layer.selected = False

    def select_all(self):
        """Selects all layers."""
        for layer in self:
            if not layer.selected:
                layer.selected = True

    def remove_selected(self):
        """Removes selected items from list."""
        to_delete = []
        for i in range(len(self)):
            if self[i].selected:
                to_delete.append(i)
        to_delete.reverse()
        for i in to_delete:
            self.pop(i)
        if len(to_delete) > 0:
            first_to_delete = to_delete[-1]
            if first_to_delete == 0 and len(self) > 0:
                self[0].selected = True
            elif first_to_delete > 0:
                self[first_to_delete - 1].selected = True

    def select_next(self, shift=False):
        """Selects next item from list.
        """
        selected = []
        for i in range(len(self)):
            if self[i].selected:
                selected.append(i)
        if len(selected) > 0:
            if selected[-1] == len(self) - 1:
                if shift is False:
                    self.unselect_all(ignore=self[selected[-1]])
            elif selected[-1] < len(self) - 1:
                if shift is False:
                    self.unselect_all(ignore=self[selected[-1] + 1])
                self[selected[-1] + 1].selected = True
        elif len(self) > 0:
            self[-1].selected = True

    def select_previous(self, shift=False):
        """Selects previous item from list.
        """
        selected = []
        for i in range(len(self)):
            if self[i].selected:
                selected.append(i)
        if len(selected) > 0:
            if selected[0] == 0:
                if shift is False:
                    self.unselect_all(ignore=self[0])
            elif selected[0] > 0:
                if shift is False:
                    self.unselect_all(ignore=self[selected[0] - 1])
                self[selected[0] - 1].selected = True
        elif len(self) > 0:
            self[0].selected = True

    def toggle_selected_visibility(self):
        """Toggle visibility of selected layers"""
        for layer in self:
            if layer.selected:
                layer.visible = not layer.visible

    def save(
        self,
        path: str,
        *,
        selected: bool = False,
        plugin: Optional[str] = None,
    ) -> List[str]:
        """Save all or only selected layers to a path using writer plugins.

        If ``plugin`` is not provided and only one layer is targeted, then we
        directly call the corresponding``napari_write_<layer_type>`` hook (see
        :ref:`single layer writer hookspecs <write-single-layer-hookspecs>`)
        which will loop through implementations and stop when the first one
        returns a non-``None`` result. The order in which implementations are
        called can be changed with the Plugin sorter in the GUI or with the
        corresponding hook's
        :meth:`~napari.plugins._hook_callers._HookCaller.bring_to_front`
        method.

        If ``plugin`` is not provided and multiple layers are targeted,
        then we call
        :meth:`~napari.plugins.hook_specifications.napari_get_writer` which
        loops through plugins to find the first one that knows how to handle
        the combination of layers and is able to write the file. If no plugins
        offer :meth:`~napari.plugins.hook_specifications.napari_get_writer` for
        that combination of layers then the default
        :meth:`~napari.plugins.hook_specifications.napari_get_writer` will
        create a folder and call ``napari_write_<layer_type>`` for each layer
        using the ``Layer.name`` variable to modify the path such that the
        layers are written to unique files in the folder.

        If ``plugin`` is provided and a single layer is targeted, then we
        call the ``napari_write_<layer_type>`` for that plugin, and if it fails
        we error.

        If ``plugin`` is provided and multiple layers are targeted, then
        we call we call
        :meth:`~napari.plugins.hook_specifications.napari_get_writer` for
        that plugin, and if it doesn’t return a ``WriterFunction`` we error,
        otherwise we call it and if that fails if it we error.

        Parameters
        ----------
        path : str
            A filepath, directory, or URL to open.  Extensions may be used to
            specify output format (provided a plugin is avaiable for the
            requested format).
        selected : bool
            Optional flag to only save selected layers. False by default.
        plugin : str, optional
            Name of the plugin to use for saving. If None then all plugins
            corresponding to appropriate hook specification will be looped
            through to find the first one that can save the data.

        Returns
        -------
        list of str
            File paths of any files that were written.
        """
        from ..plugins.io import save_layers

        layers = self.selected if selected else list(self)

        if not layers:
            import warnings

            warnings.warn(f"No layers {'selected' if selected else 'to save'}")
            return []

        return save_layers(path, layers, plugin=plugin)
