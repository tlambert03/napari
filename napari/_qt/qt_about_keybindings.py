from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QComboBox,
)
from collections import OrderedDict
import napari
from ..utils.interactions import get_keybindings_summary


class QtAboutKeybindings(QDialog):
    """Qt dialog window for displaying keybinding information.

    Parameters
    ----------
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.

    Attributes
    ----------
    keybindings_strs : collections.OrderedDict
        Ordered dictionary of hotkey shortcuts and associated keybindings.
        Dictionary keys include:
        - 'All active keybindings'
        - 'Image layer'
        - 'Labels layer'
        - 'Points layer'
        - 'Shapes layer'
        - 'Surface layer'
        - 'Vectors layer'
    layout : qtpy.QtWidgets.QVBoxLayout
        Layout of the widget.
    layerTypeComboBox : qtpy.QtWidgets.QComboBox
        Dropdown menu to select layer type.
    textEditBox : qtpy.QtWidgets.QTextEdit
        Text box widget containing table of keybindings information.
    viewer : napari.components.ViewerModel
        Napari viewer containing the rendered scene, layers, and controls.
    """

    ALL_ACTIVE_KEYBINDINGS = 'All active keybindings'

    def __init__(self, viewer, parent=None):
        super().__init__(parent=parent)

        self.viewer = viewer
        self.layout = QVBoxLayout()

        self.setWindowTitle('Keybindings')
        self.setWindowModality(Qt.NonModal)
        self.setLayout(self.layout)

        # stacked keybindings widgets
        self.textEditBox = QTextEdit()
        self.textEditBox.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.textEditBox.setMinimumWidth(360)
        # Can switch to a normal dict when our minimum Python is 3.7
        self.keybindings_strs = OrderedDict()
        self.keybindings_strs[self.ALL_ACTIVE_KEYBINDINGS] = ''
        col = self.viewer.palette['secondary']
        layers = [
            napari.layers.Image,
            napari.layers.Labels,
            napari.layers.Points,
            napari.layers.Shapes,
            napari.layers.Surface,
            napari.layers.Vectors,
        ]
        for layer in layers:
            if len(layer.class_keymap) == 0:
                text = 'No keybindings'
            else:
                text = get_keybindings_summary(layer.class_keymap, col=col)
            self.keybindings_strs[f"{layer.__name__} layer"] = text

        # layer type selection
        self.layerTypeComboBox = QComboBox()
        self.layerTypeComboBox.addItems(list(self.keybindings_strs))
        self.layerTypeComboBox.activated[str].connect(self.change_layer_type)
        self.layerTypeComboBox.setCurrentText(self.ALL_ACTIVE_KEYBINDINGS)
        # self.change_layer_type(current_layer)
        layer_type_layout = QHBoxLayout()
        layer_type_layout.setContentsMargins(10, 5, 0, 0)
        layer_type_layout.addWidget(self.layerTypeComboBox)
        layer_type_layout.addStretch(1)
        layer_type_layout.setSpacing(0)
        self.layout.addLayout(layer_type_layout)
        self.layout.addWidget(self.textEditBox, 1)

        self.viewer.events.active_layer.connect(self.update_active_layer)
        self.viewer.events.palette.connect(self.update_active_layer)
        self.update_active_layer()

    def change_layer_type(self, text):
        """Change layer type selected in dropdown menu.

        Parameters
        ----------
        text : str
            Dictionary key to access keybindings associated with the layer.
            Available keys include:
            - 'All active keybindings'
            - 'Image layer'
            - 'Labels layer'
            - 'Points layer'
            - 'Shapes layer'
            - 'Surface layer'
            - 'Vectors layer'
        """
        self.textEditBox.setHtml(self.keybindings_strs[text])

    def update_active_layer(self, event=None):
        """Update the active layer and display keybindings for that layer type.

        Parameters
        ----------
        event : qtpy.QtCore.QEvent, optional.
            Event from the Qt context, by default None.
        """
        col = self.viewer.palette['secondary']
        text = ''
        # Add class and instance viewer keybindings
        text += get_keybindings_summary(self.viewer.class_keymap, col=col)
        text += get_keybindings_summary(self.viewer.keymap, col=col)

        layer = self.viewer.active_layer
        if layer is not None:
            # Add class and instance layer keybindings for the active layer
            text += get_keybindings_summary(layer.class_keymap, col=col)
            text += get_keybindings_summary(layer.keymap, col=col)

        # Update layer speficic keybindings if all active are displayed
        self.keybindings_strs[self.ALL_ACTIVE_KEYBINDINGS] = text
        if self.layerTypeComboBox.currentText() == self.ALL_ACTIVE_KEYBINDINGS:
            self.textEditBox.setHtml(text)
