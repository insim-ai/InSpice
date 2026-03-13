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
        return ':flow(br)' in self.name

    ##############################################

    def _is_device_parameter(self):
        return '.' in self.name and ':' not in self.name

    ##############################################

    @property
    def simplified_name(self):
        if self.is_branch_current():
            return self.name.split(':')[0]
        return self.name

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

    def fix_case(self):
        circuit = self.circuit
        element_translation = {element.lower(): element for element in circuit.element_names}
        node_translation = {node.lower(): node for node in circuit.node_names}
        for variable in self.variables.values():
            variable.fix_case(element_translation, node_translation)

    ##############################################

    def _to_dc_analysis(self):
        # VACASK DC sweep: first variable is the sweep variable
        first_var = next(iter(self.variables.values()))
        return super()._to_dc_analysis(first_var)
