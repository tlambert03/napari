from vispy.scene.subscene import SubScene

from .base import VispyBaseLayer


class VispyLayerGroup(VispyBaseLayer):
    def __init__(self, layer):
        self.node = SubScene()
        super().__init__(layer, self.node)

    def _on_data_change(self, event=None):
        pass

    def add_layer(self, layer: VispyBaseLayer):
        if layer is not None:
            layer.node.parent = self.node
