###################################################################################################
#
# InSpice - A Spice Package for Python
# Copyright (C) 2021 Fabrice Salvaire
# Copyright (C) 2025 Innovoltive
# Modified by Innovoltive on April 18, 2025
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

"""This modules provides classes to handle analysis parameters.

"""

####################################################################################################

__all__ = [
    'ACAnalysisParameters',
    'AcSensitivityAnalysisParameters',
    'DCAnalysisParameters',
    'DcSensitivityAnalysisParameters',
    'DistortionAnalysisParameters',
    'MeasureParameters',
    'NoiseAnalysisParameters',
    'OperatingPointAnalysisParameters',
    'PoleZeroAnalysisParameters',
    'TransferFunctionAnalysisParameters',
    'TransientAnalysisParameters',
]

####################################################################################################

import logging

####################################################################################################

from ..Unit import as_s, as_Hz
from .StringTools import join_list

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class AnalysisParameters:

    """Base class for analysis parameters"""

    _ANALYSIS_NAME = None

    ##############################################

    @property
    def analysis_name(self):
        return self._ANALYSIS_NAME

    ##############################################

    def to_list(self):
        return ()

    ##############################################

    def to_spice(self):
        return '.{0.analysis_name} {1}'.format(self, join_list(self.to_list()))

    def __str__(self):
        return self.to_spice()

    def to_spectre(self, simulation=None):
        """Return Spectre analysis lines. Override in subclasses."""
        return []

####################################################################################################

class OperatingPointAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for operating point analysis."""

    _ANALYSIS_NAME = 'op'

    def to_spectre(self, simulation=None):
        return ['analysis op1 op']

####################################################################################################

class DcSensitivityAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for DC sensitivity analysis."""

    _ANALYSIS_NAME = 'sens'

    ##############################################

    def __init__(self, output_variable):
        self._output_variable = output_variable

    ##############################################

    @property
    def output_variable(self):
        return self._output_variable

    ##############################################

    def to_list(self):
        return (self._output_variable,)

####################################################################################################

class AcSensitivityAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for AC sensitivity analysis."""

    _ANALYSIS_NAME = 'sens'

    ##############################################

    def __init__(self, output_variable, variation, number_of_points, start_frequency, stop_frequency):

        if variation not in ('dec', 'oct', 'lin'):
            raise ValueError("Incorrect variation type")

        self._output_variable = output_variable
        self._variation = variation
        self._number_of_points = number_of_points
        self._start_frequency = as_Hz(start_frequency)
        self._stop_frequency = as_Hz(stop_frequency)

    ##############################################

    @property
    def output_variable(self):
        return self._output_variable

    @property
    def variation(self):
        return self._variation

    @property
    def number_of_points(self):
        return self._number_of_points

    @property
    def start_frequency(self):
        return self._start_frequency

    @property
    def stop_frequency(self):
        return self._stop_frequency

    ##############################################

    def to_list(self):
        return (
            self._output_variable,
            self._variation,
            self._number_of_points,
            self._start_frequency,
            self._stop_frequency
        )

####################################################################################################

class DCAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for DC analysis."""

    _ANALYSIS_NAME = 'dc'

    ##############################################

    def __init__(self, **kwargs):

        self._parameters = []
        for variable, value_slice in kwargs.items():
            variable_lower = variable.lower()
            if variable_lower[0] in ('v', 'i', 'r') or variable_lower == 'temp':
                self._parameters += [variable, value_slice.start, value_slice.stop, value_slice.step]
            else:
                raise NameError('Sweep variable must be a voltage/current source, '
                                'a resistor or the circuit temperature')

    ##############################################

    @property
    def parameters(self):
        return self._parameters

    ##############################################

    def to_list(self):
        return self._parameters

    ##############################################

    def to_spectre(self, simulation=None):
        from .Spectre import format_spectre_value
        lines = []
        params = self._parameters
        for i in range(0, len(params), 4):
            src = str(params[i]).lower()
            start = format_spectre_value(params[i + 1])
            stop = format_spectre_value(params[i + 2])
            step = format_spectre_value(params[i + 3])
            lines.append(
                f'sweep {src} instance="{src}" parameter="dc" '
                f'from={start} to={stop} step={step}'
            )
        op_line = 'analysis op1 op'
        if simulation is not None and simulation._node_set:
            ns_parts = []
            for key, value in simulation._node_set.items():
                node = key
                if node.startswith('V(') and node.endswith(')'):
                    node = node[2:-1]
                ns_parts.append(f'"{node}"; {format_spectre_value(value)}')
            op_line = f'analysis op1 op nodeset=[{"; ".join(ns_parts)}]'
        lines.append(op_line)
        return lines

