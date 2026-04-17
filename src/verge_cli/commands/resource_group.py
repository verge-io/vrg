"""Resource group management commands for device passthrough."""

from __future__ import annotations

import re
from typing import Annotated, Any

import typer

from verge_cli.columns import BOOL_STYLES, ColumnDef, format_bool_yn, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_error, output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="resource-group",
    help=(
        "Manage resource groups for physical device passthrough on VergeOS.\n\n"
        "**Resource groups** bundle physical host devices — PCI cards, USB"
        " devices, host GPUs, NVIDIA vGPU profiles, or SR-IOV NIC virtual"
        " functions — into named pools that can be attached to VMs. When a"
        " VM requests a device from a group, the scheduler picks a free"
        " member on a node capable of hosting the workload.\n\n"
        "Five device types are supported: `pci` (generic PCI passthrough),"
        " `usb` (USB device passthrough), `host-gpu` (full-GPU PCI"
        " passthrough, `max_instances=1` per GPU), `nvidia-vgpu` (NVIDIA"
        " vGPU time-slicing across multiple VMs — requires a licensed host"
        " driver uploaded as a custom driver), and `sriov-nic` (SR-IOV"
        " virtual functions carved out of a physical NIC).\n\n"
        "Resource groups are **not** the same thing as tags. Tags"
        " (`vrg tag`) are metadata labels for classification; resource"
        " groups allocate real hardware. PCI passthrough and full-GPU"
        " passthrough prevent live migration — the physical device is"
        " exclusively bound to one VM on one node.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every resource group\n"
        "    vrg resource-group list\n\n"
        "    # Machine-readable output for agents\n"
        "    vrg -o json resource-group list\n\n"
        "    # Narrow by device type or class\n"
        "    vrg resource-group list --type host-gpu\n"
        "    vrg resource-group list --class gpu --enabled\n\n"
        "    # Inspect a single group (UUID or name)\n"
        "    vrg resource-group get gpu-pool\n"
        "    vrg -o json resource-group get gpu-pool\n\n"
        "    # Create a GPU passthrough pool\n"
        "    vrg resource-group create --name gpu-pool --type host-gpu \\\n"
        "        --description 'Full GPUs for AI workloads'\n\n"
        "    # Create an NVIDIA vGPU pool (driver file is required)\n"
        "    vrg resource-group create --name vgpu-pool --type nvidia-vgpu \\\n"
        "        --driver-file 42 --vgpu-profile 7 --make-guest-driver-iso\n\n"
        "    # Create an SR-IOV NIC pool with 8 virtual functions\n"
        "    vrg resource-group create --name sriov-pool --type sriov-nic \\\n"
        "        --vf-count 8 --native-vlan 100\n\n"
        "    # Disable a pool without deleting it\n"
        "    vrg resource-group update gpu-pool --no-enabled\n\n"
        "    # Delete a pool (prompts unless --yes)\n"
        "    vrg resource-group delete gpu-pool --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Resource groups are referenced by **UUID** or **name**. Ambiguous"
        " name resolution exits with code 7.\n\n"
        "PCI and host-GPU passthrough require `iommu=true` on the node and"
        " IOMMU/VT-d enabled in BIOS. NVIDIA vGPU requires the licensed"
        " host driver installed as a custom driver (and a node reboot to"
        " activate). See `vrg node` and the node lifecycle docs.\n\n"
        "VMs with PCI or full-GPU devices **cannot be live migrated** —"
        " the device is exclusively bound. NVIDIA vGPU live migration is"
        " experimental and gated on `allow_vgpu_migration`."
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

# CLI device type -> SDK API value
DEVICE_TYPE_MAP: dict[str, str] = {
    "pci": "node_pci_devices",
    "usb": "node_usb_devices",
    "host-gpu": "node_host_gpu_devices",
    "nvidia-vgpu": "node_nvidia_vgpu_devices",
    "sriov-nic": "node_sriov_nic_devices",
}

RESOURCE_GROUP_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="UUID"),
    ColumnDef("name"),
    ColumnDef("device_type", header="Device Type"),
    ColumnDef("device_class", header="Class"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("resource_count", header="Devices"),
    ColumnDef("description", wide_only=True),
    ColumnDef("created_at", header="Created", format_fn=format_epoch, wide_only=True),
]

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _group_to_dict(group: Any) -> dict[str, Any]:
    """Convert a ResourceGroup SDK object to a dict for output."""
    created_at = group.created_at
    return {
        "$key": str(group.key),
        "name": str(group.name),
        "device_type": str(group.device_type_display),
        "device_class": str(group.device_class_display),
        "enabled": bool(group.is_enabled),
        "resource_count": int(group.resource_count),
        "description": str(group.description),
        "created_at": created_at.timestamp() if created_at else None,
    }


