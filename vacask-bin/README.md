# vacask-bin

Prebuilt [VACASK](https://github.com/pepijndevos/VACASK) circuit simulator binaries, packaged as platform-specific Python wheels.

## Installation

```bash
pip install vacask-bin
```

Or as part of InSpice:

```bash
pip install InSpice[vacask]
```

## Supported Platforms

- Linux x86_64 and aarch64 (glibc >= 2.34)
- macOS arm64 (macOS 14 Sonoma+)
- Windows x86_64

## Usage

After installation, the `vacask` command is available on your PATH:

```bash
vacask input.sim
```

From Python:

```python
import vacask_bin

print(vacask_bin.VACASK_CMD)   # Path to vacask binary
print(vacask_bin.OPENVAF_CMD)  # Path to openvaf-r binary
print(vacask_bin.MOD_DIR)      # Path to OSDI device models
```

## Publishing a release

`vacask-bin` is released independently of InSpice. Its Python package version
is derived from the VACASK tag (for example, `_0.3.4-dev` becomes
`0.3.4.dev0` when normalized by Python packaging tools).

1. Publish the VACASK release with archives for all supported platforms.
2. Update `vacask-bin/VACASK_VERSION` to the exact upstream release tag and
   merge the change into `main`. Changes to this file on `main` automatically
   build and publish only `vacask-bin` using the pinned tag.

To retry manually, in GitHub Actions select **Upload Python Package**, then
**Run workflow** on `main`. Alternatively, run:

```bash
gh workflow run python-publish.yml --repo insim-ai/InSpice --ref main
```

Publishing an InSpice GitHub release builds and publishes only InSpice.
Both packages use the `pypi` environment and the existing
`python-publish.yml` PyPI trusted publisher. Already-published files are
skipped when retrying a publication.

To build the VACASK wheels locally before publishing:

```bash
python vacask-bin/build_wheels.py \
  --release-tag "$(cat vacask-bin/VACASK_VERSION)" \
  --output-dir dist/
```
