"""Include options at the circuit-to-simulator serialization boundary."""

from pathlib import Path

import pytest

from InSpice.Spice.Netlist import Circuit
from InSpice.Spice.Simulator import Simulator


def vacask_netlist(circuit):
    simulator = Simulator.factory(simulator='vacask')
    simulation = simulator.simulation(circuit)
    simulation.operating_point(run=False)
    return str(simulation)


def test_native_and_foreign_includes_coexist(tmp_path):
    circuit = Circuit('Mixed libraries')
    native = tmp_path / 'native.lib'
    foreign = tmp_path / 'spice models.lib'
    circuit.include(native)
    circuit.include(foreign, lang='ngspice')
    circuit.lib(foreign, 'tt', lang='xyce')
    circuit.lib(native, 'native_tt')

    netlist = vacask_netlist(circuit)
    assert f'include "{native}"\n' in netlist
    assert f'include "{foreign}" lang=ngspice\n' in netlist
    assert f'include "{foreign}" lang=xyce section=tt\n' in netlist
    assert f'include "{native}" section=native_tt\n' in netlist
    assert netlist.index('include ') < netlist.index('control\n')
    assert 'analysis op1 op' in netlist


def test_include_options_deduplicate_by_path_and_options(tmp_path):
    circuit = Circuit('Includes')
    path = tmp_path / 'models.lib'
    circuit.include(path, lang='ngspice', section='tt')
    circuit.include(path.parent / '.' / path.name, False, section='tt', lang='ngspice')
    circuit.include(path, lang='xyce', section='tt')
    circuit.include(path)

    lines = [line for line in vacask_netlist(circuit).splitlines() if line.startswith('include ')]
    assert len(lines) == 3
    assert sum('lang=ngspice' in line for line in lines) == 1
    assert list(circuit.includes) == [path, path, path]
    assert all(isinstance(path, Path) for path in circuit.includes)


def test_library_options_and_sections_survive_clone(tmp_path):
    circuit = Circuit('Libraries')
    path = tmp_path / 'models.lib'
    circuit.lib(path, 'tt', lang='ngspice')
    circuit.lib(path, 'tt', lang='ngspice')
    circuit.lib(path, 'ff', lang='ngspice')
    circuit.lib(path, 'tt', lang='xyce')
    circuit.lib(path, lang='ngspice')
    circuit.include(path, lang='xyce')

    clone = circuit.clone()
    assert vacask_netlist(clone) == vacask_netlist(circuit)
    lines = [line for line in vacask_netlist(clone).splitlines() if line.startswith('include ')]
    assert len(lines) == 5
    assert f'include "{path}" lang=ngspice section=ff' in lines
    assert f'include "{path}" lang=ngspice' in lines
    # Cloning owns its option dictionaries as well as its directive lists.
    assert clone._include_directives[0].options is not circuit._include_directives[0].options
    assert clone._lib_directives[0].options is not circuit._lib_directives[0].options
    clone.lib(path, 'ss', lang='ngspice')
    assert 'section=ss' not in vacask_netlist(circuit)


def test_copy_to_preserves_directives_and_options(tmp_path):
    source = Circuit('Source')
    path = tmp_path / 'models.lib'
    source.include(path, lang='ngspice')
    source.lib(path, 'tt', lang='xyce')
    source.parameter('supply', 1.8)
    source.R(1, 'out', 0, 1000)
    target = Circuit('Target')
    target.include(tmp_path / 'native.lib')
    assert source.copy_to(target) is target

    netlist = vacask_netlist(target)
    assert f'include "{path}" lang=ngspice\n' in netlist
    assert f'include "{path}" lang=xyce section=tt\n' in netlist
    assert f'include "{tmp_path / "native.lib"}"\n' in netlist
    assert 'parameters supply=1.8' in netlist
    assert 'r1 (out 0)' in netlist


@pytest.mark.parametrize('method', ['include', 'lib'])
@pytest.mark.parametrize('simulator', [None, 'ngspice', 'xyce'])
def test_spice_output_rejects_backend_options(method, simulator):
    circuit = Circuit('Foreign include')
    getattr(circuit, method)('models.lib', lang='ngspice')
    with pytest.raises(ValueError, match='SPICE include/lib output does not support options: lang'):
        circuit.str(simulator=simulator)


@pytest.mark.parametrize('method', ['include', 'lib'])
@pytest.mark.parametrize('options', [
    {'unsupported': 'value'},
    {'lang': 'ngspice section=tt'},
    {'lang': '"ngspice"'},
    {'lang': None},
    {'lang': ['ngspice']},
    {'section': 'tt\ncontrol'},
    {'section': 0},
    {'section': False},
    {'section': []},
])
def test_vacask_rejects_unrepresentable_options(method, options):
    circuit = Circuit('Invalid options')
    getattr(circuit, method)('models.lib', **options)
    with pytest.raises(ValueError, match='VACASK include'):
        vacask_netlist(circuit)


def test_legacy_directives_and_views(tmp_path):
    circuit = Circuit('Legacy includes')
    path = tmp_path / 'models.lib'
    circuit.include(path, False)
    circuit.include(path, False)
    circuit.lib(str(path), 'tt')
    circuit.lib(str(path), 'tt')
    circuit.lib(path, '')
    assert circuit._includes == [path]
    assert circuit._libs == [(str(path), 'tt'), (path, '')]
    for simulator in (None, 'ngspice', 'xyce'):
        netlist = circuit.str(simulator=simulator)
        assert netlist.count(f'.include {path}\n') == 1
        assert netlist.count(f'.lib {path} tt\n') == 1
    assert f'include "{path}"\n' in vacask_netlist(circuit)


def test_spice_library_flavour_selection(tmp_path):
    path = tmp_path / 'models.lib'
    flavour = tmp_path / 'models.lib@xyce'
    flavour.touch()
    circuit = Circuit('Library flavour')
    circuit.include(path)
    circuit.lib(path, 'tt')
    netlist = circuit.str(simulator='xyce')
    assert f'.include {flavour}\n' in netlist
    assert f'.lib {flavour} tt\n' in netlist
