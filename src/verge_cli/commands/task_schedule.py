"""Task schedule management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import click
import typer

from verge_cli.columns import SCHEDULE_UPCOMING_COLUMNS, TASK_SCHEDULE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="schedule",
    help=(
        "Manage task schedules — recurring or one-time triggers that fire"
        " tasks at specific times.\n\n"
        "A **schedule** defines *when* a task runs (the event counterpart is"
        " `vrg task event`). Schedules are reusable: a single schedule can be"
        " linked to many tasks via `vrg task trigger` so one 'nightly 2 AM'"
        " definition drives every nightly job. Configure frequency with"
        " `--repeat-every` (minute/hour/day/week/month/year/never) and"
        " `--repeat-iteration` (run every N intervals), then constrain by"
        " time-of-day window (`--start-time`/`--end-time`, seconds from"
        " midnight), date window (`--start-date`/`--end-date`), weekday"
        " (`--monday`…`--sunday`), or day-of-month"
        " (`first`/`last`/`15th`/`start_date`). Set `--repeat-every never`"
        " for a one-shot schedule.\n\n"
        "Use `vrg task schedule show <id>` to preview the next N upcoming"
        " execution times before enabling — cheap way to verify a cron-like"
        " pattern does what you expect.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List schedules\n"
        "    vrg task schedule list\n\n"
        "    # Only enabled daily schedules\n"
        "    vrg task schedule list --enabled --repeat-every day\n\n"
        "    # Get schedule details as JSON\n"
        "    vrg -o json task schedule get nightly-2am\n\n"
        "    # Create a daily 2 AM weekday-only schedule\n"
        "    vrg task schedule create --name nightly-2am \\\n"
        "        --repeat-every day --repeat-iteration 1 \\\n"
        "        --start-time 7200 --end-time 10800 \\\n"
        "        --no-saturday --no-sunday\n\n"
        "    # Create a monthly schedule that fires on the 1st\n"
        "    vrg task schedule create --name monthly-first \\\n"
        "        --repeat-every month --day-of-month first\n\n"
        "    # Preview the next 20 runs\n"
        "    vrg task schedule show nightly-2am\n\n"
        "    # Disable temporarily, then re-enable\n"
        "    vrg task schedule disable nightly-2am\n"
        "    vrg task schedule enable nightly-2am\n\n"
        "    # Delete a schedule\n"
        "    vrg task schedule delete nightly-2am --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Schedules are referenced by name or numeric key (`$key`). When a name"
        " matches multiple schedules, vrg prints all matches and exits with"
        " code 7 — use the key to disambiguate.\n\n"
        "`--start-time` and `--end-time` are integer seconds from midnight"
        " (0–86400), not clock strings. For 2:00 AM pass `7200`; for 5:00 PM"
        " pass `61200`. The schedule fires only inside this daily window.\n\n"
        "Creating a schedule does not run any task — it only defines timing."
        " Link it to a task with `vrg task trigger create <task> --schedule"
        " <schedule>` so the task fires on each occurrence."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _seconds_to_time(seconds: int) -> str:
    """Convert seconds from midnight to HH:MM format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def _schedule_to_dict(schedule: Any) -> dict[str, Any]:
    """Convert a TaskSchedule SDK object to a dictionary for output."""
    return {
        "$key": int(schedule.key),
        "name": schedule.name,
        "description": schedule.get("description", ""),
        "enabled": schedule.is_enabled,
        "repeat_every": schedule.get("repeat_every", ""),
        "repeat_display": schedule.repeat_every_display,
        "repeat_iteration": schedule.repeat_count,
        "start_date": schedule.get("start_date", ""),
        "end_date": schedule.get("end_date", ""),
        "start_time_of_day": schedule.get("start_time_of_day", 0),
        "start_time_display": _seconds_to_time(int(schedule.get("start_time_of_day", 0))),
        "end_time_of_day": schedule.get("end_time_of_day", 86400),
        "end_time_display": _seconds_to_time(int(schedule.get("end_time_of_day", 86400))),
        "day_of_month": schedule.get("day_of_month", ""),
        "active_days": ", ".join(schedule.active_days),
    }


def _upcoming_to_dict(entry: Any) -> dict[str, Any]:
    """Convert an upcoming execution entry to a dictionary for output."""
    if isinstance(entry, dict):
        return {"execution_time": str(entry.get("time", entry.get("execution_time", "")))}
    return {"execution_time": str(entry)}


