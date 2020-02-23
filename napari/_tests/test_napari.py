import numpy as np
import pytest
import napari

from napari._tests.utils import check_viewer_functioning, layer_test_data


@pytest.mark.parametrize('layer_type, data, ndim', layer_test_data)
def test_view(viewermodel_factory, layer_type, data, ndim):

    view, viewer = viewermodel_factory()
    getattr(viewer, f'add_{layer_type.__name__.lower()}')(data)
    check_viewer_functioning(viewer, view, data, ndim)


def test_view_multichannel(qtbot):
    """Test adding image."""

    np.random.seed(0)
    data = np.random.random((15, 10, 5))
    viewer = napari.view_image(data, channel_axis=-1)
    view = viewer.window.qt_viewer
    qtbot.addWidget(view)

    assert len(viewer.layers) == data.shape[-1]
    for i in range(data.shape[-1]):
        assert np.all(viewer.layers[i].data == data.take(i, axis=-1))

    # Close the viewer
    view.shutdown()
    viewer.window.close()
