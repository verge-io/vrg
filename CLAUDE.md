# Verge CLI

> Command-line interface for VergeOS, wrapping the pyvergeos SDK to provide scriptable infrastructure management.

## Documentation Index

| Document | When to Read |
|----------|--------------|
| [`docs/COMMANDS.md`](docs/COMMANDS.md) | Complete command reference organized by domain |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Design patterns, context flow, template system, exit codes |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Dev workflow, adding commands, commit format, PR process |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, fixtures, coverage, CI commands |
| [`docs/COOKBOOK.md`](docs/COOKBOOK.md) | Task-oriented recipes for common workflows |
| [`docs/TEMPLATES.md`](docs/TEMPLATES.md) | Template language reference (`.vrg.yaml` format) |

## Quick Start

```bash
uv sync                              # Install dependencies
uv run vrg --help                    # CLI help
uv run vrg vm list                   # Example command

uv run pytest                        # Run all tests
uv run pytest tests/unit/            # Unit tests only
uv run ruff check                    # Lint
uv run ruff format --check .         # Format check
uv run mypy src/verge_cli            # Type check
uv build                             # Build package
```

## Project Structure

```text
vrg/
├── src/verge_cli/
│   ├── __init__.py         # Version string
│   ├── __main__.py         # Entry point for `python -m verge_cli`
│   ├── cli.py              # Main Typer app, global options, command registration
│   ├── config.py           # TOML config loading/saving, env var handling
│   ├── auth.py             # pyvergeos client creation with credentials
│   ├── context.py          # VergeContext dataclass passed to commands
│   ├── columns.py          # ColumnDef system for table column definitions
│   ├── output.py           # Table/JSON/CSV formatters with Rich
│   ├── errors.py           # Exception classes and exit code mapping
│   ├── utils.py            # Resolver (name→key) and waiter utilities
│   ├── template/           # VM template subsystem (loader, schema, resolver, builder, units)
│   ├── schemas/            # JSON schema for .vrg.yaml templates
│   └── commands/           # Command modules (~75 files, organized by domain)
│       ├── vm.py, vm_drive.py, vm_nic.py, vm_device.py, vm_snapshot.py
│       ├── network.py, network_rule.py, network_dns.py, network_host.py, network_alias.py, network_diag.py
│       ├── tenant.py, tenant_node.py, tenant_storage.py, tenant_net.py, tenant_snapshot.py, tenant_stats.py, tenant_share.py
│       ├── nas.py, nas_service.py, nas_volume.py, nas_cifs.py, nas_nfs.py, nas_user.py, nas_sync.py, nas_files.py
│       ├── cluster.py, node.py, storage.py, snapshot.py, snapshot_profile.py, site.py, site_sync*.py
│       ├── user.py, group.py, permission.py, api_key.py, auth_source.py
│       ├── task.py, task_schedule.py, task_trigger.py, task_event.py, task_script.py
│       ├── recipe.py, recipe_section.py, recipe_question.py, recipe_instance.py, recipe_log.py
│       ├── tag.py, tag_category.py, resource_group.py
│       ├── certificate.py, oidc.py, oidc_user.py, oidc_group.py, oidc_log.py
│       ├── catalog.py, catalog_repo.py, catalog_log.py, catalog_repo_log.py
│       ├── update.py, update_source.py, update_branch.py, update_package.py, update_available.py, update_log.py
│       ├── alarm.py, alarm_history.py, log.py
│       ├── file.py, system.py, configure.py, completion.py
│       └── ...
├── tests/
│   ├── conftest.py         # Shared fixtures (cli_runner, mock_client, 50+ resource mocks)
│   ├── unit/               # Unit tests (~50+ test files)
│   ├── integration/        # Integration tests (real API, marked)
│   └── shakedown/          # End-to-end shakedown scripts
├── docs/                   # Documentation (see index above)
├── .claude/
│   ├── PRD.md              # Full product requirements
│   └── skills/             # Claude Code skills
└── pyproject.toml          # Project metadata, dependencies, tool config
```

## Command Structure

```
vrg <domain> <action> [options]
```

27 top-level command groups with 200+ subcommands across compute, networking, tenants, storage, identity, automation, and monitoring. Examples:

```bash
vrg vm list                          # List VMs
vrg -o json vm get web-01            # Get VM as JSON
vrg network rule create ...          # Create firewall rule
vrg tenant snapshot create acme ...  # Snapshot a tenant
```

Full reference: [`docs/COMMANDS.md`](docs/COMMANDS.md) | VM templates: [`docs/TEMPLATES.md`](docs/TEMPLATES.md)

## Development Workflow

- **Branches**: `feature/<name>`, `fix/<name>`, `refactor/<name>`
- **Commits**: Conventional format with emoji (e.g., `feat: ✨ add vm snapshot restore`)
- **PRs**: Summary + test plan, one feature/fix per PR

Details: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

## Configuration Precedence

1. CLI arguments (`--token`, `--host`, etc.)
2. Environment variables (`VERGE_HOST`, `VERGE_TOKEN`, etc.)
3. Named profile in `~/.vrg/config.toml`
4. Default profile

## External References

- **pyVergeOS SDK** (local): `/Volumes/HOME/projects/pyVergeOS`
- **VergeOS API docs** (local): `/Users/larry/Development/VergeOS-Docs/`
  - `docs/api-reference/` — Rendered endpoint documentation
  - `RAW/api-schema/endpoints/*.json` — Canonical JSON schemas (336 endpoints)

> **Important**: The SDK does not wrap every API endpoint. Never infer API limitations from SDK gaps — always check the API docs.

## Core Dependencies

- **Python** 3.10+ | **Package Manager**: uv
- **CLI**: Typer + Rich | **SDK**: pyvergeos
- **Config**: TOML (`~/.vrg/config.toml`)
- **Testing**: pytest, pytest-mock, pytest-cov
- **Linting**: ruff | **Type Checking**: mypy (strict)
