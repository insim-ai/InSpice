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
####################################################################################################

"""Unit tests for the VACASK simulator interface."""

import unittest
from unittest import mock

from InSpice.Spice.Netlist import Circuit
from InSpice.Spice.Simulator import Simulator
from InSpice.Unit import *

####################################################################################################

class TestVacaskSimulatorFactory(unittest.TestCase):

    def test_factory_creates_vacask_simulator(self):
        simulator = Simulator.factory(simulator='vacask')
        self.assertEqual(simulator.SIMULATOR, 'vacask')

    def test_vacask_in_simulators_list(self):
        self.assertIn('vacask', Simulator.SIMULATORS)

####################################################################################################

class TestVacaskNetlistGeneration(unittest.TestCase):

    def setUp(self):
        self.simulator = Simulator.factory(simulator='vacask')

    def _make_simulation(self, circuit):
        return self.simulator.simulation(circuit)

    ##############################################

    def test_simple_rc_transient(self):
        circuit = Circuit('RC Test')
        circuit.V('input', 'inp', circuit.gnd, 5)
        circuit.R(1, 'inp', 'out', kilo(1))
        circuit.C(1, 'out', circuit.gnd, micro(1))

        simulation = self._make_simulation(circuit)
        simulation.transient(step_time=1@u_us, end_time=10@u_ms, run=False)

        netlist = str(simulation)

        self.assertIn('// RC Test', netlist)
        self.assertIn('ground 0', netlist)
        self.assertIn('load', netlist)
        self.assertIn('vinput (inp 0) vsource dc=5', netlist)
        self.assertIn('r1 (inp out) sp_resistor r=1000', netlist)
        self.assertIn('c1 (out 0) sp_capacitor c=1e-06', netlist)
        self.assertIn('analysis tran1 tran step=1e-06 stop=0.01', netlist)
        self.assertIn('rawfile="binary"', netlist)
        self.assertIn('control', netlist)
        self.assertIn('endc', netlist)

    ##############################################

    def test_operating_point(self):
        circuit = Circuit('OP Test')
        circuit.V('cc', 'vcc', circuit.gnd, 5)
        circuit.R(1, 'vcc', 'out', kilo(1))
        circuit.R(2, 'out', circuit.gnd, kilo(1))

        simulation = self._make_simulation(circuit)
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('analysis op1 op', netlist)

    ##############################################

    def test_ac_analysis(self):
        circuit = Circuit('AC Test')
        circuit.SinusoidalVoltageSource('input', 'inp', circuit.gnd,
                                        dc_offset=0, ac_magnitude=1,
                                        offset=0, amplitude=5, frequency=1@u_kHz)
        circuit.R(1, 'inp', 'out', kilo(1))
        circuit.C(1, 'out', circuit.gnd, nano(100))

        simulation = self._make_simulation(circuit)
        simulation.ac(variation='dec', number_of_points=10,
                     start_frequency=100@u_Hz, stop_frequency=1@u_MHz, run=False)

        netlist = str(simulation)
        self.assertIn('type="sine"', netlist)
        self.assertIn('ampl=5', netlist)
        self.assertIn('freq=1000', netlist)
        self.assertIn('analysis ac1 ac from=100 to=1e+06 mode="dec" points=10', netlist)

    ##############################################

    def test_dc_sweep(self):
        circuit = Circuit('DC Sweep')
        circuit.V('in', 'inp', circuit.gnd, 0)
        circuit.R(1, 'inp', 'out', kilo(10))
        circuit.R(2, 'out', circuit.gnd, kilo(10))

        simulation = self._make_simulation(circuit)
        simulation.dc(Vin=slice(0, 5, 0.1), run=False)

        netlist = str(simulation)
        self.assertIn('sweep vin instance="vin" parameter="dc" from=0 to=5 step=0.1', netlist)
        self.assertIn('analysis op1 op', netlist)

    ##############################################

    def test_diode_model(self):
        circuit = Circuit('Diode Test')
        circuit.model('1N4148', 'D', Is=2.52e-9, N=1.752)
        circuit.V('input', 'inp', circuit.gnd, 5)
        circuit.R(1, 'inp', 'out', kilo(1))
        circuit.D(1, 'out', circuit.gnd, model='1N4148')

        simulation = self._make_simulation(circuit)
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('model mod_1n4148 sp_diode', netlist)
        self.assertIn('d1 (out 0) mod_1n4148', netlist)
        self.assertIn('spice/diode.osdi', netlist)

    ##############################################

    def test_mosfet_model(self):
        circuit = Circuit('MOSFET Test')
        circuit.model('nch', 'NMOS', level=1, Kp=110e-6, Vto=0.7)
        circuit.V('dd', 'vdd', circuit.gnd, 5)
        circuit.V('gs', 'gate', circuit.gnd, 2)
        circuit.R('d', 'vdd', 'drain', kilo(1))
        circuit.M(1, 'drain', 'gate', circuit.gnd, circuit.gnd, model='nch')

        simulation = self._make_simulation(circuit)
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('model nch sp_mos1 type=1', netlist)
        self.assertIn('m1 (drain gate 0 0) nch', netlist)

    ##############################################

    def test_pulse_source(self):
        circuit = Circuit('Pulse Test')
        circuit.PulseVoltageSource('clk', 'clk', circuit.gnd,
                                    initial_value=0, pulsed_value=5,
                                    pulse_width=5@u_ms, period=10@u_ms,
                                    rise_time=1@u_us, fall_time=1@u_us)
        circuit.R(1, 'clk', circuit.gnd, kilo(1))

        simulation = self._make_simulation(circuit)
        simulation.transient(step_time=1@u_us, end_time=50@u_ms, run=False)

        netlist = str(simulation)
        self.assertIn('type="pulse"', netlist)
        self.assertIn('val0=0', netlist)
        self.assertIn('val1=5', netlist)

    ##############################################

    def test_vcvs(self):
        circuit = Circuit('VCVS Test')
        circuit.V('input', 'inp', circuit.gnd, 1)
        circuit.R(1, 'inp', circuit.gnd, kilo(1))
        circuit.VCVS('amp', 'out', circuit.gnd, 'inp', circuit.gnd, voltage_gain=10)
        circuit.R(2, 'out', circuit.gnd, kilo(10))

        simulation = self._make_simulation(circuit)
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('vcvs gain=10', netlist)

    ##############################################

    def test_vccs(self):
        circuit = Circuit('VCCS Test')
        circuit.V('input', 'inp', circuit.gnd, 1)
        circuit.R(1, 'inp', circuit.gnd, kilo(1))
        circuit.VCCS('gm', 'out', circuit.gnd, 'inp', circuit.gnd, transconductance=0.001)
        circuit.R(2, 'out', circuit.gnd, kilo(10))

        simulation = self._make_simulation(circuit)
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('vccs gain=0.001', netlist)

    ##############################################

    def test_noise_analysis(self):
        circuit = Circuit('Noise Test')
        circuit.V('input', 'inp', circuit.gnd, 0)
        circuit.R(1, 'inp', 'out', kilo(1))
        circuit.C(1, 'out', circuit.gnd, nano(10))

        simulation = self._make_simulation(circuit)
        simulation.noise('out', circuit.gnd, 'Vinput', variation='dec',
                        points=10, start_frequency=1@u_Hz,
                        stop_frequency=1@u_MHz, run=False)

        netlist = str(simulation)
        self.assertIn('analysis noise1 noise', netlist)
        self.assertIn('in="vinput"', netlist)

    ##############################################

    def test_options_temperature(self):
        circuit = Circuit('Temp Test')
        circuit.V('cc', 'vcc', circuit.gnd, 5)
        circuit.R(1, 'vcc', circuit.gnd, kilo(1))

        simulation = self._make_simulation(circuit)
        simulation.temperature = 85
        simulation.operating_point(run=False)

        netlist = str(simulation)
        self.assertIn('temp=85', netlist)

    ##############################################

    def test_initial_condition(self):
        circuit = Circuit('IC Test')
        circuit.V('cc', 'vcc', circuit.gnd, 5)
        circuit.R(1, 'vcc', 'out', kilo(1))
        circuit.C(1, 'out', circuit.gnd, micro(1))

        simulation = self._make_simulation(circuit)
        simulation.initial_condition(out=2.5)
        simulation.transient(step_time=1@u_us, end_time=10@u_ms,
                            use_initial_condition=True, run=False)

        netlist = str(simulation)
        self.assertIn('icmode="uic"', netlist)
        self.assertIn('ic=[', netlist)

