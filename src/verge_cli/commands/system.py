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
    help=(
        "Inspect and manage the VergeOS cloud itself.\n\n"
        "This group covers system-wide state that isn't scoped to a single"
        " resource — version and build identity, aggregate counts of running"
        " resources, cloud-wide settings, installed licenses, and the"
        " support diagnostic bundles used for escalations. Most commands"
        " read from the cloud root and require admin-level access. Use"
        " `vrg doctor` for a scripted health audit that layers on top of"
        " this data.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `version`, `os_version`, `cloud_name`, `vms_total`, `vms_online`,"
        " `nodes_total`, `nodes_online`, `alarms_total`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Version and dashboard-style counts for the current cloud\n"
        "    vrg system info\n"
        "    vrg -o json system info\n\n"
        "    # VergeOS and underlying OS version\n"
        "    vrg system version\n\n"
        "    # Full resource inventory (opt-in per category)\n"
        "    vrg system inventory\n"
        "    vrg system inventory --vms --networks --no-tenants\n\n"
        "    # Cloud-wide settings (see subcommands below)\n"
        "    vrg system settings list --modified\n"
        "    vrg system settings get ui.theme\n\n"
        "    # License inventory and air-gap provisioning\n"
        "    vrg system license list\n"
        "    vrg system license generate-payload\n\n"
        "    # Create a diagnostic bundle for Verge.io support\n"
        "    vrg system diag create support-2026-04-17 --send-to-support\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`vrg system info` reports the cloud the current profile is"
        " connected to; when a tenant scope is active, counts reflect that"
        " tenant. Run against the provider cloud for system-wide numbers.\n\n"
        "Settings keys are string-addressed and mostly undocumented — pull"
        " the list with `settings list` and filter with `--modified` to see"
        " what has been changed from defaults before editing blindly."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(system_diag.app, name="diag")

# ---------------------------------------------------------------------------
# Settings sub-group
# ---------------------------------------------------------------------------
settings_app = typer.Typer(
    name="settings",
    help=(
        "Read and modify cloud-wide system settings.\n\n"
        "Settings are the key/value knobs that control platform behavior"
        " across the entire cloud — UI defaults, scheduler tunables,"
        " security toggles, notification endpoints, and similar. Each"
        " setting has a `key`, a current `value`, a `default_value`, and a"
        " `modified` flag indicating whether it has been changed from"
        " default. Settings apply to the whole cloud, not per-tenant.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `key`, `value`, `default_value`, `modified`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # All settings, or only those changed from default\n"
        "    vrg system settings list\n"
        "    vrg system settings list --modified\n\n"
        "    # Inspect one setting\n"
        "    vrg -o json system settings get ui.theme\n\n"
        "    # Change a setting, then revert to default\n"
        "    vrg system settings set ui.theme dark\n"
        "    vrg system settings reset ui.theme\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Settings are addressed by string key, not numeric key. There is no"
        " central catalog of valid keys — use `list` to discover what is"
        " available before editing. Most settings take effect immediately;"
        " a few require a service restart (the setting description, when"
        " present, calls this out)."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
app.add_typer(settings_app, name="settings")

# ---------------------------------------------------------------------------
# License sub-group
# ---------------------------------------------------------------------------
license_app = typer.Typer(
    name="license",
    help=(
        "Inspect and install VergeOS licenses.\n\n"
        "Licenses gate platform features and feature tiers for the cloud."
        " Connected systems pull and renew licenses automatically; air-gap"
        " systems require a manual exchange — generate a request payload,"
        " send it to Verge.io support, and install the returned license"
        " key. Each license record carries `is_valid`, `valid_from`,"
        " `valid_until`, a comma-separated `features` string, and an"
        " `auto_renewal` flag.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `is_valid`, `valid_from`, `valid_until`, `features`,"
        " `auto_renewal`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List installed licenses\n"
        "    vrg system license list\n"
        "    vrg -o json system license list\n\n"
        "    # Inspect one license by name or key\n"
        "    vrg system license get 1\n"
        "    vrg system license get enterprise\n\n"
        "    # Air-gap workflow: produce a payload to send to support\n"
        "    vrg system license generate-payload > request.txt\n\n"
        "    # Install the license text returned by support\n"
        '    vrg system license add --license-text "$(cat license.key)"\n\n'
        "---\n\n"
        "**Notes:**\n\n"
        "`generate-payload` and `add` are only needed on air-gap systems."
        " Cloud-connected systems provision and renew licenses"
        " automatically; manual intervention there is usually a sign of"
        " broken outbound connectivity to licensing."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
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
    """Display system information and statistics.

    Examples:

        vrg system info
        vrg -o json system info
        vrg -o json system info --query "vms_online"

    Reports version, cloud name, and dashboard-style counts for the
    cloud the current profile is connected to. When a tenant scope
    is active, counts reflect that tenant — run against the provider
    cloud for system-wide numbers.
    """
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
    """Display VergeOS version.

    Examples:

        vrg system version
        vrg -o json system version

    Reports VergeOS platform version plus the underlying OS version.
    Useful for agent pre-flight checks that need to verify API
    compatibility before issuing calls.
    """
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
    """Display system inventory.

    Examples:

        vrg system inventory
        vrg system inventory --vms --networks --no-tenants
        vrg -o json system inventory --nodes

    Each category flag is tri-state (enabled / disabled / unset) —
    omit to use server defaults, pass `--vms` to force-include, or
    `--no-vms` to force-exclude. Expensive categories (storage,
    nodes) may add noticeable latency on large clouds.
    """
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
    """List system settings.

    Examples:

        vrg system settings list
        vrg system settings list --modified
        vrg -o json system settings list --query "[?modified==`true`]"

    Settings are cloud-wide key/value knobs. `--modified` / `-m`
    restricts output to settings changed from their default — the
    quickest way to audit what has been tuned on a cloud.
    """
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
    """Get a specific system setting.

    Examples:

        vrg system settings get ui.theme
        vrg -o json system settings get ui.theme

    Settings are addressed by string key, not numeric key. Use
    `vrg system settings list` to discover valid keys.
    """
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
    """Set a system setting value.

    Examples:

        vrg system settings set ui.theme dark
        vrg system settings set max.vm_cpus 64

    Applies cloud-wide. Most settings take effect immediately; a few
    require a service restart — the setting description (visible in
    `get`) notes this when applicable.
    """
    vctx = get_context(ctx)
    vctx.client.system.settings.update(key, value)
    output_success(f"Set '{key}' to '{value}'", quiet=vctx.quiet)


@settings_app.command("reset")
@handle_errors()
def settings_reset_cmd(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Setting key")],
) -> None:
    """Reset a system setting to its default value.

    Examples:

        vrg system settings reset ui.theme

    Reverts `key` back to `default_value`. Pair with
    `vrg system settings list --modified` to find candidates.
    """
    vctx = get_context(ctx)
    vctx.client.system.settings.reset(key)
    output_success(f"Reset '{key}' to default", quiet=vctx.quiet)


# ---------------------------------------------------------------------------
# License sub-commands
# ---------------------------------------------------------------------------


@license_app.command("list")
@handle_errors()
def license_list_cmd(ctx: typer.Context) -> None:
    """List system licenses.

    Examples:

        vrg system license list
        vrg -o json system license list
        vrg -o json system license list --query "[?is_valid==`false`]"

    Shows every installed license with `is_valid`, `valid_until`,
    `features`, and `auto_renewal`. Use `--query` to surface expired
    or soon-to-expire entries.
    """
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
    """Get details of a license.

    Examples:

        vrg system license get 1
        vrg system license get enterprise
        vrg -o json system license get enterprise

    Accepts either numeric `$key` or license `name`. Ambiguous name
    matches exit with code 7.
    """
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
    """Install a license key (for air-gap systems).

    Examples:

        vrg system license add --license-text "$(cat license.key)"

    Installs the license text returned by Verge.io support after an
    air-gap exchange. Cloud-connected systems provision licenses
    automatically — manual `add` there usually indicates broken
    outbound connectivity to licensing.
    """
    vctx = get_context(ctx)
    result = vctx.client.system.licenses.add(license_text)
    output_success(f"Added license (key: {result.key})", quiet=vctx.quiet)


@license_app.command("generate-payload")
@handle_errors()
def license_generate_payload_cmd(ctx: typer.Context) -> None:
    """Generate air-gap license request payload.

    Examples:

        vrg system license generate-payload > request.txt
        vrg -o json system license generate-payload

    For systems without internet access. Send the output to Verge.io
    support to receive a license key, then install with
    `vrg system license add --license-text ...`.
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
