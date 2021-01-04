# flake8: noqa
"""The Window class is the primary entry to the napari GUI.

This defines the WindowProtocol that the GUI "front-end" would need to
implement to serve as a graphical user interface for napari.  These are all
the methods that the viewer is allowed to call on the window object.

Currently, this module is just a stub file that will simply pass through the
:class:`napari._qt.qt_main_window.Window` class.  
"""

from typing import TYPE_CHECKING, Optional, Type

from typing_extensions import Protocol

if TYPE_CHECKING:
    import numpy as np

    from napari.viewer import Viewer


class WindowProtocol(Protocol):
    def __init__(self, viewer: 'Viewer', *, show: bool = True):
        """Initialize Window for viewer instance"""

    def close(self) -> None:
        """Close the window."""

    def screenshot(
        self, path: Optional[str] = None, *, canvas_only: bool = True
    ) -> 'np.ndarray':
        """Take currently displayed screen and convert to an image array.

        Parameters
        ----------
        path : str, optional
            Filename for saving screenshot image. If not provided, no
        canvas_only : bool
            If True, screenshot shows only the image display canvas, and
            if False include the napari viewer frame in the screenshot,
            By default, True.

        Returns
        -------
        image : array
            Numpy array of type ubyte and shape (h, w, 4). Index [0, 0] is the
            upper-left corner of the rendered region.
        """

    def update_console(self, variables):
        """Update console's namespace with desired variables.

        Parameters
        ----------
        variables : dict, str or list/tuple of str
            The variables to inject into the console's namespace.  If a dict, a
            simple update is done.  If a str, the string is assumed to have
            variable names separated by spaces.  A list/tuple of str can also
            be used to give the variable names.  If just the variable names are
            give (list/tuple/str) then the variable values looked up in the
            callers frame.
        """


class MockWindow:
    def __init__(self, *a, **k):
        """Initialize Window for viewer instance"""

    def close(self):
        pass

    def screenshot(self, *args, **kwargs):
        pass

    def update_console(self, variables):
        pass


try:
    from ._qt import Window as QtWind

    Window: Type[WindowProtocol] = QtWind
except ImportError:

    Window = MockWindow
