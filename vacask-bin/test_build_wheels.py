"""Regression tests for release archive to wheel packaging."""

import importlib.util
from pathlib import Path
import zipfile

import pytest


spec = importlib.util.spec_from_file_location(
    'build_wheels', Path(__file__).with_name('build_wheels.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture(params=['.exe', ''])
def release_layout(tmp_path, request):
    suffix = request.param
    archive = tmp_path / 'archive'
    sim = archive / 'simulator'
    sim.mkdir(parents=True)
    for name in ('vacask', 'openvaf-r'):
        (sim / (name + suffix)).write_bytes(b'executable')
    lib = archive / 'lib' if suffix else archive / 'lib' / 'vacask'
    for name in ('mod/resistor.osdi', 'mod/spice/diode.osdi', 'inc/builtins.inc'):
        path = lib / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
    pkg = tmp_path / 'pkg'
    pkg.mkdir()
    return archive, lib, pkg, suffix


def test_release_payload_survives_wheel(release_layout, tmp_path):
    archive, lib, pkg, suffix = release_layout
    builder.build_package_layout(str(archive), str(pkg), '0.0.dev0', suffix)
    wheel = builder.make_wheel(str(pkg), '0.0.dev0', 'win_amd64' if suffix
                               else 'manylinux_2_34_x86_64', str(tmp_path))
    builder.validate_wheel(str(archive), wheel, suffix)
    with zipfile.ZipFile(wheel) as whl:
        for source in lib.rglob('*'):
            if source.is_file():
                name = 'vacask_bin/data/lib/vacask/' + source.relative_to(lib).as_posix()
                assert whl.read(name) == source.read_bytes()


@pytest.mark.parametrize('missing', ['mod/resistor.osdi', 'inc/builtins.inc'])
def test_validation_rejects_lost_wheel_payload(release_layout, tmp_path, missing):
    archive, lib, pkg, suffix = release_layout
    builder.build_package_layout(str(archive), str(pkg), '0.0.dev0', suffix)
    staged = pkg / 'data/lib/vacask' / missing
    if staged.exists():
        staged.unlink()
    wheel = builder.make_wheel(str(pkg), '0.0.dev0', 'win_amd64', str(tmp_path))
    with pytest.raises(ValueError, match='Missing wheel payload'):
        builder.validate_wheel(str(archive), wheel, suffix)


def test_validation_rejects_archive_without_models(release_layout, tmp_path):
    archive, lib, pkg, suffix = release_layout
    for model in lib.rglob('*.osdi'):
        model.unlink()
    builder.build_package_layout(str(archive), str(pkg), '0.0.dev0', suffix)
    wheel = builder.make_wheel(str(pkg), '0.0.dev0', 'win_amd64', str(tmp_path))
    with pytest.raises(ValueError, match='No OSDI files'):
        builder.validate_wheel(str(archive), wheel, suffix)
