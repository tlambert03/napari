import numpy as np
from napari.layers import Surface


def test_random_surface():
    """Test instantiating Surface layer with random 2D data."""
    np.random.seed(0)
    vertices = np.random.random((10, 2))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random(10)
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.ndim == 2
    assert np.all([np.all(ld == d) for ld, d in zip(layer.data, data)])
    assert np.all(layer.vertices == vertices)
    assert np.all(layer.faces == faces)
    assert np.all(layer.vertex_values == values)
    assert layer._data_view.shape[1] == 2
    assert layer._view_vertex_values.ndim == 1


def test_random_3D_surface():
    """Test instantiating Surface layer with random 3D data."""
    np.random.seed(0)
    vertices = np.random.random((10, 3))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random(10)
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.ndim == 3
    assert np.all([np.all(ld == d) for ld, d in zip(layer.data, data)])
    assert layer._data_view.shape[1] == 2
    assert layer._view_vertex_values.ndim == 1

    layer.dims.ndisplay = 3
    assert layer._data_view.shape[1] == 3
    assert layer._view_vertex_values.ndim == 1


def test_random_4D_surface():
    """Test instantiating Surface layer with random 4D data."""
    np.random.seed(0)
    vertices = np.random.random((10, 4))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random(10)
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.ndim == 4
    assert np.all([np.all(ld == d) for ld, d in zip(layer.data, data)])
    assert layer._data_view.shape[1] == 2
    assert layer._view_vertex_values.ndim == 1

    layer.dims.ndisplay = 3
    assert layer._data_view.shape[1] == 3
    assert layer._view_vertex_values.ndim == 1


def test_random_3D_timeseries_surface():
    """Test instantiating Surface layer with random 3D timeseries data."""
    np.random.seed(0)
    vertices = np.random.random((10, 3))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random((22, 10))
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.ndim == 4
    assert np.all([np.all(ld == d) for ld, d in zip(layer.data, data)])
    assert layer._data_view.shape[1] == 2
    assert layer._view_vertex_values.ndim == 1
    assert layer.shape[0] == 22

    layer.dims.ndisplay = 3
    assert layer._data_view.shape[1] == 3
    assert layer._view_vertex_values.ndim == 1

    # If a values axis is made to be a displayed axis then no data should be
    # shown
    layer.dims.order = [3, 0, 1, 2]
    assert len(layer._data_view) == 0


def test_random_3D_multitimeseries_surface():
    """Test instantiating Surface layer with random 3D multitimeseries data."""
    np.random.seed(0)
    vertices = np.random.random((10, 3))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random((16, 22, 10))
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.ndim == 5
    assert np.all([np.all(ld == d) for ld, d in zip(layer.data, data)])
    assert layer._data_view.shape[1] == 2
    assert layer._view_vertex_values.ndim == 1
    assert layer.shape[0] == 16
    assert layer.shape[1] == 22

    layer.dims.ndisplay = 3
    assert layer._data_view.shape[1] == 3
    assert layer._view_vertex_values.ndim == 1


def test_visiblity():
    """Test setting layer visiblity."""
    np.random.seed(0)
    vertices = np.random.random((10, 3))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random(10)
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.visible is True

    layer.visible = False
    assert layer.visible is False

    layer = Surface(data, visible=False)
    assert layer.visible is False

    layer.visible = True
    assert layer.visible is True


def test_surface_gamma():
    """Test setting gamma."""
    np.random.seed(0)
    vertices = np.random.random((10, 3))
    faces = np.random.randint(10, size=(6, 3))
    values = np.random.random(10)
    data = (vertices, faces, values)
    layer = Surface(data)
    assert layer.gamma == 1

    # Change gamma property
    gamma = 0.7
    layer.gamma = gamma
    assert layer.gamma == gamma

    # Set gamma as keyword argument
    layer = Surface(data, gamma=gamma)
    assert layer.gamma == gamma
