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

####################################################################################################

import logging

####################################################################################################

from ..Simulation import Simulation
from ..StringTools import join_list

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class XyceSimulation(Simulation):

    _logger = _module_logger.getChild('XyceSimulation')

    ##############################################

    def str_options(self):
        return super().str_options(unit=False)

    ##############################################

    def str_simulation(self):
        """Override to generate Xyce-specific .print directives instead of .save"""
        lines = self.str_options()
        if self._initial_condition:
            from ..StringTools import join_dict
            lines += '.ic ' + join_dict(self._initial_condition)
        if self._node_set:
            from ..StringTools import join_dict
            lines += '.nodeset ' + join_dict(self._node_set)

        # Xyce requires .print directives for each analysis type
        # Map ngspice analysis names to Xyce print types
        analysis_type_map = {
            'op': 'dc',      # Operating point uses DC in Xyce
            'dc': 'dc',
            'ac': 'ac',
            'tran': 'tran',
            'sens': 'sens',
            'noise': 'noise',
        }

        # Determine what to print
        if self._saved_nodes:
            # User specified nodes to save
            saved_nodes = self._saved_nodes.copy()
            # Xyce doesn't have 'all' keyword, but we can use it as a flag
            if 'all' in saved_nodes:
                saved_nodes.remove('all')
                # Add v(*) to get all voltages when 'all' is specified
                saved_nodes.add('v(*)')
            output_vars = join_list(saved_nodes)
        else:
            # Default: match ngspice behavior (all node voltages)
            output_vars = 'v(*)'

        # Generate .print directive for each analysis
        for analysis_parameters in self._analyses.values():
            analysis_name = analysis_parameters.analysis_name
            print_type = analysis_type_map.get(analysis_name, analysis_name)
            lines += f'.print {print_type} {output_vars}'

        # Add measure statements
        for measure_parameters in self._measures:
            lines += str(measure_parameters)

        # Add analysis directives
        for analysis_parameters in self._analyses.values():
            lines += str(analysis_parameters)

        lines += '.end'
        return str(lines)
