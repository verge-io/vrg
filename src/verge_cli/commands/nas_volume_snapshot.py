"""NAS volume snapshot sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch, format_epoch_or_never
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource

app = typer.Typer(
    name="snapshot",
    help=(
        "Manage NAS volume snapshots — point-in-time copies of a volume's"
        " filesystem data.\n\n"
        "Snapshots use copy-on-write (COW): taking one is instantaneous and"
        " consumes no extra vSAN space initially. As the source volume diverges"
        " from the snapshot, preserved original blocks accumulate in a shadow"
        " volume, so storage cost grows with write activity — not with logical"
        " volume size. Read-heavy workloads snapshot almost for free;"
        " write-heavy ones should keep retention short.\n\n"
        "Snapshots only apply to volumes of `type=local`. A volume holds a"
        " maximum of 1,000 snapshots and they cascade-delete with the parent"
        " volume. `--quiesce` freezes filesystem I/O via `fsfreeze` for the"
        " duration of the snapshot, producing an application-consistent copy"
        " (required for databases) at the cost of a brief I/O pause.\n\n"
        "Default expiry is 3 days (72 hours). `--never-expires` disables"
        " automatic cleanup — use sparingly, as long-lived snapshots on"
        " write-heavy volumes accumulate significant vSAN usage. Automated"
        " snapshot schedules live on the parent volume's `snapshot_profile`"
        " — this command group is for manual snapshots.\n\n"
        "Snapshots are addressed by name or numeric key within a volume;"
        " ambiguous names exit with code 7 — use the numeric key to"
        " disambiguate. Use `-o json` for machine-readable output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List snapshots on a volume (name or hex key)\n"
        "    vrg nas volume snapshot list shared-data\n\n"
        "    # Get one snapshot as JSON for scripting / agents\n"
        "    vrg -o json nas volume snapshot get shared-data nightly\n\n"
        "    # Take a manual snapshot (default 3-day expiry)\n"
        "    vrg nas volume snapshot create shared-data --name nightly\n\n"
        "    # Application-consistent snapshot for a database volume\n"
        "    vrg nas volume snapshot create db-data \\\n"
        "        --name pre-migration --quiesce --expires-days 7\n\n"
        "    # Permanent milestone snapshot (manual deletion required)\n"
        "    vrg nas volume snapshot create shared-data \\\n"
        "        --name baseline --never-expires \\\n"
        "        --description 'Clean baseline for restore testing'\n\n"
        "    # Delete a snapshot (skip prompt for scripts / agents)\n"
        "    vrg nas volume snapshot delete shared-data nightly --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Snapshot creation is **near-instant** but `--quiesce` adds a brief"
        " I/O pause (typically sub-second) while the filesystem is frozen."
        " Schedule quiesced snapshots on latency-sensitive volumes during"
        " maintenance windows.\n\n"
        "Expired snapshots are removed by a background reaper; you may see a"
        " snapshot persist briefly after its `expires` timestamp. Explicit"
        " `delete` is immediate.\n\n"
        "Restoring a volume from a snapshot is **not exposed here** — it lives"
        " under `vrg nas volume` (volume-level action). Cloning and"
        " restore-to-new flows use the snapshot as the source of truth; see"
        " the volume commands for those operations.\n\n"
        "Snapshot storage cost is invisible in logical volume size — monitor"
        " **vSAN tier consumption** when tuning retention, not the volume's"
        " reported used space."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

NAS_VOLUME_SNAPSHOT_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("created", format_fn=format_epoch),
    ColumnDef("expires", format_fn=format_epoch_or_never),
    ColumnDef("description", wide_only=True),
]


def _snapshot_to_dict(snap: Any) -> dict[str, Any]:
    """Convert a NAS volume snapshot SDK object to a dict for output."""
    return {
        "$key": snap.key,
        "name": snap.name,
        "created": snap.get("created"),
        "expires": snap.get("expires"),
        "description": snap.get("description", ""),
    }


def _resolve_volume(ctx: typer.Context, volume_identifier: str) -> tuple[Any, str]:
    """Resolve volume identifier and return (vctx, volume_key)."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_volumes, volume_identifier, "NAS volume")
    return vctx, key


