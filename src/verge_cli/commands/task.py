"""Task management commands for Verge CLI."""

from __future__ import annotations

import json
from typing import Annotated, Any

import click
import typer

from verge_cli.columns import TASK_COLUMNS
from verge_cli.commands import task_event, task_schedule, task_script, task_trigger
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_error, output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="task",
    help=(
        "Manage tasks — VergeOS's built-in automation engine.\n\n"
        "A **task** is an automated operation that runs against a VergeOS"
        " resource (a VM, tenant, network, system, etc.). Tasks can be invoked"
        " manually, run on a recurring **schedule** (cron-like), or fire in"
        " response to system **events** (alarms raised, logs written, resources"
        " created/modified/deleted). Common actions include snapshot"
        " creation, power operations, notification delivery (email/webhook),"
        " and custom **script** execution.\n\n"
        "Every task has an `owner` (the target resource), a `table` (resource"
        " type, e.g., `vms`, `tenants`), and an `action` (e.g., `poweron`,"
        " `snapshot`). Task status is `Idle` or `Running`; a stuck `Running`"
        " task usually indicates an error — check task logs.\n\n"
        "Subresources have their own groups: `vrg task schedule` (recurring"
        " triggers), `vrg task trigger` (event-driven triggers), `vrg task"
        " event` (execution history), and `vrg task script` (reusable code"
        " blocks).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List recent tasks\n"
        "    vrg task list\n\n"
        "    # List only running tasks\n"
        "    vrg task list --running\n\n"
        "    # Filter by enabled status\n"
        "    vrg task list --enabled\n\n"
        "    # Get task details as JSON\n"
        "    vrg -o json task get nightly-snapshot\n\n"
        "    # Run a task immediately and wait for completion\n"
        "    vrg task run nightly-snapshot --wait\n\n"
        "    # Enable / disable a task\n"
        "    vrg task enable nightly-snapshot\n"
        "    vrg task disable nightly-snapshot\n\n"
        "    # Cancel a running task\n"
        "    vrg task cancel 1234\n\n"
        "    # List recurring schedules\n"
        "    vrg task schedule list\n\n"
        "    # List event triggers for a task\n"
        "    vrg task trigger list nightly-snapshot\n\n"
        "    # Inspect execution history\n"
        "    vrg task event list\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Tasks are referenced by name or numeric key (`$key`). When a name"
        " matches multiple tasks, vrg prints all matches and exits with code 7."
        " Use the numeric key to disambiguate.\n\n"
        "`vrg task run` dispatches execution and returns immediately unless"
        " `--wait` is passed. With `--wait`, vrg polls until the task returns"
        " to `Idle` or `--timeout` (default 300s) elapses; a non-zero exit code"
        " reflects task failure.\n\n"
        "A task's behavior is defined by its `action` plus any settings passed"
        " via `--settings-json` (on create/update) or `--params-json` (on"
        " run). `delete_after_run` is useful for one-shot maintenance tasks."
        " To see configured recurring work, use `vrg task schedule list`; for"
        " event-driven automation, use `vrg task trigger list`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Register sub-command groups
app.add_typer(task_event.app, name="event")
app.add_typer(task_schedule.app, name="schedule")
app.add_typer(task_script.app, name="script")
app.add_typer(task_trigger.app, name="trigger")


def _task_to_dict(task: Any) -> dict[str, Any]:
    """Convert a Task SDK object to a dictionary for output."""
    return {
        "$key": int(task.key),
        "name": task.name,
        "description": task.get("description", ""),
        "status": task.status,
        "enabled": task.is_enabled,
        "action": task.get("action", ""),
        "action_display": task.get("action_display", ""),
        "table": task.get("table", ""),
        "owner": task.get("owner"),
        "owner_display": task.owner_display,
        "creator_display": task.creator_display,
        "last_run": task.get("last_run"),
        "delete_after_run": task.is_delete_after_run,
        "system_created": task.is_system_created,
        "progress": task.progress,
        "error": task.get("error", ""),
        "triggers_count": task.trigger_count,
        "events_count": task.event_count,
    }


@app.command("list")
@handle_errors()
def task_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    running: Annotated[
        bool,
        typer.Option("--running", help="Show only running tasks."),
    ] = False,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled/disabled status."),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by status.",
            click_type=click.Choice(["idle", "running"]),
        ),
    ] = None,
) -> None:
    """List tasks."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.tasks.list(), _task_to_dict, TASK_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter:
        kwargs["filter"] = filter
    if running:
        kwargs["running"] = True
    if enabled is not None:
        kwargs["enabled"] = enabled
    if status:
        kwargs["status"] = status
    tasks = vctx.client.tasks.list(**kwargs)
    output_result(
        [_task_to_dict(t) for t in tasks],
        columns=TASK_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def task_get(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
) -> None:
    """Get a task by ID or name."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    task = vctx.client.tasks.get(key)
    output_result(
        _task_to_dict(task),
        columns=TASK_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def task_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Task name.")],
    owner: Annotated[int, typer.Option("--owner", help="Owner resource key.")],
    action: Annotated[
        str, typer.Option("--action", help="Action to perform (e.g. poweron, snapshot).")
    ],
    table: Annotated[
        str,
        typer.Option("--table", help="Owner resource type (e.g. vms, tenants)."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Task description."),
    ] = None,
    disabled: Annotated[
        bool,
        typer.Option("--disabled", help="Create task in disabled state."),
    ] = False,
    delete_after_run: Annotated[
        bool,
        typer.Option("--delete-after-run", help="Delete task after execution."),
    ] = False,
    settings_json: Annotated[
        str | None,
        typer.Option("--settings-json", help="Task settings as JSON string."),
    ] = None,
) -> None:
    """Create a new task."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "name": name,
        "owner": owner,
        "action": action,
        "table": table,
        "enabled": not disabled,
        "delete_after_run": delete_after_run,
    }
    if description is not None:
        kwargs["description"] = description
    if settings_json is not None:
        try:
            kwargs["settings_args"] = json.loads(settings_json)
        except json.JSONDecodeError as exc:
            output_error(f"Invalid JSON for --settings-json: {exc}")
            raise typer.Exit(2) from None
    task = vctx.client.tasks.create(**kwargs)
    output_success(f"Task '{task.name}' created (key={int(task.key)}).", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def task_update(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New task name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled", help="Enable or disable the task."),
    ] = None,
    delete_after_run: Annotated[
        bool | None,
        typer.Option("--delete-after-run", help="Delete task after execution."),
    ] = None,
    settings_json: Annotated[
        str | None,
        typer.Option("--settings-json", help="Task settings as JSON string."),
    ] = None,
) -> None:
    """Update a task."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if enabled is not None:
        kwargs["enabled"] = enabled
    if delete_after_run is not None:
        kwargs["delete_after_run"] = delete_after_run
    if settings_json is not None:
        try:
            kwargs["settings_args"] = json.loads(settings_json)
        except json.JSONDecodeError as exc:
            output_error(f"Invalid JSON for --settings-json: {exc}")
            raise typer.Exit(2) from None
    vctx.client.tasks.update(key, **kwargs)
    output_success(f"Task '{identifier}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def task_delete(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a task."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    if not confirm_action(f"Delete task '{identifier}'?", yes=yes):
        raise typer.Exit(0)
    vctx.client.tasks.delete(key)
    output_success(f"Task '{identifier}' deleted.", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def task_enable(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
) -> None:
    """Enable a task."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    vctx.client.tasks.enable(key)
    output_success(f"Task '{identifier}' enabled.", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def task_disable(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
) -> None:
    """Disable a task."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    vctx.client.tasks.disable(key)
    output_success(f"Task '{identifier}' disabled.", quiet=vctx.quiet)


@app.command("run")
@handle_errors()
def task_run(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for task completion."),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Wait timeout in seconds (only with --wait)."),
    ] = 300,
    params_json: Annotated[
        str | None,
        typer.Option("--params-json", help="Execution parameters as JSON string."),
    ] = None,
) -> None:
    """Execute a task immediately."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    params: dict[str, Any] = {}
    if params_json is not None:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError as exc:
            output_error(f"Invalid JSON for --params-json: {exc}")
            raise typer.Exit(2) from None
    vctx.client.tasks.execute(key, **params)
    if wait:
        task = vctx.client.tasks.wait(key, timeout=timeout, raise_on_error=True)
        output_success(f"Task '{identifier}' completed (status={task.status}).", quiet=vctx.quiet)
    else:
        output_success(f"Task '{identifier}' started.", quiet=vctx.quiet)


@app.command("cancel")
@handle_errors()
def task_cancel(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Task ID or name.")],
) -> None:
    """Cancel a running task."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tasks, identifier, "Task")
    vctx.client.tasks.cancel(key)
    output_success(f"Task '{identifier}' cancelled.", quiet=vctx.quiet)
