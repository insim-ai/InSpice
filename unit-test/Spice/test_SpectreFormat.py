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

"""Unit tests for the distributed to_spectre() methods across InSpice classes."""

import unittest

from InSpice.Spice.Netlist import Circuit, SubCircuit
from InSpice.Spice.Spectre import SpectreContext
from InSpice.Unit import *

####################################################################################################

class TestDeviceModelSpectre(unittest.TestCase):

    def test_diode_model(self):
        circuit = Circuit('Test')
        model = circuit.model('1N4148', 'D', Is=2.52e-9, N=1.752)
        ctx = SpectreContext()
        result = model.to_spectre(ctx)
        self.assertIn('model mod_1n4148 sp_diode', result)
        self.assertIn('is=2.52e-09', result)
        self.assertIn('n=1.752', result)
        self.assertIn('spice/diode.osdi', ctx.osdi_files)

    def test_nmos_model(self):
        circuit = Circuit('Test')
        model = circuit.model('nch', 'NMOS', level=1, Kp=110e-6, Vto=0.7)
        ctx = SpectreContext()
        result = model.to_spectre(ctx)
        self.assertIn('model nch sp_mos1', result)
        self.assertIn('type=1', result)
        self.assertIn('kp=0.00011', result)
        self.assertIn('vto=0.7', result)
        # level should be removed for NMOS
        self.assertNotIn('level=', result)
        self.assertIn('spice/mos1.osdi', ctx.osdi_files)

    def test_unsupported_model(self):
        circuit = Circuit('Test')
        model = circuit.model('mymodel', 'UNKNOWN_TYPE')
        result = model.to_spectre()
        self.assertIn('// Unsupported', result)

####################################################################################################

class TestElementSpectre(unittest.TestCase):

    def test_resistor(self):
        circuit = Circuit('Test')
        circuit.R(1, 'a', 'b', kilo(1))
        element = circuit['R1']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertEqual(result, 'r1 (a b) sp_resistor r=1000')
        self.assertIn('R', ctx.default_models)

    def test_capacitor(self):
        circuit = Circuit('Test')
        circuit.C(1, 'a', 'b', micro(1))
        element = circuit['C1']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertEqual(result, 'c1 (a b) sp_capacitor c=1e-06')
        self.assertIn('C', ctx.default_models)

    def test_inductor(self):
        circuit = Circuit('Test')
        circuit.L(1, 'a', 'b', milli(10))
        element = circuit['L1']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertEqual(result, 'l1 (a b) sp_inductor l=0.01')
        self.assertIn('L', ctx.default_models)

    def test_voltage_source_dc(self):
        circuit = Circuit('Test')
        circuit.V('in', 'a', circuit.gnd, 5)
        element = circuit['Vin']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertEqual(result, 'vin (a 0) vsource dc=5')
        self.assertIn('vsource', ctx.builtin_models)

    def test_current_source_dc(self):
        circuit = Circuit('Test')
        circuit.I('bias', 'a', circuit.gnd, milli(1))
        element = circuit['Ibias']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertEqual(result, 'ibias (a 0) isource dc=0.001')
        self.assertIn('isource', ctx.builtin_models)

    def test_vcvs(self):
        circuit = Circuit('Test')
        circuit.VCVS('amp', 'out', circuit.gnd, 'inp', circuit.gnd, voltage_gain=10)
        element = circuit['Eamp']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vcvs gain=10', result)
        self.assertIn('vcvs', ctx.builtin_models)

    def test_vccs(self):
        circuit = Circuit('Test')
        circuit.VCCS('gm', 'out', circuit.gnd, 'inp', circuit.gnd, transconductance=0.001)
        element = circuit['Ggm']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vccs gain=0.001', result)
        self.assertIn('vccs', ctx.builtin_models)

    def test_cccs(self):
        circuit = Circuit('Test')
        circuit.V('sense', 'a', 'b', 0)
        circuit.CCCS('mirror', 'c', circuit.gnd, source='Vsense', current_gain=2)
        element = circuit['Fmirror']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('cccs', result)
        self.assertIn('ctlinst="vsense"', result)
        self.assertIn('gain=2', result)

    def test_ccvs(self):
        circuit = Circuit('Test')
        circuit.V('sense', 'a', 'b', 0)
        circuit.CCVS('trans', 'c', circuit.gnd, source='Vsense', transresistance=100)
        element = circuit['Htrans']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('ccvs', result)
        self.assertIn('ctlinst="vsense"', result)
        self.assertIn('gain=100', result)

    def test_diode(self):
        circuit = Circuit('Test')
        circuit.model('1N4148', 'D', Is=2.52e-9)
        circuit.D(1, 'a', circuit.gnd, model='1N4148')
        element = circuit['D1']
        result = element.to_spectre()
        self.assertEqual(result, 'd1 (a 0) mod_1n4148')

    def test_mosfet(self):
        circuit = Circuit('Test')
        circuit.model('nch', 'NMOS', level=1)
        circuit.M(1, 'drain', 'gate', circuit.gnd, circuit.gnd, model='nch')
        element = circuit['M1']
        result = element.to_spectre()
        self.assertEqual(result, 'm1 (drain gate 0 0) nch')

    def test_subcircuit_element(self):
        circuit = Circuit('Test')
        sub = SubCircuit('amp', 'inp', 'out', 'vdd', 'gnd')
        sub.R(1, 'inp', 'out', kilo(1))
        circuit.subcircuit(sub)
        circuit.X('u1', 'amp', 'sig_in', 'sig_out', 'vcc', circuit.gnd)
        element = circuit['Xu1']
        result = element.to_spectre()
        self.assertEqual(result, 'xu1 (sig_in sig_out vcc 0) amp')

