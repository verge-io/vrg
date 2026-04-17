# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Verge CLI (`vrg`) — a Python CLI for managing VergeOS infrastructure, wrapping the pyvergeos SDK. ~200+ commands across 28 domains (compute, networking, tenants, storage, identity, automation, monitoring).

## Documentation Index

| Document | When to Read |
|----------|--------------|
| [`docs/COMMANDS.md`](docs/COMMANDS.md) | Complete command reference organized by domain |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Design patterns, context flow, template system, exit codes |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Dev workflow, adding commands, commit format, PR process |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, fixtures, coverage, CI commands |
| [`docs/COOKBOOK.md`](docs/COOKBOOK.md) | Task-oriented recipes for common workflows |
| [`docs/TEMPLATES.md`](docs/TEMPLATES.md) | Template language reference (`.vrg.yaml` format) |

## Commands

```bash
# Setup
uv sync --all-extras                     # Install all dependencies

# Run CLI
uv run vrg --help                        # CLI help
uv run vrg vm list                       # Example command

# Tests
uv run pytest                            # All tests
uv run pytest tests/unit/                # Unit tests only
uv run pytest tests/unit/test_vm.py::test_vm_list  # Single test
uv run pytest -m "not integration"       # Skip integration tests
uv run pytest tests/unit/ --cov          # With coverage

# Linting & Formatting
uv run ruff check .                      # Lint
uv run ruff check . --fix                # Auto-fix lint issues
uv run ruff format --check .             # Check formatting
uv run ruff format .                     # Auto-format

# Type Checking
uv run mypy src/verge_cli                # Strict mode

# Build
uv build                                 # Build wheel + sdist
```

**CI pipeline** (`.github/workflows/ci.yml`): lint → type check → test (3.10, 3.11, 3.12) → build.

## Architecture

### Context Flow

Global options parsed in `cli.py` main callback → stored in `ctx.obj` → accessed via `get_context(ctx)` in commands:

```python
@app.command()
@handle_errors()
def vm_list(ctx: typer.Context):
    vctx = get_context(ctx)           # VergeContext with authenticated client
    vms = vctx.client.vms.list()
    output_result(
        [_vm_to_dict(v) for v in vms],
        columns=VM_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
```

Key modules: `cli.py` (Typer app, global options) → `context.py` (VergeContext dataclass) → `auth.py` (lazy client creation) → `config.py` (TOML profiles, env vars).

### Command Pattern

Every command follows the same shape:
1. `@handle_errors()` decorator catches exceptions, maps SDK errors to exit codes
2. `get_context(ctx)` provides authenticated client + output settings
3. SDK objects converted to dicts via `_foo_to_dict()` helpers
4. `output_result()` handles table/wide/json/csv formatting

### ColumnDef System (`columns.py`)

Declarative table column definitions used by every list/get command:

```python
COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("description", wide_only=True),  # Only in -o wide
]
```

Shared style maps: `STATUS_STYLES` (running→green, stopped→dim, error→red), `FLAG_STYLES`, `BOOL_STYLES`.

### Name Resolution (`utils.py`)

`resolve_resource_id()`: numeric string → Key (int); text string → search by name via SDK. Returns single match or raises `ResourceNotFoundError` (exit 6) / `MultipleMatchesError` (exit 7).

### Error Handling (`errors.py`)

Exit codes: 0=success, 1=general, 2=usage, 3=config, 4=auth, 5=forbidden, 6=not found, 7=conflict, 8=validation, 9=timeout, 10=connection.

### Template Pipeline (`src/verge_cli/template/`)

`.vrg.yaml` files processed through: `loader.py` (YAML + `${VAR}` substitution) → `schema.py` (jsonschema validation) → `units.py` ("4GB" → 4096 MB) → `resolver.py` (names → keys) → `builder.py` (VM + drives + NICs creation).

### Credential Precedence

1. CLI arguments (`--token`, `--host`, etc.)
2. Environment variables (`VERGE_HOST`, `VERGE_TOKEN`, etc.)
3. Named profile in `~/.vrg/config.toml`
4. Default profile
5. Interactive prompt (if TTY)

### Multi-Profile (`multi.py`)

`--all-profiles` / `-A` runs list commands across all configured profiles concurrently, merging results with a profile column.

## Testing

**Fixtures** (`tests/conftest.py`): `cli_runner` (CliRunner), `mock_client` (patches `get_client`), 50+ pre-configured mock resource objects (`mock_vm`, `mock_network`, etc.).

**Test pattern**:
```python
def test_vm_list(cli_runner, mock_client):
    mock_client.vms.list.return_value = [mock_vm]
    result = cli_runner.invoke(app, ["vm", "list"])
    assert result.exit_code == 0
```

Markers: `@pytest.mark.integration` for tests hitting real API (skip with `-m "not integration"`).

## Development Workflow

- **Branches**: `feature/<name>`, `fix/<name>`, `refactor/<name>` — branched from `dev`
- **Flow**: feature/fix branch → PR to `dev` → when ready for release, PR `dev` to `main`
- **Commits**: Conventional format with emoji (e.g., `feat: ✨ add vm snapshot restore`)
- **PRs**: Summary + test plan, one feature/fix per PR

## Security

**Never disclose internal infrastructure details** in PRs, commit messages, or any content pushed to GitHub. This includes IP addresses, hostnames, system names, and profile names. Use generic references ("dev instance", "prod") instead.

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
- **Pre-commit**: ruff check, ruff format, mypy, trailing-whitespace
