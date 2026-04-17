# Contributing

Guide for contributing to the Verge CLI project.

## Getting Started

```bash
# Clone the repository
git clone https://github.com/verge-io/vrg.git
cd vrg

# Install with development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check

# Type check
uv run mypy src/verge_cli

# Build
uv build
```

## Development Workflow

### 1. Create a Branch

```
feature/<name>    # New features
fix/<name>        # Bug fixes
refactor/<name>   # Code improvements
```

### 2. Make Changes

- Read existing code before modifying — follow established patterns
- Keep functions small and focused (single responsibility)
- Use type hints on all function signatures
- Prefer early returns to reduce nesting

### 3. Commit

Use [conventional commits](https://www.conventionalcommits.org/) with emoji:

```
feat: ✨ add vm snapshot restore command
fix: 🐛 handle missing network name in resolver
refactor: ♻️ extract common CRUD patterns
docs: 📝 update template guide examples
test: ✅ add integration tests for tenant clone
chore: 📦 bump pyvergeos to 0.15.0
```

Keep commits atomic — one logical change per commit. Write messages in imperative mood.

### 4. Create a Pull Request

- Include a summary of changes
- Add a test plan (what to verify)
- Reference related issues
- Keep PRs focused — one feature or fix per PR

## Adding a New Command Group

### Step 1: Create the Command Module

Create `src/verge_cli/commands/<resource>.py`:

```python
"""<Resource> management commands."""
import typer
from verge_cli.columns import ColumnDef
from verge_cli.context import get_context
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(help="Manage <resources>.")

COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map={"running": "green", "stopped": "red"}),
    ColumnDef("description", wide_only=True),
]

def _to_dict(obj: object) -> dict:
    """Convert SDK object to dict for output."""
    return {
        "$key": obj.key,
        "name": obj.name,
        "status": obj.get("status"),
        "description": obj.get("description"),
    }

@app.command("list")
def list_resources(ctx: typer.Context):
    """List all <resources>."""
    vctx = get_context(ctx)
    items = vctx.client.<resources>.list()
    output_result(
        [_to_dict(i) for i in items],
        columns=COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )

@app.command()
def get(ctx: typer.Context, identifier: str):
    """Get <resource> by ID or name."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.<resources>, identifier)
    item = vctx.client.<resources>.get(key)
    output_result(
        _to_dict(item),
        columns=COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
```

### Step 2: Register in cli.py

```python
from verge_cli.commands import <resource>
app.add_typer(<resource>.app, name="<resource>")
```

### Step 3: Add Tests

Create `tests/unit/test_<resource>.py` with mocked SDK responses. See [TESTING.md](TESTING.md) for fixtures and patterns.

## Code Style

This is a **Python** project. Key conventions:

- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes, `SCREAMING_SNAKE_CASE` for constants
- **Booleans**: Prefix with `is_`, `has_`, `can_`, `should_`
- **Formatting**: `ruff format` enforces style — run before committing
- **Linting**: `ruff check` catches issues — fix all warnings
- **Types**: `mypy --strict` — always add type annotations, wrap SDK `.key` access with `int()`
- **Imports**: Group as stdlib, third-party, local. `ruff` enforces ordering.

## Documentation

When to update which file:

| Change | Update |
|--------|--------|
| New command group | `docs/COMMANDS.md`, `CLAUDE.md` project structure |
| New query/diagnostic commands | `docs/COMMANDS.md`, `docs/COOKBOOK.md` |
| New global option | `docs/COMMANDS.md` Global Options table |
| New architecture pattern | `docs/ARCHITECTURE.md` |
| New test fixture | `docs/TESTING.md` |
| New workflow recipe | `docs/COOKBOOK.md` |
| New health check | `docs/COMMANDS.md` doctor section, `docs/COOKBOOK.md` |
| New known limitation | `docs/KNOWN_ISSUES.md` |

## Contributor License Agreement

By submitting a pull request, you agree to the terms of our [Contributor License Agreement](../CLA.md). This grants Verge.io the necessary rights to use and distribute your contributions while you retain ownership of your work.
