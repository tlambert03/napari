from functools import wraps

from ..utils.action_manager import action_manager
from ..utils.settings import get_settings
from ..utils.theme import available_themes
from ..utils.translations import trans
from .viewer_model import ViewerModel


def register_viewer_action(description):
    """
    Convenient decorator to register an action with the current ViewerModel

    It will use the function name as the action name. We force the description
    to be given instead of function docstring for translation purpose.
    """

    def _inner(func):
        # convert these functions to argument-free functions
        # that act on the current viewer
        @wraps(func)
        def _func():
            from ..viewer import Viewer

            v = Viewer.current()
            if v is not None:
                return func(v)

        action_manager.register_action(
            name='napari:' + func.__name__,
            command=_func,
            description=description,
            keymapprovider=ViewerModel,
        )
        return _func

    return _inner


@register_viewer_action(trans._("Reset scroll."))
def reset_scroll_progress(viewer):

    # on key press
    viewer.dims._scroll_progress = 0
    yield

    # on key release
    viewer.dims._scroll_progress = 0


reset_scroll_progress.__doc__ = trans._("Reset dims scroll progress")


@register_viewer_action(trans._("Toggle ndisplay."))
def toggle_ndisplay(viewer):
    viewer.dims.ndisplay = 2 if viewer.dims.ndisplay == 3 else 3


@register_viewer_action(trans._("Show/Hide IPython console"))
def toggle_console_visibility(viewer):
    viewer.window.qt_viewer.toggle_console_visibility()


# Making this an action makes vispy really unhappy during the tests
# on mac only with:
# ```
# RuntimeError: wrapped C/C++ object of type CanvasBackendDesktop has been deleted
# ```
@register_viewer_action(trans._("Toggle theme."))
def toggle_theme(viewer):
    """Toggle theme for viewer"""
    settings = get_settings()
    themes = available_themes()
    current_theme = settings.appearance.theme
    idx = themes.index(current_theme)
    idx += 1
    if idx == len(themes):
        idx = 0

    settings.appearance.theme = themes[idx]


@register_viewer_action(trans._("Reset view to original state."))
def reset_view(viewer):
    viewer.reset_view()


@register_viewer_action(trans._("Increment dimensions slider to the left."))
def increment_dims_left(viewer):
    viewer.dims._increment_dims_left()


@register_viewer_action(trans._("Increment dimensions slider to the right."))
def increment_dims_right(viewer):
    viewer.dims._increment_dims_right()


@register_viewer_action(trans._("Move focus of dimensions slider up."))
def focus_axes_up(viewer):
    viewer.dims._focus_up()


@register_viewer_action(trans._("Move focus of dimensions slider down."))
def focus_axes_down(viewer):
    viewer.dims._focus_down()


@register_viewer_action(
    trans._("Change order of the visible axes, e.g. [0, 1, 2] -> [2, 0, 1]."),
)
def roll_axes(viewer):
    viewer.dims._roll()


@register_viewer_action(
    trans._(
        "Transpose order of the last two visible axes, e.g. [0, 1] -> [1, 0]."
    )
)
def transpose_axes(viewer):
    viewer.dims._transpose()


@register_viewer_action(trans._("Toggle grid mode."))
def toggle_grid(viewer):
    viewer.grid.enabled = not viewer.grid.enabled


@register_viewer_action(trans._("Toggle visibility of selected layers"))
def toggle_selected_visibility(viewer):
    viewer.layers.toggle_selected_visibility()
