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
        self.assertIn('model 1n4148 sp_diode', netlist)
        self.assertIn('d1 (out 0) 1n4148', netlist)
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

####################################################################################################

if __name__ == '__main__':
    unittest.main()
