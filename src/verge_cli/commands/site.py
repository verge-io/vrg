"""Site management commands."""

from __future__ import annotations

from typing import Annotated, Any

import click
import typer

from verge_cli.columns import SITE_COLUMNS
from verge_cli.commands import site_sync
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="site",
    help=(
        "Manage remote VergeOS sites and the site syncs that replicate data"
        " between them.\n\n"
        "A **site** is a trusted peer VergeOS system, typically at a different"
        " geographic location. Site records pair two clusters so they can"
        " replicate cloud snapshots, share statistics, and manage each other's"
        " resources. Sites are the foundation for disaster recovery,"
        " multi-site monitoring, and centralized management across"
        " geographically distributed deployments.\n\n"
        "Replication is **directional** and operates at the cloud-snapshot"
        " level. An **outgoing sync** on the source pushes cloud snapshots to"
        " a remote site; an **incoming sync** on the destination receives"
        " them. Outgoing and incoming syncs are paired via a registration"
        " code generated on the destination.\n\n"
        "Subresources have their own groups: `vrg site sync outgoing`"
        " (outbound replication jobs), `vrg site sync incoming` (inbound"
        " receivers), and `vrg site sync schedule` (per-sync scheduling"
        " overrides).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List configured sites\n"
        "    vrg site list\n\n"
        "    # Get site details as JSON\n"
        "    vrg -o json site get dr-east\n\n"
        "    # Create a site connection (one-time auth handshake)\n"
        "    vrg site create --name dr-east --url https://dr.example.com \\\n"
        "        --username admin --password 's3cret' \\\n"
        "        --cloud-snapshots both\n\n"
        "    # Re-authenticate after a credential rotation\n"
        "    vrg site reauth dr-east --username admin --password 'new-s3cret'\n\n"
        "    # Temporarily disable replication to a site without deleting it\n"
        "    vrg site disable dr-east\n"
        "    vrg site enable dr-east\n\n"
        "    # Inspect syncs to / from a site\n"
        "    vrg site sync outgoing list\n"
        "    vrg site sync incoming list\n\n"
        "    # JSON output for scripting / agents\n"
        "    vrg -o json site list\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Site connectivity requires network reachability between the two"
        " VergeOS systems on both the API URL and the vSAN data plane"
        " (default port 14201). The initial site-create call performs a"
        " one-time authentication handshake; the temporary credentials are"
        " not stored after setup — ongoing replication uses a dedicated"
        " service account.\n\n"
        "Each site has four independently configurable capability flags"
        " (cloud snapshots, statistics, management, repair server), each with"
        " `disabled` / `send` / `receive` / `both` options. The"
        " `--cloud-snapshots` flag controls the replication direction for"
        " snapshot data.\n\n"
        "System limit: **1,000 sites** per system. Sites are referenced by"
        " name or numeric key (`$key`). When a name matches multiple sites,"
        " vrg prints all matches and exits with code 7 — use the numeric key"
        " to disambiguate. Use `-o json` for machine-readable output suitable"
        " for automation and agents."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(site_sync.app, name="sync")


def _site_to_dict(site: Any) -> dict[str, Any]:
    """Convert a Site SDK object to a dict for output."""
    return {
        "$key": site.key,
        "name": site.name,
        "url": site.get("url"),
        "status": site.get("status"),
        "enabled": site.get("enabled"),
        "authentication_status": site.get("authentication_status"),
        "config_cloud_snapshots": site.get("config_cloud_snapshots"),
        "description": site.get("description", ""),
        "domain": site.get("domain"),
        "city": site.get("city"),
        "country": site.get("country"),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (e.g., online, offline, error)"),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option(
            "--enabled/--disabled",
            help="Filter by enabled state",
        ),
    ] = None,
) -> None:
    """List all registered sites."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.sites.list(), _site_to_dict, SITE_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if status is not None:
        kwargs["status"] = status
    if enabled is not None:
        kwargs["enabled"] = enabled
    sites = vctx.client.sites.list(**kwargs)
    data = [_site_to_dict(s) for s in sites]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SITE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
) -> None:
    """Get details of a site."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")
    item = vctx.client.sites.get(key)
    output_result(
        _site_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Site name")],
    url: Annotated[str, typer.Option("--url", help="Site URL (e.g., https://site2.example.com)")],
    username: Annotated[str, typer.Option("--username", help="Authentication username")],
    password: Annotated[str, typer.Option("--password", help="Authentication password")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Site description")
    ] = None,
    allow_insecure: Annotated[
        bool, typer.Option("--allow-insecure", help="Allow insecure SSL connections")
    ] = False,
    cloud_snapshots: Annotated[
        str,
        typer.Option(
            "--cloud-snapshots",
            help="Cloud snapshot config",
            click_type=click.Choice(["disabled", "send", "receive", "both"]),
        ),
    ] = "disabled",
    auto_create_syncs: Annotated[
        bool,
        typer.Option("--auto-create-syncs/--no-auto-create-syncs", help="Auto-create sync configs"),
    ] = True,
) -> None:
    """Create a new site connection."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "url": url,
        "username": username,
        "password": password,
        "allow_insecure": allow_insecure,
        "config_cloud_snapshots": cloud_snapshots,
        "auto_create_syncs": auto_create_syncs,
    }
    if description is not None:
        kwargs["description"] = description

    result = vctx.client.sites.create(**kwargs)
    site_name = result.name if result else name
    site_key = result.key if result else "?"
    output_success(
        f"Created site '{site_name}' (key: {site_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New site name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Site description")
    ] = None,
    cloud_snapshots: Annotated[
        str | None,
        typer.Option(
            "--cloud-snapshots",
            help="Cloud snapshot config",
            click_type=click.Choice(["disabled", "send", "receive", "both"]),
        ),
    ] = None,
) -> None:
    """Update a site's settings."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if cloud_snapshots is not None:
        kwargs["config_cloud_snapshots"] = cloud_snapshots

    vctx.client.sites.update(key, **kwargs)
    output_success(f"Updated site '{site}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a site."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")

    if not confirm_action(f"Delete site '{site}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.sites.delete(key)
    output_success(f"Deleted site '{site}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
) -> None:
    """Enable a disabled site."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")
    vctx.client.sites.enable(key)
    output_success(f"Enabled site '{site}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
) -> None:
    """Disable a site without deleting it."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")
    vctx.client.sites.disable(key)
    output_success(f"Disabled site '{site}'", quiet=vctx.quiet)


@app.command("reauth")
@handle_errors()
def reauth_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
    username: Annotated[str, typer.Option("--username", help="New username")],
    password: Annotated[str, typer.Option("--password", help="New password")],
) -> None:
    """Re-authenticate with updated credentials."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")
    vctx.client.sites.reauthenticate(key, username, password)
    output_success(f"Re-authenticated site '{site}'", quiet=vctx.quiet)


@app.command("refresh")
@handle_errors()
def refresh_cmd(
    ctx: typer.Context,
    site: Annotated[str, typer.Argument(help="Site name or key")],
) -> None:
    """Refresh site connection and metadata."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.sites, site, "Site")
    vctx.client.sites.refresh_site(key)
    output_success(f"Refreshed site '{site}'", quiet=vctx.quiet)
