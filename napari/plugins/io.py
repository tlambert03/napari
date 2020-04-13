from . import PluginError, get_plugin_manager
from typing import Optional, Union, Sequence, List
from ..types import LayerData
from ..layers import Layer
from logging import getLogger

logger = getLogger(__name__)


def read_data_with_plugins(
    path: Union[str, Sequence[str]]
) -> Optional[LayerData]:
    """Iterate reader hooks and return first non-None LayerData or None.

    This function returns as soon as the path has been read successfully,
    while catching any plugin exceptions, storing them for later retrievial,
    providing useful error messages, and relooping until either layer data is
    returned, or no valid readers are found.

    Exceptions will be caught and stored as PluginErrors
    (in plugins.PLUGIN_ERRORS)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to open.

    Returns
    -------
    LayerData : list of tuples, or None
        LayerData that can be passed to :func:`Viewer._add_layer_from_data()
        <napari.components.add_layers_mixin.AddLayersMixin._add_layer_from_data>`.
        ``LayerData`` is a list tuples, where each tuple is one of
        ``(data,)``, ``(data, meta)``, or ``(data, meta, layer_type)`` .

        If no reader plugins are (or they all error), returns ``None``
    """
    plugin_manager = get_plugin_manager()
    skip_impls = []
    while True:
        (reader, implementation) = plugin_manager.hook.napari_get_reader(
            path=path, _return_impl=True, _skip_impls=skip_impls
        )
        if not reader:
            # we're all out of reader plugins
            return None
        try:
            return reader(path)  # try to read data
        except Exception as exc:
            # If the hook did return a reader, but the reader then failed
            # while trying to read the path, we store the traceback for later
            # retrieval, warn the user, and continue looking for readers
            # (skipping this one)
            msg = (
                f"Error in plugin '{implementation.plugin_name}', "
                "hook 'napari_get_reader'"
            )
            # instantiating this PluginError stores it in
            # plugins.exceptions.PLUGIN_ERRORS, where it can be retrieved later
            err = PluginError(
                msg, implementation.plugin_name, implementation.plugin.__name__
            )
            err.__cause__ = exc  # like `raise PluginError() from exc`

            skip_impls.append(implementation)  # don't try this impl again
            if implementation.plugin_name != 'builtins':
                # If builtins doesn't work, they will get a "no reader" found
                # error anyway, so it looks a bit weird to show them that the
                # "builtin plugin" didn't work.
                logger.error(err.format_with_contact_info())


def write_layers_with_plugins(
    path: str,
    layers: Union[List[Layer], Layer],
    plugin_name: Optional[str] = None,
):
    """Write list of layers of individual layer to a path using writer plugins.

    If a `plugin_name` is not provided and only one layer is passed, then we
    just directly call ``plugin_manager.hook.napari_write_<layer>()`` which
    will loop through implementations and stop when the first one returns a
    non-None result. The order in which implementations are called can be
    changed with the implementation sorter/disabler.

    If a `plugin_name` is not provided and multiple layers are passed, then we
    call ``plugin_manager.hook.napari_get_writer()`` which loops through
    plugins to find the first one that knows how to handle the combination
    of layers and is able to write the file. If no plugins offer
    `napari_get_writer` for that combination of layers then the default
    `napari_get_writer` will create a folder and call
    `napari_write_<layer>` for each layer using the `layer.name` variable
    to modify the path such that the layers are written to unique files in
    the folder.

    If a `plugin_name` is provided and a single layer is passed, then
    we call the `napari_write_<layer_type>` for that plugin, and if it
    fails we error.

    If a `plugin_name` is provided and multiple layers are passed, then
    we call we call `napari_get_writer` for that plugin, and if it
    doesn’t return a WriterFunction we error, otherwise we call it and if
    that fails if it we error.

    Parameters
    ----------
    path : str
        A filepath, directory, or URL (or a list of any) to open.
    layers : List[layers.Layer]
        List of layers to be saved. If only a single layer is passed then
        we use the hook specification corresponding to its layer type,
        `napari_write_<layer_type>`. If multiple layers are passed then we
        use the `napari_get_writer` hook specification.
    plugin_name : str, optional
        Name of the plugin to use for saving. If None then all plugins
        corresponding to appropriate hook specification will be looped
        through to find the first one that can save the data.

    Returns
    -------
    bool
        Return True if data is successfully written.
    """
    if isinstance(layers, list):
        if len(layers) > 1:
            return _write_multiple_layers(path, layers, plugin_name)
        elif len(layers) == 1:
            layers = layers[0]
    if isinstance(layers, Layer):
        return _write_single_layer(path, layers, plugin_name)
    return False


