import napari
import numpy as np
from napari import Viewer
from napari.layers import Image, Labels, Points, Shapes, Vectors, Surface

"""
Used as pytest params for testing layer add and view functionality (Layer class, data, ndim)
"""
layer_test_data = [
    (Image, np.random.random((10, 15)), 2),
    (Image, np.random.random((10, 15, 20)), 3),
    (Image, [np.random.random(s) for s in [(40, 20), (20, 10), (10, 5)]], 2),
    (Labels, np.random.randint(20, size=(10, 15)), 2),
    (Labels, np.random.randint(20, size=(6, 10, 15)), 3),
    (Points, 20 * np.random.random((10, 2)), 2),
    (Points, 20 * np.random.random((10, 3)), 3),
    (Vectors, 20 * np.random.random((10, 2, 2)), 2),
    (Shapes, 20 * np.random.random((10, 4, 2)), 2),
    (Shapes, 20 * np.random.random((10, 4, 2)), 2),
    (
        Surface,
        (
            np.random.random((10, 3)),
            np.random.randint(10, size=(6, 3)),
            np.random.random(10),
        ),
        3,
    ),
]


classes = [Labels, Points, Vectors, Shapes, Surface, Image]
names = [cls.__name__.lower() for cls in classes]
layer2addmethod = {
    cls: getattr(Viewer, 'add_' + name) for cls, name in zip(classes, names)
}

layer2viewmethod = {
    cls: getattr(napari, 'view_' + name) for cls, name in zip(classes, names)
}

# examples of valid tuples that might be passed to viewer._add_layer_from_data
good_layer_data = [
    (np.random.random((10, 10)),),
    (np.random.random((10, 10, 3)), {'rgb': True}),
    (np.random.randint(20, size=(10, 15)), {'seed': 0.3}, 'labels'),
    (np.random.random((10, 2)) * 20, {'face_color': 'blue'}, 'points'),
    (np.random.random((10, 2, 2)) * 20, {}, 'vectors'),
    (np.random.random((10, 4, 2)) * 20, {'opacity': 1}, 'shapes'),
    (
        (
            np.random.random((10, 3)),
            np.random.randint(10, size=(6, 3)),
            np.random.random(10),
        ),
        {'name': 'some surface'},
        'surface',
    ),
]


def add_layer_by_type(viewer, layer_type, data, visible=True):
    """
    Convenience method that maps a LayerType to its add_layer method.

    Parameters
    ----------
    layer_type : LayerTypes
        Layer type to add
    data
        The layer data to view
    """
    return layer2addmethod[layer_type](viewer, data, visible=visible)


def view_layer_type(layer_type, data):
    """
    Convenience method that maps a LayerType to it's view method.

    Parameters
    ----------
    layer_type : LayerTypes
        Layer type to view
    data
        The layer data to view
    """
    return layer2viewmethod[layer_type](data, show=False)


def check_viewer_functioning(viewer, view=None, data=None, ndim=2):
    viewer.dims.ndisplay = 2
    assert np.all(viewer.layers[0].data == data)
    assert len(viewer.layers) == 1
    assert view.layers.vbox_layout.count() == 2 * len(viewer.layers) + 2

    assert viewer.dims.ndim == ndim
    assert view.dims.nsliders == viewer.dims.ndim
    assert np.sum(view.dims._displayed_sliders) == ndim - 2

    # Switch to 3D rendering mode and back to 2D rendering mode
    viewer.dims.ndisplay = 3
    assert viewer.dims.ndisplay == 3

    # Flip dims order displayed
    dims_order = list(range(ndim))
    viewer.dims.order = dims_order
    assert viewer.dims.order == dims_order

    # Flip dims order including non-displayed
    dims_order[0], dims_order[-1] = dims_order[-1], dims_order[0]
    viewer.dims.order = dims_order
    assert viewer.dims.order == dims_order

    viewer.dims.ndisplay = 2
    assert viewer.dims.ndisplay == 2


def check_view_transform_consistency(layer, viewer, transf_dict):
    """Check layer transforms have been applied to the view.

    Parameters
    ----------
    layer : napari.layers.Layer
        Layer model.
    viewer : napari.Viewer
        Viewer, including Qt elements
    transf_dict : dict
        Dictionary of transform properties with keys referring to the name of
        the transform property (i.e. `scale`, `translate`) and the value
        corresponding to the array of property values
    """
    # Get an handle on visual layer:
    vis_lyr = viewer.window.qt_viewer.layer_to_visual[layer]

    # Visual layer attributes should match expected from viewer dims:
    for transf_name, transf in transf_dict.items():
        disp_dims = viewer.dims.displayed  # dimensions displayed in 2D
        # values of visual layer
        vis_vals = getattr(vis_lyr, transf_name)[1::-1]

        # The transform of the visual includes both values from the
        # data2world transform and the tile2data transform and so any
        # any additional scaling / translation from tile2data transform
        # must be taken into account
        transform = layer._transforms['tile2data'].set_slice(disp_dims)
        tile_transf = getattr(transform, transf_name)
        if transf_name == 'scale':
            # expected scale values
            correct_vals = np.multiply(transf[disp_dims], tile_transf)
        else:
            # expected translate values
            correct_vals = np.add(transf[disp_dims], tile_transf)
        assert (vis_vals == correct_vals).all()
