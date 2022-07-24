"""All commands that are available in the napari GUI are defined here.

Internally, prefer using the CommandId enum instead of the string literal.
When adding a new command, add a new title/description in the _COMMAND_INFO dict
below.  The title will be used in the GUI, and the may be used in auto generated
documentation.

CommandId values should be namespaced, e.g. 'napari:layer:something' for a command
that operates on layers.
"""
from enum import Enum
from typing import NamedTuple, Optional

from ...utils.translations import trans


# fmt: off
class CommandId(str, Enum):
    """Id representing a napari command."""

    TOGGLE_FULLSCREEN = 'napari:window:view:toggle_fullscreen'
    TOGGLE_MENUBAR = 'napari:window:view:toggle_menubar'
    TOGGLE_PLAY = 'napari:window:view:toggle_play'
    TOGGLE_OCTREE_CHUNK_OUTLINES = 'napari:window:view:toggle_octree_chunk_outlines'
    TOGGLE_LAYER_TOOLTIPS = 'napari:window:view:toggle_layer_tooltips'
    TOGGLE_ACTIVITY_DOCK = 'napari:window:view:toggle_activity_dock'

    TOGGLE_VIEWER_AXES = 'napari:window:view:toggle_viewer_axes'
    TOGGLE_VIEWER_AXES_COLORED = 'napari:window:view:toggle_viewer_axes_colored'
    TOGGLE_VIEWER_AXES_LABELS = 'napari:window:view:toggle_viewer_axes_labels'
    TOGGLE_VIEWER_AXES_DASHED = 'napari:window:view:toggle_viewer_axesdashed'
    TOGGLE_VIEWER_AXES_ARROWS = 'napari:window:view:toggle_viewer_axes_arrows'
    TOGGLE_VIEWER_SCALE_BAR = 'napari:window:view:toggle_viewer_scale_bar'
    TOGGLE_VIEWER_SCALE_BAR_COLORED = 'window:view:toggle_viewer_scale_bar_colored'
    TOGGLE_VIEWER_SCALE_BAR_TICKS = 'napari:window:view:toggle_viewer_scale_bar_ticks'

    LAYER_DUPLICATE = 'napari:layer:duplicate'
    LAYER_SPLIT_STACK = 'napari:layer:split_stack'
    LAYER_SPLIT_RGB = 'napari:layer:split_rgb'
    LAYER_MERGE_STACK = 'napari:layer:merge_stack'
    LAYER_TOGGLE_VISIBILITY = 'napari:layer:toggle_visibility'

    LAYER_LINK_SELECTED = 'napari:layer:link_selected_layers'
    LAYER_UNLINK_SELECTED = 'napari:layer:unlink_selected_layers'
    LAYER_SELECT_LINKED = 'napari:layer:select_linked_layers'

    LAYER_CONVERT_TO_LABELS = 'napari:layer:convert_to_labels'
    LAYER_CONVERT_TO_IMAGE = 'napari:layer:convert_to_image'

    LAYER_CONVERT_TO_INT8 = 'napari:layer:convert_to_int8'
    LAYER_CONVERT_TO_INT16 = 'napari:layer:convert_to_int16'
    LAYER_CONVERT_TO_INT32 = 'napari:layer:convert_to_int32'
    LAYER_CONVERT_TO_INT64 = 'napari:layer:convert_to_int64'
    LAYER_CONVERT_TO_UINT8 = 'napari:layer:convert_to_uint8'
    LAYER_CONVERT_TO_UINT16 = 'napari:layer:convert_to_uint16'
    LAYER_CONVERT_TO_UINT32 = 'napari:layer:convert_to_uint32'
    LAYER_CONVERT_TO_UINT64 = 'napari:layer:convert_to_uint64'

    LAYER_PROJECT_MAX = 'napari:layer:project_max'
    LAYER_PROJECT_MIN = 'napari:layer:project_min'
    LAYER_PROJECT_STD = 'napari:layer:project_std'
    LAYER_PROJECT_SUM = 'napari:layer:project_sum'
    LAYER_PROJECT_MEAN = 'napari:layer:project_mean'
    LAYER_PROJECT_MEDIAN = 'napari:layer:project_median'

    @property
    def title(self) -> str:
        return _COMMAND_INFO[self].title

    @property
    def description(self) -> Optional[str]:
        return _COMMAND_INFO[self].description


