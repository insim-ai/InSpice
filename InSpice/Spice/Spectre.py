####################################################################################################
#
# InSpice - A Spice Package for Python
# Copyright (C) 2025 Innovoltive
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
####################################################################################################

"""This module provides Spectre format helpers, mapping tables, and the SpectreContext class
used by the distributed to_spectre() methods across InSpice classes.
"""

####################################################################################################

import logging
import os

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

# SPICE model type -> (extra_params, family, remove_level, remove_version)
TYPE_MAP = {
    'r':     ({},                'r',     False, False),
    'res':   ({},                'r',     False, False),
    'c':     ({},                'c',     False, False),
    'l':     ({},                'l',     False, False),
    'd':     ({},                'd',     False, False),
    'npn':   ({'type': '1'},     'bjt',   True,  False),
    'pnp':   ({'type': '-1'},    'bjt',   True,  False),
    'njf':   ({'type': '1'},     'jfet',  True,  False),
    'pjf':   ({'type': '-1'},    'jfet',  True,  False),
    'nmf':   ({'type': '1'},     'mes',   True,  False),
    'pmf':   ({'type': '-1'},    'mes',   True,  False),
    'nhfet': ({'type': '1'},     'hemt',  True,  False),
    'phfet': ({'type': '-1'},    'hemt',  True,  False),
    'nmos':  ({'type': '1'},     'mos',   True,  True),
    'pmos':  ({'type': '-1'},    'mos',   True,  True),
    'nsoi':  ({'type': '1'},     'soi',   True,  True),
    'psoi':  ({'type': '-1'},    'soi',   True,  True),
}

