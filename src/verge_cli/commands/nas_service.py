"""NAS service management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import NAS_SERVICE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="service",
    help=(
        "Manage NAS service VMs — the runtime host for VergeOS NAS storage.\n\n"
        "A NAS service is a dedicated VM deployed from the standard NAS VM"
        " recipe. It mounts block devices from the vSAN, runs the filesystem"
        " drivers (ext4, YBFSv2, remote CIFS/NFS), and hosts the kernel NFS"
        " server and Samba daemons that serve shares. Volumes, shares, users,"
        " and syncs are all scoped to a single NAS service.\n\n"
        "Default sizing is 4 cores and 4 GB RAM; adjust based on concurrent"
        " client count, volume I/O, sync job parallelism, and antivirus"
        " workload. `--cpu-cores` / `--memory-gb` changes require a restart"
        " to take effect.\n\n"
        "Use `-o json` for machine-readable output. Services are referenced"
        " by name or numeric key (`$key`); ambiguous names exit with code 7.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List services, optionally filtered by status\n"
        "    vrg nas service list\n"
        "    vrg nas service list --status running\n\n"
        "    # Get one service, as JSON for scripting / agents\n"
        "    vrg -o json nas service get my-nas\n\n"
        "    # Deploy a new service (creates the VM from the NAS recipe)\n"
        "    vrg nas service create --name my-nas --network internal-net \\\n"
        "        --cores 4 --memory-gb 8\n\n"
        "    # Tune concurrency and performance knobs\n"
        "    vrg nas service update my-nas --max-imports 4 --max-syncs 4\n\n"
        "    # Power control — shares are unavailable while stopped\n"
        "    vrg nas service power-on my-nas\n"
        "    vrg nas service power-off my-nas\n"
        "    vrg nas service restart my-nas\n\n"
        "    # View and tune CIFS/SMB settings (workgroup, min protocol, guest map)\n"
        "    vrg nas service cifs-settings my-nas\n"
        "    vrg nas service set-cifs-settings my-nas \\\n"
        "        --workgroup CORP --min-protocol SMB3\n\n"
        "    # View and tune NFS settings (NFSv4, allowed hosts, squash)\n"
        "    vrg nas service nfs-settings my-nas\n"
        "    vrg nas service set-nfs-settings my-nas \\\n"
        "        --enable-nfsv4 --squash root_squash\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "A NAS service is a VM. It **must be powered on** before any of its"
        " volumes will mount or its shares serve traffic. Use `power-on` /"
        " `power-off` / `restart` to control the service VM; `--force` on"
        " `power-off` performs a hard shutdown.\n\n"
        "Volumes are bound to a NAS service at creation and **cannot be"
        " migrated** to another service. Deleting a service with existing"
        " volumes requires `--force` and is destructive.\n\n"
        "CIFS/SMB settings (`set-cifs-settings`) are server-wide for this"
        " service — they apply to all CIFS shares it hosts. NFS settings"
        " (`set-nfs-settings`) are defaults applied to NFS exports on this"
        " service. For per-share configuration, see `vrg nas cifs` and"
        " `vrg nas nfs`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _service_to_dict(svc: Any) -> dict[str, Any]:
    """Convert a NAS service SDK object to a dict for output."""
    return {
        "$key": svc.key,
        "name": svc.name,
        "vm_running": svc.get("vm_running"),
        "volume_count": svc.get("volume_count"),
        "vm_cores": svc.get("vm_cores"),
        "vm_ram": svc.get("vm_ram"),
        "max_imports": svc.get("max_imports"),
        "max_syncs": svc.get("max_syncs"),
    }


def _cifs_settings_to_dict(settings: Any) -> dict[str, Any]:
    """Convert CIFS settings SDK object to a dict for output."""
    return {
        "workgroup": settings.get("workgroup"),
        "server_type": settings.get("server_type"),
        "server_min_protocol": settings.get("server_min_protocol"),
        "map_to_guest": settings.get("map_to_guest"),
        "extended_acl_support": settings.get("extended_acl_support"),
        "ad_status": settings.get("ad_status"),
    }


def _nfs_settings_to_dict(settings: Any) -> dict[str, Any]:
    """Convert NFS settings SDK object to a dict for output."""
    return {
        "enable_nfsv4": settings.get("enable_nfsv4"),
        "allow_all": settings.get("allow_all"),
        "allowed_hosts": settings.get("allowed_hosts"),
        "squash": settings.get("squash"),
        "data_access": settings.get("data_access"),
        "anonuid": settings.get("anonuid"),
        "anongid": settings.get("anongid"),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    status: Annotated[
        str | None,
        typer.Option("--status", "-s", help="Filter by status (running or stopped)"),
    ] = None,
) -> None:
    """List all NAS services.

    **Examples:**

        vrg nas service list
        vrg nas service list --status running
        vrg -o json nas service list
    """
    vctx = get_context(ctx)
    if status is not None:
        services = vctx.client.nas_services.list(status=status)
    else:
        services = vctx.client.nas_services.list()
    data = [_service_to_dict(s) for s in services]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NAS_SERVICE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
) -> None:
    """Get details of a NAS service.

    **Examples:**

        vrg nas service get my-nas
        vrg -o json nas service get 42
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    item = vctx.client.nas_services.get(key)
    output_result(
        _service_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Service name")],
    hostname: Annotated[
        str | None,
        typer.Option("--hostname", help="Hostname (auto-generated from name if omitted)"),
    ] = None,
    network: Annotated[str | None, typer.Option("--network", help="Network name or key")] = None,
    cores: Annotated[int, typer.Option("--cores", help="CPU cores")] = 4,
    memory_gb: Annotated[int, typer.Option("--memory-gb", help="RAM in GB")] = 8,
) -> None:
    """Create a new NAS service.

    Deploys the VergeOS NAS VM recipe, producing a running service VM that
    hosts volumes and shares. Sizing defaults to 4 cores / 8 GB RAM; tune
    for concurrent client count, sync parallelism, and antivirus load.

    **Examples:**

        vrg nas service create --name my-nas --network internal-net
        vrg nas service create --name my-nas --network internal-net --cores 8 --memory-gb 16
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "name": name,
        "cores": cores,
        "memory_gb": memory_gb,
    }
    if hostname is not None:
        kwargs["hostname"] = hostname
    if network is not None:
        kwargs["network"] = network

    result = vctx.client.nas_services.create(**kwargs)
    svc_name = result.name if result else name
    svc_key = result.key if result else "?"
    output_success(
        f"Created NAS service '{svc_name}' (key: {svc_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Service description")
    ] = None,
    cpu_cores: Annotated[
        int | None, typer.Option("--cpu-cores", help="CPU cores (requires restart)")
    ] = None,
    memory_gb: Annotated[
        int | None, typer.Option("--memory-gb", help="RAM in GB (requires restart)")
    ] = None,
    max_imports: Annotated[
        int | None, typer.Option("--max-imports", help="Max concurrent imports (1-10)")
    ] = None,
    max_syncs: Annotated[
        int | None, typer.Option("--max-syncs", help="Max concurrent syncs (1-10)")
    ] = None,
    disable_swap: Annotated[
        bool | None,
        typer.Option("--disable-swap/--enable-swap", help="Disable swap"),
    ] = None,
    read_ahead_kb: Annotated[
        int | None,
        typer.Option("--read-ahead-kb", help="Read-ahead buffer (0/64/128/256/512/1024/2048/4096)"),
    ] = None,
) -> None:
    """Update NAS service settings.

    `--cpu-cores` / `--memory-gb` changes require a service restart to
    take effect. `--max-imports` and `--max-syncs` cap concurrent job
    parallelism (1-10).

    **Examples:**

        vrg nas service update my-nas --max-imports 4 --max-syncs 4
        vrg nas service update my-nas --cpu-cores 8 --memory-gb 16
        vrg nas service update my-nas --read-ahead-kb 1024
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")

    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    if cpu_cores is not None:
        kwargs["cpu_cores"] = cpu_cores
    if memory_gb is not None:
        kwargs["memory_gb"] = memory_gb
    if max_imports is not None:
        kwargs["max_imports"] = max_imports
    if max_syncs is not None:
        kwargs["max_syncs"] = max_syncs
    if disable_swap is not None:
        kwargs["disable_swap"] = disable_swap
    if read_ahead_kb is not None:
        kwargs["read_ahead_kb"] = read_ahead_kb

    vctx.client.nas_services.update(key, **kwargs)
    output_success(f"Updated NAS service '{service}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
    force: Annotated[
        bool, typer.Option("--force", help="Force delete even if volumes exist")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a NAS service.

    This is destructive: it removes the NAS service VM. `--force` is
    required when the service still has volumes attached, and deleting a
    service deletes its volumes and shares. Prompts before acting unless
    `--yes` is passed.

    **Examples:**

        vrg nas service delete my-nas
        vrg nas service delete my-nas --yes
        vrg nas service delete my-nas --force --yes
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")

    if not confirm_action(f"Delete NAS service '{service}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.nas_services.delete(key, force=force)
    output_success(f"Deleted NAS service '{service}'", quiet=vctx.quiet)


@app.command("power-on")
@handle_errors()
def power_on_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
) -> None:
    """Power on a NAS service.

    The service VM must be running before volumes will mount or shares
    serve traffic.

    **Examples:**

        vrg nas service power-on my-nas
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    vctx.client.nas_services.power_on(key)
    output_success(f"Powered on NAS service '{service}'", quiet=vctx.quiet)


@app.command("power-off")
@handle_errors()
def power_off_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
    force: Annotated[bool, typer.Option("--force", help="Force power off (hard shutdown)")] = False,
) -> None:
    """Power off a NAS service.

    Shares and volumes become unavailable until the service is started
    again. `--force` performs a hard shutdown instead of a graceful
    guest-OS shutdown.

    **Examples:**

        vrg nas service power-off my-nas
        vrg nas service power-off my-nas --force
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    vctx.client.nas_services.power_off(key, force=force)
    output_success(f"Powered off NAS service '{service}'", quiet=vctx.quiet)


@app.command("restart")
@handle_errors()
def restart_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
) -> None:
    """Restart a NAS service.

    Use this after changing `--cpu-cores` / `--memory-gb` to apply the
    new VM sizing.

    **Examples:**

        vrg nas service restart my-nas
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    vctx.client.nas_services.restart(key)
    output_success(f"Restarted NAS service '{service}'", quiet=vctx.quiet)


@app.command("cifs-settings")
@handle_errors()
def cifs_settings_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
) -> None:
    """Display CIFS/SMB settings for a NAS service.

    Shows the server-wide CIFS configuration (workgroup, minimum
    protocol, guest mapping, AD join status). Per-share settings live on
    `vrg nas cifs`.

    **Examples:**

        vrg nas service cifs-settings my-nas
        vrg -o json nas service cifs-settings my-nas
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    settings = vctx.client.nas_services.get_cifs_settings(key)
    output_result(
        _cifs_settings_to_dict(settings),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("set-cifs-settings")
@handle_errors()
def set_cifs_settings_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
    workgroup: Annotated[
        str | None, typer.Option("--workgroup", help="NetBIOS workgroup name")
    ] = None,
    min_protocol: Annotated[
        str | None,
        typer.Option(
            "--min-protocol",
            help="Minimum SMB protocol (none, SMB2, SMB2_02, SMB2_10, SMB3, SMB3_00, SMB3_02, SMB3_11)",
        ),
    ] = None,
    guest_mapping: Annotated[
        str | None,
        typer.Option(
            "--guest-mapping", help="Guest access mode (never, bad user, bad password, bad uid)"
        ),
    ] = None,
    extended_acl: Annotated[
        bool | None,
        typer.Option("--extended-acl/--no-extended-acl", help="Enable extended ACL support"),
    ] = None,
) -> None:
    """Update CIFS/SMB settings for a NAS service.

    These settings are server-wide — they apply to every CIFS share on
    this service. Set `--min-protocol SMB3` or higher to disable legacy
    SMBv1/v2 clients.

    **Examples:**

        vrg nas service set-cifs-settings my-nas --workgroup CORP
        vrg nas service set-cifs-settings my-nas --min-protocol SMB3
        vrg nas service set-cifs-settings my-nas --extended-acl
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")

    kwargs: dict[str, Any] = {}
    if workgroup is not None:
        kwargs["workgroup"] = workgroup
    if min_protocol is not None:
        kwargs["min_protocol"] = min_protocol
    if guest_mapping is not None:
        kwargs["guest_mapping"] = guest_mapping
    if extended_acl is not None:
        kwargs["extended_acl_support"] = extended_acl

    vctx.client.nas_services.set_cifs_settings(key, **kwargs)
    output_success(f"Updated CIFS settings for NAS service '{service}'", quiet=vctx.quiet)


@app.command("nfs-settings")
@handle_errors()
def nfs_settings_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
) -> None:
    """Display NFS settings for a NAS service.

    Shows default NFS server settings (NFSv4 on/off, allowed hosts,
    squash, anon uid/gid). These are defaults applied to exports — per
    share config is on `vrg nas nfs`.

    **Examples:**

        vrg nas service nfs-settings my-nas
        vrg -o json nas service nfs-settings my-nas
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
    settings = vctx.client.nas_services.get_nfs_settings(key)
    output_result(
        _nfs_settings_to_dict(settings),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("set-nfs-settings")
@handle_errors()
def set_nfs_settings_cmd(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="NAS service name or key")],
    enable_nfsv4: Annotated[
        bool | None,
        typer.Option("--enable-nfsv4/--no-nfsv4", help="Enable NFSv4 protocol support"),
    ] = None,
    allowed_hosts: Annotated[
        str | None,
        typer.Option("--allowed-hosts", help="Comma-separated host/CIDR list"),
    ] = None,
    allow_all: Annotated[
        bool | None,
        typer.Option("--allow-all/--no-allow-all", help="Allow all hosts to access NFS exports"),
    ] = None,
    squash: Annotated[
        str | None,
        typer.Option("--squash", help="Squash mode (root_squash, all_squash, no_root_squash)"),
    ] = None,
    data_access: Annotated[
        str | None,
        typer.Option("--data-access", help="Access mode (ro, rw)"),
    ] = None,
    anon_uid: Annotated[int | None, typer.Option("--anon-uid", help="Anonymous user ID")] = None,
    anon_gid: Annotated[int | None, typer.Option("--anon-gid", help="Anonymous group ID")] = None,
    no_acl: Annotated[
        bool | None,
        typer.Option("--no-acl/--acl", help="Disable ACL support"),
    ] = None,
    insecure: Annotated[
        bool | None,
        typer.Option("--insecure/--secure", help="Allow connections from non-privileged ports"),
    ] = None,
    async_mode: Annotated[
        bool | None,
        typer.Option("--async/--sync", help="Enable async mode for performance"),
    ] = None,
) -> None:
    """Update NFS settings for a NAS service.

    Server-wide NFS defaults. Use `--allowed-hosts` to restrict mounts
    to specific CIDRs; `--allow-all` exports to the world. Squash modes:
    `root_squash`, `all_squash`, `no_root_squash`.

    **Examples:**

        vrg nas service set-nfs-settings my-nas --enable-nfsv4
        vrg nas service set-nfs-settings my-nas --allowed-hosts 10.0.0.0/24,10.0.1.0/24
        vrg nas service set-nfs-settings my-nas --squash root_squash --async
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")

    kwargs: dict[str, Any] = {}
    if enable_nfsv4 is not None:
        kwargs["enable_nfsv4"] = enable_nfsv4
    if allowed_hosts is not None:
        kwargs["allowed_hosts"] = allowed_hosts
    if allow_all is not None:
        kwargs["allow_all"] = allow_all
    if squash is not None:
        kwargs["squash"] = squash
    if data_access is not None:
        kwargs["data_access"] = data_access
    if anon_uid is not None:
        kwargs["anon_uid"] = anon_uid
    if anon_gid is not None:
        kwargs["anon_gid"] = anon_gid
    if no_acl is not None:
        kwargs["no_acl"] = no_acl
    if insecure is not None:
        kwargs["insecure"] = insecure
    if async_mode is not None:
        kwargs["async_mode"] = async_mode

    vctx.client.nas_services.set_nfs_settings(key, **kwargs)
    output_success(f"Updated NFS settings for NAS service '{service}'", quiet=vctx.quiet)
