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
    help="Manage remote sites.",
    no_args_is_help=True,
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
