"""System log management commands."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_warning

app = typer.Typer(
    name="log",
    help=(
        "View the VergeOS event log.\n\n"
        "The event log is a centralized, append-only record of operational"
        " activity across the platform — VM lifecycle, node and cluster"
        " state changes, network operations, authentication events, task"
        " executions, and similar. It serves both as a real-time monitoring"
        " feed and as an audit trail. Entries carry a severity `level`"
        " (`critical`, `error`, `warning`, `audit`, `message`), an"
        " `object_type` (the resource category, e.g. `vm`, `vnet`, `node`,"
        " `tenant`, `user`, `system`, `task`), an `object_name`, the"
        " acting `user`, and a microsecond-precision `timestamp`.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `level`, `object_type`, `object_name`, `user`, `text`,"
        " `timestamp`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Recent log entries (newest first)\n"
        "    vrg log list\n\n"
        "    # Only error and critical entries\n"
        "    vrg log list --errors\n"
        "    vrg log list --level error\n\n"
        "    # Scope by object type or user\n"
        "    vrg log list --type vm\n"
        "    vrg log list --user admin\n\n"
        "    # Time-window filtering\n"
        "    vrg log list --since 2026-04-01\n"
        "    vrg log list --since 2026-04-15T08:00:00 --before 2026-04-15T18:00:00\n\n"
        "    # Free-text search across log messages\n"
        '    vrg log search "migration failed"\n'
        '    vrg log search "login" --type user --since 2026-04-01\n\n'
        "    # Fetch a single entry by key\n"
        "    vrg -o json log get 12345\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Logs are retained up to 25,000 entries or 31 days, whichever comes"
        " first — older entries are pruned automatically. Export via `-o"
        " json` to an external system if long-term retention is required.\n\n"
        "`--before` is only honored on the general listing path. When"
        " combined with `--errors`, `--level`, `--type`, or `--user` in"
        " isolation, the CLI routes to a specialized SDK method that does"
        " not accept `--before`, and the flag is ignored with a warning.\n\n"
        "Log entries are identified by numeric key, not by name. Log"
        " entries also emit events that the Task Engine can subscribe to"
        " — see `vrg task trigger` for event-driven automation."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef(
        "level",
        style_map={
            "critical": "red bold",
            "error": "red",
            "warning": "yellow",
            "audit": "cyan",
            "message": "dim",
        },
    ),
    ColumnDef("text", header="Message"),
    ColumnDef("object_type", header="Type"),
    ColumnDef("object_name", header="Object"),
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("user", wide_only=True),
]


def _log_to_dict(log: Any) -> dict[str, Any]:
    """Convert SDK Log object to output dict."""
    # Log timestamps are in microseconds — convert to seconds for format_epoch
    ts = log.timestamp_us
    if isinstance(ts, (int, float)) and ts > 1e12:
        ts = ts / 1e6
    return {
        "$key": int(log.key),
        "level": log.level,
        "text": log.text,
        "object_type": log.object_type_display,
        "object_name": log.object_name,
        "timestamp": ts,
        "user": log.user,
    }


def _parse_datetime(value: str) -> datetime:
    """Parse a datetime string (ISO 8601 or date-only)."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise typer.BadParameter(
        f"Invalid datetime format: '{value}'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option(
            "--filter",
            help="OData filter expression.",
        ),
    ] = None,
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            "-l",
            help="Filter by log level (critical, error, warning, message, audit).",
        ),
    ] = None,
    object_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by object type (vm, vnet, node, user, system, tenant, etc.).",
        ),
    ] = None,
    user: Annotated[
        str | None,
        typer.Option(
            "--user",
            help="Filter by user who performed the action.",
        ),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Show logs after this datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
        ),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(
            "--before",
            help="Show logs before this datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
        ),
    ] = None,
    errors: Annotated[
        bool,
        typer.Option(
            "--errors",
            help="Show only error and critical logs.",
        ),
    ] = False,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = 100,
) -> None:
    """List system log entries."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.logs.list(), _log_to_dict, LOG_COLUMNS)
        return
    vctx = get_context(ctx)

    since_dt = _parse_datetime(since) if since else None
    before_dt = _parse_datetime(before) if before else None

    # Warn if --before will be ignored by specialized routes
    if before_dt and (
        errors
        or (user and not level and not object_type)
        or (object_type and not level and not user)
        or (level and not user and not object_type)
    ):
        output_warning(
            "--before is not supported with --errors/--user/--object-type/--level filters and will be ignored.",
            quiet=vctx.quiet,
        )

    # Route to appropriate SDK method based on filters
    if errors:
        logs = vctx.client.logs.list_errors(limit=limit, since=since_dt)
    elif user and not level and not object_type:
        logs = vctx.client.logs.list_by_user(user=user, limit=limit, since=since_dt)
    elif object_type and not level and not user:
        logs = vctx.client.logs.list_by_object_type(
            object_type=object_type, limit=limit, since=since_dt
        )
    elif level and not user and not object_type:
        logs = vctx.client.logs.list_by_level(level=level, limit=limit, since=since_dt)
    else:
        logs = vctx.client.logs.list(
            filter=filter,
            level=level,
            object_type=object_type,
            user=user,
            since=since_dt,
            before=before_dt,
            limit=limit,
        )

    output_result(
        [_log_to_dict(entry) for entry in logs],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def get(
    ctx: typer.Context,
    key: Annotated[
        int,
        typer.Argument(help="Log entry key (numeric ID)."),
    ],
) -> None:
    """Get a log entry by key."""
    vctx = get_context(ctx)
    entry = vctx.client.logs.get(key=key)
    output_result(
        _log_to_dict(entry),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def search(
    ctx: typer.Context,
    text: Annotated[
        str,
        typer.Argument(help="Text to search for in log messages."),
    ],
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            "-l",
            help="Filter by log level.",
        ),
    ] = None,
    object_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by object type.",
        ),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Search logs after this datetime (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = 100,
) -> None:
    """Search log entries by text content."""
    vctx = get_context(ctx)

    since_dt = _parse_datetime(since) if since else None

    logs = vctx.client.logs.search(
        text=text,
        level=level,
        object_type=object_type,
        since=since_dt,
        limit=limit,
    )

    output_result(
        [_log_to_dict(entry) for entry in logs],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