####################################################################################################

class TestHighLevelElementSpectre(unittest.TestCase):

    def test_sinusoidal_voltage_source(self):
        circuit = Circuit('Test')
        circuit.SinusoidalVoltageSource('sig', 'inp', circuit.gnd,
                                        dc_offset=0, ac_magnitude=1,
                                        offset=0, amplitude=5, frequency=1@u_kHz)
        element = circuit['Vsig']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vsource', result)
        self.assertIn('type="sine"', result)
        self.assertIn('ampl=5', result)
        self.assertIn('freq=1000', result)
        self.assertIn('vsource', ctx.builtin_models)

    def test_pulse_voltage_source(self):
        circuit = Circuit('Test')
        circuit.PulseVoltageSource('clk', 'clk', circuit.gnd,
                                    initial_value=0, pulsed_value=5,
                                    pulse_width=5@u_ms, period=10@u_ms,
                                    rise_time=1@u_us, fall_time=1@u_us)
        element = circuit['Vclk']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vsource', result)
        self.assertIn('type="pulse"', result)
        self.assertIn('val0=0', result)
        self.assertIn('val1=5', result)
        self.assertIn('rise=1e-06', result)

    def test_exponential_voltage_source(self):
        circuit = Circuit('Test')
        circuit.ExponentialVoltageSource('exp', 'out', circuit.gnd,
                                         initial_value=0, pulsed_value=5,
                                         rise_delay_time=1e-6, rise_time_constant=1e-6,
                                         fall_delay_time=2e-6, fall_time_constant=1e-6)
        element = circuit['Vexp']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vsource', result)
        self.assertIn('type="exp"', result)
        self.assertIn('val0=0', result)
        self.assertIn('val1=5', result)

    def test_pwl_voltage_source(self):
        circuit = Circuit('Test')
        circuit.PieceWiseLinearVoltageSource('pwl', 'out', circuit.gnd,
                                             values=[(0, 0), (1e-3, 5)])
        element = circuit['Vpwl']
        ctx = SpectreContext()
        result = element.to_spectre(ctx)
        self.assertIn('vsource', result)
        self.assertIn('type="pwl"', result)
        self.assertIn('wave=[', result)

####################################################################################################