def _write_multiple_layers(
    path: str, layers: List[Layer], plugin_name: Optional[str] = None
):
    """Write data from multiple layers data with a plugin.

    If a `plugin_name` is not provided we loops through plugins to find the
    first one that knows how to handle the combination of layers and is able to
    write the file. If no plugins offer `napari_get_writer` for that
    combination of layers then the default `napari_get_writer` will create a
    folder and call `napari_write_<layer>` for each layer using the
    `layer.name` variable to modify the path such that the layers are written
    to unique files in the folder.

    If a `plugin_name` is provided, then we call we call `napari_get_writer`
    for that plugin, and if it doesn’t return a WriterFunction we error,
    otherwise we call it and if that fails if it we error.

    Exceptions will be caught and stored as PluginErrors
    (in plugin_manager._exceptions)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to write.
    layers : List of napari.layers.Layer
        List of napari layers to write.
    """
    layer_data = [
        (layer.data, layer._get_state(), layer.__class__.__name__.lower())
        for layer in layers
    ]
    layer_types = [ld[2] for ld in layer_data]

    plugin_manager = get_plugin_manager()

    if plugin_name is None:
        # Loop through all plugins using first successful one
        skip_impls = []
        while True:
            (writer, implementation) = plugin_manager.hook.napari_get_writer(
                path=path,
                layer_types=layer_types,
                _return_impl=True,
                _skip_impls=skip_impls,
            )
            if not writer:
                # we're all out of writer plugins
                return None
            try:
                return writer(path, layer_data)  # try to write data
            except Exception as exc:
                # If the hook did return a writer, but the writer then
                # failed while trying to write the path, we store the traceback
                # for later retrieval, warn the user, and continue looking for
                # writers (skipping this one)
                msg = (
                    f"Error in plugin '{implementation.plugin_name}', "
                    "hook 'napari_get_writer'"
                )
                # instantiating this PluginError stores it in
                # plugins.exceptions.PLUGIN_ERRORS, where it can be retrieved
                # later
                err = PluginError(
                    msg,
                    implementation.plugin_name,
                    implementation.plugin.__name__,
                )
                err.__cause__ = exc  # like `raise PluginError() from exc`

                skip_impls.append(implementation)  # don't try this impl again
                if implementation.plugin_name != 'builtins':
                    # If builtins doesn't work, they will get a "no writer"
                    # found error anyway, so it looks a bit weird to show them
                    # that the "builtin plugin" didn't work.
                    logger.error(err.format_with_contact_info())
        else:
            # Call napari_get_writer from named plugin
            writer = plugin_manager.hook.napari_get_writer(
                _plugin=plugin_name, path=path, layer_types=layer_types
            )
            writer(path, layer_data)  # try to write data


def _write_single_layer(
    path: str, layer: Layer, plugin_name: Optional[str] = None
):
    """Write single layer data with a plugin.

    If a `plugin_name` is not provided then we just directly call
    ``plugin_manager.hook.napari_write_<layer>()`` which will loop through
    implementations and stop when the first one returns a non-None result. The
    order in which implementations are called can be changed with the
    implementation sorter/disabler.

    If a `plugin_name` is provided, then we call the
    `napari_write_<layer_type>` for that plugin, and if it fails we error.

    Exceptions will be caught and stored as PluginErrors
    (in plugin_manager._exceptions)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to write.
    layer : napari.layers.Layer
        Layer to be written out.
    plugin_name : str, optional
        Name of the plugin to write data with. If None then all plugins
        corresponding to appropriate hook specification will be looped
        through to find the first one that can write the data.
    """
    layer_type = layer.__class__.__name__.lower()

    hook_specification = getattr(
        get_plugin_manager().hook, 'napari_write_' + layer_type
    )

    if plugin_name is None:
        # Loop through all plugins with hook_specification using first
        # successful one
        return hook_specification(
            path=path, data=layer.data, meta=layer._get_state()
        )
    else:
        # Call hook_specification from named plugin
        return hook_specification(
            _plugin=plugin_name,
            path=path,
            data=layer.data,
            meta=layer._get_state(),
        )
