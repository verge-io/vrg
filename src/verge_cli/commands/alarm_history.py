"""Alarm history commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result

app = typer.Typer(
    name="history",
    help=(
        "Browse the archive of resolved/lowered alarms.\n\n"
        "When an alarm is lowered — either because the underlying condition"
        " cleared or because an operator ran a resolve action — the record"
        " moves from active alarms into the alarm archive. History entries"
        " preserve the original `owner`, `alarm_type`, `level`, `status`,"
        " and `alarm_id`, plus `raised_at` and `lowered_at` timestamps and"
        " the `archived_by` actor. The archive is capped at 100,000"
        " records.\n\n"
        "This is the surface for MTTR analysis and recurring-issue"
        " identification — compare `raised_at` and `lowered_at` to measure"
        " time-to-resolution, and group by `alarm_type` to spot chronic"
        " conditions. Use `-o json` for structured output. Useful fields"
        " to `--query`: `level`, `alarm_type`, `status`, `owner`,"
        " `raised_at`, `lowered_at`, `archived_by`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Recent alarm history\n"
        "    vrg alarm history list\n\n"
        "    # Filter by severity\n"
        "    vrg alarm history list --level critical\n"
        "    vrg alarm history list --level warning\n\n"
        "    # OData filter (see the VergeOS API reference)\n"
        "    vrg alarm history list \\\n"
        "        --filter \"alarm_type eq 'disk_full'\"\n\n"
        "    # Cap result size for quick scans\n"
        "    vrg alarm history list --limit 50\n\n"
        "    # Structured output for downstream processing\n"
        "    vrg -o json alarm history list\n\n"
        "    # Inspect a single archived entry\n"
        "    vrg alarm history get 1842\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "History entries are identified by numeric key, not by name. The"
        " `$key` of a history entry is distinct from the `$key` of the"
        " original active alarm — use `alarm_id` (the 8-character instance"
        " identifier) to correlate an archived entry back to the event"
        " that raised it.\n\n"
        "The archive is automatically trimmed at 100,000 records. Pull"
        " history as JSON and store it externally if you need longer"
        " retention for audit or capacity planning."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

ALARM_HISTORY_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef(
        "level",
        style_map={
            "critical": "red bold",
            "error": "red",
            "warning": "yellow",
            "message": "dim",
        },
    ),
    ColumnDef("alarm_type", header="Type"),
    ColumnDef("status"),
    ColumnDef("owner"),
    ColumnDef("raised_at", header="Raised", format_fn=format_epoch),
    ColumnDef("lowered_at", header="Lowered", format_fn=format_epoch),
    ColumnDef("archived_by", header="Archived By", wide_only=True),
    ColumnDef("alarm_id", header="Alarm ID", wide_only=True),
]


def _history_to_dict(entry: Any) -> dict[str, Any]:
    """Convert SDK AlarmHistory object to output dict."""
    return {
        "$key": int(entry.key),
        "level": entry.level,
        "alarm_type": entry.alarm_type,
        "alarm_id": entry.alarm_id,
        "status": entry.status,
        "owner": entry.owner,
        "archived_by": entry.archived_by,
        "raised_at": entry.raised_at.timestamp() if entry.raised_at else None,
        "lowered_at": entry.lowered_at.timestamp() if entry.lowered_at else None,
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            "-l",
            help="Filter by alarm level.",
        ),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option(
            "--filter",
            help="OData filter expression.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = None,
) -> None:
    """List alarm history (resolved/lowered alarms)."""
    vctx = get_context(ctx)
    entries = vctx.client.alarms.list_history(
        filter=filter,
        level=level,
        limit=limit,
    )
    output_result(
        [_history_to_dict(e) for e in entries],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALARM_HISTORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def get(
    ctx: typer.Context,
    key: Annotated[
        int,
        typer.Argument(help="Alarm history key (numeric ID)."),
    ],
) -> None:
    """Get alarm history entry by key."""
    vctx = get_context(ctx)
    entry = vctx.client.alarms.get_history(key)
    output_result(
        _history_to_dict(entry),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALARM_HISTORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
