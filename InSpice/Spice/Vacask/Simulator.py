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

"""This module implements the VACASK simulator interface."""

####################################################################################################

import logging

####################################################################################################

from ..Simulator import Simulator
from .Server import VacaskServer
from .Simulation import VacaskSimulation

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class VacaskSimulator(Simulator):

    _logger = _module_logger.getChild('VacaskSimulator')

    SIMULATOR = 'vacask'

    ##############################################

    def __init__(self, **kwargs):
        vacask_command = kwargs.get('vacask_command', None)
        osdi_path = kwargs.get('osdi_path', None)
        self._vacask_server = VacaskServer(vacask_command=vacask_command, osdi_path=osdi_path)

    ##############################################

    @property
    def version(self):
        return ''

    ##############################################

    @property
    def osdi_path(self):
        return self._vacask_server.osdi_path

    ##############################################

    def simulation(self, circuit, **kwargs):
        return VacaskSimulation(self, circuit, **kwargs)

    ##############################################

    # Maps analysis parameter class names to the instance names used in to_spectre()
    _ANALYSIS_RAW_FILES = {
        'OperatingPointAnalysisParameters': 'op1',
        'DCAnalysisParameters': 'op1',
        'ACAnalysisParameters': 'ac1',
        'TransientAnalysisParameters': 'tran1',
        'NoiseAnalysisParameters': 'noise1',
    }

    def run(self, simulation, *args, **kwargs):
        # Determine the expected raw file name from the analysis type
        raw_filename = None
        for analysis in simulation._analyses.values():
            class_name = type(analysis).__name__
            if class_name in self._ANALYSIS_RAW_FILES:
                raw_filename = self._ANALYSIS_RAW_FILES[class_name] + '.raw'
                break

        raw_file = self._vacask_server(str(simulation), raw_filename=raw_filename)
        raw_file.simulation = simulation
        return raw_file.to_analysis()
