from typing import Union, Dict, Tuple, List
from copy import copy, deepcopy
from itertools import cycle
import warnings

import numpy as np
from vispy.color.colormap import Colormap

from ...utils.colormaps import ensure_colormap_tuple
from ...types import ValidColormapArg

from ..base import Layer
from ...utils.event import Event
from ...utils.status_messages import format_float
from ...utils.colormaps.standardize_color import (
    transform_color,
    hex_to_name,
    get_color_namelist,
    rgb_to_hex,
)
from ..utils.color_transformations import (
    transform_color_with_defaults,
    transform_color_cycle,
    normalize_and_broadcast_colors,
    ColorType,
)
from ._points_constants import Symbol, SYMBOL_ALIAS, Mode, ColorMode
from ._points_mouse_bindings import add, select, highlight
from ._points_utils import (
    create_box,
    points_to_squares,
)
from ..utils.layer_utils import (
    dataframe_to_properties,
    guess_continuous,
    map_property,
)

DEFAULT_COLOR_CYCLE = np.array([[1, 0, 1, 1], [0, 1, 0, 1]])


class Points(Layer):
    """Points layer.

    Parameters
    ----------
    data : array (N, D)
        Coordinates for N points in D dimensions.
    properties : dict {str: array (N,)}, DataFrame
        Properties for each point. Each property should be an array of length N,
        where N is the number of points.
    symbol : str
        Symbol to be used for the point markers. Must be one of the
        following: arrow, clobber, cross, diamond, disc, hbar, ring,
        square, star, tailed_arrow, triangle_down, triangle_up, vbar, x.
    size : float, array
        Size of the point marker. If given as a scalar, all points are made
        the same size. If given as an array, size must be the same
        broadcastable to the same shape as the data.
    edge_width : float
        Width of the symbol edge in pixels.
    edge_color : str, array-like
        Color of the point marker border. Numeric color values should be RGB(A).
    edge_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to edge_color if a
        categorical attribute is used color the vectors.
    edge_colormap : str, vispy.color.colormap.Colormap
        Colormap to set edge_color if a continuous attribute is used to set face_color.
        See vispy docs for details: http://vispy.org/color.html#vispy.color.Colormap
    edge_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value
        of the specified property that are mapped to 0 and 1, respectively.
        The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    face_color : str, array-like
        Color of the point marker body. Numeric color values should be RGB(A).
    face_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to face_color if a
        categorical attribute is used color the vectors.
    face_colormap : str, vispy.color.colormap.Colormap
        Colormap to set face_color if a continuous attribute is used to set face_color.
        See vispy docs for details: http://vispy.org/color.html#vispy.color.Colormap
    face_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value
        of the specified property that are mapped to 0 and 1, respectively.
        The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    n_dimensional : bool
        If True, renders points not just in central plane but also in all
        n-dimensions according to specified point marker size.
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
    data : array (N, D)
        Coordinates for N points in D dimensions.
    properties : dict {str: array (N,)}
        Annotations for each point. Each property should be an array of length N,
        where N is the number of points.
    symbol : str
        Symbol used for all point markers.
    size : array (N, D)
        Array of sizes for each point in each dimension. Must have the same
        shape as the layer `data`.
    edge_width : float
        Width of the marker edges in pixels for all points
    edge_color : Nx4 numpy array
        Array of edge color RGBA values, one for each point.
    edge_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to edge_color if a
        categorical attribute is used color the vectors.
    edge_colormap : str, vispy.color.colormap.Colormap
        Colormap to set edge_color if a continuous attribute is used to set face_color.
        See vispy docs for details: http://vispy.org/color.html#vispy.color.Colormap
    edge_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value
        of the specified property that are mapped to 0 and 1, respectively.
        The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    face_color : Nx4 numpy array
        Array of face color RGBA values, one for each point.
    face_color_cycle : np.ndarray, list
        Cycle of colors (provided as string name, RGB, or RGBA) to map to face_color if a
        categorical attribute is used color the vectors.
    face_colormap : str, vispy.color.colormap.Colormap
        Colormap to set face_color if a continuous attribute is used to set face_color.
        See vispy docs for details: http://vispy.org/color.html#vispy.color.Colormap
    face_contrast_limits : None, (float, float)
        clims for mapping the property to a color map. These are the min and max value
        of the specified property that are mapped to 0 and 1, respectively.
        The default value is None. If set the none, the clims will be set to
        (property.min(), property.max())
    current_size : float
        Size of the marker for the next point to be added or the currently
        selected point.
    current_edge_color : str
        Size of the marker edge for the next point to be added or the currently
        selected point.
    current_face_color : str
        Size of the marker edge for the next point to be added or the currently
        selected point.
    n_dimensional : bool
        If True, renders points not just in central plane but also in all
        n-dimensions according to specified point marker size.
    selected_data : set
        Integer indices of any selected points.
    mode : str
        Interactive mode. The normal, default mode is PAN_ZOOM, which
        allows for normal interactivity with the canvas.

        In ADD mode clicks of the cursor add points at the clicked location.

        In SELECT mode the cursor can select points by clicking on them or
        by dragging a box around them. Once selected points can be moved,
        have their properties edited, or be deleted.
    face_color_mode : str
        Face color setting mode.

        DIRECT (default mode) allows each point to be set arbitrarily

        CYCLE allows the color to be set via a color cycle over an attribute

        COLORMAP allows color to be set via a color map over an attribute
    edge_color_mode : str
        Edge color setting mode.

        DIRECT (default mode) allows each point to be set arbitrarily

        CYCLE allows the color to be set via a color cycle over an attribute

        COLORMAP allows color to be set via a color map over an attribute

    Extended Summary
    ----------
    _property_choices : dict {str: array (N,)}
        Possible values for the properties in Points.properties.
        If properties is not provided, it will be {} (empty dictionary).
    _view_data : array (M, 2)
        2D coordinates of points in the currently viewed slice.
    _view_size : array (M, )
        Size of the point markers in the currently viewed slice.
    _indices_view : array (M, )
        Integer indices of the points in the currently viewed slice.
    _selected_view :
        Integer indices of selected points in the currently viewed slice within
        the `_view_data` array.
    _selected_box : array (4, 2) or None
        Four corners of any box either around currently selected points or
        being created during a drag action. Starting in the top left and
        going clockwise.
    _drag_start : list or None
        Coordinates of first cursor click during a drag action. Gets reset to
        None after dragging is done.
    """

    # The max number of points that will ever be used to render the thumbnail
    # If more points are present then they are randomly subsampled
    _max_points_thumbnail = 1024

    def __init__(
        self,
        data=None,
        *,
        properties=None,
        symbol='o',
        size=10,
        edge_width=1,
        edge_color='black',
        edge_color_cycle=None,
        edge_colormap='viridis',
        edge_contrast_limits=None,
        face_color='white',
        face_color_cycle=None,
        face_colormap='viridis',
        face_contrast_limits=None,
        n_dimensional=False,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        opacity=1,
        blending='translucent',
        visible=True,
    ):
        if data is None:
            data = np.empty((0, 2))
        else:
            data = np.atleast_2d(data)
        ndim = data.shape[1]
        super().__init__(
            data,
            ndim,
            name=name,
            metadata=metadata,
            scale=scale,
            translate=translate,
            opacity=opacity,
            blending=blending,
            visible=visible,
        )

        self.events.add(
            mode=Event,
            size=Event,
            edge_width=Event,
            face_color=Event,
            current_face_color=Event,
            edge_color=Event,
            current_edge_color=Event,
            current_properties=Event,
            symbol=Event,
            n_dimensional=Event,
            highlight=Event,
        )
        # update highlights when the layer is selected/deselected
        self.events.select.connect(self._set_highlight)
        self.events.deselect.connect(self._set_highlight)

        self._colors = get_color_namelist()

        # Save the point coordinates
        self._data = np.asarray(data)
        self.dims.clip = False

        # Save the properties
        if properties is None:
            self._properties = {}
            self._property_choices = {}
        elif len(data) > 0:
            properties, _ = dataframe_to_properties(properties)
            self._properties = self._validate_properties(properties)
            self._property_choices = {
                k: np.unique(v) for k, v in properties.items()
            }
        elif len(data) == 0:
            self._property_choices = {
                k: np.asarray(v) for k, v in properties.items()
            }
            empty_properties = {
                k: np.empty(0, dtype=v.dtype)
                for k, v in self._property_choices.items()
            }
            self._properties = empty_properties

        # Save the point style params
        self.symbol = symbol
        self._n_dimensional = n_dimensional
        self.edge_width = edge_width

        # The following point properties are for the new points that will
        # be added. For any given property, if a list is passed to the
        # constructor so each point gets its own value then the default
        # value is used when adding new points
        if np.isscalar(size):
            self._current_size = np.asarray(size)
        else:
            self._current_size = 10

        # Indices of selected points
        self._selected_data = set()
        self._selected_data_stored = set()
        self._selected_data_history = set()
        # Indices of selected points within the currently viewed slice
        self._selected_view = []
        # Index of hovered point
        self._value = None
        self._value_stored = None
        self._mode = Mode.PAN_ZOOM
        self._mode_history = self._mode
        self._status = self.mode
        self._highlight_index = []
        self._highlight_box = None

        self._drag_start = None

        # initialize view data
        self._indices_view = []
        self._view_size_scale = []

        self._drag_box = None
        self._drag_box_stored = None
        self._is_selecting = False
        self._clipboard = {}

        with self.block_update_properties():
            self._edge_color_property = ''
            self.edge_color = edge_color
            if edge_color_cycle is None:
                edge_color_cycle = deepcopy(DEFAULT_COLOR_CYCLE)
            self.edge_color_cycle = edge_color_cycle
            self.edge_color_cycle_map = {}
            self.edge_colormap = edge_colormap
            self._edge_contrast_limits = edge_contrast_limits

            self._face_color_property = ''
            self.face_color = face_color
            if face_color_cycle is None:
                face_color_cycle = deepcopy(DEFAULT_COLOR_CYCLE)
            self.face_color_cycle = face_color_cycle
            self.face_color_cycle_map = {}
            self.face_colormap = face_colormap
            self._face_contrast_limits = face_contrast_limits

        self.refresh_colors()

        self.size = size
        # set the current_* properties
        if len(data) > 0:
            self._current_edge_color = self.edge_color[-1]
            self._current_face_color = self.face_color[-1]
            self.current_properties = {
                k: np.asarray([v[-1]]) for k, v in self.properties.items()
            }
        elif len(data) == 0 and self.properties:
            self.current_properties = {
                k: np.asarray([v[0]])
                for k, v in self._property_choices.items()
            }
            self._initialize_current_color_for_empty_layer(edge_color, 'edge')
            self._initialize_current_color_for_empty_layer(face_color, 'face')
        else:
            self._current_edge_color = self.edge_color[-1]
            self._current_face_color = self.face_color[-1]
            self.current_properties = {}

        # Trigger generation of view slice and thumbnail
        self._update_dims()

    def _initialize_current_color_for_empty_layer(
        self, color: ColorType, attribute: str
    ):
        """Initialize current_{edge,face}_color when starting with empty layer.

        Parameters:
        -----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_color or 'face' for face_color.
        """
        color_mode = getattr(self, f'_{attribute}_color_mode')
        if color_mode == ColorMode.DIRECT:
            curr_color = transform_color_with_defaults(
                num_entries=1,
                colors=color,
                elem_name=f'{attribute}_color',
                default="white",
            )

        elif color_mode == ColorMode.CYCLE:
            color_cycle = getattr(self, f'_{attribute}_color_cycle')
            curr_color = transform_color(next(color_cycle))

            # add the new color cycle mapping
            color_property = getattr(self, f'_{attribute}_color_property')
            prop_value = self._property_choices[color_property][0]
            color_cycle_map = getattr(self, f'{attribute}_color_cycle_map')
            color_cycle_map[prop_value] = np.squeeze(curr_color)
            setattr(self, f'{attribute}_color_cycle_map', color_cycle_map)

        elif color_mode == ColorMode.COLORMAP:
            color_property = getattr(self, f'_{attribute}_color_property')
            prop_value = self._property_choices[color_property][0]
            colormap = getattr(self, f'{attribute}_colormap')
            contrast_limits = getattr(self, f'_{attribute}_contrast_limits')
            curr_color, _ = map_property(
                prop=prop_value,
                colormap=colormap[1],
                contrast_limits=contrast_limits,
            )
        setattr(self, f'_current_{attribute}_color', curr_color)

    @property
    def data(self) -> np.ndarray:
        """(N, D) array: coordinates for N points in D dimensions."""
        return self._data

    @data.setter
    def data(self, data: np.ndarray):
        cur_npoints = len(self._data)
        self._data = data

        # Adjust the size array when the number of points has changed
        if len(data) < cur_npoints:
            # If there are now fewer points, remove the size and colors of the
            # extra ones
            with self.events.set_data.blocker():
                self._edge_color = self.edge_color[: len(data)]
                self._face_color = self.face_color[: len(data)]
                self._size = self._size[: len(data)]

                for k in self.properties:
                    self.properties[k] = self.properties[k][: len(data)]

        elif len(data) > cur_npoints:
            # If there are now more points, add the size and colors of the
            # new ones
            with self.events.set_data.blocker():
                adding = len(data) - cur_npoints
                if len(self._size) > 0:
                    new_size = copy(self._size[-1])
                    for i in self.dims.displayed:
                        new_size[i] = self.current_size
                else:
                    # Add the default size, with a value for each dimension
                    new_size = np.repeat(
                        self.current_size, self._size.shape[1]
                    )
                size = np.repeat([new_size], adding, axis=0)

                for k in self.properties:
                    new_property = np.repeat(
                        self.current_properties[k], adding, axis=0
                    )
                    self.properties[k] = np.concatenate(
                        (self.properties[k], new_property), axis=0
                    )

                # add new edge colors
                self._add_point_color(adding, 'edge')

                # add new face colors
                self._add_point_color(adding, 'face')

                self.size = np.concatenate((self._size, size), axis=0)
                self.selected_data = set(np.arange(cur_npoints, len(data)))

        self._update_dims()
        self.events.data()

    def _add_point_color(self, adding: int, attribute: str):
        """Add the edge or face colors for new points.

        Parameters:
        ----------
        adding : int
            the number of points that were added
            (and thus the number of color entries to add)
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_colo_moder or 'face' for face_color_mode.
        """
        color_mode = getattr(self, f'_{attribute}_color_mode')
        if color_mode == ColorMode.DIRECT:
            current_face_color = getattr(self, f'_current_{attribute}_color')
            new_colors = np.tile(current_face_color, (adding, 1))
        elif color_mode == ColorMode.CYCLE:
            property_name = getattr(self, f'_{attribute}_color_property')
            color_property_value = self.current_properties[property_name][0]

            # check if the new color property is in the cycle map
            # and add it if it is not
            color_cycle_map = getattr(self, f'{attribute}_color_cycle_map')
            color_cycle_keys = [*color_cycle_map]
            if color_property_value not in color_cycle_keys:
                color_cycle = getattr(self, f'_{attribute}_color_cycle')
                color_cycle_map[color_property_value] = np.squeeze(
                    transform_color(next(color_cycle))
                )

                setattr(self, f'{attribute}_color_cycle_map', color_cycle_map)

            new_colors = np.tile(
                color_cycle_map[color_property_value], (adding, 1)
            )
        elif color_mode == ColorMode.COLORMAP:
            property_name = getattr(self, f'_{attribute}_color_property')
            color_property_value = self.current_properties[property_name][0]
            colormap = getattr(self, f'{attribute}_colormap')
            contrast_limits = getattr(self, f'_{attribute}_contrast_limits')

            fc, _ = map_property(
                prop=color_property_value,
                colormap=colormap[1],
                contrast_limits=contrast_limits,
            )
            new_colors = np.tile(fc, (adding, 1))
        colors = getattr(self, f'{attribute}_color')
        setattr(self, f'_{attribute}_color', np.vstack((colors, new_colors)))

    @property
    def properties(self) -> Dict[str, np.ndarray]:
        """dict {str: np.ndarray (N,)}, DataFrame: Annotations for each point"""
        return self._properties

    @properties.setter
    def properties(self, properties: Dict[str, np.ndarray]):
        if not isinstance(properties, dict):
            properties, _ = dataframe_to_properties(properties)
        self._properties = self._validate_properties(properties)
        if self._face_color_property and (
            self._face_color_property not in self._properties
        ):
            self._face_color_property = ''
            warnings.warn(
                'property used for face_color dropped', RuntimeWarning
            )

        if self._edge_color_property and (
            self._edge_color_property not in self._properties
        ):
            self._edge_color_property = ''
            warnings.warn(
                'property used for edge_color dropped', RuntimeWarning
            )

    @property
    def current_properties(self) -> Dict[str, np.ndarray]:
        """dict{str: np.ndarray(1,)}: properties for the next added point."""
        return self._current_properties

    @current_properties.setter
    def current_properties(self, current_properties):
        self._current_properties = current_properties

        if (
            self._update_properties
            and len(self.selected_data) > 0
            and self._mode != Mode.ADD
        ):
            props = self.properties
            for k in props:
                props[k][list(self.selected_data)] = current_properties[k]
            self.properties = props

            self.refresh_colors()
        self.events.current_properties()

    def _validate_properties(
        self, properties: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Validates the type and size of the properties"""
        for k, v in properties.items():
            if len(v) != len(self.data):
                raise ValueError(
                    'the number of properties must equal the number of points'
                )
            # ensure the property values are a numpy array
            if type(v) != np.ndarray:
                properties[k] = np.asarray(v)

        return properties

    def _get_ndim(self) -> int:
        """Determine number of dimensions of the layer."""
        return self.data.shape[1]

    def _get_extent(self) -> List[Tuple[int, int, int]]:
        """Determine ranges for slicing given by (min, max, step)."""
        if len(self.data) == 0:
            maxs = np.ones(self.data.shape[1], dtype=int)
            mins = np.zeros(self.data.shape[1], dtype=int)
        else:
            maxs = np.max(self.data, axis=0)
            mins = np.min(self.data, axis=0)

        return [(min, max) for min, max in zip(mins, maxs)]

    @property
    def n_dimensional(self) -> bool:
        """bool: renders points as n-dimensionsal."""
        return self._n_dimensional

    @n_dimensional.setter
    def n_dimensional(self, n_dimensional: bool) -> None:
        self._n_dimensional = n_dimensional
        self.events.n_dimensional()
        self.refresh()

    @property
    def symbol(self) -> str:
        """str: symbol used for all point markers."""
        return str(self._symbol)

    @symbol.setter
    def symbol(self, symbol: Union[str, Symbol]) -> None:

        if isinstance(symbol, str):
            # Convert the alias string to the deduplicated string
            if symbol in SYMBOL_ALIAS:
                symbol = SYMBOL_ALIAS[symbol]
            else:
                symbol = Symbol(symbol)
        self._symbol = symbol
        self.events.symbol()
        self.events.highlight()

    @property
    def size(self) -> Union[int, float, np.ndarray, list]:
        """(N, D) array: size of all N points in D dimensions."""
        return self._size

    @size.setter
    def size(self, size: Union[int, float, np.ndarray, list]) -> None:
        try:
            self._size = np.broadcast_to(size, self.data.shape).copy()
        except Exception:
            try:
                self._size = np.broadcast_to(
                    size, self.data.shape[::-1]
                ).T.copy()
            except Exception:
                raise ValueError("Size is not compatible for broadcasting")
        self.refresh()

    @property
    def current_size(self) -> Union[int, float]:
        """float: size of marker for the next added point."""
        return self._current_size

    @current_size.setter
    def current_size(self, size: Union[None, float]) -> None:
        self._current_size = size
        if (
            self._update_properties
            and len(self.selected_data) > 0
            and self._mode != Mode.ADD
        ):
            for i in self.selected_data:
                self.size[i, :] = (self.size[i, :] > 0) * size
            self.refresh()
            self.events.size()
        self.status = format_float(self.current_size)

    @property
    def edge_width(self) -> Union[None, int, float]:
        """float: width used for all point markers."""
        return self._edge_width

    @edge_width.setter
    def edge_width(self, edge_width: Union[None, float]) -> None:
        self._edge_width = edge_width
        self.status = format_float(self.edge_width)
        self.events.edge_width()

    @property
    def edge_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA edge colors for each point"""
        return self._edge_color

    @edge_color.setter
    def edge_color(self, edge_color):
        self._set_color(edge_color, 'edge')

    @property
    def edge_color_cycle(self) -> np.ndarray:
        """Union[list, np.ndarray] :  Color cycle for edge_color.
        Can be a list of colors defined by name, RGB or RGBA

        """
        return self._edge_color_cycle_values

    @edge_color_cycle.setter
    def edge_color_cycle(self, edge_color_cycle: Union[list, np.ndarray]):
        self._set_color_cycle(edge_color_cycle, 'edge')

    @property
    def edge_colormap(self) -> Tuple[str, Colormap]:
        """Return the colormap to be applied to a property to get the edge color.

        Returns
        -------
        colormap_name : str
            The name of the current colormap.
        colormap : vispy.color.Colormap
            The vispy colormap object.
        """
        return self._edge_colormap_name, self._edge_colormap

    @edge_colormap.setter
    def edge_colormap(self, colormap: ValidColormapArg):
        name, cmap = ensure_colormap_tuple(colormap)
        self._edge_colormap_name = name
        self._edge_colormap = cmap

    @property
    def edge_contrast_limits(self) -> Tuple[float, float]:
        """ None, (float, float): contrast limits for mapping
        the edge_color colormap property to 0 and 1
        """
        return self._edge_contrast_limits

    @edge_contrast_limits.setter
    def edge_contrast_limits(
        self, contrast_limits: Union[None, Tuple[float, float]]
    ):
        self._edge_contrast_limits = contrast_limits

    @property
    def current_edge_color(self) -> str:
        """str: Edge color of marker for the next added point or the selected point(s)."""
        hex_ = rgb_to_hex(self._current_edge_color)[0]
        return hex_to_name.get(hex_, hex_)

    @current_edge_color.setter
    def current_edge_color(self, edge_color: ColorType) -> None:
        self._current_edge_color = transform_color(edge_color)
        if (
            self._update_properties
            and len(self.selected_data) > 0
            and self._mode != Mode.ADD
        ):
            cur_colors: np.ndarray = self.edge_color
            index = list(self.selected_data)
            cur_colors[index] = self._current_edge_color
            self.edge_color = cur_colors
        self.events.current_edge_color()

    @property
    def edge_color_mode(self) -> str:
        """str: Edge color setting mode

        DIRECT (default mode) allows each point to be set arbitrarily

        CYCLE allows the color to be set via a color cycle over an attribute

        COLORMAP allows color to be set via a color map over an attribute
        """
        return str(self._edge_color_mode)

    @edge_color_mode.setter
    def edge_color_mode(self, edge_color_mode: Union[str, ColorMode]):
        self._set_color_mode(edge_color_mode, 'edge')

    @property
    def face_color(self) -> np.ndarray:
        """(N x 4) np.ndarray: Array of RGBA face colors for each point"""
        return self._face_color

    @face_color.setter
    def face_color(self, face_color):
        self._set_color(face_color, 'face')

    @property
    def face_color_cycle(self) -> np.ndarray:
        """Union[np.ndarray, cycle]:  Color cycle for face_color
        Can be a list of colors defined by name, RGB or RGBA
        """
        return self._face_color_cycle_values

    @face_color_cycle.setter
    def face_color_cycle(self, face_color_cycle: Union[np.ndarray, cycle]):
        self._set_color_cycle(face_color_cycle, 'face')

    @property
    def face_colormap(self) -> Tuple[str, Colormap]:
        """Return the colormap to be applied to a property to get the edge color.

        Returns
        -------
        colormap_name : str
            The name of the current colormap.
        colormap : vispy.color.Colormap
            The vispy colormap object.
        """
        return self._face_colormap_name, self._face_colormap

    @face_colormap.setter
    def face_colormap(self, colormap: ValidColormapArg):
        name, cmap = ensure_colormap_tuple(colormap)
        self._face_colormap_name = name
        self._face_colormap = cmap

    @property
    def face_contrast_limits(self) -> Union[None, Tuple[float, float]]:
        """None, (float, float) : clims for mapping the face_color
        colormap property to 0 and 1
        """
        return self._face_contrast_limits

    @face_contrast_limits.setter
    def face_contrast_limits(
        self, contrast_limits: Union[None, Tuple[float, float]]
    ):
        self._face_contrast_limits = contrast_limits

    @property
    def current_face_color(self) -> str:
        """Face color of marker for the next added point or the selected point(s)."""
        hex_ = rgb_to_hex(self._current_face_color)[0]
        return hex_to_name.get(hex_, hex_)

    @current_face_color.setter
    def current_face_color(self, face_color: ColorType) -> None:
        self._current_face_color = transform_color(face_color)
        if (
            self._update_properties
            and len(self.selected_data) > 0
            and self._mode != Mode.ADD
        ):
            cur_colors: np.ndarray = self.face_color
            index = list(self.selected_data)
            cur_colors[index] = self._current_face_color
            self.face_color = cur_colors

        self.events.current_face_color()

    @property
    def face_color_mode(self) -> str:
        """str: Face color setting mode

        DIRECT (default mode) allows each point to be set arbitrarily

        CYCLE allows the color to be set via a color cycle over an attribute

        COLORMAP allows color to be set via a color map over an attribute
        """
        return str(self._face_color_mode)

    @face_color_mode.setter
    def face_color_mode(self, face_color_mode):
        self._set_color_mode(face_color_mode, 'face')

    def _set_color_mode(
        self, color_mode: Union[ColorMode, str], attribute: str
    ):
        """ Set the face_color_mode or edge_color_mode property

        Parameters
        ----------
        color_mode : str, ColorMode
            The value for setting edge or face_color_mode. If color_mode is a string,
            it should be one of: 'direct', 'cycle', or 'colormap'
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_colo_moder or 'face' for face_color_mode.
        """
        color_mode = ColorMode(color_mode)

        if color_mode == ColorMode.DIRECT:
            setattr(self, f'_{attribute}_color_mode', color_mode)
        elif color_mode in (ColorMode.CYCLE, ColorMode.COLORMAP):
            color_property = getattr(self, f'_{attribute}_color_property')
            if color_property == '':
                if self.properties:
                    new_color_property = next(iter(self.properties))
                    setattr(
                        self,
                        f'_{attribute}_color_property',
                        new_color_property,
                    )
                    warnings.warn(
                        '_{attribute}_color_property was not set, setting to: {new_color_property}'
                    )
                else:
                    raise ValueError(
                        'There must be a valid Points.properties to use {color_mode}'
                    )

            # ColorMode.COLORMAP can only be applied to numeric properties
            color_property = getattr(self, f'_{attribute}_color_property')
            if (color_mode == ColorMode.COLORMAP) and not issubclass(
                self.properties[color_property].dtype.type, np.number
            ):
                raise TypeError(
                    'selected property must be numeric to use ColorMode.COLORMAP'
                )
            setattr(self, f'_{attribute}_color_mode', color_mode)
            self.refresh_colors()

    def _set_color(self, color: ColorType, attribute: str):
        """ Set the face_color or edge_color property

        Parameters
        ----------
        color : (N, 4) array or str
            The value for setting edge or face_color
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_color or 'face' for face_color.
        """
        # if the provided color is a string, first check if it is a key in the properties.
        # otherwise, assume it is the name of a color
        if self._is_color_mapped(color):
            if guess_continuous(self.properties[color]):
                setattr(self, f'_{attribute}_color_mode', ColorMode.COLORMAP)
            else:
                setattr(self, f'_{attribute}_color_mode', ColorMode.CYCLE)
            setattr(self, f'_{attribute}_color_property', color)
            self.refresh_colors()

        else:
            transformed_color = transform_color_with_defaults(
                num_entries=len(self.data),
                colors=color,
                elem_name="face_color",
                default="white",
            )
            colors = normalize_and_broadcast_colors(
                len(self.data), transformed_color
            )
            setattr(self, f'_{attribute}_color', colors)
            setattr(self, f'_{attribute}_color_mode', ColorMode.DIRECT)

            color_event = getattr(self.events, f'{attribute}_color')
            color_event()

    def _set_color_cycle(self, color_cycle: np.ndarray, attribute: str):
        """ Set the face_color_cycle or edge_color_cycle property

        Parameters
        ----------
        color_cycle : (N, 4) or (N, 1) array
            The value for setting edge or face_color_cycle
        attribute : str in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_color or 'face' for face_color.
        """
        transformed_color_cycle, transformed_colors = transform_color_cycle(
            color_cycle=color_cycle,
            elem_name=f'{attribute}_color_cycle',
            default="white",
        )
        setattr(self, f'_{attribute}_color_cycle_values', transformed_colors)
        setattr(self, f'_{attribute}_color_cycle', transformed_color_cycle)
        color_mode = getattr(self, f'_{attribute}_color_mode')
        if color_mode == ColorMode.CYCLE:
            self.refresh_colors(update_color_mapping=True)

    def refresh_colors(self, update_color_mapping: bool = False):
        """Calculate and update face and edge colors if using a cycle or color map

        Parameters
        ----------
        update_color_mapping : bool
            If set to True, the function will recalculate the color cycle map
            or colormap (whichever is being used). If set to False, the function
            will use the current color cycle map or color map. For example, if you
            are adding/modifying points and want them to be colored with the same
            mapping as the other points (i.e., the new points shouldn't affect
            the color cycle map or colormap), set update_color_mapping=False.
            Default value is False.
        """

        self._refresh_color('face', update_color_mapping)
        self._refresh_color('edge', update_color_mapping)

    def _refresh_color(self, attribute, update_color_mapping: bool = False):
        """Calculate and update face or edge colors if using a cycle or color map

        Parameters
        ----------
        attribute : str  in {'edge', 'face'}
            The name of the attribute to set the color of.
            Should be 'edge' for edge_color or 'face' for face_color.
        update_color_mapping : bool
            If set to True, the function will recalculate the color cycle map
            or colormap (whichever is being used). If set to False, the function
            will use the current color cycle map or color map. For example, if you
            are adding/modifying points and want them to be colored with the same
            mapping as the other points (i.e., the new points shouldn't affect
            the color cycle map or colormap), set update_color_mapping=False.
            Default value is False.
        """
        if self._update_properties:
            color_mode = getattr(self, f'_{attribute}_color_mode')
            if color_mode == ColorMode.CYCLE:
                color_property = getattr(self, f'_{attribute}_color_property')
                color_properties = self.properties[color_property]
                if update_color_mapping:
                    color_cycle = getattr(self, f'_{attribute}_color_cycle')
                    color_cycle_map = {
                        k: np.squeeze(transform_color(c))
                        for k, c in zip(
                            np.unique(color_properties), color_cycle
                        )
                    }
                    setattr(
                        self, f'{attribute}_color_cycle_map', color_cycle_map
                    )

                else:
                    # add properties if they are not in the colormap
                    # and update_color_mapping==False
                    color_cycle_map = getattr(
                        self, f'{attribute}_color_cycle_map'
                    )
                    color_cycle_keys = [*color_cycle_map]
                    props_in_map = np.in1d(color_properties, color_cycle_keys)
                    if not np.all(props_in_map):
                        props_to_add = np.unique(
                            color_properties[np.logical_not(props_in_map)]
                        )
                        color_cycle = getattr(
                            self, f'_{attribute}_color_cycle'
                        )
                        for prop in props_to_add:
                            color_cycle_map[prop] = np.squeeze(
                                transform_color(next(color_cycle))
                            )
                        setattr(
                            self,
                            f'{attribute}_color_cycle_map',
                            color_cycle_map,
                        )
                colors = np.array(
                    [color_cycle_map[x] for x in color_properties]
                )
                if len(colors) == 0:
                    colors = np.empty((0, 4))
                setattr(self, f'_{attribute}_color', colors)

            elif color_mode == ColorMode.COLORMAP:
                color_property = getattr(self, f'_{attribute}_color_property')
                color_properties = self.properties[color_property]
                if len(color_properties) > 0:
                    contrast_limits = getattr(
                        self, f'{attribute}_contrast_limits'
                    )
                    colormap = getattr(self, f'{attribute}_colormap')
                    if update_color_mapping or contrast_limits is None:

                        colors, contrast_limits = map_property(
                            prop=color_properties, colormap=colormap[1]
                        )
                        setattr(
                            self,
                            f'{attribute}_contrast_limits',
                            contrast_limits,
                        )
                    else:

                        colors, _ = map_property(
                            prop=color_properties,
                            colormap=colormap[1],
                            contrast_limits=contrast_limits,
                        )
                else:
                    colors = np.empty((0, 4))
                setattr(self, f'_{attribute}_color', colors)

            color_event = getattr(self.events, f'{attribute}_color')
            color_event()

    def _is_color_mapped(self, color):
        """ determines if the new color argument is for directly setting or cycle/colormap"""
        if isinstance(color, str):
            if color in self.properties:
                return True
            else:
                return False
        elif isinstance(color, (list, np.ndarray)):
            return False
        else:
            raise ValueError(
                'face_color should be the name of a color, an array of colors, or the name of an property'
            )

    def _get_state(self):
        """Get dictionary of layer state.

        Returns
        -------
        state : dict
            Dictionary of layer state.
        """
        state = self._get_base_state()
        state.update(
            {
                'symbol': self.symbol,
                'edge_width': self.edge_width,
                'face_color': self.face_color,
                'face_color_cycle': self.face_color_cycle,
                'face_colormap': self.face_colormap[0],
                'face_contrast_limits': self.face_contrast_limits,
                'edge_color': self.edge_color,
                'edge_color_cycle': self.edge_color_cycle,
                'edge_colormap': self.edge_colormap[0],
                'edge_contrast_limits': self.edge_contrast_limits,
                'properties': self.properties,
                'n_dimensional': self.n_dimensional,
                'size': self.size,
                'data': self.data,
            }
        )
        return state

    @property
    def selected_data(self) -> set:
        """set: set of currently selected points."""
        return self._selected_data

    @selected_data.setter
    def selected_data(self, selected_data):
        self._selected_data = set(selected_data)
        selected = []
        for c in self._selected_data:
            if c in self._indices_view:
                ind = list(self._indices_view).index(c)
                selected.append(ind)
        self._selected_view = selected

        # Update properties based on selected points
        if len(self._selected_data) == 0:
            self._set_highlight()
            return
        index = list(self._selected_data)
        edge_colors = np.unique(self.edge_color[index], axis=0)
        if len(edge_colors) == 1:
            edge_color = edge_colors[0]
            with self.block_update_properties():
                self.current_edge_color = edge_color

        face_colors = np.unique(self.face_color[index], axis=0)
        if len(face_colors) == 1:
            face_color = face_colors[0]
            with self.block_update_properties():
                self.current_face_color = face_color

        size = list(
            set([self.size[i, self.dims.displayed].mean() for i in index])
        )
        if len(size) == 1:
            size = size[0]
            with self.block_update_properties():
                self.current_size = size

        properties = {
            k: np.unique(v[index], axis=0) for k, v in self.properties.items()
        }
        n_unique_properties = np.array([len(v) for v in properties.values()])
        if np.all(n_unique_properties == 1):
            with self.block_update_properties():
                self.current_properties = properties
        self._set_highlight()

    def interaction_box(self, index) -> np.ndarray:
        """Create the interaction box around a list of points in view.

        Parameters
        ----------
        index : list
            List of points around which to construct the interaction box.

        Returns
        ----------
        box : np.ndarray
            4x2 array of corners of the interaction box in clockwise order
            starting in the upper-left corner.
        """
        if len(index) == 0:
            box = None
        else:
            data = self._view_data[index]
            size = self._view_size[index]
            data = points_to_squares(data, size)
            box = create_box(data)

        return box

    @property
    def mode(self) -> str:
        """str: Interactive mode

        Interactive mode. The normal, default mode is PAN_ZOOM, which
        allows for normal interactivity with the canvas.

        In ADD mode clicks of the cursor add points at the clicked location.

        In SELECT mode the cursor can select points by clicking on them or
        by dragging a box around them. Once selected points can be moved,
        have their properties edited, or be deleted.
        """
        return str(self._mode)

    @mode.setter
    def mode(self, mode):
        mode = Mode(mode)

        if not self.editable:
            mode = Mode.PAN_ZOOM

        if mode == self._mode:
            return
        old_mode = self._mode

        if old_mode == Mode.ADD:
            self.mouse_drag_callbacks.remove(add)
        elif old_mode == Mode.SELECT:
            # add mouse drag and move callbacks
            self.mouse_drag_callbacks.remove(select)
            self.mouse_move_callbacks.remove(highlight)

        if mode == Mode.ADD:
            self.cursor = 'pointing'
            self.interactive = False
            self.help = 'hold <space> to pan/zoom'
            self.selected_data = set()
            self._set_highlight()
            self.mouse_drag_callbacks.append(add)
        elif mode == Mode.SELECT:
            self.cursor = 'standard'
            self.interactive = False
            self.help = 'hold <space> to pan/zoom'
            # add mouse drag and move callbacks
            self.mouse_drag_callbacks.append(select)
            self.mouse_move_callbacks.append(highlight)
        elif mode == Mode.PAN_ZOOM:
            self.cursor = 'standard'
            self.interactive = True
            self.help = ''
        else:
            raise ValueError("Mode not recognized")

        if not (mode == Mode.SELECT and old_mode == Mode.SELECT):
            self._selected_data_stored = set()

        self.status = str(mode)
        self._mode = mode
        self._set_highlight()

        self.events.mode(mode=mode)

    @property
    def _view_data(self) -> np.ndarray:
        """Get the coords of the points in view

        Returns
        -------
        view_data : (N x D) np.ndarray
            Array of coordinates for the N points in view
        """
        if len(self._indices_view) > 0:

            data = self.data[np.ix_(self._indices_view, self.dims.displayed)]

        else:
            # if no points in this slice send dummy data
            data = np.zeros((0, self.dims.ndisplay))

        return data

    @property
    def _view_size(self) -> np.ndarray:
        """Get the sizes of the points in view

       Returns
       -------
       view_size : (N x D) np.ndarray
           Array of sizes for the N points in view
        """
        if len(self._indices_view) > 0:
            # Get the point sizes and scale for ndim display
            sizes = (
                self.size[
                    np.ix_(self._indices_view, self.dims.displayed)
                ].mean(axis=1)
                * self._view_size_scale
            )

        else:
            # if no points, return an empty list
            sizes = np.array([])
        return sizes

    @property
    def _view_face_color(self) -> np.ndarray:
        """Get the face colors of the points in view

        Returns
        -------
        view_face_color : (N x 4) np.ndarray
            RGBA color array for the face colors of the N points in view.
            If there are no points in view, returns array of length 0.
        """
        return self.face_color[self._indices_view]

    @property
    def _view_edge_color(self) -> np.ndarray:
        """Get the edge colors of the points in view

        Returns
        -------
        view_edge_color : (N x 4) np.ndarray
            RGBA color array for the edge colors of the N points in view.
            If there are no points in view, returns array of length 0.
        """
        return self.edge_color[self._indices_view]

    def _set_editable(self, editable=None):
        """Set editable mode based on layer properties."""
        if editable is None:
            if self.dims.ndisplay == 3:
                self.editable = False
            else:
                self.editable = True

        if not self.editable:
            self.mode = Mode.PAN_ZOOM

    def _slice_data(
        self, dims_indices
    ) -> Tuple[List[int], Union[float, np.ndarray]]:
        """Determines the slice of points given the indices.

        Parameters
        ----------
        dims_indices : sequence of int or slice
            Indices to slice with.

        Returns
        ----------
        slice_indices : list
            Indices of points in the currently viewed slice.
        scale : float, (N, ) array
            If in `n_dimensional` mode then the scale factor of points, where
            values of 1 corresponds to points located in the slice, and values
            less than 1 correspond to points located in neighboring slices.
        """
        # Get a list of the data for the points in this slice
        not_disp = list(self.dims.not_displayed)
        indices = np.array(dims_indices)
        if len(self.data) > 0:
            if self.n_dimensional is True and self.ndim > 2:
                distances = abs(self.data[:, not_disp] - indices[not_disp])
                sizes = self.size[:, not_disp] / 2
                matches = np.all(distances <= sizes, axis=1)
                size_match = sizes[matches]
                size_match[size_match == 0] = 1
                scale_per_dim = (size_match - distances[matches]) / size_match
                scale_per_dim[size_match == 0] = 1
                scale = np.prod(scale_per_dim, axis=1)
                slice_indices = np.where(matches)[0].astype(int)
                return slice_indices, scale
            else:
                data = self.data[:, not_disp].astype('int')
                matches = np.all(data == indices[not_disp], axis=1)
                slice_indices = np.where(matches)[0].astype(int)
                return slice_indices, 1
        else:
            return [], []

    def _get_value(self) -> Union[None, int]:
        """Determine if points at current coordinates.

        Returns
        ----------
        selection : int or None
            Index of point that is at the current coordinate if any.
        """
        # Display points if there are any in this slice
        if len(self._view_data) > 0:
            # Get the point sizes
            distances = abs(self._view_data - self.displayed_coordinates)
            in_slice_matches = np.all(
                distances <= np.expand_dims(self._view_size, axis=1) / 2,
                axis=1,
            )
            indices = np.where(in_slice_matches)[0]
            if len(indices) > 0:
                selection = self._indices_view[indices[-1]]
            else:
                selection = None
        else:
            selection = None

        return selection

    def _set_view_slice(self):
        """Sets the view given the indices to slice with."""
        # get the indices of points in view
        indices, scale = self._slice_data(self.dims.indices)
        self._view_size_scale = scale
        self._indices_view = indices
        # get the selected points that are in view
        selected = []
        for c in self.selected_data:
            if c in self._indices_view:
                ind = list(self._indices_view).index(c)
                selected.append(ind)
        self._selected_view = selected
        with self.events.highlight.blocker():
            self._set_highlight(force=True)

    def _set_highlight(self, force=False):
        """Render highlights of shapes including boundaries, vertices,
        interaction boxes, and the drag selection box when appropriate.
        Highlighting only occurs in Mode.SELECT.

        Parameters
        ----------
        force : bool
            Bool that forces a redraw to occur when `True`
        """
        # Check if any point ids have changed since last call
        if self.selected:
            if (
                self.selected_data == self._selected_data_stored
                and self._value == self._value_stored
                and np.all(self._drag_box == self._drag_box_stored)
            ) and not force:
                return
            self._selected_data_stored = copy(self.selected_data)
            self._value_stored = copy(self._value)
            self._drag_box_stored = copy(self._drag_box)

            if self._value is not None or len(self._selected_view) > 0:
                if len(self._selected_view) > 0:
                    index = copy(self._selected_view)
                    # highlight the hovered point if not in adding mode
                    if (
                        self._value in self._indices_view
                        and self._mode == Mode.SELECT
                        and not self._is_selecting
                    ):
                        hover_point = list(self._indices_view).index(
                            self._value
                        )
                        if hover_point in index:
                            pass
                        else:
                            index.append(hover_point)
                    index.sort()
                else:
                    # only highlight hovered points in select mode
                    if (
                        self._value in self._indices_view
                        and self._mode == Mode.SELECT
                        and not self._is_selecting
                    ):
                        hover_point = list(self._indices_view).index(
                            self._value
                        )
                        index = [hover_point]
                    else:
                        index = []

                self._highlight_index = index
            else:
                self._highlight_index = []

            # only display dragging selection box in 2D
            if self.dims.ndisplay == 2 and self._is_selecting:
                pos = create_box(self._drag_box)
                pos = pos[list(range(4)) + [0]]
            else:
                pos = None

            self._highlight_box = pos
            self.events.highlight()
        else:
            self._highlight_box = None
            self._highlight_index = []
            self.events.highlight()

    def _update_thumbnail(self):
        """Update thumbnail with current points and colors."""
        colormapped = np.zeros(self._thumbnail_shape)
        colormapped[..., 3] = 1
        if len(self._view_data) > 0:
            min_vals = [self.dims.range[i][0] for i in self.dims.displayed]
            shape = np.ceil(
                [
                    self.dims.range[i][1] - self.dims.range[i][0] + 1
                    for i in self.dims.displayed
                ]
            ).astype(int)
            zoom_factor = np.divide(
                self._thumbnail_shape[:2], shape[-2:]
            ).min()
            if len(self._view_data) > self._max_points_thumbnail:
                thumbnail_indices = np.random.randint(
                    0, len(self._view_data), self._max_points_thumbnail
                )
                points = self._view_data[thumbnail_indices]
            else:
                points = self._view_data
                thumbnail_indices = self._indices_view
            coords = np.floor(
                (points[:, -2:] - min_vals[-2:] + 0.5) * zoom_factor
            ).astype(int)
            coords = np.clip(
                coords, 0, np.subtract(self._thumbnail_shape[:2], 1)
            )
            colors = self.face_color[thumbnail_indices]
            colormapped[coords[:, 0], coords[:, 1]] = colors

        colormapped[..., 3] *= self.opacity
        self.thumbnail = colormapped

    def add(self, coord):
        """Adds point at coordinate.

        Parameters
        ----------
        coord : sequence of indices to add point at
        """
        self.data = np.append(self.data, np.atleast_2d(coord), axis=0)

    def remove_selected(self):
        """Removes selected points if any."""
        index = list(self.selected_data)
        index.sort()
        if len(index) > 0:
            self._size = np.delete(self._size, index, axis=0)
            self._edge_color = np.delete(self.edge_color, index, axis=0)
            self._face_color = np.delete(self.face_color, index, axis=0)
            for k in self.properties:
                self.properties[k] = np.delete(
                    self.properties[k], index, axis=0
                )
            if self._value in self.selected_data:
                self._value = None
            self.selected_data = set()
            self.data = np.delete(self.data, index, axis=0)

    def _move(self, index, coord):
        """Moves points relative drag start location.

        Parameters
        ----------
        index : list
            Integer indices of points to move
        coord : tuple
            Coordinates to move points to
        """
        if len(index) > 0:
            index = list(index)
            disp = list(self.dims.displayed)
            if self._drag_start is None:
                center = self.data[np.ix_(index, disp)].mean(axis=0)
                self._drag_start = np.array(coord)[disp] - center
            center = self.data[np.ix_(index, disp)].mean(axis=0)
            shift = np.array(coord)[disp] - center - self._drag_start
            self.data[np.ix_(index, disp)] = (
                self.data[np.ix_(index, disp)] + shift
            )
            self.refresh()

    def _paste_data(self):
        """Paste any point from clipboard and select them."""
        npoints = len(self._view_data)
        totpoints = len(self.data)

        if len(self._clipboard.keys()) > 0:
            not_disp = self.dims.not_displayed
            data = deepcopy(self._clipboard['data'])
            offset = [
                self.dims.indices[i] - self._clipboard['indices'][i]
                for i in not_disp
            ]
            data[:, not_disp] = data[:, not_disp] + np.array(offset)
            self._data = np.append(self.data, data, axis=0)
            self._size = np.append(
                self.size, deepcopy(self._clipboard['size']), axis=0
            )
            self._edge_color = np.vstack(
                (
                    self.edge_color,
                    transform_color(deepcopy(self._clipboard['edge_color'])),
                )
            )
            self._face_color = np.vstack(
                (
                    self.face_color,
                    transform_color(deepcopy(self._clipboard['face_color'])),
                )
            )
            for k in self.properties:
                self.properties[k] = np.concatenate(
                    (self.properties[k], self._clipboard['properties'][k]),
                    axis=0,
                )
            self._selected_view = list(
                range(npoints, npoints + len(self._clipboard['data']))
            )
            self._selected_data = set(
                range(totpoints, totpoints + len(self._clipboard['data']))
            )
            self.refresh()

    def _copy_data(self):
        """Copy selected points to clipboard."""
        if len(self.selected_data) > 0:
            index = list(self.selected_data)
            self._clipboard = {
                'data': deepcopy(self.data[index]),
                'edge_color': deepcopy(self.edge_color[index]),
                'face_color': deepcopy(self.face_color[index]),
                'size': deepcopy(self.size[index]),
                'properties': {
                    k: deepcopy(v[index]) for k, v in self.properties.items()
                },
                'indices': self.dims.indices,
            }
        else:
            self._clipboard = {}