class _ci(NamedTuple):
    title: str
    description: Optional[str] = None


_COMMAND_INFO = {
    CommandId.TOGGLE_FULLSCREEN: _ci(trans._('Toggle Full Screen'),),
    CommandId.TOGGLE_MENUBAR: _ci(trans._('Toggle Menubar Visibility'),),
    CommandId.TOGGLE_PLAY: _ci(trans._('Toggle Play'),),
    CommandId.TOGGLE_OCTREE_CHUNK_OUTLINES: _ci(trans._('Toggle Chunk Outlines'),),
    CommandId.TOGGLE_LAYER_TOOLTIPS: _ci(trans._('Toggle Layer Tooltips'),),
    CommandId.TOGGLE_ACTIVITY_DOCK: _ci(trans._('Toggle Activity Dock'),),
    CommandId.TOGGLE_VIEWER_AXES: _ci(trans._('Axes Visible')),
    CommandId.TOGGLE_VIEWER_AXES_COLORED: _ci(trans._('Axes Colored')),
    CommandId.TOGGLE_VIEWER_AXES_LABELS: _ci(trans._('Axes Labels')),
    CommandId.TOGGLE_VIEWER_AXES_DASHED: _ci(trans._('Axes Dashed')),
    CommandId.TOGGLE_VIEWER_AXES_ARROWS: _ci(trans._('Axes Arrows')),
    CommandId.TOGGLE_VIEWER_SCALE_BAR: _ci(trans._('Scale Bar Visible')),
    CommandId.TOGGLE_VIEWER_SCALE_BAR_COLORED: _ci(trans._('Scale Bar Colored')),
    CommandId.TOGGLE_VIEWER_SCALE_BAR_TICKS: _ci(trans._('Scale Bar Ticks')),

    CommandId.LAYER_DUPLICATE: _ci(trans._('Duplicate Layer'),),
    CommandId.LAYER_SPLIT_STACK: _ci(trans._('Split Stack'),),
    CommandId.LAYER_SPLIT_RGB: _ci(trans._('Split RGB'),),
    CommandId.LAYER_MERGE_STACK: _ci(trans._('Merge to Stack'),),
    CommandId.LAYER_TOGGLE_VISIBILITY: _ci(trans._('Toggle visibility'),),
    CommandId.LAYER_LINK_SELECTED: _ci(trans._('Link Layers'),),
    CommandId.LAYER_UNLINK_SELECTED: _ci(trans._('Unlink Layers'),),
    CommandId.LAYER_SELECT_LINKED: _ci(trans._('Select Linked Layers'),),
    CommandId.LAYER_CONVERT_TO_LABELS: _ci(trans._('Convert to Labels'),),
    CommandId.LAYER_CONVERT_TO_IMAGE: _ci(trans._('Convert to Image'),),
    CommandId.LAYER_CONVERT_TO_INT8: _ci(trans._('Convert to int8'),),
    CommandId.LAYER_CONVERT_TO_INT16: _ci(trans._('Convert to int16'),),
    CommandId.LAYER_CONVERT_TO_INT32: _ci(trans._('Convert to int32'),),
    CommandId.LAYER_CONVERT_TO_INT64: _ci(trans._('Convert to int64'),),
    CommandId.LAYER_CONVERT_TO_UINT8: _ci(trans._('Convert to uint8'),),
    CommandId.LAYER_CONVERT_TO_UINT16: _ci(trans._('Convert to uint16'),),
    CommandId.LAYER_CONVERT_TO_UINT32: _ci(trans._('Convert to uint32'),),
    CommandId.LAYER_CONVERT_TO_UINT64: _ci(trans._('Convert to uint64'),),
    CommandId.LAYER_PROJECT_MAX: _ci(trans._('Max projection'),),
    CommandId.LAYER_PROJECT_MIN: _ci(trans._('Min projection'),),
    CommandId.LAYER_PROJECT_STD: _ci(trans._('Std projection'),),
    CommandId.LAYER_PROJECT_SUM: _ci(trans._('Sum projection'),),
    CommandId.LAYER_PROJECT_MEAN: _ci(trans._('Mean projection'),),
    CommandId.LAYER_PROJECT_MEDIAN: _ci(trans._('Median projection'),),
}
# fmt: on