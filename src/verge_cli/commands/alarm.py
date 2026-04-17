"""Alarm management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn, format_epoch
from verge_cli.commands import alarm_history
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success

app = typer.Typer(
    name="alarm",
    help=(
        "View and manage VergeOS alarms.\n\n"
        "Alarms are real-time alerts raised automatically when a monitored"
        " resource enters an abnormal state — hardware failures, missing or"
        " vulnerable configuration, security concerns, capacity thresholds,"
        " sync failures, and similar conditions. They are not created or"
        " deleted manually; the platform raises them when a condition trips"
        " and lowers them when the condition clears. Each alarm is bound to"
        " an `owner` resource (`VM`, `Network`, `Node`, `Tenant`, `User`,"
        " `System`, or `CloudSnapshot`) and has a severity `level`"
        " (`critical`, `error`, `warning`, `message`).\n\n"
        "Active alarms are listed here. Use `vrg alarm history` for the"
        " archive of resolved/lowered alarms. Use `-o json` for structured"
        " output. Useful fields to `--query`: `level`, `alarm_type`,"
        " `status`, `owner_type`, `owner_name`, `is_resolvable`,"
        " `is_snoozed`, `created_at`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List active alarms\n"
        "    vrg alarm list\n\n"
        "    # Only critical or error-level alarms\n"
        "    vrg alarm list --level critical\n"
        "    vrg alarm list --level error\n\n"
        "    # Alarms against a specific owner type\n"
        "    vrg alarm list --owner-type Node\n"
        "    vrg alarm list --owner-type VM\n\n"
        "    # Include snoozed alarms (hidden by default)\n"
        "    vrg alarm list --include-snoozed\n\n"
        "    # Counts by severity and state\n"
        "    vrg alarm summary\n\n"
        "    # Inspect one alarm by key\n"
        "    vrg -o json alarm get 412\n\n"
        "    # Snooze for 4 hours, then unsnooze\n"
        "    vrg alarm snooze 412 --hours 4\n"
        "    vrg alarm unsnooze 412\n\n"
        "    # Run the alarm's built-in resolve action (if resolvable)\n"
        "    vrg alarm resolve 412\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Snoozing is suppression, not acknowledgment — the alarm reappears"
        " in the active view when the snooze timestamp passes. Default"
        " snooze is 24 hours; alarm types may cap the duration and repeat"
        " count.\n\n"
        "Only alarms with `is_resolvable = true` accept `resolve` — it"
        " triggers the alarm type's built-in corrective action (e.g."
        " restart a VM after a config change, apply pending firewall"
        " rules). Non-resolvable alarms clear automatically once the"
        " underlying condition is addressed.\n\n"
        "Alarms are identified by numeric key, not by name. Active alarms"
        " live in `/v4/alarms`; archived alarms live in `/v4/alarm_archives`"
        " (capped at 100,000 records). Use `vrg doctor` for a quick health"
        " audit that includes active alarm state."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Register sub-commands
app.add_typer(alarm_history.app, name="history")

ALARM_COLUMNS: list[ColumnDef] = [
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
    ColumnDef("owner_type", header="Owner Type"),
    ColumnDef("owner_name", header="Owner"),
    ColumnDef("created_at", header="Created", format_fn=format_epoch),
    # wide-only
    ColumnDef("alarm_id", header="Alarm ID", wide_only=True),
    ColumnDef("description", wide_only=True),
    ColumnDef("is_snoozed", header="Snoozed", format_fn=format_bool_yn, wide_only=True),
    ColumnDef("is_resolvable", header="Resolvable", format_fn=format_bool_yn, wide_only=True),
]

ALARM_SUMMARY_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        "level",
        style_map={
            "critical": "red bold",
            "error": "red",
            "warning": "yellow",
            "message": "dim",
            "active": "green",
            "snoozed": "yellow",
            "resolvable": "cyan",
            "total": "bold",
        },
    ),
    ColumnDef("count"),
]


def _alarm_to_dict(alarm: Any) -> dict[str, Any]:
    """Convert SDK Alarm object to output dict."""
    return {
        "$key": int(alarm.key),
        "level": alarm.level,
        "alarm_type": alarm.alarm_type,
        "alarm_id": alarm.alarm_id,
        "status": alarm.status,
        "description": alarm.description,
        "owner_type": alarm.owner_type_display,
        "owner_name": alarm.owner_name,
        "is_resolvable": alarm.is_resolvable,
        "resolve_text": alarm.resolve_text,
        "is_snoozed": alarm.is_snoozed,
        "snoozed_by": alarm.snoozed_by,
        "created_at": alarm.created_at.timestamp() if alarm.created_at else None,
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
            help="Filter by alarm level (critical, error, warning, message).",
        ),
    ] = None,
    owner_type: Annotated[
        str | None,
        typer.Option(
            "--owner-type",
            help="Filter by owner type (VM, Network, Node, Tenant, User, System, CloudSnapshot).",
        ),
    ] = None,
    include_snoozed: Annotated[
        bool,
        typer.Option(
            "--include-snoozed",
            help="Include snoozed alarms (hidden by default).",
        ),
    ] = False,
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
    """List active alarms."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.alarms.list(), _alarm_to_dict, ALARM_COLUMNS)
        return
    vctx = get_context(ctx)

    # Route to the appropriate SDK method based on filters
    if level == "critical":
        alarms = vctx.client.alarms.list_critical(include_snoozed=include_snoozed, limit=limit)
    elif level == "error":
        alarms = vctx.client.alarms.list_errors(include_snoozed=include_snoozed, limit=limit)
    elif level == "warning":
        alarms = vctx.client.alarms.list_warnings(include_snoozed=include_snoozed, limit=limit)
    elif owner_type:
        alarms = vctx.client.alarms.list_by_owner_type(
            owner_type=owner_type,
            include_snoozed=include_snoozed,
            limit=limit,
        )
    else:
        alarms = vctx.client.alarms.list(
            filter=filter,
            level=level,
            include_snoozed=include_snoozed,
            limit=limit,
        )

    output_result(
        [_alarm_to_dict(a) for a in alarms],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALARM_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def get(
    ctx: typer.Context,
    alarm: Annotated[
        int,
        typer.Argument(help="Alarm key (numeric ID)."),
    ],
) -> None:
    """Get alarm details by key."""
    vctx = get_context(ctx)
    item = vctx.client.alarms.get(key=alarm)
    output_result(
        _alarm_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALARM_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def snooze(
    ctx: typer.Context,
    alarm: Annotated[
        int,
        typer.Argument(help="Alarm key (numeric ID)."),
    ],
    hours: Annotated[
        int,
        typer.Option(
            "--hours",
            "-h",
            help="Number of hours to snooze (default: 24, max: 8760).",
        ),
    ] = 24,
) -> None:
    """Snooze an alarm for a specified duration."""
    vctx = get_context(ctx)
    vctx.client.alarms.snooze(alarm, hours=hours)
    output_success(
        f"Alarm {alarm} snoozed for {hours} hour(s).",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def unsnooze(
    ctx: typer.Context,
    alarm: Annotated[
        int,
        typer.Argument(help="Alarm key (numeric ID)."),
    ],
) -> None:
    """Remove snooze from an alarm."""
    vctx = get_context(ctx)
    vctx.client.alarms.unsnooze(alarm)
    output_success(
        f"Alarm {alarm} unsnoozed.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def resolve(
    ctx: typer.Context,
    alarm: Annotated[
        int,
        typer.Argument(help="Alarm key (numeric ID)."),
    ],
) -> None:
    """Resolve a resolvable alarm."""
    vctx = get_context(ctx)
    vctx.client.alarms.resolve(alarm)
    output_success(
        f"Alarm {alarm} resolved.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def summary(
    ctx: typer.Context,
) -> None:
    """Show alarm summary with counts by level."""
    vctx = get_context(ctx)
    data = vctx.client.alarms.get_summary()

    # Build summary rows for table output
    rows = [
        {"level": "critical", "count": data.get("critical", 0)},
        {"level": "error", "count": data.get("error", 0)},
        {"level": "warning", "count": data.get("warning", 0)},
        {"level": "message", "count": data.get("message", 0)},
        {"level": "active", "count": data.get("active", 0)},
        {"level": "snoozed", "count": data.get("snoozed", 0)},
        {"level": "resolvable", "count": data.get("resolvable", 0)},
        {"level": "total", "count": data.get("total", 0)},
    ]

    output_result(
        rows,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=ALARM_SUMMARY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
