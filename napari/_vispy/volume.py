from vispy.color import get_colormap
from vispy.scene.visuals import create_visual_node
from vispy.visuals.shaders import Function

from .vendored import VolumeVisual as _VolumeVisual
from .vendored.volume import FRAG_SHADER, frag_dict

ATTENUATED_MIP_SNIPPETS = dict(
    before_loop="""
        float maxval = -99999.0; // The maximum encountered value
        float sumval = 0.0; // The sum of the encountered values
        float scaled = 0.0; // The scaled value
        int maxi = 0;  // Where the maximum value was encountered
        vec3 maxloc = vec3(0.0);  // Location where the maximum value was encountered
        """,
    in_loop="""
        sumval = sumval + val;
        scaled = val * exp(-u_attenuation * (sumval - 1) / u_relative_step_size);
        if( scaled > maxval ) {
            maxval = scaled;
            maxi = iter;
            maxloc = loc;
        }
        """,
    after_loop="""
        gl_FragColor = applyColormap(maxval);
        """,
)
ATTENUATED_MIP_FRAG_SHADER = FRAG_SHADER.format(**ATTENUATED_MIP_SNIPPETS)

frag_dict['attenuated_mip'] = ATTENUATED_MIP_FRAG_SHADER


# Custom volume class is needed for better 3D rendering
class VolumeVisual(_VolumeVisual):
    def __init__(self, *args, **kwargs):
        self._attenuation = 1.0
        super().__init__(*args, **kwargs)

    @property
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, cmap):
        self._cmap = get_colormap(cmap)
        self.shared_program.frag['cmap'] = Function(self._cmap.glsl_map)
        # Colormap change fix
        self.shared_program['texture2D_LUT'] = (
            self.cmap.texture_lut()
            if (hasattr(self.cmap, 'texture_lut'))
            else None
        )
        self.update()

    @property
    def threshold(self):
        """The threshold value to apply for the isosurface render method.
        """
        return self._threshold

    @threshold.setter
    def threshold(self, value):
        # Fix for #1399, should be fixed in the VisPy threshold setter
        self._threshold = float(value)
        self.shared_program['u_threshold'] = self._threshold
        self.update()

    @property
    def attenuation(self):
        """The attenuation value to apply for the attenuated mip render method.
        """
        return self._attenuation

    @attenuation.setter
    def attenuation(self, value):
        # Fix for #1399, should be fixed in the VisPy threshold setter
        self._attenuation = float(value)
        attenuation = self._attenuation
        if self._texture_float:
            attenuation /= 100  # TODO: empirically chosen magic number...
        self.shared_program['u_attenuation'] = attenuation
        self.update()


Volume = create_visual_node(VolumeVisual)
