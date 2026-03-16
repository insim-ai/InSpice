"""Integration test for VACASK simulator - run actual simulations."""
import sys
import numpy as np
from InSpice.Spice.Netlist import Circuit
from InSpice.Spice.Simulator import Simulator
from InSpice.Unit import *

import os
VACASK_CMD = os.environ.get('VACASK_CMD', '/tmp/vacask-arm/simulator/vacask')
OSDI_PATH = os.environ.get('VACASK_OSDI_PATH', '/tmp/vacask-arm/lib/vacask/mod')

def make_simulator():
    return Simulator.factory(
        simulator='vacask',
        vacask_command=VACASK_CMD,
        osdi_path=OSDI_PATH,
    )

def test_transient_rc():
    print("=== Transient RC Circuit ===")
    circuit = Circuit('RC Transient')
    circuit.V('input', 'inp', circuit.gnd, 5)
    circuit.R(1, 'inp', 'out', kilo(1))
    circuit.C(1, 'out', circuit.gnd, micro(1))

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.transient(step_time=1@u_us, end_time=10@u_ms)

    print(f"  Time points: {len(analysis.time)}")
    print(f"  Time range: {float(analysis.time[0]):.6g} to {float(analysis.time[-1]):.6g}")
    v_out = float(analysis['out'][-1])
    print(f"  V(out) final: {v_out:.4f}")
    # RC time constant = 1k * 1u = 1ms, after 10ms (10 tau) should be ~5V
    assert abs(v_out - 5.0) < 0.01, f"Expected ~5V, got {v_out}"
    print("  PASS")

def test_operating_point():
    print("=== Operating Point ===")
    circuit = Circuit('Voltage Divider')
    circuit.V('cc', 'vcc', circuit.gnd, 10)
    circuit.R(1, 'vcc', 'mid', kilo(1))
    circuit.R(2, 'mid', circuit.gnd, kilo(1))

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.operating_point()

    v_mid = float(analysis['mid'][0])
    print(f"  V(mid): {v_mid:.4f}")
    assert abs(v_mid - 5.0) < 0.01, f"Expected 5V, got {v_mid}"
    print("  PASS")

def test_ac_analysis():
    print("=== AC Analysis ===")
    circuit = Circuit('RC Filter')
    circuit.SinusoidalVoltageSource(
        'input', 'inp', circuit.gnd,
        dc_offset=0, ac_magnitude=1,
        offset=0, amplitude=1, frequency=1@u_kHz,
    )
    circuit.R(1, 'inp', 'out', kilo(1))
    circuit.C(1, 'out', circuit.gnd, nano(100))

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.ac(
        variation='dec', number_of_points=10,
        start_frequency=100@u_Hz, stop_frequency=10@u_MHz,
    )

    print(f"  Frequency points: {len(analysis.frequency)}")
    # At low freq, gain should be ~1 (0 dB)
    gain_low = abs(complex(analysis['out'][0]))
    # At high freq, gain should be much less
    gain_high = abs(complex(analysis['out'][-1]))
    print(f"  Gain at {float(analysis.frequency[0]):.0f} Hz: {gain_low:.4f}")
    print(f"  Gain at {float(analysis.frequency[-1]):.0f} Hz: {gain_high:.6f}")
    assert gain_low > 0.9, f"Expected gain ~1 at low freq, got {gain_low}"
    assert gain_high < 0.01, f"Expected low gain at high freq, got {gain_high}"
    print("  PASS")

def test_dc_sweep():
    print("=== DC Sweep ===")
    circuit = Circuit('DC Sweep')
    circuit.V('in', 'inp', circuit.gnd, 0)
    circuit.R(1, 'inp', 'out', kilo(10))
    circuit.R(2, 'out', circuit.gnd, kilo(10))

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.dc(Vin=slice(0, 5, 0.5))

    sweep = np.array(analysis.sweep)
    v_out = np.array(analysis['out'])
    print(f"  Sweep points: {len(sweep)}")
    print(f"  Sweep range: {float(sweep[0]):.1f} to {float(sweep[-1]):.1f}")
    # Voltage divider: V(out) = V(in) / 2
    expected = sweep / 2.0
    max_err = float(np.max(np.abs(v_out - expected)))
    print(f"  Max error from V/2: {max_err:.6f}")
    assert max_err < 0.001, f"DC sweep error too large: {max_err}"
    print("  PASS")

def test_diode():
    print("=== Diode Model ===")
    circuit = Circuit('Diode Test')
    circuit.model('1N4148', 'D', Is=2.52e-9, Rs=0.568, N=1.752, Bv=100, Ibv=100e-6)
    circuit.V('input', 'inp', circuit.gnd, 5)
    circuit.R(1, 'inp', 'out', kilo(1))
    circuit.D(1, 'out', circuit.gnd, model='1N4148')

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.operating_point()

    v_out = float(analysis['out'][0])
    print(f"  V(out) [diode forward]: {v_out:.4f}")
    # Diode forward voltage should be roughly 0.5-0.8V
    assert 0.3 < v_out < 1.0, f"Expected diode Vf ~0.5-0.8V, got {v_out}"
    print("  PASS")

def test_pulse_transient():
    print("=== Pulse Transient ===")
    circuit = Circuit('Pulse RC')
    circuit.PulseVoltageSource(
        'clk', 'clk', circuit.gnd,
        initial_value=0, pulsed_value=5,
        pulse_width=5@u_ms, period=10@u_ms,
        rise_time=1@u_us, fall_time=1@u_us,
    )
    circuit.R(1, 'clk', 'out', kilo(1))
    circuit.C(1, 'out', circuit.gnd, micro(1))

    simulator = make_simulator()
    simulation = simulator.simulation(circuit)
    analysis = simulation.transient(step_time=10@u_us, end_time=20@u_ms)

    print(f"  Time points: {len(analysis.time)}")
    v_out = np.array(analysis['out'])
    v_max = float(np.max(v_out))
    print(f"  V(out) max: {v_max:.4f}")
    assert v_max > 3.0, f"Expected V(out) to charge above 3V, got {v_max}"
    print("  PASS")

if __name__ == '__main__':
    tests = [
        test_transient_rc,
        test_operating_point,
        test_ac_analysis,
        test_dc_sweep,
        test_diode,
        test_pulse_transient,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed else 0)
