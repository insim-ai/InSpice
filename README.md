# InSpice

This repository has been forked from it's original repository PySpice.

## About

InSpice is a Python interface to the Ngspice and Xyce circuit simulators. It provides a Python API to describe electronic circuits and to run analog simulations.

## Installation

You can install InSpice from PyPI:

```bash
pip install inspice
```

For development installation:

```bash
git clone https://github.com/Innovoltive/InSpice.git
cd InSpice
pip install -e .
```

## Dependencies

- Python >= 3.12
- Ngspice (as shared library)
- matplotlib (for plotting)
- numpy (for numerical computation)

## Usage

See the `examples` directory for various examples of using InSpice.

Basic example:

```python
import InSpice
from InSpice.Unit import *

circuit = InSpice.Circuit('Simple RC Circuit')
circuit.R('1', 'input', 'output', 1@kΩ)
circuit.C('1', 'output', circuit.gnd, 1@µF)
```

### Backend-specific include options

`Circuit.include()` and `Circuit.lib()` accept extra keyword arguments for the
target simulator's include directive. For example, a parser-enabled VACASK build
can load SPICE libraries directly:

```python
from InSpice.Spice.Netlist import Circuit
from InSpice.Spice.Simulator import Simulator

circuit = Circuit('Foreign model libraries')
circuit.include('native-models.lib')
circuit.include('ngspice-models.lib', lang='ngspice')
circuit.lib('xyce-corners.lib', 'tt', lang='xyce')

simulation = Simulator.factory(simulator='vacask').simulation(circuit)
simulation.operating_point(run=False)
print(simulation)
```

The foreign directives become `include "/absolute/path/ngspice-models.lib"
lang=ngspice` and `include "/absolute/path/xyce-corners.lib" lang=xyce section=tt`.
VACASK supports `lang` and `section` options as bare identifiers; unsupported
options or values raise `ValueError` during serialization. Analysis commands
remain in the native VACASK control block.

Calls without extra options retain their existing behavior. Options participate
in duplicate detection and are preserved by `Circuit.clone()` and
`Circuit.copy_to()`. Generating
ordinary SPICE output (including ngspice and Xyce output) with extra options
raises `ValueError`, rather than silently dropping them. The caller chooses
options appropriate to the target; InSpice does not infer a dialect from a path.

## Documentation

For detailed documentation, please refer to the examples and docstrings.

## License

InSpice is licensed under the GNU General Public License v3.0 (GPL-3.0), the same license as the original PySpice project.

### GNU GPL v3.0

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Acknowledgments

Original project (PySpice) by Fabrice Salvaire
# Copyright (C) 2025 Innovoltive
# Modified by Innovoltive on April 18, 2025.
