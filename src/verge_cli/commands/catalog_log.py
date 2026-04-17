"""Catalog log management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_nas_resource

app = typer.Typer(
    name="log",
    help=(
        "View catalog operation logs — download, sync, and refresh"
        " activity.\n\n"
        "Catalog logs record events from recipe downloads, catalog"
        " refreshes, and version checks. Each entry has a **level**"
        " (`message`, `warning`, `error`, `critical`) and a timestamp.\n\n"
        "Use `-o json` for machine-readable output. Filter with `--catalog`"
        " (name or hex key) and `--level`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg catalog log list\n"
        "    vrg catalog log list --catalog windows-server\n"
        "    vrg catalog log list --level error\n"
        "    vrg -o json catalog log list\n\n"
        "---"
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

CATALOG_LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("level", style_map={"error": "red", "warning": "yellow", "critical": "red bold"}),
    ColumnDef("text", header="Message"),
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("user", wide_only=True),
]


def _log_to_dict(log: Any) -> dict[str, Any]:
    """Convert a CatalogLog SDK object to a dict for output."""
    # Timestamp is in microseconds in the SDK — convert to seconds for format_epoch
    ts = log.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 1e12:
        ts = ts / 1e6
    return {
        "$key": int(log.key),
        "level": log.get("level", ""),
        "text": log.get("text", ""),
        "timestamp": ts,
        "user": log.get("user", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    catalog: Annotated[
        str | None,
        typer.Option("--catalog", help="Filter by catalog name or hex key."),
    ] = None,
    level: Annotated[
        str | None,
        typer.Option("--level", help="Filter by log level."),
    ] = None,
) -> None:
    """List catalog operation logs.

    Examples:

        vrg catalog log list
        vrg catalog log list --catalog windows-server
        vrg catalog log list --level error
        vrg -o json catalog log list --query "[?level!='message']"

    Log levels: `message`, `warning`, `error`, `critical`. `--catalog`
    accepts a name or SHA-1 hex key. Timestamps are normalized to
    seconds for display.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if catalog is not None:
        catalog_key = resolve_nas_resource(
            vctx.client.catalogs,
            catalog,
            resource_type="catalog",
        )
        kwargs["catalog"] = catalog_key
    if level is not None:
        kwargs["level"] = level
    logs = vctx.client.catalog_logs.list(**kwargs)
    data = [_log_to_dict(entry) for entry in logs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    log: Annotated[str, typer.Argument(help="Log entry key.")],
) -> None:
    """Get a catalog log entry by key.

    Examples:

        vrg catalog log get 4217
        vrg -o json catalog log get 4217

    `log` must be a numeric key (found via `vrg catalog log list`).
    """
    vctx = get_context(ctx)
    key = int(log)
    item = vctx.client.catalog_logs.get(key=key)
    output_result(
        _log_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