def _resolve_snapshot(vctx: Any, volume_key: str, identifier: str) -> int:
    """Resolve a snapshot name or key to an integer key.

    NAS volume snapshots use integer keys (unlike volume hex keys).
    """
    if identifier.isdigit():
        return int(identifier)

    snap_mgr = vctx.client.nas_volumes.snapshots(volume_key)
    snapshots = snap_mgr.list()
    matches = [s for s in snapshots if s.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(
            f"Error: Multiple snapshots match '{identifier}'. Use a numeric key.",
            err=True,
        )
        raise typer.Exit(7)
    typer.echo(f"Error: Snapshot '{identifier}' not found.", err=True)
    raise typer.Exit(6)


@app.command("list")
@handle_errors()
def snapshot_list(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
) -> None:
    """List snapshots for a NAS volume.

    **Examples:**

        vrg nas volume snapshot list shared-data
        vrg -o json nas volume snapshot list shared-data
    """
    vctx, volume_key = _resolve_volume(ctx, volume)
    snap_mgr = vctx.client.nas_volumes.snapshots(volume_key)
    snapshots = snap_mgr.list()
    data = [_snapshot_to_dict(s) for s in snapshots]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NAS_VOLUME_SNAPSHOT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def snapshot_get(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
) -> None:
    """Get details of a NAS volume snapshot.

    **Examples:**

        vrg nas volume snapshot get shared-data nightly
        vrg -o json nas volume snapshot get shared-data 42
    """
    vctx, volume_key = _resolve_volume(ctx, volume)
    snap_key = _resolve_snapshot(vctx, volume_key, snapshot)
    snap_mgr = vctx.client.nas_volumes.snapshots(volume_key)
    snap_obj = snap_mgr.get(snap_key)
    output_result(
        _snapshot_to_dict(snap_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def snapshot_create(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
    name: Annotated[str, typer.Option("--name", "-n", help="Snapshot name")],
    expires_days: Annotated[
        int,
        typer.Option("--expires-days", help="Retention in days (default 3)"),
    ] = 3,
    never_expires: Annotated[
        bool,
        typer.Option("--never-expires", help="Snapshot never expires"),
    ] = False,
    quiesce: Annotated[
        bool,
        typer.Option("--quiesce", help="Quiesce filesystem before snapshot"),
    ] = False,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Snapshot description"),
    ] = None,
) -> None:
    """Create a snapshot of a NAS volume.

    Snapshots are copy-on-write and near-instant. Default retention is
    3 days; use `--never-expires` for manual management. `--quiesce`
    attempts a filesystem sync for application-consistent captures.

    **Examples:**

        vrg nas volume snapshot create shared-data --name nightly
        vrg nas volume snapshot create shared-data --name pre-upgrade --never-expires
        vrg nas volume snapshot create shared-data --name app-consistent --quiesce
    """
    # Mutual exclusion check
    if never_expires and expires_days != 3:
        typer.echo("Error: --never-expires and --expires-days are mutually exclusive.", err=True)
        raise typer.Exit(2)

    vctx, volume_key = _resolve_volume(ctx, volume)
    snap_mgr = vctx.client.nas_volumes.snapshots(volume_key)

    create_kwargs: dict[str, Any] = {
        "name": name,
    }
    if description is not None:
        create_kwargs["description"] = description
    if never_expires:
        create_kwargs["never_expires"] = True
    else:
        create_kwargs["expires_days"] = expires_days
    if quiesce:
        create_kwargs["quiesce"] = True

    result = snap_mgr.create(**create_kwargs)
    snap_name = result.name if result else name
    snap_key = result.key if result else "?"
    output_success(
        f"Created snapshot '{snap_name}' (key: {snap_key})",
        quiet=vctx.quiet,
    )


@app.command("delete")
@handle_errors()
def snapshot_delete(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
    snapshot: Annotated[str, typer.Argument(help="Snapshot name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a NAS volume snapshot.

    **Examples:**

        vrg nas volume snapshot delete shared-data nightly
        vrg nas volume snapshot delete shared-data nightly --yes
    """
    vctx, volume_key = _resolve_volume(ctx, volume)
    snap_key = _resolve_snapshot(vctx, volume_key, snapshot)

    if not confirm_action(f"Delete snapshot '{snapshot}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    snap_mgr = vctx.client.nas_volumes.snapshots(volume_key)
    snap_mgr.delete(snap_key)
    output_success(f"Deleted snapshot '{snapshot}'", quiet=vctx.quiet)
