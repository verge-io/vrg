"""Outgoing site sync management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SITE_SYNC_OUTGOING_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="outgoing",
    help=(
        "Manage **outgoing site syncs** — the sending end of a"
        " replication pair.\n\n"
        "An outgoing sync lives on the source VergeOS system and pushes"
        " cloud snapshots to a paired incoming sync on a remote site."
        " Pairing is established by entering the destination's one-time"
        " registration code when the outgoing sync is created; after"
        " that, transfers use a dedicated vSAN user provisioned by the"
        " destination.\n\n"
        "Transport tuning: `threads` (1-32, default 8) sets parallel"
        " send workers; `file_threads` (1-64, default 4) scans for"
        " changes; `encryption` and `compression` default on;"
        " `destination_tier` (1-5) can pin received data to a specific"
        " tier on the remote. `sendthrottle` caps bandwidth in bytes/sec"
        " (0 = unlimited) and can be adjusted at runtime with"
        " `set-throttle` / `disable-throttle`.\n\n"
        "The transfer queue is fed two ways: **automatic** (a snapshot"
        " profile period link fires and enqueues the new snapshot) or"
        " **manual** (the `add_to_queue` API action). Failed transfers"
        " retry with exponential backoff (`queue_retry_count` default 10,"
        " `queue_retry_interval_seconds` default 60s).\n\n"
        "Status values: `Initializing`, `Syncing`, `Offline` (normal"
        " between transfers), and `Error`. The `refresh-remote` command"
        " re-reads the cache of snapshots held on the destination.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all outgoing syncs on this (source) system\n"
        "    vrg site sync outgoing list\n\n"
        "    # Filter to a specific paired site\n"
        "    vrg site sync outgoing list --site dr-east\n\n"
        "    # Full details for scripting / agents\n"
        "    vrg -o json site sync outgoing get production-sync\n\n"
        "    # Trigger a sync to run now\n"
        "    vrg site sync outgoing start production-sync\n\n"
        "    # Cap send rate at 100 Mbps during business hours\n"
        "    vrg site sync outgoing set-throttle production-sync --mbps 100\n\n"
        "    # Remove the bandwidth cap\n"
        "    vrg site sync outgoing disable-throttle production-sync\n\n"
        "    # Refresh the cached list of snapshots on the destination\n"
        "    vrg site sync outgoing refresh-remote production-sync\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "System limit: **100,000 outgoing syncs** per system. Syncs are"
        " referenced by name or numeric `$key`; when a name matches"
        " multiple records, vrg exits with code 7 — use the key to"
        " disambiguate. `disable` pauses the sender without deleting the"
        " pairing or queued items. `stop` aborts an in-progress transfer"
        " but leaves the queue intact. Use `-o json` for machine-readable"
        " output; useful `--query` fields include `status`, `enabled`,"
        " `state`, `last_run`, `destination_tier`, `threads`,"
        " `encryption`, and `compression`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _sync_to_dict(sync: Any) -> dict[str, Any]:
    """Convert a SiteSyncOutgoing SDK object to a dict for output."""
    return {
        "$key": sync.key,
        "name": sync.name,
        "site": sync.get("site"),
        "status": sync.get("status"),
        "enabled": sync.get("enabled"),
        "state": sync.get("state"),
        "encryption": sync.get("encryption"),
        "compression": sync.get("compression"),
        "threads": sync.get("threads"),
        "last_run": sync.get("last_run"),
        "destination_tier": sync.get("destination_tier"),
        "description": sync.get("description", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    site: Annotated[
        str | None,
        typer.Option("--site", "-s", help="Filter by site (name or key)"),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option(
            "--enabled/--disabled",
            help="Filter by enabled state",
        ),
    ] = None,
) -> None:
    """List all outgoing site syncs.

    Examples:

        vrg site sync outgoing list
        vrg site sync outgoing list --site dr-east --enabled
        vrg -o json site sync outgoing list | jq '.[] | select(.status == "Error") | .name'

    Useful `--query` fields include `status`, `enabled`, `state`,
    `last_run`, `destination_tier`, `threads`, `encryption`, and
    `compression`.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}

    if site is not None:
        # If numeric, use site_key; otherwise use site_name
        if site.isdigit():
            kwargs["site_key"] = int(site)
        else:
            kwargs["site_name"] = site

    if enabled is not None:
        kwargs["enabled"] = enabled

    syncs = vctx.client.site_syncs.list(**kwargs)
    data = [_sync_to_dict(s) for s in syncs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SITE_SYNC_OUTGOING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Get details of an outgoing site sync.

    Examples:

        vrg site sync outgoing get production-sync
        vrg -o json site sync outgoing get 12
        vrg -o json site sync outgoing get production-sync \\
            --query "{status: status, last_run: last_run, threads: threads}"

    Resolves `sync` by name or numeric key. Ambiguous names exit 7.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    item = vctx.client.site_syncs.get(key)
    output_result(
        _sync_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Enable an outgoing site sync.

    Examples:

        vrg site sync outgoing enable production-sync
        vrg site sync outgoing enable 12

    Resumes auto-enqueue and transfer activity for this sync. Queued but
    not-yet-transferred snapshots are processed according to priority.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.enable(key)
    output_success(f"Enabled outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Disable an outgoing site sync.

    Examples:

        vrg site sync outgoing disable production-sync
        vrg site sync outgoing disable 12

    Pauses the sender without deleting the pairing or the queue. Any
    in-progress transfer is stopped cleanly. Re-enable with
    `vrg site sync outgoing enable`.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.disable(key)
    output_success(f"Disabled outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("start")
@handle_errors()
def start_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Trigger an outgoing site sync to run now.

    Examples:

        vrg site sync outgoing start production-sync
        vrg site sync outgoing start 12

    Kicks off transfer of any queued snapshots immediately, bypassing the
    normal scheduled cadence. Has no effect if the queue is empty.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.start(key)
    output_success(f"Started outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("stop")
@handle_errors()
def stop_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Stop a running outgoing site sync.

    Examples:

        vrg site sync outgoing stop production-sync
        vrg site sync outgoing stop 12

    Aborts the in-progress transfer but leaves the queue intact. The
    interrupted transfer resumes from where it left off on the next run.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.stop(key)
    output_success(f"Stopped outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("set-throttle")
@handle_errors()
def set_throttle_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
    mbps: Annotated[int, typer.Option("--mbps", help="Throttle limit in Mbps")],
) -> None:
    """Set bandwidth throttle on an outgoing site sync.

    Examples:

        vrg site sync outgoing set-throttle production-sync --mbps 100
        vrg site sync outgoing set-throttle 12 --mbps 500

    Caps the send rate at the specified megabits per second. Applied
    immediately to in-progress and future transfers. Remove with
    `vrg site sync outgoing disable-throttle`.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.set_throttle(key, mbps)
    output_success(f"Set throttle to {mbps} Mbps on outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("disable-throttle")
@handle_errors()
def disable_throttle_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Remove bandwidth throttle from an outgoing site sync.

    Examples:

        vrg site sync outgoing disable-throttle production-sync
        vrg site sync outgoing disable-throttle 12

    Clears any bandwidth cap previously set with `set-throttle`. Transfers
    resume at full available link speed.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.disable_throttle(key)
    output_success(f"Disabled throttle on outgoing sync '{sync}'", quiet=vctx.quiet)


@app.command("refresh-remote")
@handle_errors()
def refresh_remote_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Refresh remote snapshots for an outgoing site sync.

    Examples:

        vrg site sync outgoing refresh-remote production-sync
        vrg site sync outgoing refresh-remote 12

    Re-reads the cache of snapshots held on the destination. Useful when
    the remote side has pruned or added snapshots out-of-band and the
    source's view of what exists there has drifted.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs, sync, "Outgoing Sync")
    vctx.client.site_syncs.refresh_remote_snapshots(key)
    output_success(f"Refreshed remote snapshots for outgoing sync '{sync}'", quiet=vctx.quiet)