class TestNetlistSpectre(unittest.TestCase):

    def test_netlist_body(self):
        circuit = Circuit('Test')
        circuit.V('in', 'inp', circuit.gnd, 5)
        circuit.R(1, 'inp', 'out', kilo(1))
        ctx = SpectreContext()
        body = circuit.to_spectre(ctx)
        self.assertIn('vin (inp 0) vsource dc=5', body)
        self.assertIn('r1 (inp out) sp_resistor r=1000', body)
        self.assertIn('vsource', ctx.builtin_models)
        self.assertIn('R', ctx.default_models)

    def test_subcircuit_spectre(self):
        sub = SubCircuit('inverter', 'inp', 'out', 'vdd', 'gnd')
        sub.model('nch', 'NMOS', level=1, Kp=110e-6)
        sub.M(1, 'out', 'inp', 'gnd', 'gnd', model='nch')
        ctx = SpectreContext()
        result = sub.to_spectre(ctx)
        self.assertIn('subckt inverter(inp out vdd gnd)', result)
        self.assertIn('ends', result)
        self.assertIn('model nch sp_mos1', result)
        self.assertIn('m1 (out inp gnd gnd) nch', result)

####################################################################################################

class TestAnalysisSpectre(unittest.TestCase):

    def test_operating_point(self):
        from InSpice.Spice.AnalysisParameters import OperatingPointAnalysisParameters
        ap = OperatingPointAnalysisParameters()
        lines = ap.to_spectre()
        self.assertEqual(lines, ['analysis op1 op'])

    def test_transient(self):
        from InSpice.Spice.AnalysisParameters import TransientAnalysisParameters
        ap = TransientAnalysisParameters(step_time=1e-6, end_time=1e-3)
        lines = ap.to_spectre()
        self.assertEqual(len(lines), 1)
        self.assertIn('analysis tran1 tran', lines[0])
        self.assertIn('step=1e-06', lines[0])
        self.assertIn('stop=0.001', lines[0])

    def test_ac(self):
        from InSpice.Spice.AnalysisParameters import ACAnalysisParameters
        ap = ACAnalysisParameters('dec', 10, 100, 1e6)
        lines = ap.to_spectre()
        self.assertEqual(len(lines), 1)
        self.assertIn('analysis ac1 ac', lines[0])
        self.assertIn('from=100', lines[0])
        self.assertIn('to=1e+06', lines[0])
        self.assertIn('mode="dec"', lines[0])
        self.assertIn('points=10', lines[0])

    def test_dc(self):
        from InSpice.Spice.AnalysisParameters import DCAnalysisParameters
        ap = DCAnalysisParameters(Vin=slice(0, 5, 0.1))
        lines = ap.to_spectre()
        self.assertEqual(len(lines), 2)
        self.assertIn('sweep vin', lines[0])
        self.assertIn('analysis op1 op', lines[1])

    def test_noise(self):
        from InSpice.Spice.AnalysisParameters import NoiseAnalysisParameters
        ap = NoiseAnalysisParameters('V(out, 0)', 'Vinput', 'dec', 10, 1, 1e6, None)
        lines = ap.to_spectre()
        self.assertEqual(len(lines), 1)
        self.assertIn('analysis noise1 noise', lines[0])
        self.assertIn('in="vinput"', lines[0])
        self.assertIn('out="out, 0"', lines[0])

####################################################################################################

class TestSpectreContext(unittest.TestCase):

    def test_context_accumulation(self):
        ctx = SpectreContext(osdi_path='/path/to/osdi')
        ctx.register_osdi('spice/resistor.osdi')
        ctx.register_builtin('vsource')
        ctx.register_default_model('R')

        self.assertIn('spice/resistor.osdi', ctx.osdi_files)
        self.assertIn('vsource', ctx.builtin_models)
        self.assertIn('R', ctx.default_models)
        self.assertEqual(ctx.osdi_file_path('spice/resistor.osdi'),
                         '/path/to/osdi/spice/resistor.osdi')

####################################################################################################

if __name__ == '__main__':
    unittest.main()
