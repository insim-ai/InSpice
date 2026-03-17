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

"""This module provides an interface to run VACASK and get back the simulation output."""

####################################################################################################

import glob
import logging
import os
import shutil
import subprocess
import tempfile

from .RawFile import VacaskRawFile

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class VacaskServer:

    VACASK_COMMAND = 'vacask'

    _logger = _module_logger.getChild('VacaskServer')

    ##############################################

    def __init__(self, **kwargs):
        self._vacask_command = kwargs.get('vacask_command') or self._discover_vacask_command()
        self._osdi_path = kwargs.get('osdi_path') or self._discover_osdi_path()

    ##############################################

    @staticmethod
    def _discover_vacask_command():
        try:
            import vacask_bin
            if os.path.isfile(vacask_bin.VACASK_CMD):
                return vacask_bin.VACASK_CMD
        except ImportError:
            pass
        return VacaskServer.VACASK_COMMAND

    ##############################################

    def _discover_osdi_path(self):
        env_path = os.environ.get('VACASK_OSDI_PATH')
        if env_path:
            return env_path

        try:
            import vacask_bin
            if os.path.isdir(vacask_bin.MOD_DIR):
                return vacask_bin.MOD_DIR
        except ImportError:
            pass

        vacask_bin_path = shutil.which(self._vacask_command)
        if vacask_bin_path:
            vacask_bin_path = os.path.realpath(vacask_bin_path)
            bin_dir = os.path.dirname(vacask_bin_path)
            osdi_path = os.path.join(bin_dir, '..', 'lib', 'vacask', 'mod')
            osdi_path = os.path.normpath(osdi_path)
            if os.path.isdir(osdi_path):
                return osdi_path

        return None

    ##############################################

    @property
    def osdi_path(self):
        return self._osdi_path

    ##############################################

    def _parse_stdout(self, stdout, stderr):
        output = stdout.decode('utf-8')
        self._logger.info(os.linesep + output)

        err_output = stderr.decode('utf-8')
        if err_output:
            self._logger.debug(os.linesep + err_output)

        if 'Error' in output or 'error' in err_output:
            raise NameError("Errors found by VACASK:\n" + output + err_output)

    ##############################################

    def __call__(self, simulation_input):
        self._logger.debug('Start the VACASK subprocess')

        tmp_dir = tempfile.mkdtemp()
        input_filename = os.path.join(tmp_dir, 'input.sim')
        with open(input_filename, 'w') as f:
            f.write(str(simulation_input))

        command = (self._vacask_command, input_filename)
        self._logger.info('Run {}'.format(' '.join(command)))
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp_dir,
        )
        stdout, stderr = process.communicate()

        self._parse_stdout(stdout, stderr)

        # VACASK writes {analysis_name}.raw files to cwd
        raw_files = glob.glob(os.path.join(tmp_dir, '*.raw'))
        if not raw_files:
            raise NameError("VACASK did not produce any raw output files")

        with open(raw_files[0], 'rb') as f:
            output = f.read()

        raw_file = VacaskRawFile(output)
        shutil.rmtree(tmp_dir)

        return raw_file
