import warnings
from logging import getLogger
from typing import List, Optional, Sequence, Union

from napari_plugin_engine import (
    HookImplementation,
    PluginCallError,
    PluginManager,
)

from ..layers import Layer
from ..types import LayerData
from ..utils.misc import abspath_or_url
from . import plugin_manager as napari_plugin_manager

logger = getLogger(__name__)


def read_data_with_plugins(
    path: Union[str, Sequence[str]],
    plugin: Optional[str] = None,
    plugin_manager: PluginManager = napari_plugin_manager,
) -> List[LayerData]:
    """Iterate reader hooks and return first non-None LayerData or None.

    This function returns as soon as the path has been read successfully,
    while catching any plugin exceptions, storing them for later retrievial,
    providing useful error messages, and relooping until either layer data is
    returned, or no valid readers are found.

    Exceptions will be caught and stored as PluginErrors
    (in plugins.exceptions.PLUGIN_ERRORS)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to open
    plugin : str, optional
        Name of a plugin to use.  If provided, will force ``path`` to be read
        with the specified ``plugin``.  If the requested plugin cannot read
        ``path``, a PluginCallError will be raised.
    plugin_manager : plugins.PluginManager, optional
        Instance of a napari PluginManager.  by default the main napari
        plugin_manager will be used.

    Returns
    -------
    LayerData : list of tuples, or None
        LayerData that can be passed to :func:`Viewer._add_layer_from_data()
        <napari.components.add_layers_mixin.AddLayersMixin._add_layer_from_data>`.
        ``LayerData`` is a list tuples, where each tuple is one of
        ``(data,)``, ``(data, meta)``, or ``(data, meta, layer_type)`` .

        If no reader plugins are (or they all error), returns ``None``

    Raises
    ------
    PluginCallError
        If ``plugin`` is specified but raises an Exception while reading.
    """
    hook_caller = plugin_manager.hook.napari_get_reader

    if plugin:
        if plugin not in plugin_manager.plugins:
            names = {i.plugin_name for i in hook_caller.get_hookimpls()}
            raise ValueError(
                f"There is no registered plugin named '{plugin}'.\n"
                f"Names of plugins offering readers are: {names}"
            )
        reader = hook_caller._call_plugin(plugin, path=path)
        if not callable(reader):
            raise ValueError(f'Plugin {plugin!r} does not support file {path}')
        return reader(path) or []

    errors: List[PluginCallError] = []
    path = abspath_or_url(path)
    skip_impls: List[HookImplementation] = []
    layer_data = None
    while True:
        result = hook_caller.call_with_result_obj(
            path=path, _skip_impls=skip_impls
        )
        reader = result.result  # will raise exceptions if any occurred
        if not reader:
            # we're all out of reader plugins
            break
        try:
            layer_data = reader(path)  # try to read data
            if layer_data:
                break
        except Exception as exc:
            # collect the error and log it, but don't raise it.
            err = PluginCallError(result.implementation, cause=exc)
            err.log(logger=logger)
            errors.append(err)
        # don't try this impl again
        skip_impls.append(result.implementation)

    if not layer_data:
        # if layer_data is empty, it means no plugin could read path
        # we just want to provide some useful feedback, which includes
        # whether or not paths were passed to plugins as a list.
        if isinstance(path, (tuple, list)):
            path_repr = f"[{path[0]}, ...] as stack"
        else:
            path_repr = repr(path)
        # TODO: change to a warning notification in a later PR
        raise ValueError(f'No plugin found capable of reading {path_repr}.')

    if errors:
        names = set([repr(e.plugin_name) for e in errors])
        err_msg = f"({len(errors)}) error{'s' if len(errors) > 1 else ''} "
        err_msg += f"occurred in plugins: {', '.join(names)}. "
        err_msg += 'See full error logs in "Plugins → Plugin Errors..."'
        logger.error(err_msg)

    return layer_data or []


def save_layers(
    path: str, layers: List[Layer], *, plugin: Optional[str] = None,
) -> List[str]:
    """Write list of layers or individual layer to a path using writer plugins.

    If ``plugin`` is not provided and only one layer is passed, then we
    directly call ``plugin_manager.hook.napari_write_<layer>()`` which
    will loop through implementations and stop when the first one returns a
    non-None result. The order in which implementations are called can be
    changed with the hook ``bring_to_front`` method, for instance:
    ``plugin_manager.hook.napari_write_points.bring_to_front``

    If ``plugin`` is not provided and multiple layers are passed, then
    we call ``plugin_manager.hook.napari_get_writer()`` which loops through
    plugins to find the first one that knows how to handle the combination of
    layers and is able to write the file. If no plugins offer
    ``napari_get_writer`` for that combination of layers then the builtin
    ``napari_get_writer`` implementation will create a folder and call
    ``napari_write_<layer>`` for each layer using the ``layer.name`` variable
    to modify the path such that the layers are written to unique files in the
    folder.

    If ``plugin`` is provided and a single layer is passed, then
    we call the ``napari_write_<layer_type>`` for that plugin, and if it
    fails we error.

    If a ``plugin`` is provided and multiple layers are passed, then
    we call we call ``napari_get_writer`` for that plugin, and if it
    doesn’t return a WriterFunction we error, otherwise we call it and if
    that fails if it we error.

    Parameters
    ----------
    path : str
        A filepath, directory, or URL to open.
    layers : List[layers.Layer]
        List of layers to be saved. If only a single layer is passed then
        we use the hook specification corresponding to its layer type,
        ``napari_write_<layer_type>``. If multiple layers are passed then we
        use the ``napari_get_writer`` hook specification.
    plugin : str, optional
        Name of the plugin to use for saving. If None then all plugins
        corresponding to appropriate hook specification will be looped
        through to find the first one that can save the data.

    Returns
    -------
    list of str
        File paths of any files that were written.
    """
    if len(layers) > 1:
        written = _write_multiple_layers_with_plugins(
            path, layers, plugin_name=plugin
        )
    elif len(layers) == 1:
        _written = _write_single_layer_with_plugins(
            path, layers[0], plugin_name=plugin
        )
        written = [_written] if _written else []
    else:
        written = []

    if not written:
        # if written is empty, it means no plugin could write the
        # path/layers combination
        # we just want to provide some useful feedback
        warnings.warn(
            'No data written! There may be no plugins '
            f'capable of writing these {len(layers)} layers to {path}.'
        )

    return written


