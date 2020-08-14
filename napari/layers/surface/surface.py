import warnings

import numpy as np

from ...utils.colormaps import AVAILABLE_COLORMAPS
from ...utils.event import Event
from ..base import Layer
from ..intensity_mixin import IntensityVisualizationMixin
from ..utils.layer_utils import calc_data_range


# Mixin must come before Layer
class Surface(IntensityVisualizationMixin, Layer):
    """
    Surface layer renders meshes onto the canvas.

    Parameters
    ----------
    data : 3-tuple of array
        The first element of the tuple is an (N, D) array of vertices of
        mesh triangles. The second is an (M, 3) array of int of indices
        of the mesh triangles. The third element is the (K0, ..., KL, N)
        array of values used to color vertices where the additional L
        dimensions are used to color the same mesh with different values.
    colormap : str, vispy.Color.Colormap, tuple, dict
        Colormap to use for luminance images. If a string must be the name
        of a supported colormap from vispy or matplotlib. If a tuple the
        first value must be a string to assign as a name to a colormap and
        the second item must be a Colormap. If a dict the key must be a
        string to assign as a name to a colormap and the value must be a
        Colormap.
    contrast_limits : list (2,)
        Color limits to be used for determining the colormap bounds for
        luminance images. If not passed is calculated as the min and max of
        the image.
    gamma : float
        Gamma correction for determining colormap linearity. Defaults to 1.
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
    data : 3-tuple of array
        The first element of the tuple is an (N, D) array of vertices of
        mesh triangles. The second is an (M, 3) array of int of indices
        of the mesh triangles. The third element is the (K0, ..., KL, N)
        array of values used to color vertices where the additional L
        dimensions are used to color the same mesh with different values.
    vertices : (N, D) array
        Vertices of mesh triangles.
    faces : (M, 3) array of int
        Indices of mesh triangles.
    vertex_values : (K0, ..., KL, N) array
        Values used to color vertices.
    colormap : str, vispy.Color.Colormap, tuple, dict
        Colormap to use for luminance images. If a string must be the name
        of a supported colormap from vispy or matplotlib. If a tuple the
        first value must be a string to assign as a name to a colormap and
        the second item must be a Colormap. If a dict the key must be a
        string to assign as a name to a colormap and the value must be a
        Colormap.
    contrast_limits : list (2,)
        Color limits to be used for determining the colormap bounds for
        luminance images. If not passed is calculated as the min and max of
        the image.
    gamma : float
        Gamma correction for determining colormap linearity.

    Extended Summary
    ----------
    _data_view : (M, 2) or (M, 3) array
        The coordinates of the vertices given the viewed dimensions.
    _view_faces : (P, 3) array
        The integer indices of the vertices that form the triangles
        in the currently viewed slice.
    _colorbar : array
        Colorbar for current colormap.
    """

    _colormaps = AVAILABLE_COLORMAPS

    def __init__(
        self,
        data,
        *,
        colormap='gray',
        contrast_limits=None,
        gamma=1,
        name=None,
        metadata=None,
        scale=None,
        translate=None,
        opacity=1,
        blending='translucent',
        visible=True,
    ):

        ndim = data[0].shape[1]

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

        self.events.add(interpolation=Event, rendering=Event)

        # Set contrast_limits and colormaps
        self._gamma = gamma
        if contrast_limits is None:
            self._contrast_limits_range = calc_data_range(data[2])
        else:
            self._contrast_limits_range = contrast_limits
        self._contrast_limits = tuple(self._contrast_limits_range)
        self.colormap = colormap
        self.contrast_limits = self._contrast_limits

        # Data containing vectors in the currently viewed slice
        self._data_view = np.zeros((0, self.dims.ndisplay))
        self._view_faces = np.zeros((0, 3))
        self._view_vertex_values = []

        # assign mesh data and establish default behavior
        self._vertices = data[0]
        self._faces = data[1]
        self._vertex_values = data[2]

        # Trigger generation of view slice and thumbnail
        self._update_dims()

    def _calc_data_range(self):
        return calc_data_range(self.vertex_values)

    @property
    def dtype(self):
        return self.vertex_values.dtype

    @property
    def data(self):
        return (self.vertices, self.faces, self.vertex_values)

    @property
    def vertices(self):
        return self._vertices

    @vertices.setter
    def vertices(self, vertices):
        """Array of vertices of mesh triangles."""

        self._vertices = vertices

        self._update_dims()
        self.refresh()
        self.events.data()

    @property
    def vertex_values(self) -> np.ndarray:
        return self._vertex_values

    @vertex_values.setter
    def vertex_values(self, vertex_values: np.ndarray):
        """Array of values used to color vertices.."""

        self._vertex_values = vertex_values

        self.refresh()
        self.events.data()

    @property
    def faces(self) -> np.ndarray:
        return self._faces

    @faces.setter
    def faces(self, faces: np.ndarray):
        """Array of indices of mesh triangles.."""

        self.faces = faces

        self.refresh()
        self.events.data()

    def _get_ndim(self):
        """Determine number of dimensions of the layer."""
        return self.vertices.shape[1] + (self.vertex_values.ndim - 1)

    @property
    def _extent_data(self) -> np.ndarray:
        """Extent of layer in data coordinates.

        Returns
        -------
        extent_data : array, shape (2, D)
        """
        if len(self.vertices) == 0:
            extrema = np.full((2, self.ndim), np.nan)
        else:
            maxs = np.max(self.vertices, axis=0)
            mins = np.min(self.vertices, axis=0)

            # The full dimensionality and shape of the layer is determined by
            # the number of additional vertex value dimensions and the
            # dimensionality of the vertices themselves
            if self.vertex_values.ndim > 1:
                mins = [0] * (self.vertex_values.ndim - 1) + list(mins)
                maxs = list(self.vertex_values.shape[:-1]) + list(maxs)
            extrema = np.vstack([mins, maxs])
        return extrema

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
                'colormap': self.colormap[0],
                'contrast_limits': self.contrast_limits,
                'gamma': self.gamma,
                'data': self.data,
            }
        )
        return state

    def _set_view_slice(self):
        """Sets the view given the indices to slice with."""
        N, vertex_ndim = self.vertices.shape
        values_ndim = self.vertex_values.ndim - 1

        # Take vertex_values dimensionality into account if more than one value
        # is provided per vertex.
        if values_ndim > 0:
            # Get indices for axes corresponding to values dimensions
            values_indices = self.dims.indices[:-vertex_ndim]
            values = self.vertex_values[values_indices]
            if values.ndim > 1:
                warnings.warn(
                    """Assigning multiple values per vertex after slicing is
                    not allowed. All dimensions corresponding to vertex_values
                    must be non-displayed dimensions. Data will not be
                    visible."""
                )
                self._data_view = np.zeros((0, self.dims.ndisplay))
                self._view_faces = np.zeros((0, 3))
                self._view_vertex_values = []
                return

            self._view_vertex_values = values
            # Determine which axes of the vertices data are being displayed
            # and not displayed, ignoring the additional dimensions
            # corresponding to the vertex_values.
            indices = np.array(self.dims.indices[-vertex_ndim:])
            disp = [
                d
                for d in np.subtract(self.dims.displayed, values_ndim)
                if d >= 0
            ]
            not_disp = [
                d
                for d in np.subtract(self.dims.not_displayed, values_ndim)
                if d >= 0
            ]
        else:
            self._view_vertex_values = self.vertex_values
            indices = np.array(self.dims.indices)
            not_disp = list(self.dims.not_displayed)
            disp = list(self.dims.displayed)

        self._data_view = self.vertices[:, disp]
        if len(self.vertices) == 0:
            self._view_faces = np.zeros((0, 3))
        elif vertex_ndim > self.dims.ndisplay:
            vertices = self.vertices[:, not_disp].astype('int')
            triangles = vertices[self.faces]
            matches = np.all(triangles == indices[not_disp], axis=(1, 2))
            matches = np.where(matches)[0]
            if len(matches) == 0:
                self._view_faces = np.zeros((0, 3))
            else:
                self._view_faces = self.faces[matches]
        else:
            self._view_faces = self.faces

    def _update_thumbnail(self):
        """Update thumbnail with current surface."""
        pass

    def _get_value(self):
        """Returns coordinates, values, and a string for a given mouse position
        and set of indices.

        Returns
        -------
        value : int, None
            Value of the data at the coord.
        """

        return None