####################################################################################################

class ACAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for AC analysis."""

    _ANALYSIS_NAME = 'ac'

    ##############################################

    def __init__(self, variation, number_of_points, start_frequency, stop_frequency):

        # Fixme: use mixin

        if variation not in ('dec', 'oct', 'lin'):
            raise ValueError("Incorrect variation type")

        self._variation = variation
        self._number_of_points = number_of_points
        self._start_frequency = as_Hz(start_frequency)
        self._stop_frequency = as_Hz(stop_frequency)

    ##############################################

    @property
    def variation(self):
        return self._variation

    @property
    def number_of_points(self):
        return self._number_of_points

    @property
    def start_frequency(self):
        return self._start_frequency

    @property
    def stop_frequency(self):
        return self._stop_frequency

    ##############################################

    def to_list(self):
        return (
            self._variation,
            self._number_of_points,
            self._start_frequency,
            self._stop_frequency
        )

    ##############################################

    def to_spectre(self, simulation=None):
        from .Spectre import format_spectre_value
        parts = ['analysis ac1 ac']
        parts.append(f"from={format_spectre_value(self._start_frequency)}")
        parts.append(f"to={format_spectre_value(self._stop_frequency)}")
        parts.append(f'mode="{self._variation}"')
        parts.append(f"points={self._number_of_points}")
        return [' '.join(parts)]

####################################################################################################

class TransientAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for transient analysis."""

    _ANALYSIS_NAME = 'tran'

    ##############################################

    def __init__(self, step_time, end_time, start_time=0, max_time=None, use_initial_condition=False):

        self._step_time = as_s(step_time)
        self._end_time = as_s(end_time)
        self._start_time = as_s(start_time)
        self._max_time = as_s(max_time, none=True)
        self._use_initial_condition = use_initial_condition

    ##############################################

    @property
    def step_time(self):
        return self._step_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def start_time(self):
        return self._start_time

    @property
    def max_time(self):
        return self._max_time

    @property
    def use_initial_condition(self):
        return self._use_initial_condition

    ##############################################

    def to_list(self):
        return (
            self._step_time,
            self._end_time,
            self._start_time,
            self._max_time,
            'uic' if self._use_initial_condition else None,
        )

    ##############################################

    def to_spectre(self, simulation=None):
        from .Spectre import format_spectre_value
        parts = ['analysis tran1 tran']
        parts.append(f"step={format_spectre_value(self._step_time)}")
        parts.append(f"stop={format_spectre_value(self._end_time)}")
        if self._max_time is not None:
            parts.append(f"maxstep={format_spectre_value(self._max_time)}")
        if self._use_initial_condition:
            parts.append('icmode="uic"')
        if simulation is not None and simulation._initial_condition:
            ic_parts = []
            for key, value in simulation._initial_condition.items():
                node = key
                if node.startswith('V(') and node.endswith(')'):
                    node = node[2:-1]
                ic_parts.append(f'"{node}"; {format_spectre_value(value)}')
            parts.append(f"ic=[{'; '.join(ic_parts)}]")
        return [' '.join(parts)]

####################################################################################################

class MeasureParameters(AnalysisParameters):

    """This class defines measurements on analysis.

    """

    _ANALYSIS_NAME = 'meas'

    ##############################################

    def __init__(self, analysis_type, name, *args):

        _analysis_type = str(analysis_type).upper()
        if _analysis_type not in ('AC', 'DC', 'OP', 'TRAN', 'TF', 'NOISE'):
            raise ValueError('Incorrect analysis type {}'.format(analysis_type))

        self._parameters = [_analysis_type, name, *args]

    ##############################################

    @property
    def parameters(self):
        return self._parameters

    ##############################################

    def to_list(self):
        return self._parameters

