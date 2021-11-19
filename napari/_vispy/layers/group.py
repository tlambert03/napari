from vispy.scene.subscene import SubScene

from .base import VispyBaseLayer


class VispyLayerGroup(VispyBaseLayer):
    def __init__(self, layer):
        self.node = SubScene()
        super().__init__(layer, self.node)

        self.layer.events.inserted.connect(self._on_inserted)

    def _on_inserted(self, event=None):
        for child in self.layer:
            # print(child)
            ...

    def _on_data_change(self, event=None):
        pass

    def add_layer(self, layer: VispyBaseLayer):
        if layer is not None:
            layer.node.parent = self.node
