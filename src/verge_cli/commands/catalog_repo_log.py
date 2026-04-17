"""Catalog repository log commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="log",
    help=(
        "View catalog repository logs — refresh, sync, and connection"
        " activity.\n\n"
        "Repository logs record events from remote repository refreshes,"
        " connectivity checks, and recipe sync operations. Each entry has"
        " a **level** (`message`, `warning`, `error`, `critical`) and a"
        " timestamp. Useful for diagnosing failed refreshes against remote"
        " repositories.\n\n"
        "Use `-o json` for machine-readable output. Filter with `--repo`"
        " (name or key) and `--level`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg catalog repo log list\n"
        "    vrg catalog repo log list --repo MarketPlace\n"
        "    vrg catalog repo log list --level error\n"
        "    vrg -o json catalog repo log list\n\n"
        "---"
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

REPO_LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef(
        "level",
        style_map={"error": "red", "warning": "yellow", "critical": "red bold"},
    ),
    ColumnDef("text", header="Message"),
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("user", wide_only=True),
]


def _log_to_dict(log: Any) -> dict[str, Any]:
    """Convert a CatalogRepositoryLog SDK object to a dict for output."""
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
    repo: Annotated[
        str | None,
        typer.Option("--repo", help="Filter by repository name or key."),
    ] = None,
    level: Annotated[
        str | None,
        typer.Option("--level", help="Filter by log level (message/warning/error/critical)."),
    ] = None,
) -> None:
    """List catalog repository logs.

    Examples:

        vrg catalog repo log list
        vrg catalog repo log list --repo MarketPlace
        vrg catalog repo log list --level error
        vrg -o json catalog repo log list --query "[?level!='message']"

    Log levels: `message`, `warning`, `error`, `critical`. `--repo`
    accepts a name or integer key. Useful for diagnosing failed
    refreshes against remote repositories.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if repo is not None:
        repo_key = resolve_resource_id(
            vctx.client.catalog_repositories,
            repo,
            "Catalog repository",
        )
        kwargs["catalog_repository"] = repo_key
    if level is not None:
        kwargs["level"] = level
    logs = vctx.client.catalog_repository_logs.list(**kwargs)
    data = [_log_to_dict(entry) for entry in logs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=REPO_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    log_key: Annotated[str, typer.Argument(help="Log entry key.")],
) -> None:
    """Get a catalog repository log entry by key.

    Examples:

        vrg catalog repo log get 4217
        vrg -o json catalog repo log get 4217

    `log_key` must be a numeric key (found via `vrg catalog repo log
    list`).
    """
    vctx = get_context(ctx)
    key = int(log_key)
    item = vctx.client.catalog_repository_logs.get(key=key)
    output_result(
        _log_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=REPO_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
