"""Task event management commands for Verge CLI."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from verge_cli.columns import TASK_EVENT_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="event",
    help=(
        "Manage task events — event-driven triggers that fire tasks when"
        " something happens in VergeOS.\n\n"
        "A **task event** binds a task (`--task`) to an event (`--event`) on a"
        " specific table (`--table`, e.g., `vms`, `alarms`, `users`). When the"
        " event fires on a matching row the linked task executes, with an"
        " optional filter (`--filters-json`) narrowing which rows qualify and an"
        " optional `--context-json` payload passed to the task. This is the"
        " event side of the task engine; for recurring (cron-style) execution"
        " see `vrg task schedule` and `vrg task trigger`.\n\n"
        "Use events for reactions like: power on a VM when a user logs in, send"
        " a webhook when a sync fails, create a snapshot when an alarm raises,"
        " or run cleanup when a resource is deleted.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all task events\n"
        "    vrg task event list\n\n"
        "    # Filter by source table and event type\n"
        "    vrg task event list --table vms --event powered_on\n\n"
        "    # List events bound to a specific task\n"
        "    vrg task event list --task nightly-snapshot\n\n"
        "    # Get event details as JSON\n"
        "    vrg -o json task event get 42\n\n"
        "    # Create an event: fire 'alert-ops' when an alarm is raised\n"
        "    vrg task event create --task alert-ops --table alarms \\\n"
        "        --event raised --event-name 'Alarm raised'\n\n"
        "    # Attach a filter (only fire for critical severity)\n"
        "    vrg task event create --task alert-ops --table alarms \\\n"
        "        --event raised \\\n"
        '        --filters-json \'{"severity": "critical"}\'\n\n'
        "    # Manually fire an event for testing\n"
        "    vrg task event trigger 42\n\n"
        "    # Delete an event binding\n"
        "    vrg task event delete 42 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Task events reference tasks by name or key; ambiguous names exit with"
        " code 7. Events themselves are referenced only by numeric `$key`.\n\n"
        "Available event names depend on the source `--table` — VergeOS tables"
        " declare their own named events (e.g., `vms` exposes `powered_on`,"
        " `powered_off`; `alarms` exposes `raised`, `resolved`). Check the"
        " table's schema or existing events (`vrg task event list --table"
        " <table>`) to see what's available.\n\n"
        "`--filters-json` is a JSON object matched against the source row; only"
        " matching rows trigger the task. `--context-json` (on create/update)"
        " sets a default context merged into every firing; `--context-json` on"
        " `trigger` overrides it for a single manual fire."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _event_to_dict(event: Any) -> dict[str, Any]:
    """Convert a TaskEvent SDK object to a dictionary for output."""
    return {
        "$key": int(event.key),
        "event": event.event_type or "",
        "event_name": event.event_name_display or "",
        "owner_key": event.owner_key,
        "owner_display": event.get("owner_display", ""),
        "table": event.owner_table or "",
        "task_key": event.task_key,
        "task_display": event.task_display,
        "filters": event.event_filters,
        "context": event.event_context,
    }


@app.command("list")
@handle_errors()
def event_list(
    ctx: typer.Context,
    task: Annotated[
        str | None,
        typer.Option("--task", help="Filter by task (name or key)."),
    ] = None,
    table: Annotated[
        str | None,
        typer.Option("--table", help="Filter by resource table (e.g. vms, users)."),
    ] = None,
    event: Annotated[
        str | None,
        typer.Option("--event", help="Filter by event type (e.g. poweron, login)."),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
) -> None:
    """List task events.

    **Examples:**

        vrg task event list

        vrg task event list --table vms --event powered_on

        vrg task event list --task nightly-snapshot

        vrg -o json task event list
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if task is not None:
        task_key = resolve_resource_id(vctx.client.tasks, task, "Task")
        kwargs["task"] = task_key
    if table is not None:
        kwargs["table"] = table
    if event is not None:
        kwargs["event"] = event
    if filter is not None:
        kwargs["filter"] = filter
    events = vctx.client.task_events.list(**kwargs)
    output_result(
        [_event_to_dict(e) for e in events],
        columns=TASK_EVENT_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def event_get(
    ctx: typer.Context,
    event_id: Annotated[int, typer.Argument(help="Event key (numeric).")],
) -> None:
    """Get a task event by key.

    **Examples:**

        vrg task event get 42

        vrg -o json task event get 42
    """
    vctx = get_context(ctx)
    event = vctx.client.task_events.get(event_id)
    output_result(
        _event_to_dict(event),
        columns=TASK_EVENT_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def event_create(
    ctx: typer.Context,
    task: Annotated[str, typer.Option("--task", help="Task to fire (name or key).")],
    event: Annotated[str, typer.Option("--event", help="Event identifier (e.g. lowered, login).")],
    table: Annotated[
        str,
        typer.Option("--table", help="Event source table (e.g. alarms, vms)."),
    ],
    event_name: Annotated[
        str | None,
        typer.Option("--event-name", help="Human-readable event name."),
    ] = None,
    filters_json: Annotated[
        str | None,
        typer.Option("--filters-json", help="Event filters as JSON string."),
    ] = None,
    context_json: Annotated[
        str | None,
        typer.Option("--context-json", help="Event context as JSON string."),
    ] = None,
) -> None:
    """Create a task event.

    **Examples:**

        vrg task event create --task alert-ops --table alarms \\
            --event raised --event-name 'Alarm raised'

        vrg task event create --task alert-ops --table alarms \\
            --event raised \\
            --filters-json '{"severity": "critical"}'
    """
    vctx = get_context(ctx)
    task_key = resolve_resource_id(vctx.client.tasks, task, "Task")
    kwargs: dict[str, Any] = {
        "task": task_key,
        "event": event,
        "table": table,
    }
    if event_name is not None:
        kwargs["event_name"] = event_name
    if filters_json is not None:
        kwargs["table_event_filters"] = json.loads(filters_json)
    if context_json is not None:
        kwargs["context"] = json.loads(context_json)
    result = vctx.client.task_events.create(**kwargs)
    output_success(f"Task event created (key={int(result.key)}).")


@app.command("update")
@handle_errors()
def event_update(
    ctx: typer.Context,
    event_id: Annotated[int, typer.Argument(help="Event key (numeric).")],
    filters_json: Annotated[
        str | None,
        typer.Option("--filters-json", help="Updated event filters as JSON string."),
    ] = None,
    context_json: Annotated[
        str | None,
        typer.Option("--context-json", help="Updated event context as JSON string."),
    ] = None,
) -> None:
    """Update a task event.

    **Examples:**

        vrg task event update 42 --filters-json '{"severity": "critical"}'

        vrg task event update 42 --context-json '{"notify": true}'
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filters_json is not None:
        kwargs["table_event_filters"] = json.loads(filters_json)
    if context_json is not None:
        kwargs["context"] = json.loads(context_json)
    vctx.client.task_events.update(event_id, **kwargs)
    output_success(f"Task event {event_id} updated.")


@app.command("delete")
@handle_errors()
def event_delete(
    ctx: typer.Context,
    event_id: Annotated[int, typer.Argument(help="Event key (numeric).")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a task event.

    **Examples:**

        vrg task event delete 42

        vrg task event delete 42 --yes
    """
    vctx = get_context(ctx)
    if not confirm_action(f"Delete task event {event_id}?", yes=yes):
        raise typer.Exit(0)
    vctx.client.task_events.delete(event_id)
    output_success(f"Task event {event_id} deleted.")


@app.command("trigger")
@handle_errors()
def event_trigger(
    ctx: typer.Context,
    event_id: Annotated[int, typer.Argument(help="Event key (numeric).")],
    context_json: Annotated[
        str | None,
        typer.Option("--context-json", help="Context data as JSON string."),
    ] = None,
) -> None:
    """Manually trigger a task event.

    Fires the linked task immediately, bypassing the normal event
    condition. Useful for testing a newly created event binding.

    **Examples:**

        vrg task event trigger 42

        vrg task event trigger 42 --context-json '{"test": true}'
    """
    vctx = get_context(ctx)
    context: dict[str, Any] | None = None
    if context_json is not None:
        context = json.loads(context_json)
    vctx.client.task_events.trigger(event_id, context=context)
    output_success(f"Task event {event_id} triggered.")
