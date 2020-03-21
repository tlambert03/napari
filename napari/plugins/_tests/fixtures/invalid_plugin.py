"""
Test plugin that would fail to load.
"""
import pluggy

napari_hook_implementation = pluggy.HookimplMarker("napari")


def reader_function(path):
    return True


@napari_hook_implementation
def napari_get_reader(path, arg1, arg2, i_just_love_args):
    # this has too many arguments!

    if path.endswith('ext'):
        return reader_function
