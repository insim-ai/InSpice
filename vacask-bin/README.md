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

- Linux x86_64 (glibc >= 2.39, e.g. Ubuntu 24.04+)
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
