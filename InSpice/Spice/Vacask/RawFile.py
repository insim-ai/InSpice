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

"""This module provides tools to read the output of VACASK simulator."""

####################################################################################################

import logging
import os

from InSpice.Unit import u_V, u_A, u_s, u_Hz
from ..RawFile import VariableAbc, RawFileAbc

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class VacaskVariable(VariableAbc):

    ##############################################

    def is_voltage_node(self):
        return (not self.is_branch_current()
                and not self._is_device_parameter()
                and self.name not in ('time', 'frequency'))

    ##############################################

    def is_branch_current(self):
        return ':flow(br)' in self.name or (self.name.startswith('i(') and self.name.endswith(')'))

    ##############################################

    def _is_device_parameter(self):
        return '.' in self.name and ':' not in self.name

    ##############################################

    @property
    def simplified_name(self):
        name = self.name
        if self.is_branch_current():
            # "vinput:flow(br)" -> "vinput"
            # After fix_case: "i(Vinput)" -> "Vinput"
            if name.startswith('i(') and name.endswith(')'):
                return name[2:-1]
            return name.split(':')[0]
        # After fix_case: "v(out)" -> "out"
        if name.startswith('v(') and name.endswith(')'):
            return name[2:-1]
        return name

####################################################################################################

class VacaskRawFile(RawFileAbc):

    _logger = _module_logger.getChild('VacaskRawFile')

    _variable_cls = VacaskVariable

    ##############################################

    def __init__(self, output):
        raw_data = self._read_header(output)
        self._read_variable_data(raw_data)
        self._simulation = None

    ##############################################

    def _read_header(self, output):
        binary_line = b'Binary:\n'
        binary_location = output.find(binary_line)
        if binary_location < 0:
            raise NameError('Cannot locate binary data')
        raw_data_start = binary_location + len(binary_line)
        self._logger.debug(os.linesep + output[:raw_data_start].decode('utf-8'))
        header_lines = output[:binary_location].splitlines()
        raw_data = output[raw_data_start:]
        header_line_iterator = iter(header_lines)

        self.title = self._read_header_field_line(header_line_iterator, 'Title')
        self.date = self._read_header_field_line(header_line_iterator, 'Date')
        self.plot_name = self._read_header_field_line(header_line_iterator, 'Plotname')
        self.flags = self._read_header_field_line(header_line_iterator, 'Flags')
        self.number_of_variables = int(self._read_header_field_line(header_line_iterator, 'No. Variables'))
        self.number_of_points = int(self._read_header_field_line(header_line_iterator, 'No. Points'))
        self._read_header_field_line(header_line_iterator, 'Variables')
        self._read_header_variables(header_line_iterator)

        return raw_data

    ##############################################

    def _read_header_variables(self, header_line_iterator):
        """Override to handle VACASK's 'notype' unit by inferring from variable name."""
        self.variables = {}
        for i in range(self.number_of_variables):
            line = (next(header_line_iterator)).decode('utf-8')
            self._logger.debug(line)
            items = [x.strip() for x in line.split('\t') if x]
            index, name = items[0], items[1]
            raw_unit = items[2] if len(items) > 2 else 'notype'
            unit = self._name_to_unit.get(raw_unit)
            if unit is None:
                unit = self._infer_unit(name)
            self.variables[name] = self._variable_cls(index, name, unit)

    ##############################################

    @staticmethod
    def _infer_unit(name):
        if name == 'time':
            return u_s
        elif name == 'frequency':
            return u_Hz
        elif ':flow(br)' in name:
            return u_A
        else:
            return u_V

    ##############################################

    def fix_case(self):
        circuit = self.circuit
        element_translation = {element.lower(): element for element in circuit.element_names}
        node_translation = {node.lower(): node for node in circuit.node_names}
        for variable in self.variables.values():
            variable.fix_case(element_translation, node_translation)

    ##############################################

    def to_analysis(self):
        self.fix_case()

        plot = self.plot_name
        if plot == 'Operating Point':
            # VACASK DC sweep produces "Operating Point" with multiple points
            if self.number_of_points > 1:
                return self._to_dc_analysis()
            return self._to_operating_point_analysis()
        elif plot == 'DC transfer characteristic':
            return self._to_dc_analysis()
        elif plot in ('AC Analysis', 'AC Small Signal Analysis'):
            return self._to_ac_analysis()
        elif plot == 'Transient Analysis':
            return self._to_transient_analysis()
        else:
            raise NotImplementedError("Unsupported plot name {}".format(plot))

    ##############################################

    def _to_dc_analysis(self):
        # Identify sweep variable by name from DC analysis parameters
        sweep_name = None
        from ..AnalysisParameters import DCAnalysisParameters
        for analysis in self._simulation._analyses.values():
            if isinstance(analysis, DCAnalysisParameters):
                sweep_name = str(analysis.parameters[0]).lower()
                break

        if sweep_name and sweep_name in self.variables:
            sweep_var = self.variables[sweep_name]
        else:
            # Fallback: first variable
            sweep_var = next(iter(self.variables.values()))

        return super()._to_dc_analysis(sweep_var)
