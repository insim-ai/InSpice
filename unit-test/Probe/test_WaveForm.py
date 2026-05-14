####################################################################################################
#
# InSpice - A Spice Package for Python
# Copyright (C) 2017 Fabrice Salvaire
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

import math
import unittest

import numpy as np
from numpy import testing as np_test

####################################################################################################

# Initialise logging
import InSpice.Logging.Logging as Logging
logger = Logging.setup_logging()

####################################################################################################

from InSpice.Probe.WaveForm import *
from InSpice.Unit import *

####################################################################################################

def print_rule():
    logger.info('\n' + '-'*100)

####################################################################################################

class TestUnits(unittest.TestCase):

    ##############################################

    @staticmethod
    def _test_unit_values(values, true_array):
        np_test.assert_almost_equal(values.as_ndarray(True), true_array)

    ##############################################

    # @unittest.skip('')
    def test(self):

        np_array1 = np.arange(10)
        array1 = u_mV(np_array1)
        np_raw_array1 = np_array1 / 1000

        np_array2 = np.arange(10, 20)
        array2 = u_mV(np_array2)
        np_raw_array2 = np_array2 / 1000

        print_rule()
        name = 'waveform1'
        title = 'A title'
        waveform1 = WaveForm(
            name, array1.prefixed_unit, array1.shape,
            title=title,
            abscissa=np_raw_array2,
        )
        waveform1[...] = array1
        logger.info(repr(waveform1))
        self._test_unit_values(waveform1, np_raw_array1)
        self.assertEqual(waveform1.prefixed_unit, array1.prefixed_unit)
        self.assertEqual(waveform1.name, name)
        self.assertEqual(waveform1.title, title)
        np_test.assert_array_equal(waveform1.abscissa, np_raw_array2)

        print_rule()
        waveform1 = WaveForm.from_unit_values(name, array1)
        logger.info(repr(waveform1))
        self._test_unit_values(waveform1, np_raw_array1)
        self.assertEqual(waveform1.prefixed_unit, array1.prefixed_unit)
        self.assertEqual(waveform1.name, name)

        print_rule()
        name = 'waveform2'
        waveform2 = WaveForm.from_unit_values(name, array2)
        logger.info(repr(waveform2))
        self._test_unit_values(waveform2, np_raw_array2)
        self.assertEqual(waveform2.prefixed_unit, array2.prefixed_unit)
        self.assertEqual(waveform2.name, name)

        print_rule()
        waveform3 = waveform2 - waveform1
        logger.info(repr(waveform3))
        self._test_unit_values(waveform3, np_raw_array2 - np_raw_array1)
        self.assertEqual(waveform3.prefixed_unit, array1.prefixed_unit)
        self.assertEqual(waveform3.name, '')

        print_rule()
        waveform4 = waveform3.convert(U_uV)
        logger.info('{} {}'.format(waveform4, type(waveform4)))

        print_rule()
        # Fixme:
        #     waveform5 = waveform1 >= 5
        #   File "InSpice/Probe/WaveForm.py", line 131, in __array_ufunc__
        #     result = super().__array_ufunc__(ufunc, method, *inputs, **kwargs)
        #   File "InSpice/Unit/Unit.py", line 1635, in __array_ufunc__
        #     raise ValueError
        ndarray5 = waveform1 >= 5@u_V
        np_test.assert_array_equal(ndarray5, np_raw_array1 >= 5)

        print_rule()
        waveform4 = waveform2 * waveform1
        logger.info(repr(waveform4))
        self.assertEqual(waveform4.name, '')
        self._test_unit_values(waveform4, np_raw_array2 * np_raw_array1)
        # Fixme: TypeError: unsupported operand type(s) for *: 'PrefixedUnit' and 'PrefixedUnit'
        # self.assertEqual(waveform4.prefixed_unit, array1.prefixed_unit * array2.prefixed_unit)
        mV2 = u_mV(1)*u_mV(1)
        self.assertEqual(waveform4.prefixed_unit.unit, mV2.unit)
        self.assertEqual(waveform4.prefixed_unit.power, mV2.power)

        print_rule()
        _ = waveform1 + waveform2
        waveform_mean = np.mean(_)
        logger.info(repr(waveform_mean))
        self._test_unit_values(waveform_mean, np.mean(np_raw_array1 + np_raw_array2))
        _ = u_mV(1)
        self.assertEqual(waveform_mean.unit, _.unit)
        self.assertEqual(waveform_mean.power, _.power)

####################################################################################################

class TestNoiseAnalysis(unittest.TestCase):

    """Regression test for the :class:`NoiseAnalysis` frequency abscissa."""

    def test_frequency_default_is_none(self):
        # noise2 (integrated totals) has no frequency axis.
        analysis = NoiseAnalysis(simulation=None, nodes=(), branches=(), internal_parameters=())
        self.assertIsNone(analysis.frequency)

    def test_frequency_passthrough(self):
        # noise1 (spectral) carries a frequency abscissa.
        freq = np.logspace(1, 5, 41)
        analysis = NoiseAnalysis(
            simulation=None, nodes=(), branches=(), internal_parameters=(),
            frequency=freq,
        )
        np_test.assert_array_equal(analysis.frequency, freq)

####################################################################################################

if __name__ == '__main__':

    unittest.main()
