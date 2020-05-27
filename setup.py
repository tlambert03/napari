#!/usr/bin/env python
"""Napari viewer is a fast, interactive, multi-dimensional image viewer for
Python. It's designed for browsing, annotating, and analyzing large
multi-dimensional images. It's built on top of `Qt` (for the GUI), `vispy`
(for performant GPU-based rendering), and the scientific Python stack
(`numpy`, `scipy`).
"""


from setuptools import setup

import versioneer


setup(
    version=versioneer.get_version(), cmdclass=versioneer.get_cmdclass(),
)