@app.command("list")
@handle_errors()
def schedule_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled/disabled status."),
    ] = None,
    repeat_every: Annotated[
        str | None,
        typer.Option(
            "--repeat-every",
            help="Filter by repeat interval.",
            click_type=click.Choice(["minute", "hour", "day", "week", "month", "year", "never"]),
        ),
    ] = None,
) -> None:
    """List task schedules."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter:
        kwargs["filter"] = filter
    if enabled is not None:
        kwargs["enabled"] = enabled
    if repeat_every is not None:
        kwargs["repeat_every"] = repeat_every
    schedules = vctx.client.task_schedules.list(**kwargs)
    output_result(
        [_schedule_to_dict(s) for s in schedules],
        columns=TASK_SCHEDULE_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def schedule_get(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
) -> None:
    """Get a task schedule by ID or name."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    schedule = vctx.client.task_schedules.get(key)
    output_result(
        _schedule_to_dict(schedule),
        columns=TASK_SCHEDULE_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def schedule_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Schedule name.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Schedule description."),
    ] = None,
    disabled: Annotated[
        bool,
        typer.Option("--disabled", help="Create schedule in disabled state."),
    ] = False,
    repeat_every: Annotated[
        str,
        typer.Option(
            "--repeat-every",
            help="Repeat interval.",
            click_type=click.Choice(["minute", "hour", "day", "week", "month", "year", "never"]),
        ),
    ] = "hour",
    repeat_iteration: Annotated[
        int,
        typer.Option("--repeat-iteration", help="Run every N intervals."),
    ] = 1,
    start_date: Annotated[
        str | None,
        typer.Option("--start-date", help="Start date (YYYY-MM-DD)."),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option("--end-date", help="End date (YYYY-MM-DD)."),
    ] = None,
    start_time: Annotated[
        int,
        typer.Option("--start-time", help="Start time in seconds from midnight."),
    ] = 0,
    end_time: Annotated[
        int,
        typer.Option("--end-time", help="End time in seconds from midnight."),
    ] = 86400,
    day_of_month: Annotated[
        str,
        typer.Option(
            "--day-of-month",
            help="Day of month option.",
            click_type=click.Choice(["first", "last", "15th", "start_date"]),
        ),
    ] = "start_date",
    monday: Annotated[bool, typer.Option("--monday/--no-monday")] = True,
    tuesday: Annotated[bool, typer.Option("--tuesday/--no-tuesday")] = True,
    wednesday: Annotated[bool, typer.Option("--wednesday/--no-wednesday")] = True,
    thursday: Annotated[bool, typer.Option("--thursday/--no-thursday")] = True,
    friday: Annotated[bool, typer.Option("--friday/--no-friday")] = True,
    saturday: Annotated[bool, typer.Option("--saturday/--no-saturday")] = True,
    sunday: Annotated[bool, typer.Option("--sunday/--no-sunday")] = True,
) -> None:
    """Create a new task schedule."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "name": name,
        "enabled": not disabled,
        "repeat_every": repeat_every,
        "repeat_iteration": repeat_iteration,
        "start_time_of_day": start_time,
        "end_time_of_day": end_time,
        "day_of_month": day_of_month,
        "monday": monday,
        "tuesday": tuesday,
        "wednesday": wednesday,
        "thursday": thursday,
        "friday": friday,
        "saturday": saturday,
        "sunday": sunday,
    }
    if description is not None:
        kwargs["description"] = description
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    schedule = vctx.client.task_schedules.create(**kwargs)
    output_success(f"Schedule '{schedule.name}' created (key={int(schedule.key)}).")


@app.command("update")
@handle_errors()
def schedule_update(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New schedule name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled", help="Enable or disable the schedule."),
    ] = None,
    repeat_every: Annotated[
        str | None,
        typer.Option(
            "--repeat-every",
            help="Repeat interval.",
            click_type=click.Choice(["minute", "hour", "day", "week", "month", "year", "never"]),
        ),
    ] = None,
    repeat_iteration: Annotated[
        int | None,
        typer.Option("--repeat-iteration", help="Run every N intervals."),
    ] = None,
    start_date: Annotated[
        str | None,
        typer.Option("--start-date", help="Start date (YYYY-MM-DD)."),
    ] = None,
    end_date: Annotated[
        str | None,
        typer.Option("--end-date", help="End date (YYYY-MM-DD)."),
    ] = None,
    start_time: Annotated[
        int | None,
        typer.Option("--start-time", help="Start time in seconds from midnight."),
    ] = None,
    end_time: Annotated[
        int | None,
        typer.Option("--end-time", help="End time in seconds from midnight."),
    ] = None,
    day_of_month: Annotated[
        str | None,
        typer.Option(
            "--day-of-month",
            help="Day of month option.",
            click_type=click.Choice(["first", "last", "15th", "start_date"]),
        ),
    ] = None,
    monday: Annotated[bool | None, typer.Option("--monday/--no-monday")] = None,
    tuesday: Annotated[bool | None, typer.Option("--tuesday/--no-tuesday")] = None,
    wednesday: Annotated[bool | None, typer.Option("--wednesday/--no-wednesday")] = None,
    thursday: Annotated[bool | None, typer.Option("--thursday/--no-thursday")] = None,
    friday: Annotated[bool | None, typer.Option("--friday/--no-friday")] = None,
    saturday: Annotated[bool | None, typer.Option("--saturday/--no-saturday")] = None,
    sunday: Annotated[bool | None, typer.Option("--sunday/--no-sunday")] = None,
) -> None:
    """Update a task schedule."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if enabled is not None:
        kwargs["enabled"] = enabled
    if repeat_every is not None:
        kwargs["repeat_every"] = repeat_every
    if repeat_iteration is not None:
        kwargs["repeat_iteration"] = repeat_iteration
    if start_date is not None:
        kwargs["start_date"] = start_date
    if end_date is not None:
        kwargs["end_date"] = end_date
    if start_time is not None:
        kwargs["start_time_of_day"] = start_time
    if end_time is not None:
        kwargs["end_time_of_day"] = end_time
    if day_of_month is not None:
        kwargs["day_of_month"] = day_of_month
    if monday is not None:
        kwargs["monday"] = monday
    if tuesday is not None:
        kwargs["tuesday"] = tuesday
    if wednesday is not None:
        kwargs["wednesday"] = wednesday
    if thursday is not None:
        kwargs["thursday"] = thursday
    if friday is not None:
        kwargs["friday"] = friday
    if saturday is not None:
        kwargs["saturday"] = saturday
    if sunday is not None:
        kwargs["sunday"] = sunday
    vctx.client.task_schedules.update(key, **kwargs)
    output_success(f"Schedule '{identifier}' updated.")