####################################################################################################

class TestVacaskRawFile(unittest.TestCase):

    def test_variable_classification(self):
        from InSpice.Spice.Vacask.RawFile import VacaskVariable
        from InSpice.Unit import u_V, u_A, u_s

        # Voltage node
        v = VacaskVariable(0, 'out', u_V)
        self.assertTrue(v.is_voltage_node())
        self.assertFalse(v.is_branch_current())

        # Branch current
        i = VacaskVariable(1, 'v1:flow(br)', u_A)
        self.assertTrue(i.is_branch_current())
        self.assertFalse(i.is_voltage_node())
        self.assertEqual(i.simplified_name, 'v1')

        # Time
        t = VacaskVariable(0, 'time', u_s)
        self.assertFalse(t.is_voltage_node())
        self.assertFalse(t.is_branch_current())

    ##############################################

    def test_branch_current_after_fix_case(self):
        """V2: fix_case renames 'v1:flow(br)' to 'i(V1)' — is_branch_current must still match."""
        from InSpice.Spice.Vacask.RawFile import VacaskVariable
        from InSpice.Unit import u_A

        var = VacaskVariable(1, 'v1:flow(br)', u_A)
        self.assertTrue(var.is_branch_current())

        # Simulate what fix_case does: rename to i(V1)
        var.name = 'i(V1)'
        self.assertTrue(var.is_branch_current())
        self.assertFalse(var.is_voltage_node())
        self.assertEqual(var.simplified_name, 'V1')

    ##############################################

    def test_voltage_node_not_misclassified_after_fix_case(self):
        """V2 corollary: a renamed voltage 'v(out)' must still be a voltage, not a branch."""
        from InSpice.Spice.Vacask.RawFile import VacaskVariable
        from InSpice.Unit import u_V

        var = VacaskVariable(0, 'out', u_V)
        var.name = 'v(out)'
        self.assertTrue(var.is_voltage_node())
        self.assertFalse(var.is_branch_current())

    ##############################################

    def test_unsupported_plot_raises(self):
        """V1: noise analysis and unknown plot types raise NotImplementedError."""
        from InSpice.Spice.Vacask.RawFile import VacaskRawFile
        import struct

        # Build a minimal raw file binary blob
        def make_raw(plotname):
            header = (
                f'Title: test\n'
                f'Date: now\n'
                f'Plotname: {plotname}\n'
                f'Flags: real\n'
                f'No. Variables: 1\n'
                f'No. Points: 1\n'
                f'Variables:\n'
                f'\t0\ttime\tnotype\n'
                f'Binary:\n'
            ).encode('utf-8')
            data = struct.pack('d', 0.0)
            return header + data

        raw_file = VacaskRawFile(make_raw('Noise Analysis'))
        with self.assertRaises(NotImplementedError):
            raw_file._simulation = mock.MagicMock()
            raw_file.to_analysis()

        raw_file2 = VacaskRawFile(make_raw('Unknown Analysis'))
        with self.assertRaises(NotImplementedError):
            raw_file2._simulation = mock.MagicMock()
            raw_file2.to_analysis()

