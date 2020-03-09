import numpy as np


def test_big_2D_image(viewer_factory):
    """Test big 2D image with axis exceeding max texture size."""
    view, viewer = viewer_factory()

    shape = (20_000, 10)
    data = np.random.random(shape)
    layer = viewer.add_image(data, is_pyramid=False)
    visual = view.layer_to_visual[layer]
    assert visual.node is not None
    if visual.MAX_TEXTURE_SIZE_2D is not None:
        ds = np.ceil(np.divide(shape, visual.MAX_TEXTURE_SIZE_2D)).astype(int)
        assert np.all(layer._transform_view.scale == ds)


def test_big_3D_image(viewer_factory):
    """Test big 3D image with axis exceeding max texture size."""
    view, viewer = viewer_factory(ndisplay=3)

    shape = (5, 10, 3_000)
    data = np.random.random(shape)
    layer = viewer.add_image(data, is_pyramid=False)
    visual = view.layer_to_visual[layer]
    assert visual.node is not None
    if visual.MAX_TEXTURE_SIZE_3D is not None:
        ds = np.ceil(np.divide(shape, visual.MAX_TEXTURE_SIZE_3D)).astype(int)
        assert np.all(layer._transform_view.scale == ds)