@app.command("delete")
@handle_errors()
def schedule_delete(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a task schedule."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    if not confirm_action(f"Delete schedule '{identifier}'?", yes=yes):
        raise typer.Exit(0)
    vctx.client.task_schedules.delete(key)
    output_success(f"Schedule '{identifier}' deleted.")


@app.command("enable")
@handle_errors()
def schedule_enable(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
) -> None:
    """Enable a task schedule."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    vctx.client.task_schedules.enable(key)
    output_success(f"Schedule '{identifier}' enabled.")


@app.command("disable")
@handle_errors()
def schedule_disable(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
) -> None:
    """Disable a task schedule."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    vctx.client.task_schedules.disable(key)
    output_success(f"Schedule '{identifier}' disabled.")


@app.command("show")
@handle_errors()
def schedule_show(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Schedule ID or name.")],
    max_results: Annotated[
        int,
        typer.Option("--max-results", help="Maximum number of upcoming executions."),
    ] = 20,
    start_time: Annotated[
        str | None,
        typer.Option("--start-time", help="Start of time window (datetime)."),
    ] = None,
    end_time: Annotated[
        str | None,
        typer.Option("--end-time", help="End of time window (datetime)."),
    ] = None,
) -> None:
    """Show upcoming scheduled execution times."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.task_schedules, identifier, "TaskSchedule")
    kwargs: dict[str, Any] = {"max_results": max_results}
    if start_time is not None:
        kwargs["start_time"] = int(start_time)
    if end_time is not None:
        kwargs["end_time"] = int(end_time)
    upcoming = vctx.client.task_schedules.get_schedule(key, **kwargs)
    output_result(
        [_upcoming_to_dict(entry) for entry in upcoming],
        columns=SCHEDULE_UPCOMING_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