def _write_multiple_layers_with_plugins(
    path: str,
    layers: List[Layer],
    *,
    plugin_name: Optional[str] = None,
    plugin_manager=napari_plugin_manager,
) -> List[str]:
    """Write data from multiple layers data with a plugin.

    If a ``plugin_name`` is not provided we loop through plugins to find the
    first one that knows how to handle the combination of layers and is able to
    write the file. If no plugins offer ``napari_get_writer`` for that
    combination of layers then the default ``napari_get_writer`` will create a
    folder and call ``napari_write_<layer>`` for each layer using the
    ``layer.name`` variable to modify the path such that the layers are written
    to unique files in the folder.

    If a ``plugin_name`` is provided, then call ``napari_get_writer`` for that
    plugin. If it doesn’t return a ``WriterFunction`` we error, otherwise we
    call it and if that fails if it we error.

    Exceptions will be caught and stored as PluginErrors
    (in plugins.exceptions.PLUGIN_ERRORS)

    Parameters
    ----------
    path : str
        The path (file, directory, url) to write.
    layers : List of napari.layers.Layer
        List of napari layers to write.
    plugin_name : str, optional
        If provided, force the plugin manager to use the ``napari_get_writer``
        from the requested ``plugin_name``.  If none is available, or if it is
        incapable of handling the layers, this function will fail.
    plugin_manager : plugins.PluginManager, optional
        Instance of a PluginManager.  by default the main napari
        plugin_manager will be used.

    Returns
    -------
    list of str
        A list of filenames, if any, that were written.
    """
    layer_data = [layer.as_layer_data_tuple() for layer in layers]
    layer_types = [ld[2] for ld in layer_data]

    hook_caller = plugin_manager.hook.napari_get_writer
    path = abspath_or_url(path)
    if plugin_name:
        # if plugin has been specified we just directly call napari_get_writer
        # with that plugin_name.
        if plugin_name not in plugin_manager.plugins:
            names = {i.plugin_name for i in hook_caller.get_hookimpls()}
            raise ValueError(
                f"There is no registered plugin named '{plugin_name}'.\n"
                f"Names of plugins offering writers are: {names}"
            )
        implementation = hook_caller.get_plugin_implementation(plugin_name)
        writer_function = hook_caller(
            _plugin=plugin_name, path=path, layer_types=layer_types
        )
    else:
        result = hook_caller.call_with_result_obj(
            path=path, layer_types=layer_types, _return_impl=True
        )
        writer_function = result.result
        implementation = result.implementation

    if not callable(writer_function):
        if plugin_name:
            msg = f'Requested plugin "{plugin_name}" is not capable'
        else:
            msg = 'Unable to find plugin capable'
        msg += f' of writing this combination of layer types: {layer_types}'
        raise ValueError(msg)

    try:
        return writer_function(abspath_or_url(path), layer_data)
    except Exception as exc:
        raise PluginCallError(implementation, cause=exc)


def _write_single_layer_with_plugins(
    path: str,
    layer: Layer,
    *,
    plugin_name: Optional[str] = None,
    plugin_manager=napari_plugin_manager,
) -> Optional[str]:
    """Write single layer data with a plugin.

    If ``plugin_name`` is not provided then we just directly call
    ``plugin_manager.hook.napari_write_<layer>()`` which will loop through
    implementations and stop when the first one returns a non-None result. The
    order in which implementations are called can be changed with the
    implementation sorter/disabler.

    If ``plugin_name`` is provided, then we call the
    ``napari_write_<layer_type>`` for that plugin, and if it fails we error.

    Exceptions will be caught and stored as PluginErrors
    (in plugins.exceptions.PLUGIN_ERRORS)

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
    plugin_manager : plugins.PluginManager, optional
        Instance of a napari PluginManager.  by default the main napari
        plugin_manager will be used.

    Returns
    -------
    path : str or None
        If data is successfully written, return the ``path`` that was written.
        Otherwise, if nothing was done, return ``None``.
    """
    hook_caller = getattr(
        plugin_manager.hook, f'napari_write_{layer._type_string}'
    )

    if plugin_name and (plugin_name not in plugin_manager.plugins):
        names = {i.plugin_name for i in hook_caller.get_hookimpls()}
        raise ValueError(
            f"There is no registered plugin named '{plugin_name}'.\n"
            "Plugins capable of writing layer._type_string layers"
            f"are: {names}"
        )

    # Call the hook_caller
    return hook_caller(
        _plugin=plugin_name,
        path=abspath_or_url(path),
        data=layer.data,
        meta=layer._get_state(),
    )