# (family, level, version) -> (osdi_file, module_name, extra_params)
FAMILY_MAP = {
    ('r',     None,  None):    ('spice/resistor.osdi',  'sp_resistor',  {}),
    ('c',     None,  None):    ('spice/capacitor.osdi', 'sp_capacitor', {}),
    ('l',     None,  None):    ('spice/inductor.osdi',  'sp_inductor',  {}),

    ('d',     None, None):     ('spice/diode.osdi',     'sp_diode',     {}),
    ('d',     1,    None):     ('spice/diode.osdi',     'sp_diode',     {}),
    ('d',     3,    None):     ('spice/diode.osdi',     'sp_diode',     {}),

    ('bjt',   None, None):     ('spice/bjt.osdi',       'sp_bjt',       {}),
    ('bjt',   1,    None):     ('spice/bjt.osdi',       'sp_bjt',       {}),
    ('bjt',   4,    None):     ('spice/vbic.osdi',      'sp_vbic',      {}),
    ('bjt',   9,    None):     ('spice/vbic.osdi',      'sp_vbic',      {}),

    ('jfet',  None, None):     ('spice/jfet1.osdi',     'sp_jfet1',     {}),
    ('jfet',  1,    None):     ('spice/jfet1.osdi',     'sp_jfet1',     {}),
    ('jfet',  2,    None):     ('spice/jfet2.osdi',     'sp_jfet2',     {}),

    ('mes',   None, None):     ('spice/mes1.osdi',      'sp_mes1',      {}),
    ('mes',   1,    None):     ('spice/mes1.osdi',      'sp_mes1',      {}),

    ('mos',   None, None):     ('spice/mos1.osdi',      'sp_mos1',      {}),
    ('mos',   1,    None):     ('spice/mos1.osdi',      'sp_mos1',      {}),
    ('mos',   2,    None):     ('spice/mos2.osdi',      'sp_mos2',      {}),
    ('mos',   3,    None):     ('spice/mos3.osdi',      'sp_mos3',      {}),
    ('mos',   6,    None):     ('spice/mos6.osdi',      'sp_mos6',      {}),
    ('mos',   9,    None):     ('spice/mos9.osdi',      'sp_mos9',      {}),

    ('mos',   8,    None):     ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   8,    '3.3'):    ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   8,    '3.3.0'):  ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   8,    '3.2'):    ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2"'}),
    ('mos',   8,    '3.20'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.20"'}),
    ('mos',   8,    '3.2.2'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.2"'}),
    ('mos',   8,    '3.22'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.22"'}),
    ('mos',   8,    '3.2.3'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.3"'}),
    ('mos',   8,    '3.23'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.23"'}),
    ('mos',   8,    '3.2.4'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.4"'}),
    ('mos',   8,    '3.24'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.24"'}),
    ('mos',   8,    '3.1'):    ('spice/bsim3v1.osdi',  'sp_bsim3v1',   {}),
    ('mos',   8,    '3.0'):    ('spice/bsim3v3.osdi',  'sp_bsim3v0',   {}),

    ('mos',   49,   None):     ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   49,   '3.3'):    ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   49,   '3.3.0'):  ('spice/bsim3v3.osdi',  'sp_bsim3v3',   {}),
    ('mos',   49,   '3.2'):    ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2"'}),
    ('mos',   49,   '3.20'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.20"'}),
    ('mos',   49,   '3.2.2'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.2"'}),
    ('mos',   49,   '3.22'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.22"'}),
    ('mos',   49,   '3.2.3'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.3"'}),
    ('mos',   49,   '3.23'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.23"'}),
    ('mos',   49,   '3.2.4'):  ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.2.4"'}),
    ('mos',   49,   '3.24'):   ('spice/bsim3v2.osdi',  'sp_bsim3v2',   {'version': '"3.24"'}),
    ('mos',   49,   '3.1'):    ('spice/bsim3v1.osdi',  'sp_bsim3v1',   {}),
    ('mos',   49,   '3.0'):    ('spice/bsim3v0.osdi',  'sp_bsim3v0',   {}),
}

# Default models for R/C/L elements without explicit model
DEFAULT_MODELS = {
    'R': ('spice/resistor.osdi', 'sp_resistor'),
    'C': ('spice/capacitor.osdi', 'sp_capacitor'),
    'L': ('spice/inductor.osdi', 'sp_inductor'),
}

####################################################################################################

def format_spectre_value(value):
    """Format a value for Spectre output, stripping units."""
    try:
        v = float(value)
        return '{:.6g}'.format(v)
    except (TypeError, ValueError):
        return str(value)

####################################################################################################

def spectre_identifier(name):
    """Ensure a name is a valid Spectre identifier (can't start with a digit)."""
    name = name.lower()
    if name and name[0].isdigit():
        return 'mod_' + name
    return name

####################################################################################################

def _get_model_param(model, param_name):
    """Safely get a model parameter, returning None if not found."""
    try:
        val = model[param_name]
        if val is not None:
            val_str = str(val).strip('"').strip("'")
            try:
                return int(val_str)
            except ValueError:
                return val_str
    except (KeyError, AttributeError):
        pass
    return None

####################################################################################################

def resolve_spectre_model(model):
    """Resolve a SPICE .model to its Spectre module name, OSDI file, and parameters.

    Returns (module_name, osdi_file, params) or None if unsupported.
    """
    model_type = model.model_type.lower()
    if model_type not in TYPE_MAP:
        return None

    extra_params, family, remove_level, remove_version = TYPE_MAP[model_type]
    level = _get_model_param(model, 'level')
    version = _get_model_param(model, 'version')

    key = (family, level, version)
    if key not in FAMILY_MAP:
        key = (family, level, None)
        if key not in FAMILY_MAP:
            key = (family, None, None)
            if key not in FAMILY_MAP:
                return None

    _, module_name, family_extra_params = FAMILY_MAP[key]
    osdi_file, _, _ = FAMILY_MAP[key]

    params = {}
    params.update(extra_params)
    params.update(family_extra_params)

    for param_name in model.parameters:
        p = param_name.lower()
        if remove_level and p == 'level':
            continue
        if remove_version and p == 'version':
            continue
        params[p] = format_spectre_value(model[param_name])

    return module_name, osdi_file, params

####################################################################################################

class SpectreContext:
    """Accumulator passed through to_spectre() calls to collect cross-cutting concerns."""

    def __init__(self, osdi_path=None):
        self.osdi_files = set()
        self.builtin_models = set()
        self.default_models = set()
        self.osdi_path = osdi_path

    def osdi_file_path(self, relative_path):
        if self.osdi_path:
            return os.path.join(self.osdi_path, relative_path)
        return relative_path

    def register_osdi(self, osdi_file):
        self.osdi_files.add(osdi_file)

    def register_builtin(self, name):
        self.builtin_models.add(name)

    def register_default_model(self, prefix):
        self.default_models.add(prefix)
