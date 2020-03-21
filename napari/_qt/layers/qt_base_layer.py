from qtpy.QtCore import Qt
from qtpy.QtWidgets import QSlider, QGridLayout, QFrame, QComboBox

from ...layers.base._base_constants import Blending


class QtLayerControls(QFrame):
    """Superclass for all the other LayerControl classes.

    This class is never directly instantiated anywhere.

    Parameters
    ----------
    layer : napari.layers.Layer
        An instance of a napari layer.

    Attributes
    ----------
    blendComboBox : qtpy.QtWidgets.QComboBox
        Drowpdown widget to select blending mode of layer.
    grid_layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Layer
        An instance of a napari layer.
    opacitySlider : qtpy.QtWidgets.QSlider
        Slider controlling opacity of the layer.
    """

    def __init__(self, layer):
        super().__init__()

        self.layer = layer
        layer.events.blending.connect(self._on_blending_change)
        layer.events.opacity.connect(self._on_opacity_change)
        self.setObjectName('layer')
        self.setMouseTracking(True)

        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)
        self.grid_layout.setColumnMinimumWidth(0, 86)
        self.grid_layout.setColumnStretch(1, 1)
        self.setLayout(self.grid_layout)

        sld = QSlider(Qt.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(100)
        sld.setSingleStep(1)
        sld.valueChanged.connect(self.changeOpacity)
        self.opacitySlider = sld
        self._on_opacity_change()

        blend_comboBox = QComboBox(self)
        blend_comboBox.addItems(Blending.keys())
        index = blend_comboBox.findText(
            self.layer.blending, Qt.MatchFixedString
        )
        blend_comboBox.setCurrentIndex(index)
        blend_comboBox.activated[str].connect(self.changeBlending)
        self.blendComboBox = blend_comboBox

    def changeOpacity(self, value):
        """Change opacity value on the layer model.

        Parameters
        ----------
        value : float
            Opacity value for shapes.
            Input range 0 - 100 (transparent to fully opaque).
        """
        with self.layer.events.blocker(self._on_opacity_change):
            self.layer.opacity = value / 100

    def changeBlending(self, text):
        """Change blending mode on the layer model.

        Parameters
        ----------
        text : str
            Name of blending mode, eg: 'translucent', 'additive', 'opaque'.
        """
        self.layer.blending = text

    def _on_opacity_change(self, event=None):
        """Receive layer model opacity change event and update opacity slider.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.opacity.blocker():
            self.opacitySlider.setValue(self.layer.opacity * 100)

    def _on_blending_change(self, event=None):
        """Receive layer model blending mode change event and update slider.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.blending.blocker():
            index = self.blendComboBox.findText(
                self.layer.blending, Qt.MatchFixedString
            )
            self.blendComboBox.setCurrentIndex(index)
