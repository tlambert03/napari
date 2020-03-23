"""
These convenience functions will be useful for searching pypi for packages
that match the plugin naming convention, and retrieving related metadata.
"""
import re
import sys
import os
from subprocess import run
from typing import Dict, List, Tuple, Union
from urllib import request

from ..utils.appdirs import user_plugin_dir, user_site_packages

PYPI_SIMPLE_API_URL = 'https://pypi.org/simple/'
URL_CACHE = {}  # {name: url} for packages at pypi.org/simple
VERSION_CACHE = {}  # {name: tuple of versions} for packages at pypi.org/simple


def clear_cache():
    global URL_CACHE
    global VERSION_CACHE

    URL_CACHE = {}
    VERSION_CACHE = {}


def get_packages_by_prefix(prefix: str) -> Dict[str, str]:
    """Search for packages starting with ``prefix`` on pypi.

    Packages using naming convention: http://bit.ly/pynaming-convention
    can be autodiscovered on pypi using the SIMPLE API:
    https://www.python.org/dev/peps/pep-0503/

    Returns
    -------
    dict
        {name: url} for all packages at pypi that start with ``prefix``
    """

    with request.urlopen(PYPI_SIMPLE_API_URL) as response:
        html = response.read()

    pattern = f'<a href="/simple/(.+)">({prefix}.*)</a>'
    urls = {
        name: PYPI_SIMPLE_API_URL + url
        for url, name in re.findall(pattern, html.decode())
    }
    URL_CACHE.update(urls)
    return urls


def get_package_versions(name: str) -> Tuple[str]:
    """Get available versions of a package on pypi

    Parameters
    ----------
    name : str
        name of the package

    Returns
    -------
    tuple
        versions available on pypi
    """
    url = URL_CACHE.get(name, PYPI_SIMPLE_API_URL + name)
    with request.urlopen(url) as response:
        html = response.read()

    versions = tuple(set(re.findall(f'>{name}-(.+).tar', html.decode())))
    VERSION_CACHE[name] = versions
    return versions


def install_pypi_plugin(name_or_names: Union[str, List[str]]) -> List[str]:
    names = (
        [name_or_names] if isinstance(name_or_names, str) else name_or_names
    )
    cmd = ['pip', 'install']
    env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        env['PYTHONPATH'] = user_site_packages()
        cmd += ['--prefix', user_plugin_dir()]
    result = run(cmd + names, capture_output=True, env=env)
    result.check_returncode()  # if errors: raise CalledProcessError
    output = result.stdout.decode()
    for line in reversed(output.splitlines()):
        if 'Successfully installed' in line:
            return [
                i for i in line.replace('Successfully installed', '').split()
            ]
    return []
