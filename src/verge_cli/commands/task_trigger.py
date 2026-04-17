"""Task schedule trigger management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import TASK_TRIGGER_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="trigger",
    help=(
        "Manage task schedule triggers — bindings that link a task to a"
        " schedule so it fires on a recurring (cron-style) cadence.\n\n"
        "A **schedule trigger** is the join row between a task (`vrg task`)"
        " and a schedule (`vrg task schedule`). Creating a trigger activates"
        " the task on that schedule's cadence; deleting the trigger stops"
        " recurrence without touching either side. Schedules are reusable:"
        " one 'nightly-2am' schedule can drive many tasks, each via its own"
        " trigger. This is the schedule-side counterpart to `vrg task event`"
        " (which binds tasks to runtime events like power-on or alarms).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List triggers on a task\n"
        "    vrg task trigger list nightly-snapshot\n\n"
        "    # List as JSON\n"
        "    vrg -o json task trigger list nightly-snapshot\n\n"
        "    # Attach a schedule to a task\n"
        "    vrg task trigger create nightly-snapshot \\\n"
        "        --schedule nightly-2am\n\n"
        "    # Fire a trigger manually (useful for testing)\n"
        "    vrg task trigger run 42\n\n"
        "    # Remove a trigger (task and schedule both remain)\n"
        "    vrg task trigger delete 42 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Triggers are identified only by numeric `$key` — there is no trigger"
        " name. Tasks and schedules accept name or key; ambiguous names exit"
        " with code 7.\n\n"
        "A trigger fires only when its schedule is enabled. Disabling the"
        " schedule (`vrg task schedule disable`) pauses every task bound to"
        " it; deleting a trigger removes just one binding."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _trigger_to_dict(trigger: Any) -> dict[str, Any]:
    """Convert a TaskScheduleTrigger SDK object to a dictionary for output."""
    return {
        "$key": int(trigger.key),
        "task_key": trigger.task_key,
        "task_display": trigger.task_display,
        "schedule_key": trigger.schedule_key,
        "schedule_display": trigger.schedule_display,
        "schedule_enabled": trigger.is_schedule_enabled,
        "schedule_repeat": trigger.schedule_repeat_every or "",
    }


@app.command("list")
@handle_errors()
def trigger_list(
    ctx: typer.Context,
    task: Annotated[str, typer.Argument(help="Task ID or name.")],
) -> None:
    """List schedule triggers for a task.

    **Examples:**

        vrg task trigger list nightly-snapshot

        vrg -o json task trigger list 1234
    """
    vctx = get_context(ctx)
    task_key = resolve_resource_id(vctx.client.tasks, task, "Task")
    triggers = vctx.client.task_schedule_triggers.list(task=task_key)
    output_result(
        [_trigger_to_dict(t) for t in triggers],
        columns=TASK_TRIGGER_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def trigger_create(
    ctx: typer.Context,
    task: Annotated[str, typer.Argument(help="Task ID or name.")],
    schedule: Annotated[
        str,
        typer.Option("--schedule", help="Schedule ID or name to link."),
    ],
) -> None:
    """Create a trigger linking a task to a schedule.

    **Examples:**

        vrg task trigger create nightly-snapshot --schedule nightly-2am

        vrg task trigger create 1234 --schedule 5
    """
    vctx = get_context(ctx)
    task_key = resolve_resource_id(vctx.client.tasks, task, "Task")
    schedule_key = resolve_resource_id(vctx.client.task_schedules, schedule, "TaskSchedule")
    trigger = vctx.client.task_schedule_triggers.create(task=task_key, schedule=schedule_key)
    output_success(f"Trigger created (key={int(trigger.key)}) linking task to schedule.")


@app.command("delete")
@handle_errors()
def trigger_delete(
    ctx: typer.Context,
    trigger_id: Annotated[int, typer.Argument(help="Trigger ID (numeric key).")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a schedule trigger.

    Removes the binding only; the task and the schedule remain.

    **Examples:**

        vrg task trigger delete 42

        vrg task trigger delete 42 --yes
    """
    vctx = get_context(ctx)
    if not confirm_action(f"Delete trigger {trigger_id}?", yes=yes):
        raise typer.Exit(0)
    vctx.client.task_schedule_triggers.delete(trigger_id)
    output_success(f"Trigger {trigger_id} deleted.")


@app.command("run")
@handle_errors()
def trigger_run(
    ctx: typer.Context,
    trigger_id: Annotated[int, typer.Argument(help="Trigger ID (numeric key).")],
) -> None:
    """Manually fire a schedule trigger.

    Runs the linked task immediately without waiting for the schedule's
    next occurrence. Useful for testing a newly created trigger.

    **Examples:**

        vrg task trigger run 42
    """
    vctx = get_context(ctx)
    vctx.client.task_schedule_triggers.trigger(trigger_id)
    output_success(f"Trigger {trigger_id} fired.")
