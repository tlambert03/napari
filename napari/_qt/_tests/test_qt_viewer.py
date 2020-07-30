import os
from unittest import mock

import numpy as np
import pytest

from napari.utils.io import imread
from napari._tests.utils import (
    add_layer_by_type,
    check_viewer_functioning,
    layer_test_data,
)


def test_qt_viewer(make_test_viewer):
    """Test instantiating viewer."""
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    assert viewer.title == 'napari'
    assert view.viewer == viewer
    # Check no console is present before it is requested
    assert view._console is None

    assert len(viewer.layers) == 0
    assert view.layers.vbox_layout.count() == 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0


def test_qt_viewer_with_console(make_test_viewer):
    """Test instantiating console from viewer."""
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer
    # Check no console is present before it is requested
    assert view._console is None
    # Check console is created when requested
    assert view.console is not None
    assert view.dockConsole.widget == view.console


def test_qt_viewer_toggle_console(make_test_viewer):
    """Test instantiating console from viewer."""
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer
    # Check no console is present before it is requested
    assert view._console is None
    # Check console has been created when it is supposed to be shown
    view.toggle_console_visibility(None)
    assert view._console is not None
    assert view.dockConsole.widget == view.console


@pytest.mark.parametrize('layer_class, data, ndim', layer_test_data)
def test_add_layer(make_test_viewer, layer_class, data, ndim):
    viewer = make_test_viewer(ndisplay=ndim)
    view = viewer.window.qt_viewer

    add_layer_by_type(viewer, layer_class, data)
    check_viewer_functioning(viewer, view, data, ndim)


def test_new_labels(make_test_viewer):
    """Test adding new labels layer."""
    # Add labels to empty viewer
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    viewer._new_labels()
    assert np.max(viewer.layers[0].data) == 0
    assert len(viewer.layers) == 1
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0

    # Add labels with image already present
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    np.random.seed(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    viewer._new_labels()
    assert np.max(viewer.layers[1].data) == 0
    assert len(viewer.layers) == 2
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0


def test_new_points(make_test_viewer):
    """Test adding new points layer."""
    # Add labels to empty viewer
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    viewer.add_points()
    assert len(viewer.layers[0].data) == 0
    assert len(viewer.layers) == 1
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0

    # Add points with image already present
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    np.random.seed(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    viewer.add_points()
    assert len(viewer.layers[1].data) == 0
    assert len(viewer.layers) == 2
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0


def test_new_shapes_empty_viewer(make_test_viewer):
    """Test adding new shapes layer."""
    # Add labels to empty viewer
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    viewer.add_shapes()
    assert len(viewer.layers[0].data) == 0
    assert len(viewer.layers) == 1
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0

    # Add points with image already present
    viewer = make_test_viewer()
    view = viewer.window.qt_viewer

    np.random.seed(0)
    data = np.random.random((10, 15))
    viewer.add_image(data)
    viewer.add_shapes()
    assert len(viewer.layers[1].data) == 0
    assert len(viewer.layers) == 2
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == 2
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == 0


def test_z_order_adding_removing_images(make_test_viewer):
    """Test z order is correct after adding/ removing images."""
    data = np.ones((10, 10))

    viewer = make_test_viewer()
    vis = viewer.window.qt_viewer.layer_to_visual
    viewer.add_image(data, colormap='red', name='red')
    viewer.add_image(data, colormap='green', name='green')
    viewer.add_image(data, colormap='blue', name='blue')
    order = [vis[x].order for x in viewer.layers]
    np.testing.assert_almost_equal(order, list(range(len(viewer.layers))))

    # Remove and re-add image
    viewer.layers.remove('red')
    order = [vis[x].order for x in viewer.layers]
    np.testing.assert_almost_equal(order, list(range(len(viewer.layers))))
    viewer.add_image(data, colormap='red', name='red')
    order = [vis[x].order for x in viewer.layers]
    np.testing.assert_almost_equal(order, list(range(len(viewer.layers))))

    # Remove two other images
    viewer.layers.remove('green')
    viewer.layers.remove('blue')
    order = [vis[x].order for x in viewer.layers]
    np.testing.assert_almost_equal(order, list(range(len(viewer.layers))))

    # Add two other layers back
    viewer.add_image(data, colormap='green', name='green')
    viewer.add_image(data, colormap='blue', name='blue')
    order = [vis[x].order for x in viewer.layers]
    np.testing.assert_almost_equal(order, list(range(len(viewer.layers))))


def test_screenshot(make_test_viewer):
    "Test taking a screenshot"
    viewer = make_test_viewer()

    np.random.seed(0)
    # Add image
    data = np.random.random((10, 15))
    viewer.add_image(data)

    # Add labels
    data = np.random.randint(20, size=(10, 15))
    viewer.add_labels(data)

    # Add points
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)

    # Add vectors
    data = 20 * np.random.random((10, 2, 2))
    viewer.add_vectors(data)

    # Add shapes
    data = 20 * np.random.random((10, 4, 2))
    viewer.add_shapes(data)

    # Take screenshot
    screenshot = viewer.window.qt_viewer.screenshot()
    assert screenshot.ndim == 3


def test_screenshot_dialog(make_test_viewer, tmpdir):
    """Test save screenshot functionality."""
    viewer = make_test_viewer()

    np.random.seed(0)
    # Add image
    data = np.random.random((10, 15))
    viewer.add_image(data)

    # Add labels
    data = np.random.randint(20, size=(10, 15))
    viewer.add_labels(data)

    # Add points
    data = 20 * np.random.random((10, 2))
    viewer.add_points(data)

    # Add vectors
    data = 20 * np.random.random((10, 2, 2))
    viewer.add_vectors(data)

    # Add shapes
    data = 20 * np.random.random((10, 4, 2))
    viewer.add_shapes(data)

    # Save screenshot
    input_filepath = os.path.join(tmpdir, 'test-save-screenshot')
    mock_return = (input_filepath, '')
    with mock.patch('napari._qt.qt_viewer.QFileDialog') as mocker:
        mocker.getSaveFileName.return_value = mock_return
        viewer.window.qt_viewer._screenshot_dialog()
    # Assert behaviour is correct
    expected_filepath = input_filepath + '.png'  # add default file extension
    assert os.path.exists(expected_filepath)
    output_data = imread(expected_filepath)
    expected_data = viewer.window.qt_viewer.screenshot()
    assert np.allclose(output_data, expected_data)


@pytest.mark.parametrize(
    "dtype", ['int8', 'uint8', 'int16', 'uint16', 'float32']
)
def test_qt_viewer_data_integrity(make_test_viewer, dtype):
    """Test that the viewer doesn't change the underlying array."""

    image = np.random.rand(10, 32, 32)
    image *= 200 if dtype.endswith('8') else 2 ** 14
    image = image.astype(dtype)
    imean = image.mean()

    viewer = make_test_viewer()

    viewer.add_image(image.copy())
    datamean = viewer.layers[0].data.mean()
    assert datamean == imean
    # toggle dimensions
    viewer.dims.ndisplay = 3
    datamean = viewer.layers[0].data.mean()
    assert datamean == imean
    # back to 2D
    viewer.dims.ndisplay = 2
    datamean = viewer.layers[0].data.mean()
    assert datamean == imean
