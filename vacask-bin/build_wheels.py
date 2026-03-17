#!/usr/bin/env python3
"""Build platform-specific wheels for vacask-bin from VACASK GitHub releases."""

import argparse
import csv
import hashlib
import io
import os
import re
import shutil
import stat
import struct
import tarfile
import tempfile
import time
import urllib.request
import zipfile


PLATFORMS = {
    'linux-x86_64': {
        'ext': 'tar.gz',
        'wheel_tag': 'manylinux_2_39_x86_64',
        'exe_suffix': '',
    },
    'darwin-arm64': {
        'ext': 'tar.gz',
        'wheel_tag': 'macosx_14_0_arm64',
        'exe_suffix': '',
    },
    'windows-x86_64': {
        'ext': 'zip',
        'wheel_tag': 'win_amd64',
        'exe_suffix': '.exe',
    },
}

GITHUB_REPO = 'pepijndevos/VACASK'

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'vacask_bin')


def tag_to_version(tag):
    """Convert release tag to Python version: '_0.3.2-dev2' -> '0.3.2.dev2'"""
    v = tag.lstrip('_')
    v = re.sub(r'-', '.', v)
    return v


def download_archive(tag, tag_version, platform, ext, output_dir):
    """Download a VACASK release archive from GitHub."""
    filename = f'vacask_{tag_version}_{platform}.{ext}'
    url = f'https://github.com/{GITHUB_REPO}/releases/download/{tag}/{filename}'
    dest = os.path.join(output_dir, filename)

    if os.path.exists(dest):
        print(f'  Using cached {filename}')
        return dest

    print(f'  Downloading {url}')
    urllib.request.urlretrieve(url, dest)
    return dest


def extract_archive(archive_path, ext, dest_dir):
    """Extract tar.gz or zip archive."""
    if ext == 'tar.gz':
        with tarfile.open(archive_path, 'r:gz') as tf:
            tf.extractall(dest_dir)
    elif ext == 'zip':
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(dest_dir)


def copy_tree(src, dst):
    """Recursively copy src into dst, creating directories as needed."""
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            copy_tree(os.path.join(src, name), os.path.join(dst, name))
    else:
        shutil.copy2(src, dst)


def build_package_layout(extracted_dir, pkg_dir, version, exe_suffix):
    """Build the vacask_bin package layout from extracted archive contents."""
    # Copy Python package files
    shutil.copy2(os.path.join(SRC_DIR, '__init__.py'), os.path.join(pkg_dir, '__init__.py'))

    # Write _version.py
    with open(os.path.join(pkg_dir, '_version.py'), 'w') as f:
        f.write(f'__version__ = "{version}"\n')

    data_bin = os.path.join(pkg_dir, 'data', 'bin')
    data_lib = os.path.join(pkg_dir, 'data', 'lib')
    os.makedirs(data_bin, exist_ok=True)

    sim_dir = os.path.join(extracted_dir, 'simulator')
    lib_dir = os.path.join(extracted_dir, 'lib')

    # Copy binaries
    for binary in ('vacask', 'openvaf-r'):
        src = os.path.join(sim_dir, binary + exe_suffix)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(data_bin, binary + exe_suffix))

    # Copy bundled shared libraries (Linux/macOS: simulator/lib/*)
    sim_lib = os.path.join(sim_dir, 'lib')
    if os.path.isdir(sim_lib):
        copy_tree(sim_lib, os.path.join(data_bin, 'lib'))

    # Copy DLLs (Windows: simulator/*.dll)
    if exe_suffix == '.exe':
        for f in os.listdir(sim_dir):
            if f.lower().endswith('.dll'):
                shutil.copy2(os.path.join(sim_dir, f), os.path.join(data_bin, f))

    # Copy lib/vacask (mod + inc)
    vacask_lib = os.path.join(lib_dir, 'vacask')
    if os.path.isdir(vacask_lib):
        copy_tree(vacask_lib, os.path.join(data_lib, 'vacask'))


def sha256_digest(data):
    """Return URL-safe base64 SHA256 digest (no trailing =)."""
    import base64
    h = hashlib.sha256(data).digest()
    return base64.urlsafe_b64encode(h).rstrip(b'=').decode('ascii')


