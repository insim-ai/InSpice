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

"""This module implements the VACASK simulation netlist generator.

VACASK uses Spectre-like syntax, not SPICE. This module translates InSpice Circuit objects
(SPICE-style) into VACASK format.
"""

####################################################################################################

import logging
import os

####################################################################################################

from ..Simulation import Simulation
from ..AnalysisParameters import (
    ACAnalysisParameters,
    DCAnalysisParameters,
    NoiseAnalysisParameters,
    OperatingPointAnalysisParameters,
    TransientAnalysisParameters,
)
from ..HighLevelElement import (
    SinusoidalMixin,
    PulseMixin,
    ExponentialMixin,
    PieceWiseLinearMixin,
)
from ..BasicElement import (
    VoltageSource,
    CurrentSource,
    VoltageControlledVoltageSource,
    VoltageControlledCurrentSource,
    CurrentControlledVoltageSource,
    CurrentControlledCurrentSource,
)
from ..unit import str_spice

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

def _format_value(value):
    """Format a value for VACASK output, stripping units."""
    try:
        v = float(value)
        return '{:.6g}'.format(v)
    except (TypeError, ValueError):
        return str(value)

####################################################################################################

class VacaskSimulation(Simulation):

    _logger = _module_logger.getChild('VacaskSimulation')

    ##############################################

    def __init__(self, simulator, circuit, **kwargs):
        super().__init__(simulator, circuit, **kwargs)
        self._osdi_path = simulator.osdi_path

    ##############################################

    def _osdi_file_path(self, relative_path):
        if self._osdi_path:
            return os.path.join(self._osdi_path, relative_path)
        return relative_path

    ##############################################

    def _collect_osdi_files(self):
        """Collect all OSDI files needed by models and default elements."""
        osdi_files = set()

        # From explicit models
        for model in self._circuit.models:
            model_type = model.model_type.lower()
            if model_type in TYPE_MAP:
                _, family, remove_level, remove_version = TYPE_MAP[model_type]
                level = None
                version = None
                if not remove_level:
                    level = self._get_model_param(model, 'level')
                if not remove_version:
                    version = self._get_model_param(model, 'version')
                key = (family, level, version)
                if key in FAMILY_MAP:
                    osdi_file, _, _ = FAMILY_MAP[key]
                    osdi_files.add(osdi_file)

        # From default models for elements without explicit model
        for element in self._circuit.elements:
            if not element.enabled:
                continue
            prefix = element.PREFIX
            if prefix in DEFAULT_MODELS:
                if not self._element_has_model(element):
                    osdi_file, _ = DEFAULT_MODELS[prefix]
                    osdi_files.add(osdi_file)

        # Always load vsource/isource for V/I elements
        for element in self._circuit.elements:
            if not element.enabled:
                continue
            if element.PREFIX == 'V':
                osdi_files.add('spice/vsource.osdi')
            elif element.PREFIX == 'I':
                osdi_files.add('spice/isource.osdi')
            elif element.PREFIX == 'E':
                osdi_files.add('spice/vcvs.osdi')
            elif element.PREFIX == 'G':
                osdi_files.add('spice/vccs.osdi')
            elif element.PREFIX == 'F':
                osdi_files.add('spice/cccs.osdi')
            elif element.PREFIX == 'H':
                osdi_files.add('spice/ccvs.osdi')

        return osdi_files

    ##############################################

    @staticmethod
    def _get_model_param(model, param_name):
        """Safely get a model parameter, returning None if not found."""
        try:
            val = model[param_name]
            if val is not None:
                # Strip quotes if present
                val_str = str(val).strip('"').strip("'")
                try:
                    return int(val_str)
                except ValueError:
                    return val_str
        except (KeyError, AttributeError):
            pass
        return None

    ##############################################

    @staticmethod
    def _element_has_model(element):
        """Check if an element references an explicit model."""
        try:
            model = element.model
            return model is not None and str(model) != ''
        except AttributeError:
            return False

    ##############################################

    def _translate_model(self, model):
        """Translate a SPICE .model to VACASK model declaration."""
        model_type = model.model_type.lower()
        if model_type not in TYPE_MAP:
            self._logger.warning(f"Unknown model type '{model_type}' for model '{model.name}'")
            return f"// Unsupported model type: {model.model_type} for {model.name}"

        extra_params, family, remove_level, remove_version = TYPE_MAP[model_type]
        level = self._get_model_param(model, 'level')
        version = self._get_model_param(model, 'version')

        key = (family, level, version)
        if key not in FAMILY_MAP:
            # Try fallback without version
            key = (family, level, None)
            if key not in FAMILY_MAP:
                # Try fallback without level
                key = (family, None, None)
                if key not in FAMILY_MAP:
                    self._logger.warning(f"No OSDI mapping for model '{model.name}' "
                                         f"(family={family}, level={level}, version={version})")
                    return f"// No OSDI mapping for model {model.name}"

        _, module_name, family_extra_params = FAMILY_MAP[key]

        # Build parameter list
        params = {}
        params.update(extra_params)
        params.update(family_extra_params)

        for param_name in model.parameters:
            p = param_name.lower()
            if remove_level and p == 'level':
                continue
            if remove_version and p == 'version':
                continue
            params[p] = _format_value(model[param_name])

        param_str = ' '.join(f'{k}={v}' for k, v in params.items())
        name = model.name.lower()
        if param_str:
            return f"model {name} {module_name} {param_str}"
        else:
            return f"model {name} {module_name}"

    ##############################################

    def _translate_element(self, element):
        """Translate a single SPICE element to VACASK instance."""
        prefix = element.PREFIX
        name = element.name.lower()
        nodes = ' '.join(str(n) for n in element.node_names)

        if prefix == 'R':
            return self._translate_resistor(element, name, nodes)
        elif prefix == 'C':
            return self._translate_capacitor(element, name, nodes)
        elif prefix == 'L':
            return self._translate_inductor(element, name, nodes)
        elif prefix in ('V', 'I'):
            return self._translate_source(element, name, nodes, prefix)
        elif prefix in ('D', 'Q', 'M', 'J', 'Z'):
            return self._translate_semiconductor(element, name, nodes)
        elif prefix == 'X':
            return self._translate_subcircuit(element, name, nodes)
        elif prefix == 'E':
            return self._translate_vcvs(element, name)
        elif prefix == 'G':
            return self._translate_vccs(element, name)
        elif prefix == 'F':
            return self._translate_cccs(element, name)
        elif prefix == 'H':
            return self._translate_ccvs(element, name)
        else:
            return f"// Unsupported element: {element.name}"

    ##############################################

    def _translate_resistor(self, element, name, nodes):
        if self._element_has_model(element):
            model_name = str(element.model).lower()
            params = f"r={_format_value(element.resistance)}"
        else:
            model_name = 'sp_resistor'
            params = f"r={_format_value(element.resistance)}"
        return f"{name} ({nodes}) {model_name} {params}"

    ##############################################

    def _translate_capacitor(self, element, name, nodes):
        if self._element_has_model(element):
            model_name = str(element.model).lower()
            params = f"c={_format_value(element.capacitance)}"
        else:
            model_name = 'sp_capacitor'
            params = f"c={_format_value(element.capacitance)}"
        ic = self._get_element_param(element, 'initial_condition')
        if ic is not None:
            params += f" ic={_format_value(ic)}"
        return f"{name} ({nodes}) {model_name} {params}"

    ##############################################

    def _translate_inductor(self, element, name, nodes):
        if self._element_has_model(element):
            model_name = str(element.model).lower()
            params = f"l={_format_value(element.inductance)}"
        else:
            model_name = 'sp_inductor'
            params = f"l={_format_value(element.inductance)}"
        ic = self._get_element_param(element, 'initial_condition')
        if ic is not None:
            params += f" ic={_format_value(ic)}"
        return f"{name} ({nodes}) {model_name} {params}"

    ##############################################

    def _translate_source(self, element, name, nodes, prefix):
        if prefix == 'V':
            module = 'vsource'
        else:
            module = 'isource'

        params = self._translate_source_params(element)
        return f"{name} ({nodes}) {module} {params}"

    ##############################################

    def _translate_source_params(self, element):
        """Translate source DC, AC, and waveform parameters."""
        parts = []

        if isinstance(element, SinusoidalMixin):
            dc_val = _format_value(element.dc_offset)
            ac_val = _format_value(element.ac_magnitude)
            parts.append(f"dc={dc_val}")
            parts.append(f"mag={ac_val}")
            parts.append('type="sine"')
            parts.append(f"sinedc={_format_value(element.offset)}")
            parts.append(f"ampl={_format_value(element.amplitude)}")
            parts.append(f"freq={_format_value(element.frequency)}")
            delay = element.delay
            if delay is not None and float(delay) != 0:
                parts.append(f"delay={_format_value(delay)}")
            damping = element.damping_factor
            if damping is not None and float(damping) != 0:
                parts.append(f"theta={_format_value(damping)}")

        elif isinstance(element, PulseMixin):
            dc_val = _format_value(element.dc_offset)
            parts.append(f"dc={dc_val}")
            parts.append('type="pulse"')
            parts.append(f"val0={_format_value(element.initial_value)}")
            parts.append(f"val1={_format_value(element.pulsed_value)}")
            delay = element.delay_time
            if delay is not None and float(delay) != 0:
                parts.append(f"delay={_format_value(delay)}")
            parts.append(f"rise={_format_value(element.rise_time)}")
            parts.append(f"fall={_format_value(element.fall_time)}")
            parts.append(f"width={_format_value(element.pulse_width)}")
            parts.append(f"period={_format_value(element.period)}")

        elif isinstance(element, ExponentialMixin):
            parts.append('type="exp"')
            parts.append(f"val0={_format_value(element.initial_value)}")
            parts.append(f"val1={_format_value(element.pulsed_value)}")
            if element.rise_delay_time is not None:
                parts.append(f"delay={_format_value(element.rise_delay_time)}")
            if element.rise_time_constant is not None:
                parts.append(f"tau1={_format_value(element.rise_time_constant)}")
            if element.fall_delay_time is not None:
                parts.append(f"td2={_format_value(element.fall_delay_time)}")
            if element.fall_time_constant is not None:
                parts.append(f"tau2={_format_value(element.fall_time_constant)}")

        elif isinstance(element, PieceWiseLinearMixin):
            parts.append('type="pwl"')
            # PWL values as paired list
            values = element.values
            pwl_pairs = []
            for i in range(0, len(values), 2):
                pwl_pairs.append(f"{_format_value(values[i])}, {_format_value(values[i+1])}")
            parts.append(f"wave=[{'; '.join(pwl_pairs)}]")

        else:
            # Plain DC/AC source
            dc_value = self._get_element_param(element, 'dc_value')
            ac_value = self._get_element_param(element, 'ac_value')
            if dc_value is not None:
                parts.append(f"dc={_format_value(dc_value)}")
            if ac_value is not None:
                parts.append(f"mag={_format_value(ac_value)}")

        return ' '.join(parts)

    ##############################################

    def _translate_semiconductor(self, element, name, nodes):
        """Translate D, Q, M, J, Z elements."""
        model_name = str(element.model).lower()
        params = self._collect_instance_params(element)
        param_str = ' '.join(f'{k}={v}' for k, v in params.items())
        if param_str:
            return f"{name} ({nodes}) {model_name} {param_str}"
        else:
            return f"{name} ({nodes}) {model_name}"

    ##############################################

    def _collect_instance_params(self, element):
        """Collect instance parameters for semiconductor elements."""
        params = {}
        prefix = element.PREFIX

        # Area parameters
        area = self._get_element_param(element, 'area')
        if area is not None:
            params['area'] = _format_value(area)

        # MOSFET geometry
        if prefix == 'M':
            length = self._get_element_param(element, 'length')
            width = self._get_element_param(element, 'width')
            if length is not None:
                params['l'] = _format_value(length)
            if width is not None:
                params['w'] = _format_value(width)

        # Multiplier -> $mfactor
        m = self._get_element_param(element, 'multiplier')
        if m is not None and int(m) != 1:
            params['$mfactor'] = _format_value(m)

        return params

    ##############################################

    def _translate_subcircuit(self, element, name, nodes):
        """Translate X (subcircuit) element."""
        subcircuit_name = str(element.subcircuit_name).lower()
        # Collect any parameter assignments
        params = {}
        try:
            for key, value in element.parameters.items():
                params[key] = _format_value(value)
        except AttributeError:
            pass
        param_str = ' '.join(f'{k}={v}' for k, v in params.items())
        if param_str:
            return f"{name} ({nodes}) {subcircuit_name} {param_str}"
        else:
            return f"{name} ({nodes}) {subcircuit_name}"

    ##############################################

    def _translate_vcvs(self, element, name):
        """Translate voltage-controlled voltage source (E)."""
        out_p = element.output_plus.node
        out_m = element.output_minus.node
        in_p = element.input_plus.node
        in_m = element.input_minus.node
        gain = _format_value(element.voltage_gain)
        return f"{name} ({out_p} {out_m} {in_p} {in_m}) vcvs gain={gain}"

    ##############################################

    def _translate_vccs(self, element, name):
        """Translate voltage-controlled current source (G)."""
        out_p = element.output_plus.node
        out_m = element.output_minus.node
        in_p = element.input_plus.node
        in_m = element.input_minus.node
        gm = _format_value(element.transconductance)
        return f"{name} ({out_p} {out_m} {in_p} {in_m}) vccs gain={gm}"

    ##############################################

    def _translate_cccs(self, element, name):
        """Translate current-controlled current source (F)."""
        nodes = ' '.join(str(n) for n in element.node_names)
        source = str(element.source).lower()
        gain = _format_value(element.current_gain)
        return f'{name} ({nodes}) cccs ctlinst="{source}" gain={gain}'

    ##############################################

    def _translate_ccvs(self, element, name):
        """Translate current-controlled voltage source (H)."""
        nodes = ' '.join(str(n) for n in element.node_names)
        source = str(element.source).lower()
        rm = _format_value(element.transresistance)
        return f'{name} ({nodes}) ccvs ctlinst="{source}" gain={rm}'

    ##############################################

    @staticmethod
    def _get_element_param(element, param_name):
        """Safely get an element parameter, returning None if not found or None."""
        try:
            val = getattr(element, param_name)
            if val is not None and str(val) != '':
                return val
        except AttributeError:
            pass
        return None

    ##############################################

    def _translate_subcircuit_def(self, subcircuit):
        """Translate a SubCircuit definition to VACASK format."""
        from ..Netlist import SubCircuit
        name = str(subcircuit.name).lower()
        ext_nodes = ' '.join(str(n) for n in subcircuit._external_nodes)

        lines = [f"subckt {name}({ext_nodes})"]

        # Parameters
        if hasattr(subcircuit, '_parameters') and subcircuit._parameters:
            params = ' '.join(f'{k}={v}' for k, v in subcircuit._parameters.items())
            lines.append(f"  parameters {params}")

        # Elements inside subcircuit
        for element in subcircuit.elements:
            if element.enabled:
                lines.append('  ' + self._translate_element(element))

        # Models inside subcircuit
        for model in subcircuit.models:
            lines.append('  ' + self._translate_model(model))

        lines.append("ends")
        return '\n'.join(lines)

    ##############################################

    def _translate_analysis(self, analysis_parameters):
        """Translate analysis parameters to VACASK control block lines."""
        lines = []

        if isinstance(analysis_parameters, OperatingPointAnalysisParameters):
            lines.append('analysis op1 op')

        elif isinstance(analysis_parameters, TransientAnalysisParameters):
            parts = ['analysis tran1 tran']
            parts.append(f"step={_format_value(analysis_parameters.step_time)}")
            parts.append(f"stop={_format_value(analysis_parameters.end_time)}")
            if analysis_parameters.max_time is not None:
                parts.append(f"maxstep={_format_value(analysis_parameters.max_time)}")
            if analysis_parameters.use_initial_condition:
                parts.append('icmode="uic"')
            # Add initial conditions to tran analysis
            if self._initial_condition:
                ic_parts = []
                for key, value in self._initial_condition.items():
                    # key is like V(node), extract node name
                    node = key
                    if node.startswith('V(') and node.endswith(')'):
                        node = node[2:-1]
                    ic_parts.append(f'"{node}"; {_format_value(value)}')
                parts.append(f"ic=[{'; '.join(ic_parts)}]")
            lines.append(' '.join(parts))

        elif isinstance(analysis_parameters, ACAnalysisParameters):
            parts = ['analysis ac1 ac']
            parts.append(f"from={_format_value(analysis_parameters.start_frequency)}")
            parts.append(f"to={_format_value(analysis_parameters.stop_frequency)}")
            parts.append(f'mode="{analysis_parameters.variation}"')
            parts.append(f"points={analysis_parameters.number_of_points}")
            lines.append(' '.join(parts))

        elif isinstance(analysis_parameters, NoiseAnalysisParameters):
            parts = ['analysis noise1 noise']
            # output is like V(node, ref) - extract node
            output = str(analysis_parameters.output)
            parts.append(f'out="{output}"')
            parts.append(f'in="{str(analysis_parameters.src).lower()}"')
            parts.append(f"from={_format_value(analysis_parameters.start_frequency)}")
            parts.append(f"to={_format_value(analysis_parameters.stop_frequency)}")
            parts.append(f'mode="{analysis_parameters.variation}"')
            parts.append(f"points={analysis_parameters.points}")
            lines.append(' '.join(parts))

        elif isinstance(analysis_parameters, DCAnalysisParameters):
            # DC sweep wraps an op analysis
            params = analysis_parameters.parameters
            # params is [src_name, start, stop, step, ...]
            for i in range(0, len(params), 4):
                src = str(params[i]).lower()
                start = _format_value(params[i + 1])
                stop = _format_value(params[i + 2])
                step = _format_value(params[i + 3])
                lines.append(
                    f'sweep {src} instance="{src}" parameter="dc" '
                    f'from={start} to={stop} step={step}'
                )
            lines.append('analysis op1 op')
            # Add nodesets to op analysis
            if self._node_set:
                ns_parts = []
                for key, value in self._node_set.items():
                    node = key
                    if node.startswith('V(') and node.endswith(')'):
                        node = node[2:-1]
                    ns_parts.append(f'"{node}"; {_format_value(value)}')
                # Modify the op line to include nodeset
                lines[-1] = f'analysis op1 op nodeset=[{"; ".join(ns_parts)}]'

        return lines

    ##############################################

    def _translate_options(self):
        """Translate simulation options to VACASK format."""
        parts = []
        for key, value in self._options.items():
            k = key.lower()
            if k == 'savecurrents':
                continue
            if value is not None:
                parts.append(f"{k}={_format_value(value)}")
            else:
                parts.append(k)
        # Always request binary raw file output
        parts.append('rawfile="binary"')
        return 'options ' + ' '.join(parts)

    ##############################################

    def __str__(self):
        """Generate the complete VACASK simulation netlist."""
        lines = []

        # Title
        lines.append(f"// {self._circuit.title}")
        lines.append('')

        # Ground
        lines.append('ground 0')
        lines.append('')

        # Load directives for OSDI files
        osdi_files = self._collect_osdi_files()
        for osdi_file in sorted(osdi_files):
            lines.append(f'load "{self._osdi_file_path(osdi_file)}"')
        if osdi_files:
            lines.append('')

        # Model declarations
        model_lines = []
        for model in self._circuit.models:
            model_lines.append(self._translate_model(model))
        # Add default models for R/C/L without explicit models
        default_models_needed = set()
        for element in self._circuit.elements:
            if not element.enabled:
                continue
            prefix = element.PREFIX
            if prefix in DEFAULT_MODELS and not self._element_has_model(element):
                default_models_needed.add(prefix)
        for prefix in sorted(default_models_needed):
            _, module = DEFAULT_MODELS[prefix]
            model_lines.append(f"model {module} {module}")
        if model_lines:
            for line in model_lines:
                lines.append(line)
            lines.append('')

        # Subcircuit definitions
        for subcircuit in self._circuit.subcircuits:
            lines.append(self._translate_subcircuit_def(subcircuit))
            lines.append('')

        # Element instances
        for element in self._circuit.elements:
            if element.enabled:
                lines.append(self._translate_element(element))
        lines.append('')

        # Control block
        lines.append('control')

        # Options
        lines.append('  ' + self._translate_options())

        # Save directives
        lines.append('  save default')

        # Analysis / sweep directives
        for analysis_parameters in self._analyses.values():
            for analysis_line in self._translate_analysis(analysis_parameters):
                lines.append('  ' + analysis_line)

        lines.append('endc')

        return '\n'.join(lines) + '\n'