####################################################################################################

class TestVacaskServerErrorHandling(unittest.TestCase):

    def test_nonzero_exit_code_raises_runtime_error(self):
        """V4: non-zero exit code must raise RuntimeError, not pass silently."""
        from InSpice.Spice.Vacask.Server import VacaskServer
        server = VacaskServer(vacask_command='false')  # 'false' always exits 1
        with self.assertRaises(RuntimeError) as ctx:
            server('dummy input')
        self.assertIn('exited with code', str(ctx.exception))

    def test_temp_dir_cleaned_on_error(self):
        """V3: temp dir must be cleaned up even when simulation fails."""
        import os
        import glob
        import tempfile
        from InSpice.Spice.Vacask.Server import VacaskServer

        server = VacaskServer(vacask_command='false')
        # Count temp dirs before
        before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'tmp*')))
        try:
            server('dummy input')
        except RuntimeError:
            pass
        after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'tmp*')))
        # No new temp dirs leaked
        leaked = after - before
        for d in leaked:
            if os.path.isdir(d) and os.path.exists(os.path.join(d, 'input.sim')):
                self.fail(f"Leaked temp dir: {d}")

####################################################################################################

class TestSpectreUnsupportedSources(unittest.TestCase):

    def test_sffm_spectre_not_supported(self):
        """S9: SFFM sources must raise NotImplementedError for Spectre output."""
        from InSpice.Spice.HighLevelElement import SingleFrequencyFMMixin, VoltageSourceMixinAbc
        class TestSFFM(VoltageSourceMixinAbc, SingleFrequencyFMMixin):
            pass
        src = TestSFFM(offset=0, amplitude=1, carrier_frequency=1e3,
                       modulation_index=5, signal_frequency=10)
        with self.assertRaises(NotImplementedError):
            src.format_spectre_parameters()

    def test_am_spectre_not_supported(self):
        """S9: AM sources must raise NotImplementedError for Spectre output."""
        from InSpice.Spice.HighLevelElement import AmplitudeModulatedMixin, VoltageSourceMixinAbc
        class TestAM(VoltageSourceMixinAbc, AmplitudeModulatedMixin):
            pass
        src = TestAM(offset=0, amplitude=1, modulating_frequency=100,
                     carrier_frequency=1e3, signal_delay=0)
        with self.assertRaises(NotImplementedError):
            src.format_spectre_parameters()

    def test_random_spectre_not_supported(self):
        """S9: Random sources must raise NotImplementedError for Spectre output."""
        from InSpice.Spice.HighLevelElement import RandomMixin, VoltageSourceMixinAbc
        class TestRandom(VoltageSourceMixinAbc, RandomMixin):
            pass
        src = TestRandom(random_type='uniform', duration=1e-3)
        with self.assertRaises(NotImplementedError):
            src.format_spectre_parameters()

####################################################################################################

class TestNoiseSpectreOutput(unittest.TestCase):

    def test_noise_strips_v_wrapper(self):
        """S3: Noise output must strip V() wrapper for Spectre."""
        from InSpice.Spice.AnalysisParameters import NoiseAnalysisParameters
        ap = NoiseAnalysisParameters('V(out, 0)', 'Vinput', 'dec', 10, 1, 1e6, None)
        lines = ap.to_spectre()
        self.assertIn('out="out, 0"', lines[0])
        self.assertNotIn('V(', lines[0])

    def test_noise_bare_node_unchanged(self):
        """S3: Bare node name without V() must pass through unchanged."""
        from InSpice.Spice.AnalysisParameters import NoiseAnalysisParameters
        ap = NoiseAnalysisParameters('out', 'Vinput', 'dec', 10, 1, 1e6, None)
        lines = ap.to_spectre()
        self.assertIn('out="out"', lines[0])

####################################################################################################

if __name__ == '__main__':
    unittest.main()
