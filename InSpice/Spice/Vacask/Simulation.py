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
(SPICE-style) into VACASK format using distributed to_spectre() methods on each class.
"""

####################################################################################################

import logging

####################################################################################################

from ..Simulation import Simulation
from ..Spectre import SpectreContext, format_spectre_value, DEFAULT_MODELS

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class VacaskSimulation(Simulation):

    _logger = _module_logger.getChild('VacaskSimulation')

    ##############################################

    def __init__(self, simulator, circuit, **kwargs):
        super().__init__(simulator, circuit, **kwargs)
        self._osdi_path = simulator.osdi_path

    ##############################################

    def _translate_options(self):
        """Translate simulation options to VACASK format."""
        parts = []
        for key, value in self._options.items():
            k = key.lower()
            if k == 'savecurrents':
                self._logger.warning('SAVECURRENTS is not supported by VACASK, ignored')
                continue
            if value is not None:
                parts.append(f"{k}={format_spectre_value(value)}")
            else:
                parts.append(k)
        # Always request binary raw file output
        parts.append('rawfile="binary"')
        return 'options ' + ' '.join(parts)

    ##############################################

    def to_spectre(self):
        """Generate the complete VACASK simulation netlist using distributed to_spectre() calls."""
        context = SpectreContext(osdi_path=self._osdi_path)

        # Recursively render circuit body — this populates context with
        # osdi_files, builtin_models, default_models
        circuit_body = self._circuit.to_spectre(context)

        lines = []

        # Title
        lines.append(f"// {self._circuit.title}")
        lines.append('')

        # Ground
        lines.append('ground 0')
        lines.append('')

        # Collect OSDI files from default models too
        for prefix in context.default_models:
            if prefix in DEFAULT_MODELS:
                osdi_file, _ = DEFAULT_MODELS[prefix]
                context.register_osdi(osdi_file)

        # Load directives for OSDI files
        if context.osdi_files:
            for osdi_file in sorted(context.osdi_files):
                lines.append(f'load "{context.osdi_file_path(osdi_file)}"')
            lines.append('')

        # Model declarations (from circuit body, rendered above)
        model_lines = []
        # Explicit models are already in circuit_body, but we need default + builtin declarations
        for prefix in sorted(context.default_models):
            if prefix in DEFAULT_MODELS:
                _, module = DEFAULT_MODELS[prefix]
                model_lines.append(f"model {module} {module}")
        for builtin in sorted(context.builtin_models):
            model_lines.append(f"model {builtin} {builtin}")

        if model_lines:
            for line in model_lines:
                lines.append(line)

        # Circuit body (subcircuits with models inside, explicit models, elements)
        if circuit_body:
            if model_lines:
                lines.append('')
            for line in circuit_body.split('\n'):
                lines.append(line)
        lines.append('')

        # Control block
        lines.append('control')

        # Options
        lines.append('  ' + self._translate_options())

        # Save directives
        if self._saved_nodes:
            saved = ' '.join(sorted(self._saved_nodes))
            lines.append(f'  save {saved}')
        else:
            lines.append('  save default')

        # Analysis / sweep directives
        for analysis_parameters in self._analyses.values():
            for analysis_line in analysis_parameters.to_spectre(simulation=self):
                lines.append('  ' + analysis_line)

        lines.append('endc')

        return '\n'.join(lines) + '\n'

    ##############################################

    def to_spice(self):
        raise NotImplementedError("VACASK uses Spectre format, not SPICE. Use to_spectre().")

    ##############################################

    # Analyses not supported by VACASK

    def dc_sensitivity(self, *args, **kwargs):
        raise NotImplementedError("DC sensitivity analysis is not supported by VACASK")

    def ac_sensitivity(self, *args, **kwargs):
        raise NotImplementedError("AC sensitivity analysis is not supported by VACASK")

    def polezero(self, *args, **kwargs):
        raise NotImplementedError("Pole-zero analysis is not supported by VACASK")

    def transfer_function(self, *args, **kwargs):
        raise NotImplementedError("Transfer function analysis is not supported by VACASK")

    tf = transfer_function

    def distortion(self, *args, **kwargs):
        raise NotImplementedError("Distortion analysis is not supported by VACASK")

    def measure(self, *args, **kwargs):
        raise NotImplementedError("Measure statements are not supported by VACASK")

    ##############################################

    def __str__(self):
        return self.to_spectre()
