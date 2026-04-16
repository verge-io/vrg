"""System commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import (
    SYSTEM_LICENSE_COLUMNS,
    SYSTEM_SETTING_COLUMNS,
    ColumnDef,
)
from verge_cli.commands import system_diag
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success

app = typer.Typer(
    name="system",
    help="System information and management.",
    no_args_is_help=True,
)

app.add_typer(system_diag.app, name="diag")

# ---------------------------------------------------------------------------
# Settings sub-group
# ---------------------------------------------------------------------------
settings_app = typer.Typer(
    name="settings",
    help="Manage system settings.",
    no_args_is_help=True,
)
app.add_typer(settings_app, name="settings")

# ---------------------------------------------------------------------------
# License sub-group
# ---------------------------------------------------------------------------
license_app = typer.Typer(
    name="license",
    help="Manage system licenses.",
    no_args_is_help=True,
)
app.add_typer(license_app, name="license")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setting_to_dict(setting: Any) -> dict[str, Any]:
    """Convert a SystemSetting SDK object to a dict for output."""
    return {
        "key": setting.get("key", getattr(setting, "key", "")),
        "value": setting.get("value", ""),
        "default_value": setting.get("default_value", ""),
        "description": setting.get("description", ""),
        "modified": setting.get("modified", False),
    }


def _license_to_dict(lic: Any) -> dict[str, Any]:
    """Convert a License SDK object to a dict for output."""
    return {
        "$key": lic.key,
        "name": getattr(lic, "name", lic.get("name", "")),
        "is_valid": lic.get("is_valid"),
        "valid_from": lic.get("valid_from", ""),
        "valid_until": lic.get("valid_until", ""),
        "features": lic.get("features", ""),
        "auto_renewal": lic.get("auto_renewal"),
        "allow_branding": lic.get("allow_branding"),
        "note": lic.get("note", ""),
    }


# ---------------------------------------------------------------------------
# System info/version commands
# ---------------------------------------------------------------------------


@app.command("info")
@handle_errors()
def system_info(ctx: typer.Context) -> None:
    """Display system information and statistics."""
    vctx = get_context(ctx)

    client = vctx.client

    # Get basic system info from connection
    info: dict[str, Any] = {
        "host": vctx.config.host,
        "version": client.version,
        "os_version": client.os_version,
        "cloud_name": client.cloud_name,
    }

    # Get dashboard statistics
    try:
        stats = client.system.statistics()
        info["vms_total"] = stats.vms_total
        info["vms_online"] = stats.vms_online
        info["tenants_total"] = stats.tenants_total
        info["tenants_online"] = stats.tenants_online
        info["networks_total"] = stats.networks_total
        info["networks_online"] = stats.networks_online
        info["nodes_total"] = stats.nodes_total
        info["nodes_online"] = stats.nodes_online
        info["alarms_total"] = stats.alarms_total
    except Exception:
        # Statistics might not be available, continue with basic info
        pass

    output_result(
        info,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("version")
@handle_errors()
def system_version(ctx: typer.Context) -> None:
    """Display VergeOS version."""
    vctx = get_context(ctx)

    client = vctx.client

    version_info = {
        "version": client.version,
        "os_version": client.os_version,
    }

    if vctx.query:
        output_result(
            version_info,
            output_format=vctx.output_format,
            query=vctx.query,
            quiet=vctx.quiet,
            no_color=vctx.no_color,
        )
    elif vctx.output_format == "json":
        output_result(
            version_info,
            output_format="json",
            quiet=vctx.quiet,
            no_color=vctx.no_color,
        )
    else:
        # Simple output for table mode
        typer.echo(f"VergeOS Version: {client.version}")
        if client.os_version:
            typer.echo(f"OS Version: {client.os_version}")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

INVENTORY_COLUMNS: list[ColumnDef] = [
    ColumnDef("vms", header="VMs"),
    ColumnDef("networks", header="Networks"),
    ColumnDef("storage", header="Storage"),
    ColumnDef("nodes", header="Nodes"),
    ColumnDef("clusters", header="Clusters"),
    ColumnDef("tenants", header="Tenants"),
]


@app.command("inventory")
@handle_errors()
def inventory_cmd(
    ctx: typer.Context,
    vms: Annotated[
        bool | None,
        typer.Option("--vms/--no-vms", help="Include VMs"),
    ] = None,
    networks: Annotated[
        bool | None,
        typer.Option("--networks/--no-networks", help="Include networks"),
    ] = None,
    storage: Annotated[
        bool | None,
        typer.Option("--storage/--no-storage", help="Include storage"),
    ] = None,
    nodes: Annotated[
        bool | None,
        typer.Option("--nodes/--no-nodes", help="Include nodes"),
    ] = None,
    clusters: Annotated[
        bool | None,
        typer.Option("--clusters/--no-clusters", help="Include clusters"),
    ] = None,
    tenants: Annotated[
        bool | None,
        typer.Option("--tenants/--no-tenants", help="Include tenants"),
    ] = None,
) -> None:
    """Display system inventory."""
    vctx = get_context(ctx)
    kwargs: dict[str, bool] = {}
    if vms is not None:
        kwargs["include_vms"] = vms
    if networks is not None:
        kwargs["include_networks"] = networks
    if storage is not None:
        kwargs["include_storage"] = storage
    if nodes is not None:
        kwargs["include_nodes"] = nodes
    if clusters is not None:
        kwargs["include_clusters"] = clusters
    if tenants is not None:
        kwargs["include_tenants"] = tenants

    result = vctx.client.system.inventory(**kwargs)

    output_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


# ---------------------------------------------------------------------------
# Settings sub-commands
# ---------------------------------------------------------------------------


@settings_app.command("list")
@handle_errors()
def settings_list_cmd(
    ctx: typer.Context,
    modified: Annotated[
        bool,
        typer.Option("--modified", "-m", help="Show only modified settings"),
    ] = False,
) -> None:
    """List system settings."""
    vctx = get_context(ctx)
    if modified:
        settings = vctx.client.system.settings.list_modified()
    else:
        settings = vctx.client.system.settings.list()
    data = [_setting_to_dict(s) for s in settings]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SYSTEM_SETTING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@settings_app.command("get")
@handle_errors()
def settings_get_cmd(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key")],
) -> None:
    """Get a specific system setting."""
    vctx = get_context(ctx)
    setting = vctx.client.system.settings.get(key)
    output_result(
        _setting_to_dict(setting),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@settings_app.command("set")
@handle_errors()
def settings_set_cmd(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key")],
    value: Annotated[str, typer.Argument(help="New value")],
) -> None:
    """Set a system setting value."""
    vctx = get_context(ctx)
    vctx.client.system.settings.update(key, value)
    output_success(f"Set '{key}' to '{value}'", quiet=vctx.quiet)


@settings_app.command("reset")
@handle_errors()
def settings_reset_cmd(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key")],
) -> None:
    """Reset a system setting to its default value."""
    vctx = get_context(ctx)
    vctx.client.system.settings.reset(key)
    output_success(f"Reset '{key}' to default", quiet=vctx.quiet)


# ---------------------------------------------------------------------------
# License sub-commands
# ---------------------------------------------------------------------------


@license_app.command("list")
@handle_errors()
def license_list_cmd(ctx: typer.Context) -> None:
    """List system licenses."""
    vctx = get_context(ctx)
    licenses = vctx.client.system.licenses.list()
    data = [_license_to_dict(lic) for lic in licenses]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SYSTEM_LICENSE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@license_app.command("get")
@handle_errors()
def license_get_cmd(
    ctx: typer.Context,
    license_id: Annotated[str, typer.Argument(help="License name or key")],
) -> None:
    """Get details of a license."""
    vctx = get_context(ctx)
    if license_id.isdigit():
        lic = vctx.client.system.licenses.get(int(license_id))
    else:
        lic = vctx.client.system.licenses.get(name=license_id)
    output_result(
        _license_to_dict(lic),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@license_app.command("add")
@handle_errors()
def license_add_cmd(
    ctx: typer.Context,
    license_text: Annotated[
        str, typer.Option("--license-text", help="License key text to install")
    ],
) -> None:
    """Install a license key (for air-gap systems)."""
    vctx = get_context(ctx)
    result = vctx.client.system.licenses.add(license_text)
    output_success(f"Added license (key: {result.key})", quiet=vctx.quiet)


@license_app.command("generate-payload")
@handle_errors()
def license_generate_payload_cmd(ctx: typer.Context) -> None:
    """Generate air-gap license request payload.

    For systems without internet access. Send the output to
    Verge.io support to receive a license key.
    """
    vctx = get_context(ctx)
    payload = vctx.client.system.licenses.generate_payload()
    if vctx.output_format == "json":
        output_result(
            {"payload": payload},
            output_format="json",
            quiet=vctx.quiet,
            no_color=vctx.no_color,
        )
    else:
        typer.echo(payload)
