# Architecture

Design patterns, conventions, and technical reference for the Verge CLI codebase.

## Context Pattern

Global options (`--profile`, `--host`, `--output`, etc.) are parsed in `cli.py`'s main callback and stored in `ctx.obj`. Commands call `get_context(ctx)` to get a `VergeContext` with a lazily-created pyvergeos client.

```python
from verge_cli.context import get_context
from verge_cli.output import output_result

@app.command()
def list(ctx: typer.Context):
    vctx = get_context(ctx)  # Gets authenticated client
    vms = vctx.client.vms.list()
    output_result(
        [_vm_to_dict(v) for v in vms],  # Convert SDK objects to dicts
        columns=COLUMNS,                 # ColumnDef list for table/csv
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
```

Key modules:
- `cli.py` — Main Typer app, global option parsing, command registration
- `context.py` — `VergeContext` dataclass, `get_context()` helper
- `auth.py` — `get_client()` creates authenticated pyvergeos client
- `config.py` — TOML config loading, env var handling, `get_effective_config()`

## Name Resolution

Commands accept `<ID|NAME>` arguments. Use `resolve_resource_id()` from `utils.py`:

- **Numeric string** — treated as a Key, returned as `int` directly
- **Text string** — searches by name via SDK `.list()` with name filter
- **0 matches** — raises `ResourceNotFoundError` (exit 6)
- **1 match** — returns the Key as `int`
- **Multiple matches** — raises `MultipleMatchesError` (exit 7), lists all matches

**mypy note**: SDK attribute access returns `Any`. Always wrap `.key` with `int()` in functions declared `-> int`.

## Credential Resolution Order

1. CLI arguments (`--token`, `--api-key`, `--username`/`--password`)
2. Environment variables (`VERGE_HOST`, `VERGE_TOKEN`, etc.)
3. Named profile in `~/.vrg/config.toml`
4. Default profile
5. Interactive prompt (future)

## Template System

The `verge_cli.template` package handles `.vrg.yaml` template-based VM creation:

| Module | Responsibility |
|--------|----------------|
| `units.py` | Parses human-friendly sizes like `"4GB"` → `4096` MB |
| `resolver.py` | Resolves template name references (network, tier) to API keys |
| `loader.py` | YAML loading, `${VAR}` substitution, `--set` override merging |
| `schema.py` | Validates templates against `schemas/vrg-vm-template.schema.json` |
| `builder.py` | Orchestrates VM + drives + NICs + devices + cloud-init creation |

**Flow**: `loader.py` → `schema.py` → `resolver.py` → `builder.py`

## ColumnDef System

All command output uses `ColumnDef` from `verge_cli.columns` to define table columns. Each command module defines a `COLUMNS` list:

```python
from verge_cli.columns import ColumnDef

COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map={"running": "green", "stopped": "red"}),
    ColumnDef("description", wide_only=True),  # Only shown in -o wide
]
```

`ColumnDef` options:
- `header` — Custom display header (defaults to title-cased key)
- `wide_only` — Only shown in `wide` output format
- `style_map` — Dict mapping values to Rich styles
- `style_fn` — Callable `(value, row) -> style` for dynamic styling
- `format_fn` — Callable `(value, for_csv=False) -> str` for custom formatting
- `normalize_fn` — Callable to normalize values before style lookup

## Output Formatting

Use `rich.box.SIMPLE` for tables (copy-paste friendly). Check `sys.stdout.isatty()` to disable fancy formatting when piping.

Output helpers in `verge_cli.output`:
- `output_result(data, ...)` — Main output dispatcher (table/wide/json/csv)
- `output_success(message, ...)` — Green checkmark success message
- `output_error(message, ...)` — Red error message to stderr
- `output_warning(message, ...)` — Yellow warning message

**Important**: `output_result()` takes `data` as its first arg (not a context object) and requires explicit keyword args: `output_format`, `query`, `quiet`, `no_color`.

## Async Query Pattern

Network and node diagnostic commands use an async query API. The `_query_helpers.py` module provides shared infrastructure:

```python
from verge_cli.commands._query_helpers import run_query, output_query_result

result = run_query(
    net_obj.queries,        # Any QueryManager (VNet, Node, etc.)
    "ping",                 # Query type string
    {"host": "8.8.8.8"},   # Parameters
    timeout=30,
    quiet=vctx.quiet,
    label="Running ping...",
)
output_query_result(result, output_format=vctx.output_format, ...)
```

`run_query()` submits the query, polls for completion with a Rich spinner, and raises `CliError` on timeout or failure. Used by `network_query.py` and `node_query.py`.

## Multi-Profile List

The `--all-profiles` global flag runs a `list` command across every configured profile and merges the results. Commands opt in by checking `ctx.obj["all_profiles"]` early and calling `list_all_profiles()` from `verge_cli.multi`:

```python
if ctx.obj.get("all_profiles"):
    list_all_profiles(ctx, lambda c: c.vms.list(), _vm_to_dict, VM_COLUMNS)
```

Each profile is queried in sequence, results are tagged with a `profile` column, and output is merged into a single table.

## Doctor Check Registry

`commands/doctor.py` uses a decorator-based registry for health checks:

```python
@_register("connectivity")
def check_connectivity(client: VergeClient) -> CheckResult:
    ...
    return CheckResult(name="connectivity", status=PASS, message="OK")
```

`CheckResult` is a frozen dataclass with `name`, `status` (pass/warn/fail/skip), `message`, and optional `details` dict. The `run_checks()` function iterates registered checks, isolating exceptions per-check.

## Update Operations

Use the read-patch-write pattern when the API doesn't support partial updates:

```python
current = client.vms.get(key)
updates = {k: v for k, v in cli_args.items() if v is not None}
client.vms.update(key, **{**current, **updates})
```

## Waiting on Async Operations

Use `wait_for_state()` from `utils.py` with exponential backoff:

```python
wait_for_state(vm, target_state="running", timeout=300, interval=2.0, backoff=1.5)
```

## Error Handling

Exception classes are defined in `errors.py`. SDK exceptions are mapped to CLI errors via `map_sdk_exception()`. The `handle_errors()` decorator catches exceptions and exits with the appropriate code.

| CLI Exception | Exit Code | SDK Exception |
|---------------|-----------|---------------|
| `CliError` | 1 | `VergeError` |
| `ConfigurationError` | 3 | — |
| `AuthError` | 4 | `AuthenticationError` |
| `ForbiddenError` | 5 | — |
| `ResourceNotFoundError` | 6 | `NotFoundError` |
| `MultipleMatchesError` | 7 | — |
| `ConflictCliError` | 7 | `ConflictError` |
| `ValidationCliError` | 8 | `ValidationError` |
| `TimeoutCliError` | 9 | `VergeTimeoutError` |
| `ConnectionCliError` | 10 | `VergeConnectionError` |

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
| 7 | Conflict (duplicate name) |
| 8 | Validation error |
| 9 | Timeout error |
| 10 | Connection error |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `VERGE_HOST` | VergeOS host URL |
| `VERGE_TOKEN` | Bearer token |
| `VERGE_API_KEY` | API key |
| `VERGE_USERNAME` | Username for basic auth |
| `VERGE_PASSWORD` | Password for basic auth |
| `VERGE_PROFILE` | Default profile name |
| `VERGE_OUTPUT` | Default output format |
| `VERGE_VERIFY_SSL` | SSL verification (true/false) |
| `VERGE_TIMEOUT` | Request timeout in seconds |
