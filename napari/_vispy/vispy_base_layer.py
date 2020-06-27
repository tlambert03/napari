from abc import ABC, abstractmethod
from functools import lru_cache
import numpy as np
from vispy.app import Canvas
from vispy.gloo import gl
from vispy.visuals.transforms import STTransform
from ..utils.event_handler import call_on


class VispyBaseLayer(ABC):
    """Base object for individual layer views

    Meant to be subclassed.

    Parameters
    ----------
    layer : napari.layers.Layer
        Layer model.
    node : vispy.scene.VisualNode
        Central node with which to interact with the visual.

    Attributes
    ----------
    layer : napari.layers.Layer
        Layer model.
    node : vispy.scene.VisualNode
        Central node with which to interact with the visual.
    scale : sequence of float
        Scale factors for the layer visual in the scenecanvas.
    translate : sequence of float
        Translation values for the layer visual in the scenecanvas.
    scale_factor : float
        Conversion factor from canvas coordinates to image coordinates, which
        depends on the current zoom level.
    MAX_TEXTURE_SIZE_2D : int
        Max texture size allowed by the vispy canvas during 2D rendering.
    MAX_TEXTURE_SIZE_3D : int
        Max texture size allowed by the vispy canvas during 2D rendering.

    Extended Summary
    ----------
    _master_transform : vispy.visuals.transforms.STTransform
        Transform positioning the layer visual inside the scenecanvas.
    """

    def __init__(self, layer, node):
        super().__init__()

        # When the EVH refactor #1376 is done we might not even need the layer
        # attribute anymore as all data updates will be through the handler.
        # At that point we could remove the attribute and do the registering
        # outside this class and never even need to pass the layer to this
        # class.
        self.layer = layer
        self.layer.event_handler.discover_connections(self)

        self.node = node

        MAX_TEXTURE_SIZE_2D, MAX_TEXTURE_SIZE_3D = get_max_texture_sizes()
        self.MAX_TEXTURE_SIZE_2D = MAX_TEXTURE_SIZE_2D
        self.MAX_TEXTURE_SIZE_3D = MAX_TEXTURE_SIZE_3D

        self._position = (0,) * self.layer.dims.ndisplay

    @property
    def _master_transform(self):
        """vispy.visuals.transforms.STTransform:
        Central node's firstmost transform.
        """
        # whenever a new parent is set, the transform is reset
        # to a NullTransform so we reset it here
        if not isinstance(self.node.transform, STTransform):
            self.node.transform = STTransform()

        return self.node.transform

    @property
    def order(self):
        """int: Order in which the visual is drawn in the scenegraph.

        Lower values are closer to the viewer.
        """
        return self.node.order

    @order.setter
    def order(self, order):
        self.node.order = order

    @property
    def scale(self):
        """sequence of float: Scale factors."""
        return self._master_transform.scale

    @scale.setter
    def scale(self, scale):
        # Avoid useless update if nothing changed in the displayed dims
        # Note that the master_transform scale is always a 4-vector so pad
        padded_scale = np.pad(
            scale, ((0, 4 - len(scale))), constant_values=1, mode='constant'
        )
        if self.scale is not None and np.all(self.scale == padded_scale):
            return
        self._master_transform.scale = padded_scale

    @property
    def translate(self):
        """sequence of float: Translation values."""
        return self._master_transform.translate

    @translate.setter
    def translate(self, translate):
        # Avoid useless update if nothing changed in the displayed dims
        # Note that the master_transform translate is always a 4-vector so pad
        padded_translate = np.pad(
            translate,
            ((0, 4 - len(translate))),
            constant_values=1,
            mode='constant',
        )
        if self.translate is not None and np.all(
            self.translate == padded_translate
        ):
            return
        self._master_transform.translate = padded_translate

    @property
    def scale_factor(self):
        """float: Conversion factor from canvas pixels to data coordinates.
        """
        if self.node.canvas is not None:
            transform = self.node.canvas.scene.node_transform(self.node)
            return transform.map([1, 1])[0] - transform.map([0, 0])[0]
        else:
            return 1

    @abstractmethod
    def _on_slice_data_change(self, value=None):
        raise NotImplementedError()

    @call_on.visible
    def _on_visible_change(self, value):
        """Receive layer model visibiliy and update the visual.

        Parameters
        ----------
        value : bool
            Layer visibility
        """
        self.node.visible = value

    @call_on.opacity
    def _on_opacity_change(self, value):
        """Receive layer model opacity and update the visual.

        Parameters
        ----------
        value : float
            Layer opacity between 0 and 1.
        """
        self.node.opacity = value

    @call_on.blending
    def _on_blending_change(self, text):
        """Receive layer model blending mode and update the visual.

        Parameters
        ----------
        text : str
           Blending mode used by VisPy. Must be one of our supported
           modes:
           'transluenct', 'additive', 'opaque'
        """
        self.node.set_gl_state(text)
        self.node.update()

    @call_on.scale
    def _on_scale_change(self, event=None):
        scale = self.layer._transforms.simplified.set_slice(
            self.layer.dims.displayed
        ).scale
        # convert NumPy axis ordering to VisPy axis ordering
        self.scale = scale[::-1]
        self.layer.corner_pixels = self.coordinates_of_canvas_corners()
        self.layer.position = self._transform_position(self._position)

    @call_on.translate
    def _on_translate_change(self, event=None):
        translate = self.layer._transforms.simplified.set_slice(
            self.layer.dims.displayed
        ).translate
        # convert NumPy axis ordering to VisPy axis ordering
        self.translate = translate[::-1]
        self.layer.corner_pixels = self.coordinates_of_canvas_corners()
        self.layer.position = self._transform_position(self._position)

    def _transform_position(self, position):
        """Transform cursor position from canvas space (x, y) into image space.

        Parameters
        -------
        position : 2-tuple
            Cursor position in canvase (x, y).

        Returns
        -------
        coords : tuple
            Coordinates of cursor in image space for displayed dimensions only
        """
        nd = self.layer.dims.ndisplay
        if self.node.canvas is not None:
            transform = self.node.canvas.scene.node_transform(self.node)
            # Map and offset position so that pixel center is at 0
            mapped_position = transform.map(list(position))[:nd] - 0.5
            return tuple(mapped_position[::-1])
        else:
            return (0,) * nd

    def _reset_base(self):
        self._on_visible_change(self.layer.visible)
        self._on_opacity_change(self.layer.opacity)
        self._on_blending_change(self.layer.blending)
        self._on_scale_change()
        self._on_translate_change()

    def coordinates_of_canvas_corners(self):
        """Find location of the corners of canvas in data coordinates.

        This method should only be used during 2D image viewing. The result
        depends on the current pan and zoom position.

        Returns
        ----------
        corner_pixels : array
            Coordinates of top left and bottom right canvas pixel in the data.
        """
        nd = self.layer.dims.ndisplay
        # Find image coordinate of top left canvas pixel
        if self.node.canvas is not None:
            offset = self.translate[:nd] / self.scale[:nd]
            tl_raw = np.floor(self._transform_position([0, 0]) + offset[::-1])
            br_raw = np.ceil(
                self._transform_position(self.node.canvas.size) + offset[::-1]
            )
        else:
            tl_raw = [0] * nd
            br_raw = [1] * nd

        top_left = np.zeros(self.layer.ndim)
        bottom_right = np.zeros(self.layer.ndim)
        for d, tl, br in zip(self.layer.dims.displayed, tl_raw, br_raw):
            top_left[d] = tl
            bottom_right[d] = br

        return np.array([top_left, bottom_right]).astype(int)

    def on_draw(self, event):
        """Called whenever the canvas is drawn.

        This is triggered from vispy whenever new data is sent to the canvas or
        the camera is moved and is connected in the `QtViewer`.
        """
        self.layer.scale_factor = self.scale_factor
        old_corner_pixels = self.layer.corner_pixels
        self.layer.corner_pixels = self.coordinates_of_canvas_corners()

        # For 2D multiscale data determine if new data has been requested
        if (
            self.layer.multiscale
            and self.layer.dims.ndisplay == 2
            and self.node.canvas is not None
        ):
            self.layer._update_multiscale(
                corner_pixels=old_corner_pixels,
                shape_threshold=self.node.canvas.size,
            )


@lru_cache()
def get_max_texture_sizes():
    """Get maximum texture sizes for 2D and 3D rendering.

    Returns
    -------
    MAX_TEXTURE_SIZE_2D : int or None
        Max texture size allowed by the vispy canvas during 2D rendering.
    MAX_TEXTURE_SIZE_3D : int or None
        Max texture size allowed by the vispy canvas during 2D rendering.
    """
    # A canvas must be created to access gl values
    c = Canvas(show=False)
    try:
        MAX_TEXTURE_SIZE_2D = gl.glGetParameter(gl.GL_MAX_TEXTURE_SIZE)
    finally:
        c.close()
    if MAX_TEXTURE_SIZE_2D == ():
        MAX_TEXTURE_SIZE_2D = None
    # vispy doesn't expose GL_MAX_3D_TEXTURE_SIZE so hard coding
    # MAX_TEXTURE_SIZE_3D = gl.glGetParameter(gl.GL_MAX_3D_TEXTURE_SIZE)
    # if MAX_TEXTURE_SIZE_3D == ():
    #    MAX_TEXTURE_SIZE_3D = None
    MAX_TEXTURE_SIZE_3D = 2048

    return MAX_TEXTURE_SIZE_2D, MAX_TEXTURE_SIZE_3D