def make_wheel(pkg_dir, version, wheel_tag, output_dir):
    """Create a .whl file from the package directory."""
    wheel_name = f'vacask_bin-{version}-py3-none-{wheel_tag}.whl'
    wheel_path = os.path.join(output_dir, wheel_name)

    dist_info = f'vacask_bin-{version}.dist-info'

    # Collect all files in package
    records = []

    with zipfile.ZipFile(wheel_path, 'w', zipfile.ZIP_DEFLATED) as whl:
        # Add package files
        for root, dirs, files in os.walk(pkg_dir):
            for fname in sorted(files):
                full_path = os.path.join(root, fname)
                arcname = os.path.join('vacask_bin', os.path.relpath(full_path, pkg_dir))
                data = open(full_path, 'rb').read()
                digest = sha256_digest(data)

                info = zipfile.ZipInfo(arcname)
                info.compress_type = zipfile.ZIP_DEFLATED

                # Set Unix file permissions in ZIP external attrs
                # Must include S_IFREG (regular file) for pip to honor the mode
                if _is_executable(full_path):
                    info.external_attr = (stat.S_IFREG | stat.S_IRWXU | stat.S_IRGRP |
                                          stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH) << 16
                else:
                    info.external_attr = (stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR |
                                          stat.S_IRGRP | stat.S_IROTH) << 16

                whl.writestr(info, data)
                records.append((arcname, f'sha256={digest}', str(len(data))))

        # METADATA
        metadata = (
            f'Metadata-Version: 2.1\n'
            f'Name: vacask-bin\n'
            f'Version: {version}\n'
            f'Summary: Prebuilt VACASK circuit simulator binaries\n'
            f'Requires-Python: >=3.9\n'
            f'License: GPL-3.0-or-later\n'
        )
        arcname = f'{dist_info}/METADATA'
        data = metadata.encode('utf-8')
        whl.writestr(arcname, data)
        records.append((arcname, f'sha256={sha256_digest(data)}', str(len(data))))

        # WHEEL
        wheel_meta = (
            f'Wheel-Version: 1.0\n'
            f'Generator: vacask-bin-build-wheels\n'
            f'Root-Is-Purelib: false\n'
            f'Tag: py3-none-{wheel_tag}\n'
        )
        arcname = f'{dist_info}/WHEEL'
        data = wheel_meta.encode('utf-8')
        whl.writestr(arcname, data)
        records.append((arcname, f'sha256={sha256_digest(data)}', str(len(data))))

        # entry_points.txt
        entry_points = '[console_scripts]\nvacask = vacask_bin:_run_vacask\n'
        arcname = f'{dist_info}/entry_points.txt'
        data = entry_points.encode('utf-8')
        whl.writestr(arcname, data)
        records.append((arcname, f'sha256={sha256_digest(data)}', str(len(data))))

        # top_level.txt
        arcname = f'{dist_info}/top_level.txt'
        data = b'vacask_bin\n'
        whl.writestr(arcname, data)
        records.append((arcname, f'sha256={sha256_digest(data)}', str(len(data))))

        # RECORD (no hash for itself)
        record_buf = io.StringIO()
        writer = csv.writer(record_buf)
        for row in records:
            writer.writerow(row)
        writer.writerow((f'{dist_info}/RECORD', '', ''))
        arcname = f'{dist_info}/RECORD'
        whl.writestr(arcname, record_buf.getvalue())

    print(f'  Created {wheel_name}')
    return wheel_path


def _is_executable(path):
    """Check if a file should be marked executable in the wheel."""
    name = os.path.basename(path)
    if name in ('vacask', 'openvaf-r', 'vacask.exe', 'openvaf-r.exe'):
        return True
    if name.endswith('.so') or name.endswith('.dylib'):
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Build vacask-bin wheels')
    parser.add_argument('--release-tag', required=True,
                        help='VACASK release tag (e.g. _0.3.2-dev2)')
    parser.add_argument('--output-dir', default='dist',
                        help='Output directory for wheels')
    parser.add_argument('--platform', action='append', dest='platforms',
                        choices=list(PLATFORMS.keys()),
                        help='Build only for specified platform(s)')
    parser.add_argument('--cache-dir', default=None,
                        help='Directory to cache downloaded archives')
    args = parser.parse_args()

    tag = args.release_tag
    tag_version = tag.lstrip('_')
    version = tag_to_version(tag)
    platforms = args.platforms or list(PLATFORMS.keys())

    os.makedirs(args.output_dir, exist_ok=True)
    cache_dir = args.cache_dir or tempfile.mkdtemp(prefix='vacask-bin-cache-')

    print(f'Building vacask-bin {version} from tag {tag}')
    print(f'Platforms: {", ".join(platforms)}')

    for platform in platforms:
        info = PLATFORMS[platform]
        print(f'\n--- {platform} ---')

        # Download
        archive = download_archive(tag, tag_version, platform, info['ext'], cache_dir)

        # Extract
        extract_dir = tempfile.mkdtemp(prefix=f'vacask-{platform}-')
        print(f'  Extracting to {extract_dir}')
        extract_archive(archive, info['ext'], extract_dir)

        # Find the extracted root (may be nested in a directory)
        entries = os.listdir(extract_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
            extracted_root = os.path.join(extract_dir, entries[0])
        else:
            extracted_root = extract_dir

        # Build package layout
        pkg_dir = tempfile.mkdtemp(prefix=f'vacask-pkg-{platform}-')
        print(f'  Building package layout')
        build_package_layout(extracted_root, pkg_dir, version, info['exe_suffix'])

        # Create wheel
        make_wheel(pkg_dir, version, info['wheel_tag'], args.output_dir)

        # Cleanup
        shutil.rmtree(extract_dir)
        shutil.rmtree(pkg_dir)

    print(f'\nDone! Wheels written to {args.output_dir}/')


if __name__ == '__main__':
    main()
