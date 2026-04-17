"""NAS NFS share management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_error, output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource

app = typer.Typer(
    name="nfs",
    help=(
        "Manage NFS exports — kernel NFS server entries layered on top of a"
        " NAS volume.\n\n"
        "An NFS share is a child record of a volume (`volume_nfs_shares`"
        " schema table; cascade-deletes with the parent). The kernel NFS"
        " server exports the share to UNIX/Linux/macOS clients. Multiple"
        " shares can target the same volume to export different subpaths"
        " with different access rules.\n\n"
        "Host access is gated by `allowed_hosts` (FQDNs with wildcards like"
        " `*.example.com`, hostnames, IPs, CIDR such as `192.168.0.0/28`, or"
        " NIS netgroups like `@admins`) or `allow_all` (the `*` equivalent in"
        " `/etc/exports`). If neither is set, **no hosts can connect** — the"
        " CLI enforces this at create time and requires `--allowed-hosts` or"
        " `--allow-all`.\n\n"
        "`--data-access` is `ro` (read-only, default) or `rw`. `--squash`"
        " controls UID mapping: `root_squash` (default) maps remote root to"
        " anonymous UID/GID and passes other UIDs through; `all_squash` maps"
        " every user to anonymous (use for public shares); `no_root_squash`"
        " disables remapping so remote root has full root access (trusted"
        " environments only). Anonymous UID/GID default to `65534`"
        " (`nobody`/`nogroup`) — override with `--anon-uid` / `--anon-gid`.\n\n"
        "`--async` trades durability for write performance (risk of data loss"
        " on unclean shutdown). `--insecure` permits clients from unprivileged"
        " ports (>= 1024) — required by some NFS client stacks.\n\n"
        "Shares are referenced by name or hex `$key`. Ambiguous names exit"
        " with code 7 — disambiguate with the key. Use `-o json` for"
        " machine-readable output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all NFS shares, or filter by volume / enabled state\n"
        "    vrg nas nfs list\n"
        "    vrg nas nfs list --volume shared-data\n"
        "    vrg nas nfs list --enabled\n\n"
        "    # Get one share as JSON for scripting / agents\n"
        "    vrg -o json nas nfs get nfs-share\n\n"
        "    # Create a read/write export scoped to a subnet\n"
        "    vrg nas nfs create \\\n"
        "        --volume shared-data --name nfs-share \\\n"
        "        --allowed-hosts '10.10.0.0/24' \\\n"
        "        --data-access rw\n\n"
        "    # Public-ish export — allow all hosts, map everyone to anonymous\n"
        "    vrg nas nfs create \\\n"
        "        --volume public-data --name public-nfs \\\n"
        "        --allow-all --squash all_squash\n\n"
        "    # Trusted export — preserve remote root identity\n"
        "    vrg nas nfs create \\\n"
        "        --volume backups --name backup-nfs \\\n"
        "        --allowed-hosts 'backup-01,backup-02' \\\n"
        "        --data-access rw --squash no_root_squash\n\n"
        "    # Toggle availability without destroying config\n"
        "    vrg nas nfs disable nfs-share\n"
        "    vrg nas nfs enable nfs-share\n\n"
        "    # Delete a share (volume data is retained)\n"
        "    vrg nas nfs delete nfs-share --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The parent NAS service VM **must be running** and the parent volume"
        " must be `online` for an NFS share to serve clients. Shares on a"
        " stopped service stay in `offline` / `needsrefresh` regardless of"
        " their own enabled state.\n\n"
        "Config changes to an active share transition it to `needsrefresh`"
        " — toggle `disable` then `enable` (or run `update` and then"
        " re-enable) to apply. Brief disconnects are expected; warn connected"
        " clients or schedule off-hours where practical.\n\n"
        "The `--volume` binding is **immutable** after creation — to move an"
        " export to a different volume, delete and recreate it."
        " `--allowed-hosts` replaces the entire list; there is no incremental"
        " add/remove. `--filesystem-id` must be unique among shares on the"
        " same volume (integer, `root`, or UUID); clients use `fsid` to track"
        " mounts across server restarts."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

NAS_NFS_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("volume_name", header="Volume"),
    ColumnDef(
        "enabled",
        format_fn=format_bool_yn,
        style_map={"Yes": "green", "No": "red"},
    ),
    ColumnDef("data_access", header="Access"),
    ColumnDef("squash"),
    ColumnDef("allowed_hosts", header="Allowed Hosts", wide_only=True),
    ColumnDef(
        "allow_all",
        header="Allow All",
        format_fn=format_bool_yn,
        wide_only=True,
    ),
    ColumnDef("description", wide_only=True),
]


def _nfs_share_to_dict(share: Any) -> dict[str, Any]:
    """Convert a NAS NFS share SDK object to a dict for output."""
    return {
        "$key": share.key,
        "name": share.name,
        "volume_name": share.get("volume_name"),
        "enabled": share.get("enabled"),
        "data_access": share.get("data_access"),
        "squash": share.get("squash"),
        "allowed_hosts": share.get("allowed_hosts"),
        "allow_all": share.get("allow_all"),
        "description": share.get("description", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    volume: Annotated[
        str | None,
        typer.Option("--volume", help="Filter by volume name or hex key"),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled state"),
    ] = None,
) -> None:
    """List all NFS shares."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if volume is not None:
        vol_key = resolve_nas_resource(vctx.client.nas_volumes, volume, "NAS volume")
        kwargs["volume"] = vol_key
    if enabled is not None:
        kwargs["enabled"] = enabled

    shares = vctx.client.nfs_shares.list(**kwargs)
    data = [_nfs_share_to_dict(s) for s in shares]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NAS_NFS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    share: Annotated[str, typer.Argument(help="NFS share name or hex key")],
) -> None:
    """Get details of an NFS share."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nfs_shares, share, "NFS share")
    item = vctx.client.nfs_shares.get(key=key)
    output_result(
        _nfs_share_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Share name")],
    volume: Annotated[str, typer.Option("--volume", help="NAS volume name or hex key")],
    share_path: Annotated[
        str | None,
        typer.Option("--share-path", help="Path within volume"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Share description"),
    ] = None,
    allowed_hosts: Annotated[
        str | None,
        typer.Option("--allowed-hosts", help="Comma-separated host/CIDR list"),
    ] = None,
    allow_all: Annotated[
        bool,
        typer.Option("--allow-all", help="Allow access from all hosts"),
    ] = False,
    data_access: Annotated[
        str | None,
        typer.Option("--data-access", help="Access mode: ro or rw"),
    ] = None,
    squash: Annotated[
        str | None,
        typer.Option("--squash", help="Squash mode: root_squash, all_squash, no_root_squash"),
    ] = None,
    anon_uid: Annotated[
        str | None,
        typer.Option("--anon-uid", help="Anonymous UID"),
    ] = None,
    anon_gid: Annotated[
        str | None,
        typer.Option("--anon-gid", help="Anonymous GID"),
    ] = None,
    async_mode: Annotated[
        bool,
        typer.Option("--async", help="Enable async mode"),
    ] = False,
    insecure: Annotated[
        bool,
        typer.Option("--insecure", help="Allow insecure connections"),
    ] = False,
    no_acl: Annotated[
        bool,
        typer.Option("--no-acl", help="Disable ACL support"),
    ] = False,
    filesystem_id: Annotated[
        str | None,
        typer.Option("--filesystem-id", help="Custom filesystem ID (fsid)"),
    ] = None,
) -> None:
    """Create a new NFS share."""
    vctx = get_context(ctx)

    # Validate: require either --allowed-hosts or --allow-all
    if not allowed_hosts and not allow_all:
        output_error("Either --allowed-hosts or --allow-all is required")
        raise typer.Exit(2)

    # Resolve volume name to key
    vol_key = resolve_nas_resource(vctx.client.nas_volumes, volume, "NAS volume")

    create_kwargs: dict[str, Any] = {
        "name": name,
        "volume": vol_key,
    }
    if share_path is not None:
        create_kwargs["share_path"] = share_path
    if description is not None:
        create_kwargs["description"] = description
    if allowed_hosts is not None:
        # SDK accepts comma-delimited string
        create_kwargs["allowed_hosts"] = allowed_hosts
    if allow_all:
        create_kwargs["allow_all"] = True
    if data_access is not None:
        create_kwargs["data_access"] = data_access
    if squash is not None:
        create_kwargs["squash"] = squash
    if anon_uid is not None:
        create_kwargs["anonymous_uid"] = anon_uid
    if anon_gid is not None:
        create_kwargs["anonymous_gid"] = anon_gid
    if async_mode:
        create_kwargs["async_mode"] = True
    if insecure:
        create_kwargs["insecure"] = True
    if no_acl:
        create_kwargs["no_acl"] = True
    if filesystem_id is not None:
        create_kwargs["filesystem_id"] = filesystem_id

    result = vctx.client.nfs_shares.create(**create_kwargs)
    share_name = result.name if result else name
    share_key = result.key if result else "?"
    output_success(
        f"Created NFS share '{share_name}' (key: {share_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    share: Annotated[str, typer.Argument(help="NFS share name or hex key")],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Share description"),
    ] = None,
    allowed_hosts: Annotated[
        str | None,
        typer.Option("--allowed-hosts", help="Comma-separated host/CIDR list"),
    ] = None,
    allow_all: Annotated[
        bool | None,
        typer.Option("--allow-all/--no-allow-all", help="Allow/deny access from all hosts"),
    ] = None,
    data_access: Annotated[
        str | None,
        typer.Option("--data-access", help="Access mode: ro or rw"),
    ] = None,
    squash: Annotated[
        str | None,
        typer.Option("--squash", help="Squash mode: root_squash, all_squash, no_root_squash"),
    ] = None,
    anon_uid: Annotated[
        str | None,
        typer.Option("--anon-uid", help="Anonymous UID"),
    ] = None,
    anon_gid: Annotated[
        str | None,
        typer.Option("--anon-gid", help="Anonymous GID"),
    ] = None,
    async_mode: Annotated[
        bool | None,
        typer.Option("--async/--no-async", help="Enable/disable async mode"),
    ] = None,
    insecure: Annotated[
        bool | None,
        typer.Option("--insecure/--no-insecure", help="Enable/disable insecure connections"),
    ] = None,
    no_acl: Annotated[
        bool | None,
        typer.Option("--no-acl/--acl", help="Disable/enable ACL support"),
    ] = None,
    filesystem_id: Annotated[
        str | None,
        typer.Option("--filesystem-id", help="Custom filesystem ID (fsid)"),
    ] = None,
) -> None:
    """Update an NFS share."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nfs_shares, share, "NFS share")

    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    if allowed_hosts is not None:
        kwargs["allowed_hosts"] = allowed_hosts
    if allow_all is not None:
        kwargs["allow_all"] = allow_all
    if data_access is not None:
        kwargs["data_access"] = data_access
    if squash is not None:
        kwargs["squash"] = squash
    if anon_uid is not None:
        kwargs["anonymous_uid"] = anon_uid
    if anon_gid is not None:
        kwargs["anonymous_gid"] = anon_gid
    if async_mode is not None:
        kwargs["async_mode"] = async_mode
    if insecure is not None:
        kwargs["insecure"] = insecure
    if no_acl is not None:
        kwargs["no_acl"] = no_acl
    if filesystem_id is not None:
        kwargs["filesystem_id"] = filesystem_id

    vctx.client.nfs_shares.update(key, **kwargs)
    output_success(f"Updated NFS share '{share}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    share: Annotated[str, typer.Argument(help="NFS share name or hex key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete an NFS share (data is retained on volume)."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nfs_shares, share, "NFS share")

    if not confirm_action(f"Delete NFS share '{share}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.nfs_shares.delete(key)
    output_success(f"Deleted NFS share '{share}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    share: Annotated[str, typer.Argument(help="NFS share name or hex key")],
) -> None:
    """Enable an NFS share."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nfs_shares, share, "NFS share")
    vctx.client.nfs_shares.enable(key)
    output_success(f"Enabled NFS share '{share}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    share: Annotated[str, typer.Argument(help="NFS share name or hex key")],
) -> None:
    """Disable an NFS share."""
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nfs_shares, share, "NFS share")
    vctx.client.nfs_shares.disable(key)
    output_success(f"Disabled NFS share '{share}'", quiet=vctx.quiet)
