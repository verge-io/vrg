"""Site sync schedule management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SITE_SYNC_SCHEDULE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="schedule",
    help=(
        "Manage **site sync schedules** — the link between an outgoing"
        " sync and a snapshot profile period.\n\n"
        "A schedule ties one snapshot profile period (e.g. the hourly"
        " entry of a profile) to one outgoing sync. When the period"
        " fires on the source, the resulting cloud snapshot is"
        " automatically enqueued on the matching outgoing sync and"
        " transferred to the remote site. This is how recurring,"
        " automated offsite replication is driven — without a schedule,"
        " an outgoing sync only transfers snapshots added manually via"
        " the queue.\n\n"
        "Key fields when creating a schedule:\n\n"
        "- `sync-key`: outgoing sync that will carry the transfers.\n"
        "- `profile-period-key`: snapshot profile period that fires the"
        " source snapshot (the profile/period must already exist).\n"
        "- `retention`: remote retention in **seconds**; independent of"
        " the source profile's retention.\n"
        "- `priority`: queue priority ordering (lower value = higher"
        " priority) when multiple periods feed the same sync.\n"
        "- `do-not-expire`: hold the source snapshot until the remote"
        " transfer completes; set this when local retention is shorter"
        " than the time a transfer can take, otherwise the queue item"
        " can end up in `Skip Retention`.\n"
        "- `destination-prefix`: prefix applied to the snapshot name on"
        " the destination side (default `remote`) to avoid collisions"
        " with local snapshots.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all schedules\n"
        "    vrg site sync schedule list\n\n"
        "    # Filter schedules to one outgoing sync\n"
        "    vrg site sync schedule list --sync production-sync\n\n"
        "    # Full details for scripting / agents\n"
        "    vrg -o json site sync schedule get 42\n\n"
        "    # Attach the hourly profile period to a sync, 7-day remote\n"
        "    # retention, holding source snapshots until transfer completes\n"
        "    vrg site sync schedule create \\\n"
        "        --sync-key 3 --profile-period-key 11 \\\n"
        "        --retention 604800 --do-not-expire\n\n"
        "    # Remove a schedule (stops future auto-enqueue for that period)\n"
        "    vrg site sync schedule delete 42 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Schedules apply to **outgoing** syncs only; incoming syncs"
        " receive whatever the source pushes and guard against total"
        " expiry with `min_snapshots` on the destination. Deleting a"
        " schedule does not remove snapshots already on the remote — it"
        " only stops new fires of that profile period from enqueuing."
        " `sync-key` and `profile-period-key` are numeric keys: look them"
        " up with `vrg site sync outgoing list` and `vrg snapshot profile"
        " period list`. Use `-o json` for machine-readable output; useful"
        " `--query` fields include `sync_name`, `profile_period_name`,"
        " `retention`, `priority`, `do_not_expire`, and"
        " `destination_prefix`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _schedule_to_dict(schedule: Any) -> dict[str, Any]:
    """Convert a SiteSyncSchedule SDK object to a dict for output."""
    return {
        "$key": schedule.key,
        "sync_key": schedule.get("sync_key"),
        "sync_name": schedule.get("sync_name", ""),
        "profile_period_key": schedule.get("profile_period_key"),
        "profile_period_name": schedule.get("profile_period_name", ""),
        "retention": schedule.get("retention"),
        "priority": schedule.get("priority"),
        "do_not_expire": schedule.get("do_not_expire", False),
        "destination_prefix": schedule.get("destination_prefix", "remote"),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    sync: Annotated[
        str | None,
        typer.Option("--sync", "-s", help="Filter by sync key"),
    ] = None,
) -> None:
    """List site sync schedules.

    Examples:

        vrg site sync schedule list
        vrg site sync schedule list --sync production-sync
        vrg -o json site sync schedule list | jq '.[] | select(.do_not_expire)'

    Useful `--query` fields include `sync_name`, `profile_period_name`,
    `retention`, `priority`, `do_not_expire`, and `destination_prefix`.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}

    if sync is not None:
        if sync.isdigit():
            kwargs["sync_key"] = int(sync)
        else:
            kwargs["sync_name"] = sync

    schedules = vctx.client.site_sync_schedules.list(**kwargs)
    data = [_schedule_to_dict(s) for s in schedules]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SITE_SYNC_SCHEDULE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    schedule_id: Annotated[int, typer.Argument(help="Schedule key")],
) -> None:
    """Get details of a site sync schedule.

    Examples:

        vrg site sync schedule get 42
        vrg -o json site sync schedule get 42 \\
            --query "{sync: sync_name, period: profile_period_name, retention: retention}"

    Schedules are identified only by numeric key — look them up via
    `vrg site sync schedule list`.
    """
    vctx = get_context(ctx)
    schedule = vctx.client.site_sync_schedules.get(schedule_id)
    output_result(
        _schedule_to_dict(schedule),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    sync_key: Annotated[int, typer.Option("--sync-key", help="Sync key to schedule")],
    profile_period_key: Annotated[
        int, typer.Option("--profile-period-key", help="Snapshot profile period key")
    ],
    retention: Annotated[int, typer.Option("--retention", help="Retention in seconds")],
    priority: Annotated[int | None, typer.Option("--priority", help="Schedule priority")] = None,
    do_not_expire: Annotated[
        bool, typer.Option("--do-not-expire", help="Never expire synced snapshots")
    ] = False,
    destination_prefix: Annotated[
        str, typer.Option("--destination-prefix", help="Destination prefix")
    ] = "remote",
) -> None:
    """Create a site sync schedule.

    Examples:

        # Attach the hourly profile period to a sync, 7-day remote
        # retention, holding source snapshots until transfer completes
        vrg site sync schedule create \\
            --sync-key 3 --profile-period-key 11 \\
            --retention 604800 --do-not-expire

        # Custom priority and destination prefix
        vrg site sync schedule create \\
            --sync-key 3 --profile-period-key 11 \\
            --retention 2592000 --priority 10 \\
            --destination-prefix offsite

    Both `--sync-key` and `--profile-period-key` are numeric keys: look
    them up with `vrg site sync outgoing list` and `vrg snapshot profile
    period list`. `--retention` is in **seconds**. Set `--do-not-expire`
    when local retention is shorter than a typical transfer window.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "sync_key": sync_key,
        "profile_period_key": profile_period_key,
        "retention": retention,
        "do_not_expire": do_not_expire,
        "destination_prefix": destination_prefix,
    }
    if priority is not None:
        kwargs["priority"] = priority

    result = vctx.client.site_sync_schedules.create(**kwargs)
    output_success(f"Created site sync schedule (key: {result.key})", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    schedule_id: Annotated[int, typer.Argument(help="Schedule key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a site sync schedule.

    Examples:

        vrg site sync schedule delete 42
        vrg site sync schedule delete 42 --yes

    Stops future auto-enqueue for the linked profile period. Snapshots
    already transferred to the remote are not removed — only new fires of
    the period stop enqueuing on this sync.
    """
    vctx = get_context(ctx)

    if not confirm_action(f"Delete site sync schedule {schedule_id}?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.site_sync_schedules.delete(schedule_id)
    output_success(f"Deleted site sync schedule {schedule_id}", quiet=vctx.quiet)
