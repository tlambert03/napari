from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSlider

from ...layers.image._constants import (
    ComplexRendering,
    Interpolation,
    Rendering,
)
from .qt_image_base_layer import QtBaseImageControls


class QtImageControls(QtBaseImageControls):
    """Qt view and controls for the napari Image layer.

    Parameters
    ----------
    layer : napari.layers.Image
        An instance of a napari Image layer.

    Attributes
    ----------
    attenuationSlider : qtpy.QtWidgets.QSlider
        Slider controlling attenuation rate for `attenuated_mip` mode.
    attenuationLabel : qtpy.QtWidgets.QLabel
        Label for the attenuation slider widget.
    grid_layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    interpComboBox : qtpy.QtWidgets.QComboBox
        Dropdown menu to select the interpolation mode for image display.
    interpLabel : qtpy.QtWidgets.QLabel
        Label for the interpolation dropdown menu.
    isoThresholdSlider : qtpy.QtWidgets.QSlider
        Slider controlling the isosurface threshold value for rendering.
    isoThresholdLabel : qtpy.QtWidgets.QLabel
        Label for the isosurface threshold slider widget.
    layer : napari.layers.Image
        An instance of a napari Image layer.
    renderComboBox : qtpy.QtWidgets.QComboBox
        Dropdown menu to select the rendering mode for image display.
    renderLabel : qtpy.QtWidgets.QLabel
        Label for the rendering mode dropdown menu.
    """

    def __init__(self, layer):
        super().__init__(layer)

        self.layer.events.interpolation.connect(self._on_interpolation_change)
        self.layer.events.rendering.connect(self._on_rendering_change)
        self.layer.events.iso_threshold.connect(self._on_iso_threshold_change)
        self.layer.events.attenuation.connect(self._on_attenuation_change)
        self.layer.dims.events.ndisplay.connect(self._on_ndisplay_change)
        self.layer.events.data.connect(self._on_data_change)
        self.layer.events.complex_rendering.connect(
            self._on_complex_rendering_change
        )

        interp_comboBox = QComboBox(self)
        interp_comboBox.addItems(Interpolation.keys())
        index = interp_comboBox.findText(
            self.layer.interpolation, Qt.MatchFixedString
        )
        interp_comboBox.setCurrentIndex(index)
        interp_comboBox.activated[str].connect(self.changeInterpolation)
        self.interpComboBox = interp_comboBox
        self.interpLabel = QLabel('interpolation:')

        renderComboBox = QComboBox(self)
        renderComboBox.addItems(Rendering.keys())
        index = renderComboBox.findText(
            self.layer.rendering, Qt.MatchFixedString
        )
        renderComboBox.setCurrentIndex(index)
        renderComboBox.activated[str].connect(self.changeRendering)
        self.renderComboBox = renderComboBox
        self.renderLabel = QLabel('rendering:')

        sld = QSlider(Qt.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(100)
        sld.setSingleStep(1)
        sld.setValue(self.layer.iso_threshold * 100)
        sld.valueChanged.connect(self.changeIsoThreshold)
        self.isoThresholdSlider = sld
        self.isoThresholdLabel = QLabel('iso threshold:')

        sld = QSlider(Qt.Horizontal, parent=self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setMinimum(0)
        sld.setMaximum(200)
        sld.setSingleStep(1)
        sld.setValue(self.layer.attenuation * 100)
        sld.valueChanged.connect(self.changeAttenuation)
        self.attenuationSlider = sld
        self.attenuationLabel = QLabel('attenuation:')

        self.contrastLimitsLabel = QLabel('contrast limits:')
        self.gammaLabel = QLabel('gamma:')

        # complex value combo
        self.complexLabel = QLabel('complex:')
        self.complexComboBox = QComboBox()
        self.complexComboBox.addItems(ComplexRendering.lower_members())
        self.complexComboBox.currentTextChanged.connect(self.changeComplex)

        colormap_layout = QHBoxLayout()
        colormap_layout.addWidget(self.colorbarLabel)
        colormap_layout.addWidget(self.colormapComboBox)
        colormap_layout.addStretch(1)

        self._on_ndisplay_change()
        self._on_data_change()

        # grid_layout created in QtLayerControls
        # addWidget(widget, row, column, [row_span, column_span])
        self.grid_layout.addWidget(QLabel('opacity:'), 0, 0)
        self.grid_layout.addWidget(self.opacitySlider, 0, 1)
        self.grid_layout.addWidget(self.contrastLimitsLabel, 1, 0)
        self.grid_layout.addWidget(self.contrastLimitsSlider, 1, 1)
        self.grid_layout.addWidget(self.gammaLabel, 2, 0)
        self.grid_layout.addWidget(self.gammaSlider, 2, 1)
        self.grid_layout.addWidget(QLabel('colormap:'), 3, 0)
        self.grid_layout.addLayout(colormap_layout, 3, 1)
        self.grid_layout.addWidget(QLabel('blending:'), 4, 0)
        self.grid_layout.addWidget(self.blendComboBox, 4, 1)
        self.grid_layout.addWidget(self.renderLabel, 5, 0)
        self.grid_layout.addWidget(self.renderComboBox, 5, 1)
        self.grid_layout.addWidget(self.interpLabel, 6, 0)
        self.grid_layout.addWidget(self.interpComboBox, 6, 1)
        self.grid_layout.addWidget(self.isoThresholdLabel, 7, 0)
        self.grid_layout.addWidget(self.isoThresholdSlider, 7, 1)
        self.grid_layout.addWidget(self.attenuationLabel, 8, 0)
        self.grid_layout.addWidget(self.attenuationSlider, 8, 1)
        self.grid_layout.addWidget(self.complexLabel, 9, 0)
        self.grid_layout.addWidget(self.complexComboBox, 9, 1)
        self.grid_layout.setRowStretch(10, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setSpacing(4)

    def changeInterpolation(self, text):
        """Change interpolation mode for image display.

        Parameters
        ----------
        text : str
            Interpolation mode used by vispy. Must be one of our supported
            modes:
            'bessel', 'bicubic', 'bilinear', 'blackman', 'catrom', 'gaussian',
            'hamming', 'hanning', 'hermite', 'kaiser', 'lanczos', 'mitchell',
            'nearest', 'spline16', 'spline36'
        """
        self.layer.interpolation = text

    def changeRendering(self, text):
        """Change rendering mode for image display.

        Parameters
        ----------
        text : str
            Rendering mode used by vispy.
            Selects a preset rendering mode in vispy that determines how
            volume is displayed:
            * translucent: voxel colors are blended along the view ray until
              the result is opaque.
            * mip: maxiumum intensity projection. Cast a ray and display the
              maximum value that was encountered.
            * additive: voxel colors are added along the view ray until
              the result is saturated.
            * iso: isosurface. Cast a ray until a certain threshold is
              encountered. At that location, lighning calculations are
              performed to give the visual appearance of a surface.
            * attenuated_mip: attenuated maxiumum intensity projection. Cast a
              ray and attenuate values based on integral of encountered values,
              display the maximum value that was encountered after attenuation.
              This will make nearer objects appear more prominent.
        """
        self.layer.rendering = text
        self._toggle_rendering_parameter_visbility()

    def changeIsoThreshold(self, value):
        """Change isosurface threshold on the layer model.

        Parameters
        ----------
        value : float
            Threshold for isosurface.
        """
        with self.layer.events.blocker(self._on_iso_threshold_change):
            self.layer.iso_threshold = value / 100

    def changeComplex(self, text):
        # it's possible that a custom function name has beenset
        if text in ComplexRendering.lower_members():
            self.layer.complex_rendering = text

    def _on_iso_threshold_change(self, event):
        """Receive layer model isosurface change event and update the slider.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.iso_threshold.blocker():
            self.isoThresholdSlider.setValue(self.layer.iso_threshold * 100)

    def changeAttenuation(self, value):
        """Change attenuation rate for attenuated maximum intensity projection.

        Parameters
        ----------
        value : Float
            Attenuation rate for attenuated maximum intensity projection.
        """
        with self.layer.events.blocker(self._on_attenuation_change):
            self.layer.attenuation = value / 100

    def _on_attenuation_change(self, event):
        """Receive layer model attenuation change event and update the slider.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.attenuation.blocker():
            self.attenuationSlider.setValue(self.layer.attenuation * 100)

    def _on_interpolation_change(self, event):
        """Receive layer interpolation change event and update dropdown menu.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.interpolation.blocker():
            index = self.interpComboBox.findText(
                self.layer.interpolation, Qt.MatchFixedString
            )
            self.interpComboBox.setCurrentIndex(index)

    def _on_rendering_change(self, event):
        """Receive layer model rendering change event and update dropdown menu.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent
            Event from the Qt context.
        """
        with self.layer.events.rendering.blocker():
            index = self.renderComboBox.findText(
                self.layer.rendering, Qt.MatchFixedString
            )
            self.renderComboBox.setCurrentIndex(index)
            self._toggle_rendering_parameter_visbility()

    def _on_complex_rendering_change(self, event=None):
        """Set the name of the complex_rendering mode upon change.

        Becuase Image.complex_rendering allows for the user to set custom
        functions, there is extra logic here to update the combo box if an
        unknown function has been set.  We remove them when deselected.
        """
        if isinstance(self.layer.complex_rendering, ComplexRendering):
            text = self.layer.complex_rendering.name.lower()
        else:
            text = self.layer.complex_rendering.__name__.lower()

        if self.layer.complex_rendering == ComplexRendering.COLORMAP:
            self.contrastLimitsLabel.setText('phase limits:')
            self.gammaLabel.setText('mag gamma:')
        else:
            self.contrastLimitsLabel.setText('contrast limits:')
            self.gammaLabel.setText('gamma:')

        # remove any names that may have been added and are no longer valid
        valid = set(ComplexRendering.lower_members() + [text])
        for i in reversed(range(self.complexComboBox.count())):
            if self.complexComboBox.itemText(i) not in valid:
                self.complexComboBox.removeItem(i)
        # if the current option is not in the combo box, add it.
        if self.complexComboBox.findText(text) == -1:
            self.complexComboBox.addItem(text)

        with self.layer.events.complex_rendering.blocker():
            self.complexComboBox.setCurrentText(text)

    def _toggle_rendering_parameter_visbility(self):
        """Hide isosurface rendering parameters if they aren't needed."""
        rendering = Rendering(self.layer.rendering)
        if rendering == Rendering.ISO:
            self.isoThresholdSlider.show()
            self.isoThresholdLabel.show()
        else:
            self.isoThresholdSlider.hide()
            self.isoThresholdLabel.hide()
        if rendering == Rendering.ATTENUATED_MIP:
            self.attenuationSlider.show()
            self.attenuationLabel.show()
        else:
            self.attenuationSlider.hide()
            self.attenuationLabel.hide()

    def _on_ndisplay_change(self, event=None):
        """Toggle between 2D and 3D visualization modes.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional
            Event from the Qt context, default is None.
        """
        if self.layer.dims.ndisplay == 2:
            self.isoThresholdSlider.hide()
            self.isoThresholdLabel.hide()
            self.attenuationSlider.hide()
            self.attenuationLabel.hide()
            self.renderComboBox.hide()
            self.renderLabel.hide()
            self.interpComboBox.show()
            self.interpLabel.show()
        else:
            self.renderComboBox.show()
            self.renderLabel.show()
            self.interpComboBox.hide()
            self.interpLabel.hide()
            self._toggle_rendering_parameter_visbility()

    def _on_data_change(self, event=None):
        if self.layer.is_complex:
            self.complexComboBox.show()
            self.complexLabel.show()
        else:
            self.complexComboBox.hide()
            self.complexLabel.hide()
