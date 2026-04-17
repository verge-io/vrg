"""Update log commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result

app = typer.Typer(
    name="log",
    help=(
        "View log entries emitted by the update subsystem.\n\n"
        "An *update log* is one row in `update_logs` — the audit trail for"
        " check/download/install/apply actions. Each entry has a `level`"
        " (audit/message/warning/error/critical), a free-text `text`,"
        " optionally an `object_name` identifying the package or source,"
        " and a `timestamp`. Entries are retained for up to 70 days and"
        " capped at 10,000 rows.\n\n"
        "Use `--level` to narrow by severity — `error` and `critical`"
        " surface failed downloads and failed applies. Use `-o json` for"
        " structured output. Useful fields to `--query`: `level`, `text`,"
        " `object_name`, `timestamp`, `user`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List recent update log entries\n"
        "    vrg update log list\n\n"
        "    # Show only errors and criticals\n"
        "    vrg update log list --level error\n"
        "    vrg update log list --level critical\n\n"
        "    # Pull the full log as JSON for further filtering\n"
        "    vrg -o json update log list\n\n"
        "    # Inspect one entry by key\n"
        "    vrg update log get 4821\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Timestamps are stored in microseconds on the wire; `vrg` converts"
        " them to seconds for display. Entries older than 70 days are"
        " expired automatically — archive externally if you need longer"
        " retention."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

UPDATE_LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef(
        "level",
        style_map={
            "error": "red",
            "warning": "yellow",
            "critical": "red bold",
            "audit": "cyan",
        },
    ),
    ColumnDef("text", header="Message"),
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("object_name", header="Object", wide_only=True),
    ColumnDef("user", wide_only=True),
]


def _log_to_dict(log: Any) -> dict[str, Any]:
    """Convert an UpdateLog SDK object to a dict for output."""
    # Timestamp is in microseconds in the SDK — convert to seconds for format_epoch
    ts = log.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 1e12:
        ts = ts / 1e6
    return {
        "$key": int(log.key),
        "level": log.get("level", ""),
        "text": log.get("text", ""),
        "timestamp": ts,
        "object_name": log.get("object_name", ""),
        "user": log.get("user", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            help="Filter by log level (audit/message/warning/error/critical).",
        ),
    ] = None,
) -> None:
    """List update logs."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if level is not None:
        kwargs["level"] = level
    logs = vctx.client.update_logs.list(**kwargs)
    data = [_log_to_dict(entry) for entry in logs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=UPDATE_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    log_key: Annotated[str, typer.Argument(help="Log entry key.")],
) -> None:
    """Get an update log entry by key."""
    vctx = get_context(ctx)
    key = int(log_key)
    item = vctx.client.update_logs.get(key=key)
    output_result(
        _log_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=UPDATE_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
