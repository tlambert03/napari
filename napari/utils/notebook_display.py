from io import BytesIO

__all__ = ['nbscreenshot']


def nbscreenshot(viewer, *, canvas_only=False):
    """Display napari screenshot in the jupyter notebook.

    Parameters
    ----------
    viewer : napari.Viewer
        The napari viewer.
    canvas_only : bool, optional
        If True includes the napari viewer frame in the screenshot,
        otherwise just includes the canvas. By default, True.

    Returns
    -------
    napari.utils.notebook_display.NotebookScreenshot
        Napari screenshot rendered as rich display in the jupyter notebook.
    """
    return NotebookScreenshot(viewer, canvas_only=canvas_only)


class NotebookScreenshot:
    """Display napari screenshot in the jupyter notebook.

    Functions returning an object with a _repr_png_() method
    will displayed as a rich image in the jupyter notebook.

    https://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html

    Examples
    --------
    ```
    import napari
    from skimage.data import chelsea

    viewer = napari.view_image(chelsea(), name='chelsea-the-cat')
    viewer.nbscreenshot()

    # screenshot just the canvas without the napari viewer framing it
    viewer.nbscreenshot(with_viewer=False)
    ```
    """

    def __init__(self, viewer, *, canvas_only=False):
        """Initialize screenshot object.

        Parameters
        ----------
        viewer : napari.Viewer
            The napari viewer
        canvas_only : bool, optional
            If False include the napari viewer frame in the screenshot,
            and if True then take screenshot of just the image display canvas.
            By default, False.
        """
        self.viewer = viewer
        self.canvas_only = canvas_only
        self.image = None

    def _repr_png_(self):
        """PNG representation of the viewer object for IPython.

        Returns
        -------
        In memory binary stream containing PNG screenshot image.
        """
        from imageio import imsave

        self.image = self.viewer.screenshot(canvas_only=self.canvas_only)
        with BytesIO() as file_obj:
            imsave(file_obj, self.image, format='png')
            file_obj.seek(0)
            png = file_obj.read()
        return png
