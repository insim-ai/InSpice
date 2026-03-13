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

    def run(self, simulation, *args, **kwargs):
        raw_file = self._vacask_server(str(simulation))
        raw_file.simulation = simulation
        return raw_file.to_analysis()
