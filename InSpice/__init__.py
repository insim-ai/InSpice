####################################################################################################
#
# InSpice - A Spice Package for Python
# Copyright (C) 2014 Fabrice Salvaire
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

__all__ = [
    'Circuit',
    'Simulator',
    'SpiceLibrary',
    'plot',
]

####################################################################################################

__version__ = '1.6.4.4'
GIT_TAG = 'main'

def show_version():
    print('InSpice Version {}'.format(__version__))

from InSpice.Probe.Plot import plot
from InSpice.Spice.Library import SpiceLibrary
from InSpice.Spice.Netlist import  Circuit, SubCircuit, SubCircuitFactory
from InSpice.Spice.Simulator import Simulator
