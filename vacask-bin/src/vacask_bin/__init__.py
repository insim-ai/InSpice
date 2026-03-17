"""Prebuilt VACASK circuit simulator binaries."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXE = '.exe' if sys.platform == 'win32' else ''

BIN_DIR = os.path.join(_HERE, 'data', 'bin')
MOD_DIR = os.path.join(_HERE, 'data', 'lib', 'vacask', 'mod')
VACASK_CMD = os.path.join(BIN_DIR, 'vacask' + _EXE)
OPENVAF_CMD = os.path.join(BIN_DIR, 'openvaf-r' + _EXE)

from ._version import __version__


def _run_vacask():
    """Entry point for the 'vacask' console script."""
    os.execvp(VACASK_CMD, [VACASK_CMD] + sys.argv[1:])
