# Kener Agent CLI

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

`kener-agent` is a command-line tool for managing and applying **Kener monitors** defined in YAML files.  
It supports multiple instances, automatic context switching, and integrates seamlessly with CI/CD workflows.

---

## Features

- Apply monitors from YAML files to Kener API.
- Multi-instance configuration with default context support.
- Auto-resolution of group monitors.
- CLI commands for login, apply, listing, and setting defaults.
- Fully automated releases with semantic versioning.
- Compatible with Conventional Commits and GitHub Actions for automated release notes.
- PyPI package for easy installation.

---

## Installation

Install via PyPI:

```bash
pip install kener-agent
```

After installation, the CLI command `kener-agent` is available globally.

---

## Configuration

The tool stores its configuration in YAML format at:

```bash
~/.config/kener-agent/config.yml
```

### Example configuration

```yaml
default: dev
instances:
  dev:
    host: 10.10.3.1
    port: 3000
    token: devtoken
    folder: monitors/dev
  prod:
    host: 10.20.0.5
    port: 3000
    token: prodtoken
    folder: monitors/prod
```

---

## CLI Commands

### 1. Login / Add an Instance

```bash
kener-agent login --name dev --host 10.10.3.1 --port 3000 --token <token> --folder monitors/dev --default
```

* `--name`: Name of the instance.
* `--default`: Set as default instance.
* Stores credentials and folder path in `~/.config/kener-agent/config.yml`.

### 2. Apply Monitors

```bash
kener-agent apply [--instance dev] [--folder ./other-folder]
```

* `--instance`: Optional instance name (overrides default).
* `--folder`: Optional folder override containing YAML monitor files.
* Processes YAML files in ascending numeric order (e.g., `01-monitor.yml`, `02-monitor.yml`).

### 3. List Instances

```bash
kener-agent list
```

Outputs a table of configured instances, highlighting the default.

```bash
╒══════════╤═══════════╤═════════════╤═══════╤═════════════════╕
│ Default  │ Instance  │ Host        │ Port  │ Folder          │
╞══════════╪═══════════╪═════════════╪═══════╪═════════════════╡
│ *        │ dev       │ 10.10.3.1   │ 3000  │ monitors/dev    │
│          │ prod      │ 10.20.0.5   │ 3000  │ monitors/prod   │
╘══════════╧═══════════╧═════════════╧═══════╧═════════════════╛
```

### 4. Set Default Instance

```bash
kener-agent set-default prod
```

Switches the default instance to `prod`.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Ensure tests pass.
5. Submit a pull request.

## Contact

For questions or support, open an issue on GitHub or contact the maintainer.
