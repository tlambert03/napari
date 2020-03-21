import os
import warnings

from abc import ABC, abstractmethod
from contextlib import contextmanager
from xml.etree.ElementTree import Element, tostring
import numpy as np
from skimage import img_as_ubyte
from ._base_constants import Blending

from ...components import Dims
from ...utils.event import EmitterGroup, Event
from ...utils.key_bindings import KeymapProvider
from ...utils.misc import ROOT_DIR
from ...utils.naming import magic_name
from ...utils.status_messages import status_format, format_float
from ..transforms import ScaleTranslate, TransformChain


class Layer(KeymapProvider, ABC):
    """Base layer class.

    Parameters
    ----------
    name : str
        Name of the layer.
    metadata : dict
        Layer metadata.
    scale : tuple of float
        Scale factors for the layer.
    translate : tuple of float
        Translation values for the layer.
    opacity : float
        Opacity of the layer visual, between 0.0 and 1.0.
    blending : str
        One of a list of preset blending modes that determines how RGB and
        alpha values of the layer visual get mixed. Allowed values are
        {'opaque', 'translucent', and 'additive'}.
    visible : bool
        Whether the layer visual is currently being displayed.


    Attributes
    ----------
    name : str
        Unique name of the layer.
    opacity : flaot
        Opacity of the layer visual, between 0.0 and 1.0.
    visible : bool
        Whether the layer visual is currently being displayed.
    blending : Blending
        Determines how RGB and alpha values get mixed.
            Blending.OPAQUE
                Allows for only the top layer to be visible and corresponds to
                depth_test=True, cull_face=False, blend=False.
            Blending.TRANSLUCENT
                Allows for multiple layers to be blended with different opacity
                and corresponds to depth_test=True, cull_face=False,
                blend=True, blend_func=('src_alpha', 'one_minus_src_alpha').
            Blending.ADDITIVE
                Allows for multiple layers to be blended together with
                different colors and opacity. Useful for creating overlays. It
                corresponds to depth_test=False, cull_face=False, blend=True,
                blend_func=('src_alpha', 'one').
    scale : tuple of float
        Scale factors for the layer.
    translate : tuple of float
        Translation values for the layer.
    z_index : int
        Depth of the layer visual relative to other visuals in the scenecanvas.
    coordinates : tuple of float
        Coordinates of the cursor in the image space of each layer. The length
        of the tuple is equal to the number of dimensions of the layer.
    position : 2-tuple of int
        Cursor position in the image space of only the displayed dimensions.
    shape : tuple of int
        Size of the data in the layer.
    ndim : int
        Dimensionality of the layer.
    selected : bool
        Flag if layer is selected in the viewer or not.
    thumbnail : (N, M, 4) array
        Array of thumbnail data for the layer.
    status : str
        Displayed in status bar bottom left.
    help : str
        Displayed in status bar bottom right.
    interactive : bool
        Determine if canvas pan/zoom interactivity is enabled.
    cursor : str
        String identifying which cursor displayed over canvas.
    cursor_size : int | None
        Size of cursor if custom. None yields default size
    scale_factor : float
        Conversion factor from canvas coordinates to image coordinates, which
        depends on the current zoom level.

    Notes
    -----
    Must define the following:
        * `_get_range()`: called by `range` property
        * `data` property (setter & getter)

    May define the following:
        * `_set_view_slice(indices)`: called to set currently viewed slice
        * `_basename()`: base/default name of the layer
    """

    def __init__(
        self,
        data,
        ndim,
        *,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        opacity=1,
        blending='translucent',
        visible=True,
    ):
        super().__init__()

        if name is None and data is not None and os.getenv('MAGICNAME'):
            name = magic_name(data, path_prefix=ROOT_DIR)

        self.metadata = metadata or {}
        self._opacity = opacity
        self._blending = Blending(blending)
        self._visible = visible
        self._selected = True
        self._freeze = False
        self._status = 'Ready'
        self._help = ''
        self._cursor = 'standard'
        self._cursor_size = None
        self._interactive = True
        self._value = None
        self.scale_factor = 1

        self.dims = Dims(ndim)

        if scale is None:
            scale = [1] * ndim
        if translate is None:
            translate = [0] * ndim

        # Create a transform chain consisting of three transforms:
        # 1. `tile2data`: An initial transform only needed displaying tiles
        #   of an image. It maps pixels of the tile into the coordinate space
        #   of the full resolution data and can usually be represented by a
        #   scale factor and a translation. A common use case is viewing part
        #   of lower resolution level of an image pyramid, another is using a
        #   downsampled version of an image when the full image size is larger
        #   than the maximum allowed texture size of your graphics card.
        # 2. `data2world`: The main transform mapping data to a world-like
        #   coordinate.
        # 3. `world2grid`: An additional transform mapping world-coordinates
        #   into a grid for looking at layers side-by-side.
        self._transforms = TransformChain(
            [
                ScaleTranslate(
                    np.ones(ndim), np.zeros(ndim), name='tile2data'
                ),
                ScaleTranslate(scale, translate, name='data2world'),
                ScaleTranslate(
                    np.ones(ndim), np.zeros(ndim), name='world2grid'
                ),
            ]
        )

        self.coordinates = (0,) * ndim
        self._position = (0,) * self.dims.ndisplay
        self.is_pyramid = False
        self._editable = True

        self._thumbnail_shape = (32, 32, 4)
        self._thumbnail = np.zeros(self._thumbnail_shape, dtype=np.uint8)
        self._update_properties = True
        self._name = ''
        self.events = EmitterGroup(
            source=self,
            auto_connect=True,
            refresh=Event,
            set_data=Event,
            blending=Event,
            opacity=Event,
            visible=Event,
            select=Event,
            deselect=Event,
            scale=Event,
            translate=Event,
            data=Event,
            name=Event,
            thumbnail=Event,
            status=Event,
            help=Event,
            interactive=Event,
            cursor=Event,
            cursor_size=Event,
            editable=Event,
        )
        self.name = name

        self.events.data.connect(lambda e: self._set_editable())
        self.dims.events.ndisplay.connect(lambda e: self._set_editable())
        self.dims.events.order.connect(self.refresh)
        self.dims.events.ndisplay.connect(self._update_dims)
        self.dims.events.order.connect(self._update_dims)
        self.dims.events.axis.connect(self.refresh)

        self.mouse_move_callbacks = []
        self.mouse_drag_callbacks = []
        self._persisted_mouse_event = {}
        self._mouse_drag_gen = {}

    def __str__(self):
        """Return self.name."""
        return self.name

    def __repr__(self):
        cls = type(self)
        return f"<{cls.__name__} layer {repr(self.name)} at {hex(id(self))}>"

    @classmethod
    def _basename(cls):
        return f'{cls.__name__}'

    @property
    def name(self):
        """str: Unique name of the layer."""
        return self._name

    @name.setter
    def name(self, name):
        if name == self.name:
            return
        if not name:
            name = self._basename()
        self._name = name
        self.events.name()

    @property
    def opacity(self):
        """float: Opacity value between 0.0 and 1.0.
        """
        return self._opacity

    @opacity.setter
    def opacity(self, opacity):
        if not 0.0 <= opacity <= 1.0:
            raise ValueError(
                'opacity must be between 0.0 and 1.0; ' f'got {opacity}'
            )

        self._opacity = opacity
        self._update_thumbnail()
        self.status = format_float(self.opacity)
        self.events.opacity()

    @property
    def blending(self):
        """Blending mode: Determines how RGB and alpha values get mixed.

            Blending.OPAQUE
                Allows for only the top layer to be visible and corresponds to
                depth_test=True, cull_face=False, blend=False.
            Blending.TRANSLUCENT
                Allows for multiple layers to be blended with different opacity
                and corresponds to depth_test=True, cull_face=False,
                blend=True, blend_func=('src_alpha', 'one_minus_src_alpha').
            Blending.ADDITIVE
                Allows for multiple layers to be blended together with
                different colors and opacity. Useful for creating overlays. It
                corresponds to depth_test=False, cull_face=False, blend=True,
                blend_func=('src_alpha', 'one').
        """
        return str(self._blending)

    @blending.setter
    def blending(self, blending):
        self._blending = Blending(blending)
        self.events.blending()

    @property
    def visible(self):
        """bool: Whether the visual is currently being displayed."""
        return self._visible

    @visible.setter
    def visible(self, visibility):
        self._visible = visibility
        self.refresh()
        self.events.visible()
        if self.visible:
            self.editable = self._set_editable()
        else:
            self.editable = False

    @property
    def editable(self):
        """bool: Whether the current layer data is editable from the viewer."""
        return self._editable

    @editable.setter
    def editable(self, editable):
        if self._editable == editable:
            return
        self._editable = editable
        self._set_editable(editable=editable)
        self.events.editable()

    @property
    def scale(self):
        """list: Anisotropy factors to scale data into world coordinates."""
        return self._transforms['data2world'].scale

    @scale.setter
    def scale(self, scale):
        self._transforms['data2world'].scale = np.array(scale)
        self._update_dims()
        self.events.scale()

    @property
    def translate(self):
        """list: Factors to shift the layer by in units of world coordinates."""
        return self._transforms['data2world'].translate

    @translate.setter
    def translate(self, translate):
        self._transforms['data2world'].translate = np.array(translate)
        self._update_dims()
        self.events.translate()

    @property
    def translate_grid(self):
        """list: Factors to shift the layer by."""
        return self._transforms['world2grid'].translate

    @translate_grid.setter
    def translate_grid(self, translate_grid):
        if np.all(self.translate_grid == translate_grid):
            return
        self._transforms['world2grid'].translate = np.array(translate_grid)
        self.events.translate()

    @property
    def position(self):
        """tuple of int: Cursor position in image of displayed dimensions."""
        return self._position

    @position.setter
    def position(self, position):
        if self._position == position:
            return
        self._position = position
        self._update_coordinates()

    def _update_dims(self, event=None):
        """Updates dims model, which is useful after data has been changed."""
        ndim = self._get_ndim()
        ndisplay = self.dims.ndisplay

        # If the dimensionality is changing then if the number of dimensions
        # is becoming smaller trim the property from the beginning, and if
        # the number of dimensions is becoming larger pad from the beginning
        if len(self.position) > ndisplay:
            self._position = self._position[-ndisplay:]
        elif len(self.position) < ndisplay:
            self._position = (0,) * (ndisplay - len(self.position)) + tuple(
                self.position
            )

        old_ndim = self.dims.ndim
        if old_ndim > ndim:
            keep_axes = range(old_ndim - ndim, old_ndim)
            self._transforms = self._transforms.set_slice(keep_axes)
        elif old_ndim < ndim:
            new_axes = range(ndim - old_ndim)
            self._transforms = self._transforms.expand_dims(new_axes)

        self.dims.ndim = ndim

        curr_range = self._get_range()
        for i, r in enumerate(curr_range):
            self.dims.set_range(i, r)

        self.refresh()
        self._update_coordinates()

    @property
    @abstractmethod
    def data(self):
        # user writes own docstring
        raise NotImplementedError()

    @data.setter
    @abstractmethod
    def data(self, data):
        raise NotImplementedError()

    @abstractmethod
    def _get_extent(self):
        raise NotImplementedError()

    @abstractmethod
    def _get_ndim(self):
        raise NotImplementedError()

    def _set_editable(self, editable=None):
        if editable is None:
            self.editable = True

    def _get_range(self):
        extent = self._get_extent()
        return tuple(
            (s * e[0], s * e[1], s) for e, s in zip(extent, self.scale)
        )

    def _get_base_state(self):
        """Get dictionary of attributes on base layer.

        Returns
        -------
        state : dict
            Dictionary of attributes on base layer.
        """
        base_dict = {
            'name': self.name,
            'metadata': self.metadata,
            'scale': list(self.scale),
            'translate': list(self.translate),
            'opacity': self.opacity,
            'blending': self.blending,
            'visible': self.visible,
        }
        return base_dict

    @abstractmethod
    def _get_state(self):
        raise NotImplementedError()

    @property
    def thumbnail(self):
        """array: Integer array of thumbnail for the layer"""
        return self._thumbnail

    @thumbnail.setter
    def thumbnail(self, thumbnail):
        if 0 in thumbnail.shape:
            thumbnail = np.zeros(self._thumbnail_shape, dtype=np.uint8)
        if thumbnail.dtype != np.uint8:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                thumbnail = img_as_ubyte(thumbnail)

        padding_needed = np.subtract(self._thumbnail_shape, thumbnail.shape)
        pad_amounts = [(p // 2, (p + 1) // 2) for p in padding_needed]
        thumbnail = np.pad(thumbnail, pad_amounts, mode='constant')

        # blend thumbnail with opaque black background
        background = np.zeros(self._thumbnail_shape, dtype=np.uint8)
        background[..., 3] = 255

        f_dest = thumbnail[..., 3][..., None] / 255
        f_source = 1 - f_dest
        thumbnail = thumbnail * f_dest + background * f_source

        self._thumbnail = thumbnail.astype(np.uint8)
        self.events.thumbnail()

    @property
    def ndim(self):
        """int: Number of dimensions in the data."""
        return self.dims.ndim

    @property
    def shape(self):
        """tuple of int: Shape of the data."""
        return tuple(
            np.round(r[1] - r[0]).astype(int) for r in self.dims.range
        )

    @property
    def selected(self):
        """bool: Whether this layer is selected or not."""
        return self._selected

    @selected.setter
    def selected(self, selected):
        if selected == self.selected:
            return
        self._selected = selected

        if selected:
            self.events.select()
        else:
            self.events.deselect()

    @property
    def status(self):
        """str: displayed in status bar bottom left."""
        return self._status

    @status.setter
    def status(self, status):
        if status == self.status:
            return
        self.events.status(status=status)
        self._status = status

    @property
    def help(self):
        """str: displayed in status bar bottom right."""
        return self._help

    @help.setter
    def help(self, help):
        if help == self.help:
            return
        self.events.help(help=help)
        self._help = help

    @property
    def interactive(self):
        """bool: Determine if canvas pan/zoom interactivity is enabled."""
        return self._interactive

    @interactive.setter
    def interactive(self, interactive):
        if interactive == self.interactive:
            return
        self.events.interactive(interactive=interactive)
        self._interactive = interactive

    @property
    def cursor(self):
        """str: String identifying cursor displayed over canvas."""
        return self._cursor

    @cursor.setter
    def cursor(self, cursor):
        if cursor == self.cursor:
            return
        self.events.cursor(cursor=cursor)
        self._cursor = cursor

    @property
    def cursor_size(self):
        """int | None: Size of cursor if custom. None yields default size."""
        return self._cursor_size

    @cursor_size.setter
    def cursor_size(self, cursor_size):
        if cursor_size == self.cursor_size:
            return
        self.events.cursor_size(cursor_size=cursor_size)
        self._cursor_size = cursor_size

    @abstractmethod
    def _set_view_slice(self):
        raise NotImplementedError()

    @abstractmethod
    def _update_thumbnail(self):
        raise NotImplementedError()

    @abstractmethod
    def _get_value(self):
        raise NotImplementedError()

    def get_value(self):
        """Value of data at current coordinates.

        Returns
        -------
        value : tuple, None
            Value of the data at the coordinates.
        """
        if self.visible:
            return self._get_value()
        else:
            return None

    @contextmanager
    def block_update_properties(self):
        self._update_properties = False
        yield
        self._update_properties = True

    def _set_highlight(self, force=False):
        """Render layer highlights when appropriate.

        Parameters
        ----------
        force : bool
            Bool that forces a redraw to occur when `True`.
        """
        pass

    def refresh(self, event=None):
        """Refresh all layer data based on current view slice.
        """
        if self.visible:
            self._set_view_slice()
            self.events.set_data()
            self._update_thumbnail()
            self._update_coordinates()
            self._set_highlight(force=True)

    def _update_coordinates(self):
        """Insert the cursor position into the correct position in the
        tuple of indices and update the cursor coordinates.
        """
        coords = list(self.dims.indices)
        for d, p in zip(self.dims.displayed, self.position):
            coords[d] = p
        self.coordinates = tuple(coords)
        self._value = self.get_value()
        self.status = self.get_message()

    def get_message(self):
        """Generate a status message based on the coordinates and value

        Returns
        ----------
        msg : string
            String containing a message that can be used as a status update.
        """
        coordinates = self._transforms.simplified(self.coordinates)
        full_coord = np.round(coordinates).astype(int)

        msg = f'{self.name} {full_coord}'

        value = self._value
        if value is not None:
            if isinstance(value, tuple) and value != (None, None):
                # it's a pyramid -> value = (data_level, value)
                msg += f': {status_format(value[0])}'
                if value[1] is not None:
                    msg += f', {status_format(value[1])}'
            else:
                # it's either a grayscale or rgb image (scalar or list)
                msg += f': {status_format(value)}'
        return msg

    def to_xml_list(self):
        """Generates a list of xml elements for the layer.

        Returns
        ----------
        xml : list of xml.etree.ElementTree.Element
            List of a single xml element specifying the currently viewed image
            as a png according to the svg specification.
        """
        return []

    def to_svg(self, file=None, canvas_shape=None):
        """Convert the current layer state to an SVG.

        Parameters
        ----------
        file : path-like object, optional
            An object representing a file system path. A path-like object is
            either a str or bytes object representing a path, or an object
            implementing the `os.PathLike` protocol. If passed the svg will be
            written to this file
        canvas_shape : 4-tuple, optional
            View box of SVG canvas to be generated specified as `min-x`,
            `min-y`, `width` and `height`. If not specified, calculated
            from the last two dimensions of the layer.

        Returns
        ----------
        svg : string
            SVG representation of the layer.
        """

        if canvas_shape is None:
            min_shape = [r[0] for r in self.dims.range[-2:]]
            max_shape = [r[1] for r in self.dims.range[-2:]]
            shape = np.subtract(max_shape, min_shape)
        else:
            shape = canvas_shape[2:]
            min_shape = canvas_shape[:2]

        props = {
            'xmlns': 'http://www.w3.org/2000/svg',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        }

        xml = Element(
            'svg',
            height=f'{shape[0]}',
            width=f'{shape[1]}',
            version='1.1',
            **props,
        )

        transform = f'translate({-min_shape[1]} {-min_shape[0]})'
        xml_transform = Element('g', transform=transform)

        xml_list = self.to_xml_list()
        for x in xml_list:
            xml_transform.append(x)
        xml.append(xml_transform)

        svg = (
            '<?xml version=\"1.0\" standalone=\"no\"?>\n'
            + '<!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\"\n'
            + '\"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">\n'
            + tostring(xml, encoding='unicode', method='xml')
        )

        if file:
            # Save svg to file
            with open(file, 'w') as f:
                f.write(svg)

        return svg

    def on_mouse_move(self, event):
        """Called whenever mouse moves over canvas."""
        return

    def on_mouse_press(self, event):
        """Called whenever mouse pressed in canvas.
        """
        return

    def on_mouse_release(self, event):
        """Called whenever mouse released in canvas.
        """
        return