####################################################################################################

class PoleZeroAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for pole-zero analysis."""

    _ANALYSIS_NAME = 'pz'

    ##############################################

    def __init__(self, node1, node2, node3, node4, tf_type, pz_type):

        self._nodes = (node1, node2, node3, node4)
        self._tf_type = tf_type   # transfert_function
        self._pz_type = pz_type   # pole_zero

    ##############################################

    @property
    def node1(self):
        return self._nodes[0]

    @property
    def node2(self):
        return self._nodes[1]

    def node3(self):
        return self._nodes[2]

    @property
    def node4(self):
        return self._nodes[3]

    @property
    def tf_type(self):
        return self._tf_type

    @property
    def pz_type(self):
        return self._pz_type

    ##############################################

    def to_list(self):
        return list(self._nodes) + [self._tf_type, self._pz_type]

####################################################################################################

class NoiseAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for noise analysis."""

    _ANALYSIS_NAME = 'noise'

    ##############################################

    def __init__(self, output, src, variation, points, start_frequency, stop_frequency, points_per_summary):

        self._output = output
        self._src = src
        self._variation = variation
        self._points = points
        self._start_frequency = start_frequency
        self._stop_frequency = stop_frequency
        self._points_per_summary = points_per_summary

    ##############################################

    @property
    def output(self):
        return self._output

    @property
    def src(self):
        return self._src

    @property
    def variation(self):
        return self._variation

    @property
    def points(self):
        return self._points

    # Fixme: mixin
    @property
    def start_frequency(self):
        return self._start_frequency

    @property
    def stop_frequency(self):
        return self._stop_frequency

    @property
    def points_per_summary(self):
        return self._points_per_summary

    ##############################################

    def to_list(self):

        parameters = [
            self._output,
            self._src,
            self._variation,
            self._points,
            self._start_frequency,
            self._stop_frequency,
        ]

        if self._points_per_summary:
            parameters.append(self._points_per_summary)

        return parameters

    ##############################################

    def to_spectre(self, simulation=None):
        from .Spectre import format_spectre_value
        parts = ['analysis noise1 noise']
        output = str(self._output)
        parts.append(f'out="{output}"')
        parts.append(f'in="{str(self._src).lower()}"')
        parts.append(f"from={format_spectre_value(self._start_frequency)}")
        parts.append(f"to={format_spectre_value(self._stop_frequency)}")
        parts.append(f'mode="{self._variation}"')
        parts.append(f"points={self._points}")
        return [' '.join(parts)]

####################################################################################################

class DistortionAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for distortion analysis."""

    _ANALYSIS_NAME = 'disto'

    ##############################################

    def __init__(self, variation, points, start_frequency, stop_frequency, f2overf1):

        self._variation = variation
        self._points = points
        self._start_frequency = start_frequency
        self._stop_frequency = stop_frequency
        self._f2overf1 = f2overf1

    ##############################################

    @property
    def variation(self):
        return self._variation

    @property
    def points(self):
        return self._points

    @property
    def start_frequency(self):
        return self._start_frequency

    @property
    def stop_frequency(self):
        return self._stop_frequency

    @property
    def f2overf1(self):
        return self._f2overf1

    ##############################################

    def to_list(self):

        parameters = [
            self._variation,
            self._points,
            self._start_frequency,
            self._stop_frequency,
        ]

        if self._f2overf1:
            parameters.append(self._f2overf1)

        return parameters

####################################################################################################

class TransferFunctionAnalysisParameters(AnalysisParameters):

    """This class defines analysis parameters for transfer function (.tf) analysis."""

    _ANALYSIS_NAME = 'tf'

    ##############################################

    def __init__(self, outvar, insrc):
        self._outvar = outvar
        self._insrc = insrc

    ##############################################

    @property
    def outvar(self):
        return self._outvar

    @property
    def insrc(self):
        return self._insrc

    ##############################################

    def to_list(self):
        return (self._outvar, self._insrc)