def _resolve_resource_group(client: Any, identifier: str) -> str:
    """Resolve resource group identifier (UUID or name) to UUID key."""
    if _UUID_PATTERN.match(identifier):
        # Verify it exists by fetching it
        group = client.resource_groups.get(identifier)
        return str(group.key)
    group = client.resource_groups.get(name=identifier)
    return str(group.key)


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter_expr: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    device_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by device type (pci, usb, host-gpu, nvidia-vgpu, sriov-nic).",
        ),
    ] = None,
    device_class: Annotated[
        str | None,
        typer.Option(
            "--class",
            help="Filter by device class (gpu, vgpu, storage, network, usb, pci, etc.).",
        ),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled/disabled status."),
    ] = None,
) -> None:
    """List resource groups.

    Examples:

        vrg resource-group list
        vrg resource-group list --type host-gpu
        vrg resource-group list --class gpu --enabled
        vrg -o json resource-group list --query "[?enabled].name"

    Useful `--query` fields: `name`, `device_type`, `device_class`,
    `enabled`, `resource_count`. `--type` accepts `pci`, `usb`,
    `host-gpu`, `nvidia-vgpu`, `sriov-nic`.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.resource_groups.list(), _group_to_dict, RESOURCE_GROUP_COLUMNS
        )
        return
    vctx = get_context(ctx)

    if device_type is not None:
        # Validate device type
        api_type = DEVICE_TYPE_MAP.get(device_type)
        if api_type is None:
            valid = ", ".join(sorted(DEVICE_TYPE_MAP.keys()))
            output_error(f"Invalid device type '{device_type}'. Valid: {valid}")
            raise typer.Exit(2)
        groups = vctx.client.resource_groups.list_by_type(device_type=api_type, enabled=enabled)
    elif device_class is not None:
        groups = vctx.client.resource_groups.list_by_class(
            device_class=device_class, enabled=enabled
        )
    elif enabled is True:
        groups = vctx.client.resource_groups.list_enabled()
    elif enabled is False:
        groups = vctx.client.resource_groups.list_disabled()
    else:
        kwargs: dict[str, Any] = {}
        if filter_expr is not None:
            kwargs["filter"] = filter_expr
        groups = vctx.client.resource_groups.list(**kwargs)

    output_result(
        [_group_to_dict(g) for g in groups],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RESOURCE_GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Resource group UUID or name.")],
) -> None:
    """Get a resource group by UUID or name.

    Examples:

        vrg resource-group get gpu-pool
        vrg -o json resource-group get gpu-pool
        vrg resource-group get 550e8400-e29b-41d4-a716-446655440000

    Accepts either the group's UUID (`$key`) or name. Ambiguous names
    exit with code 7 — use the UUID to disambiguate.
    """
    vctx = get_context(ctx)
    uuid_key = _resolve_resource_group(vctx.client, group)
    item = vctx.client.resource_groups.get(uuid_key)
    output_result(
        _group_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RESOURCE_GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Resource group name.")],
    device_type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="Device type (pci, usb, host-gpu, nvidia-vgpu, sriov-nic).",
        ),
    ],
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Description."),
    ] = "",
    device_class: Annotated[
        str | None,
        typer.Option("--device-class", help="Device class (gpu, storage, network, etc.)."),
    ] = None,
    no_enabled: Annotated[
        bool,
        typer.Option("--no-enabled", help="Create in disabled state."),
    ] = False,
    # USB options
    allow_guest_reset: Annotated[
        bool | None,
        typer.Option(
            "--allow-guest-reset/--no-allow-guest-reset",
            help="Allow VM to reset USB device (USB type only).",
        ),
    ] = None,
    # NVIDIA vGPU options
    driver_file: Annotated[
        int | None,
        typer.Option("--driver-file", help="Driver file key (nvidia-vgpu type, required)."),
    ] = None,
    vgpu_profile: Annotated[
        int | None,
        typer.Option("--vgpu-profile", help="vGPU profile key (nvidia-vgpu type)."),
    ] = None,
    make_guest_driver_iso: Annotated[
        bool,
        typer.Option(
            "--make-guest-driver-iso", help="Auto-create guest driver ISO (nvidia-vgpu type)."
        ),
    ] = False,
    driver_iso: Annotated[
        int | None,
        typer.Option("--driver-iso", help="Guest driver ISO file key (nvidia-vgpu type)."),
    ] = None,
    # SR-IOV NIC options
    vf_count: Annotated[
        int | None,
        typer.Option("--vf-count", help="Virtual function count (sriov-nic type)."),
    ] = None,
    native_vlan: Annotated[
        int | None,
        typer.Option("--native-vlan", help="Native VLAN tag (sriov-nic type)."),
    ] = None,
) -> None:
    """Create a new resource group.

    Examples:

        # Full-GPU passthrough pool for AI workloads
        vrg resource-group create --name gpu-pool --type host-gpu \\
            --description "Full GPUs for AI workloads"

        # NVIDIA vGPU pool (driver file key required)
        vrg resource-group create --name vgpu-pool --type nvidia-vgpu \\
            --driver-file 42 --vgpu-profile 7 --make-guest-driver-iso

        # SR-IOV NIC pool with 8 virtual functions
        vrg resource-group create --name sriov-pool --type sriov-nic \\
            --vf-count 8 --native-vlan 100

        # USB passthrough with guest-initiated reset allowed
        vrg resource-group create --name usb-pool --type usb \\
            --allow-guest-reset

    Device-type-specific flags only apply to their type and are
    ignored elsewhere. `nvidia-vgpu` requires `--driver-file` (the key
    of a previously uploaded licensed driver). `pci` and `host-gpu`
    require IOMMU/VT-d enabled on each candidate node.
    """
    vctx = get_context(ctx)

    # Validate device type
    if device_type not in DEVICE_TYPE_MAP:
        valid = ", ".join(sorted(DEVICE_TYPE_MAP.keys()))
        output_error(f"Invalid device type '{device_type}'. Valid: {valid}")
        raise typer.Exit(2)

    enabled = not no_enabled

    if device_type == "pci":
        kwargs: dict[str, Any] = {
            "name": name,
            "description": description,
            "enabled": enabled,
        }
        if device_class is not None:
            kwargs["device_class"] = device_class
        result = vctx.client.resource_groups.create_pci(**kwargs)

    elif device_type == "usb":
        usb_kwargs: dict[str, Any] = {
            "name": name,
            "description": description,
            "enabled": enabled,
        }
        if device_class is not None:
            usb_kwargs["device_class"] = device_class
        if allow_guest_reset is not None:
            usb_kwargs["allow_guest_reset"] = allow_guest_reset
        result = vctx.client.resource_groups.create_usb(**usb_kwargs)

    elif device_type == "host-gpu":
        result = vctx.client.resource_groups.create_host_gpu(
            name=name,
            description=description,
            enabled=enabled,
        )

    elif device_type == "nvidia-vgpu":
        if driver_file is None:
            output_error("--driver-file is required for nvidia-vgpu type.")
            raise typer.Exit(2)
        vgpu_kwargs: dict[str, Any] = {
            "name": name,
            "driver_file": driver_file,
            "description": description,
            "enabled": enabled,
        }
        if vgpu_profile is not None:
            vgpu_kwargs["nvidia_vgpu_profile"] = vgpu_profile
        if make_guest_driver_iso:
            vgpu_kwargs["make_guest_driver_iso"] = True
        if driver_iso is not None:
            vgpu_kwargs["driver_iso"] = driver_iso
        result = vctx.client.resource_groups.create_nvidia_vgpu(**vgpu_kwargs)

    elif device_type == "sriov-nic":
        sriov_kwargs: dict[str, Any] = {
            "name": name,
            "description": description,
            "enabled": enabled,
        }
        if vf_count is not None:
            sriov_kwargs["vf_count"] = vf_count
        if native_vlan is not None:
            sriov_kwargs["native_vlan"] = native_vlan
        result = vctx.client.resource_groups.create_sriov_nic(**sriov_kwargs)

    else:
        # Should never reach here due to validation above
        raise typer.Exit(2)

    output_result(
        _group_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RESOURCE_GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Resource group '{name}' created.", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Resource group UUID or name.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--no-enabled", help="Enable or disable."),
    ] = None,
) -> None:
    """Update a resource group.

    Examples:

        # Disable without deleting
        vrg resource-group update gpu-pool --no-enabled

        # Rename and re-describe
        vrg resource-group update gpu-pool --name ai-gpu-pool \\
            --description "Reserved for AI training"

        # Re-enable after a config change
        vrg resource-group update gpu-pool --enabled

    Only name, description, and enabled state are editable here. To
    change device type or device-type-specific options, delete and
    recreate the group.
    """
    vctx = get_context(ctx)
    uuid_key = _resolve_resource_group(vctx.client, group)

    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if enabled is not None:
        updates["enabled"] = enabled

    if not updates:
        output_error("No updates specified.")
        raise typer.Exit(2)

    result = vctx.client.resource_groups.update(uuid_key, **updates)
    output_result(
        _group_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RESOURCE_GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Resource group '{group}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Resource group UUID or name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a resource group.

    Examples:

        vrg resource-group delete gpu-pool
        vrg resource-group delete gpu-pool --yes

    Destructive: VMs that reference this group for device
    passthrough will fail to schedule on their next start. Detach
    the group from each VM first, or confirm no VMs depend on it.
    """
    vctx = get_context(ctx)
    uuid_key = _resolve_resource_group(vctx.client, group)

    if not confirm_action(f"Delete resource group '{group}'?", yes=yes):
        raise typer.Abort()

    vctx.client.resource_groups.delete(uuid_key)
    output_success(f"Resource group '{group}' deleted.", quiet=vctx.quiet)
