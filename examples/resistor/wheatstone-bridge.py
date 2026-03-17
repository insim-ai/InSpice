from InSpice import Circuit, Simulator
from InSpice.Unit import *
import numpy as np

# Build wheatstone bridge circuit
circuit = Circuit('wheatstone bridge')
circuit.V('input', 'inp', circuit.gnd, 5@u_V)

circuit.R(1, 'inp', 'n1', 5@u_Ω)
circuit.R(2, 'inp', 'n2', 5@u_Ω)
circuit.R(3, 'n1', circuit.gnd, 5@u_Ω)
circuit.R(4, 'n2', circuit.gnd, 5@u_Ω)

# middle resistor
circuit.R(5, 'n1', 'n2', 5@u_Ω)

# adding current probe
circuit.R5.plus.add_current_probe(circuit)
simulator = Simulator.factory()
simulation = simulator.simulation(circuit, temperature=25, nominal_temperature=25)
analysis = simulation.operating_point()

# Print the branches dictionary
print("Values in analysis.branches:")
print(analysis.branches)

# Print the actual current values
print("\nExtracted current values:")
for name, branch in analysis.branches.items():
    current = float(branch[0])
    print(f"{name}: {current} A")
