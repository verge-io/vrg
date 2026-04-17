"""Incoming site sync management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SITE_SYNC_INCOMING_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="incoming",
    help=(
        "Manage **incoming site syncs** — the receiving end of a"
        " replication pair.\n\n"
        "An incoming sync lives on the destination VergeOS system and"
        " accepts cloud snapshots pushed by a paired outgoing sync on a"
        " remote source. Creating an incoming sync generates a one-time"
        " **registration code** that is entered on the source side to"
        " authenticate the pairing; the system also provisions a dedicated"
        " vSAN user for the remote source to use during transfers.\n\n"
        "The most important safety field is `min_snapshots`: the"
        " destination always retains at least this many snapshots even if"
        " every snapshot has technically expired. Without it, an extended"
        " source outage can cause all remote recovery points to age out,"
        " leaving nothing to fail over to. `force_tier` optionally pins"
        " received data to a specific storage tier (1–5).\n\n"
        "Status values include `Generating Reg`, `Offline`, `Syncing`,"
        " `Error`, and `Regeneration Needed` — the last means the"
        " registration code has been invalidated and must be regenerated"
        " (via the API) before the pairing will reconnect.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all incoming syncs on this (destination) system\n"
        "    vrg site sync incoming list\n\n"
        "    # Filter to a specific paired site\n"
        "    vrg site sync incoming list --site dr-east\n\n"
        "    # Show only disabled receivers\n"
        "    vrg site sync incoming list --disabled\n\n"
        "    # Full details for scripting / agents\n"
        "    vrg -o json site sync incoming get offsite-backup\n\n"
        "    # Pause accepting new data without deleting the pairing\n"
        "    vrg site sync incoming disable offsite-backup\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "System limit: **100,000 incoming syncs** per system. Syncs are"
        " referenced by name or numeric `$key`; when a name matches"
        " multiple records, vrg exits with code 7 — use the key to"
        " disambiguate. `disable` stops the receiver from accepting new"
        " transfers but preserves the pairing and existing snapshots."
        " Use `-o json` for machine-readable output; useful `--query`"
        " fields include `status`, `enabled`, `state`, `last_sync`, and"
        " `min_snapshots`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _sync_to_dict(sync: Any) -> dict[str, Any]:
    """Convert a SiteSyncIncoming SDK object to a dict for output."""
    return {
        "$key": sync.key,
        "name": sync.name,
        "site": sync.get("site"),
        "status": sync.get("status"),
        "enabled": sync.get("enabled"),
        "state": sync.get("state"),
        "last_sync": sync.get("last_sync"),
        "min_snapshots": sync.get("min_snapshots"),
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
    """List all incoming site syncs."""
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

    syncs = vctx.client.site_syncs_incoming.list(**kwargs)
    data = [_sync_to_dict(s) for s in syncs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SITE_SYNC_INCOMING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Get details of an incoming site sync."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs_incoming, sync, "Incoming Sync")
    item = vctx.client.site_syncs_incoming.get(key)
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
    """Enable an incoming site sync."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs_incoming, sync, "Incoming Sync")
    vctx.client.site_syncs_incoming.enable(key)
    output_success(f"Enabled incoming sync '{sync}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    sync: Annotated[str, typer.Argument(help="Sync name or key")],
) -> None:
    """Disable an incoming site sync."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.site_syncs_incoming, sync, "Incoming Sync")
    vctx.client.site_syncs_incoming.disable(key)
    output_success(f"Disabled incoming sync '{sync}'", quiet=vctx.quiet)
