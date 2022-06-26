from enum import Enum


class NapariMenu(str, Enum):
    LAYERLIST_CONTEXT = 'napari/layers/context'
    LAYERS_CONVERT_DTYPE = 'napari/layers/convert_dtype'
    LAYERS_PROJECT = 'napari/layers/project'

    def __str__(self):
        return self.value


class NapariMenuGroup:
    class LAYERLIST_CONTEXT:
        NAVIGATION = 'navigation'
        CONVERSION = '1_conversion'
        SPLIT_MERGE = '5_split_merge'
        LINK = '9_link'
