# Verge CLI

Command-line interface for [VergeOS](https://www.verge.io) — manage virtual machines, networks, DNS, firewall rules, and more from your terminal.

[![PyPI version](https://img.shields.io/pypi/v/vrg)](https://pypi.org/project/vrg/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Installation

### pipx (recommended)

```bash
pipx install vrg
```

### pip

```bash
pip install vrg
```

### uv

```bash
uv tool install vrg
```

### Homebrew

```bash
brew install verge-io/tap/vrg
```

### Standalone binary

Download a pre-built binary from the [latest release](https://github.com/verge-io/vrg/releases/latest) and place it in your `PATH`. Available for Linux (x86_64), macOS (ARM64), and Windows (x86_64).

**macOS note:** You may need to remove the quarantine attribute:

```bash
xattr -d com.apple.quarantine ./vrg
```

### Verify

```bash
vrg --version
```

## Quick Start

```bash
# 1. Configure credentials
vrg configure setup

# 2. Verify connection
vrg system info

# 3. List your VMs
vrg vm list
```

## Highlights

- **200+ commands** across compute, networking, tenants, NAS, identity, automation, and monitoring
- **Declarative VM templates** — provision from `.vrg.yaml` files with variables, dry-run, and batch support
- **Flexible auth** — interactive setup via `vrg configure`, bearer token, API key, or username/password with named profiles
- **Flexible output** — table, wide, JSON, or CSV with `--query` field extraction
- **Shell completion** — tab completion for bash, zsh, fish, and PowerShell

## Commands

```
vrg <domain> [sub-domain] <action> [options]
```

| Domain | Commands |
|--------|----------|
| **Compute** | `vm`, `vm drive`, `vm nic`, `vm device`, `vm snapshot` |
| **Networking** | `network`, `network rule`, `network dns`, `network host`, `network alias`, `network diag` |
| **Tenants** | `tenant`, `tenant node`, `tenant storage`, `tenant net`, `tenant snapshot`, `tenant stats`, `tenant share`, `tenant logs` |
| **NAS** | `nas service`, `nas volume`, `nas cifs`, `nas nfs`, `nas user`, `nas sync`, `nas files` |
| **Infrastructure** | `cluster`, `node`, `storage` |
| **Snapshots** | `snapshot`, `snapshot profile` |
| **Sites & Replication** | `site`, `site sync outgoing`, `site sync incoming` |
| **Identity & Access** | `user`, `group`, `permission`, `api-key`, `auth-source` |
| **Certificates & SSO** | `certificate`, `oidc` |
| **Automation** | `task`, `task schedule`, `task trigger`, `task event`, `task script` |
| **Recipes** | `recipe`, `recipe section`, `recipe question`, `recipe instance`, `recipe log` |
| **Catalog** | `catalog`, `catalog repo` |
| **Updates** | `update`, `update source`, `update branch`, `update package`, `update available` |
| **Monitoring** | `alarm`, `alarm history`, `log` |
| **Tagging** | `tag`, `tag category`, `resource-group` |
| **System** | `system`, `configure`, `file`, `completion` |

Most commands follow a consistent CRUD pattern (`list`, `get`, `create`, `update`, `delete`). Destructive operations require `--yes` to skip confirmation.

Run `vrg <command> --help` for usage details, or see the full [Command Reference](docs/COMMANDS.md).

## Configuration

Configuration is stored in `~/.vrg/config.toml`. Run `vrg configure setup` for interactive setup, or set environment variables (`VERGE_HOST`, `VERGE_TOKEN`, etc.) to override. Multiple named profiles are supported.

See the [Cookbook](docs/COOKBOOK.md) for setup recipes and the [Command Reference](docs/COMMANDS.md) for all environment variables.

## VM Templates

Create VMs from declarative `.vrg.yaml` files instead of long command lines. Templates support variables, dry-run previews, runtime overrides (`--set`), cloud-init, and batch provisioning.

```bash
vrg vm create -f web-server.vrg.yaml --dry-run   # Preview
vrg vm create -f web-server.vrg.yaml              # Create
```

See the [Template Guide](docs/TEMPLATES.md) for the full field reference and examples.

## Output Formats

All commands support `--output table|wide|json|csv` and `--query` for field extraction. See the [Command Reference](docs/COMMANDS.md#global-options).

## Shell Completion

Tab completion is available for bash, zsh, fish, and PowerShell. Run `vrg --install-completion` for quick setup, or see the [Cookbook](docs/COOKBOOK.md) for manual configuration.

**macOS zsh note:** If you see `compinit: insecure directories` after installing completions, fix the Homebrew directory permissions:

```bash
chmod 755 /opt/homebrew/share/zsh /opt/homebrew/share/zsh/site-functions
```

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Configuration profile to use |
| `--host` | `-H` | VergeOS host URL (override) |
| `--output` | `-o` | Output format (table, wide, json, csv) |
| `--query` | | Extract field using dot notation |
| `--verbose` | `-v` | Increase verbosity (-v, -vv, -vvv) |
| `--quiet` | `-q` | Suppress non-essential output |
| `--no-color` | | Disable colored output |
| `--version` | `-V` | Show version |
| `--help` | | Show help |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Configuration error |
| 4 | Authentication error |
| 5 | Permission denied |
| 6 | Resource not found |
| 7 | Conflict (e.g., duplicate name) |
| 8 | Validation error |
| 9 | Timeout |
| 10 | Connection error |

## Contributing

We welcome contributions! Please read the following before submitting a pull request.

```bash
git clone https://github.com/verge-io/vrg.git
cd vrg
uv sync --all-extras
uv run pytest              # Tests
uv run ruff check .        # Lint
uv run mypy src/verge_cli  # Type check
```

By submitting a pull request, you agree to the terms of our [Contributor License Agreement](CLA.md).

- Follow the existing code style and conventions
- Add tests for new functionality
- Keep pull requests focused — one feature or fix per PR
- Use [conventional commit](https://www.conventionalcommits.org/) messages

## Documentation

- [Command Reference](docs/COMMANDS.md) — Full command reference
- [Template Guide](docs/TEMPLATES.md) — Template language reference
- [Cookbook](docs/COOKBOOK.md) — Task-oriented recipes
- [Architecture](docs/ARCHITECTURE.md) — Design patterns and internals
- [Known Issues](docs/KNOWN_ISSUES.md) — Current limitations and workarounds

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
