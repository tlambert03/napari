from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QComboBox, QDoubleSpinBox, QFrame
from .qt_base_layer import QtLayerControls
from vispy.color import Color


class QtVectorsControls(QtLayerControls):
    """Qt view and controls for the napari Vectors layer.

    Parameters
    ----------
    layer : napari.layers.Vectors
        An instance of a napari Vectors layer.

    Attributes
    ----------
    edgeColorSwatch : qtpy.QtWidgets.QFrame
        Color swatch showing display color of vectors.
    edgeComboBox : qtpy.QtWidgets.QComboBox
        Dropdown widget to select display color for vectors.
    grid_layout : qtpy.QtWidgets.QGridLayout
        Layout of Qt widget controls for the layer.
    layer : napari.layers.Vectors
        An instance of a napari Vectors layer.
    lengthSpinBox : qtpy.QtWidgets.QDoubleSpinBox
        Spin box widget controlling line length of vectors.
        Multiplicative factor on projections for length of all vectors.
    widthSpinBox : qtpy.QtWidgets.QDoubleSpinBox
        Spin box widget controlling edge line width of vectors.
    """

    def __init__(self, layer):
        super().__init__(layer)

        self.layer.events.edge_width.connect(self._on_width_change)
        self.layer.events.length.connect(self._on_len_change)
        self.layer.events.edge_color.connect(self._on_edge_color_change)

        # vector color adjustment and widget
        edge_comboBox = QComboBox()
        edge_comboBox.addItems(self.layer._colors)
        edge_comboBox.activated[str].connect(self.change_edge_color)
        self.edgeComboBox = edge_comboBox
        self.edgeColorSwatch = QFrame()
        self.edgeColorSwatch.setObjectName('swatch')
        self.edgeColorSwatch.setToolTip('Edge color swatch')
        self._on_edge_color_change()

        # line width in pixels
        self.widthSpinBox = QDoubleSpinBox()
        self.widthSpinBox.setKeyboardTracking(False)
        self.widthSpinBox.setSingleStep(0.1)
        self.widthSpinBox.setMinimum(0.1)
        self.widthSpinBox.setValue(self.layer.edge_width)
        self.widthSpinBox.valueChanged.connect(self.change_width)

        # line length
        self.lengthSpinBox = QDoubleSpinBox()
        self.lengthSpinBox.setKeyboardTracking(False)
        self.lengthSpinBox.setSingleStep(0.1)
        self.lengthSpinBox.setValue(self.layer.length)
        self.lengthSpinBox.setMinimum(0.1)
        self.lengthSpinBox.valueChanged.connect(self.change_length)

        # grid_layout created in QtLayerControls
        # addWidget(widget, row, column, [row_span, column_span])
        self.grid_layout.addWidget(QLabel('opacity:'), 0, 0)
        self.grid_layout.addWidget(self.opacitySlider, 0, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('width:'), 1, 0)
        self.grid_layout.addWidget(self.widthSpinBox, 1, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('length:'), 2, 0)
        self.grid_layout.addWidget(self.lengthSpinBox, 2, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('blending:'), 3, 0)
        self.grid_layout.addWidget(self.blendComboBox, 3, 1, 1, 2)
        self.grid_layout.addWidget(QLabel('edge color:'), 4, 0)
        self.grid_layout.addWidget(self.edgeComboBox, 4, 2)
        self.grid_layout.addWidget(self.edgeColorSwatch, 4, 1)
        self.grid_layout.setRowStretch(5, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setSpacing(4)

    def change_edge_color(self, text):
        """Change edge color of vectors on the layer model.

        Parameters
        ----------
        text : str
            Edge color for vectors, color name or hex string.
            Eg: 'white', 'red', 'blue', '#00ff00', etc.
        """
        self.layer.edge_color = text

    def change_width(self, value):
        """Change edge line width of vectors on the layer model.

        Parameters
        ----------
        value : float
            Line width of vectors.
        """
        self.layer.edge_width = value
        self.widthSpinBox.clearFocus()
        self.setFocus()

    def change_length(self, value):
        """Change length of vectors on the layer model.

        Multiplicative factor on projections for length of all vectors.

        Parameters
        ----------
        value : float
            Length of vectors.
        """
        self.layer.length = value
        self.lengthSpinBox.clearFocus()
        self.setFocus()

    def _on_len_change(self, event=None):
        """Change length of vectors.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.length.blocker():
            self.lengthSpinBox.setValue(self.layer.length)

    def _on_width_change(self, event=None):
        """"Receive layer model width change event and update width spinbox.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.edge_width.blocker():
            self.widthSpinBox.setValue(self.layer.edge_width)

    def _on_edge_color_change(self, event=None):
        """"Receive layer model edge color change event & update color swatch.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        with self.layer.events.edge_color.blocker():
            index = self.edgeComboBox.findText(
                self.layer.edge_color, Qt.MatchFixedString
            )
            self.edgeComboBox.setCurrentIndex(index)
        color = Color(self.layer.edge_color).hex
        self.edgeColorSwatch.setStyleSheet("background-color: " + color)
