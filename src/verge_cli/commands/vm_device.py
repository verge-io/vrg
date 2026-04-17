"""VM device sub-resource commands (TPM only)."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import DEVICE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="device",
    help=(
        "Manage emulated devices attached to a VM.\n\n"
        "Currently supports TPM (Trusted Platform Module) devices. A TPM"
        " provides hardware-backed security functions — required by Windows 11"
        " and useful for disk encryption, secure boot attestation, and key"
        " storage. Models: `crb` (Command Response Buffer, recommended) or"
        " `tis` (TIS interface, legacy). Versions: `1` (TPM 1.2) or `2`"
        " (TPM 2.0, recommended).\n\n"
        "Use `-o json` for structured output. The first argument to every"
        " command is the parent VM (name or key).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg vm device list web-01\n\n"
        "    vrg vm device create web-01\n\n"
        "    vrg vm device create web-01 --model tis --version 1\n\n"
        "    vrg vm device delete web-01 tpm-0 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Devices can be marked `--optional` so the VM still boots if the"
        " device cannot be provisioned on the target node."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


def _get_vm(ctx: typer.Context, vm_identifier: str) -> tuple[Any, Any]:
    """Get the VergeContext and VM object."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.vms, vm_identifier, "VM")
    vm_obj = vctx.client.vms.get(key)
    return vctx, vm_obj


def _device_to_dict(device: Any) -> dict[str, Any]:
    """Convert a Device object to a dict for output."""
    return {
        "$key": device.key,
        "name": device.name,
        "device_type": device.device_type,
        "enabled": device.is_enabled,
        "optional": device.is_optional,
    }


def _resolve_device(vm_obj: Any, identifier: str) -> int:
    """Resolve a device name or ID to a key."""
    if identifier.isdigit():
        return int(identifier)
    devices = vm_obj.devices.list()
    matches = [d for d in devices if d.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(f"Error: Multiple devices match '{identifier}'. Use a numeric key.", err=True)
        raise typer.Exit(7)
    typer.echo(f"Error: Device '{identifier}' not found.", err=True)
    raise typer.Exit(6)


@app.command("list")
@handle_errors()
def device_list(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
) -> None:
    """List devices on a VM.

    **Examples:**

        vrg vm device list web-01
        vrg -o json vm device list web-01
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    devices = vm_obj.devices.list()
    data = [_device_to_dict(d) for d in devices]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=DEVICE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def device_get(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    device: Annotated[str, typer.Argument(help="Device name or key")],
) -> None:
    """Get details of a VM device.

    **Examples:**

        vrg vm device get web-01 tpm-0
        vrg -o json vm device get web-01 42
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    device_key = _resolve_device(vm_obj, device)
    device_obj = vm_obj.devices.get(device_key)
    output_result(
        _device_to_dict(device_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def device_create(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Device name")] = None,
    model: Annotated[str, typer.Option("--model", "-m", help="TPM model (tis, crb)")] = "crb",
    version: Annotated[str, typer.Option("--version", "-V", help="TPM version (1, 2)")] = "2",
) -> None:
    """Add a TPM device to a VM.

    Defaults to TPM 2.0 with the CRB model. The VM must be stopped to
    add a device.

    **Examples:**

        vrg vm device create web-01
        vrg vm device create web-01 --model tis --version 1
        vrg vm device create win-11 --name tpm-win
    """
    vctx, vm_obj = _get_vm(ctx, vm)

    device_obj = vm_obj.devices.create(
        device_type="tpm",
        name=name,
        settings={"model": model, "version": version},
    )

    output_success(f"Created TPM device (key: {device_obj.key})", quiet=vctx.quiet)
    output_result(
        _device_to_dict(device_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def device_update(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    device: Annotated[str, typer.Argument(help="Device name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New device name")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description")
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--no-enabled", help="Enable or disable the device"),
    ] = None,
    optional: Annotated[
        bool | None,
        typer.Option("--optional/--no-optional", help="Toggle whether device is optional"),
    ] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="TPM model (tis, crb)")] = None,
    version: Annotated[
        str | None, typer.Option("--version", "-V", help="TPM version (1, 2)")
    ] = None,
) -> None:
    """Update a VM device.

    Only the flags you supply are changed.

    **Examples:**

        vrg vm device update web-01 tpm-0 --optional
        vrg vm device update web-01 tpm-0 --no-enabled
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    device_key = _resolve_device(vm_obj, device)

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if enabled is not None:
        kwargs["enabled"] = enabled
    if optional is not None:
        kwargs["optional"] = optional

    # Pack TPM settings if provided
    settings: dict[str, str] = {}
    if model is not None:
        settings["model"] = model
    if version is not None:
        settings["version"] = version
    if settings:
        kwargs["settings_args"] = settings

    if not kwargs:
        typer.echo("Error: No update options provided.", err=True)
        raise typer.Exit(2)

    vm_obj.devices.update(device_key, **kwargs)
    device_obj = vm_obj.devices.get(device_key)
    output_success(f"Updated device '{device}'", quiet=vctx.quiet)
    output_result(
        _device_to_dict(device_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def device_delete(
    ctx: typer.Context,
    vm: Annotated[str, typer.Argument(help="VM name or key")],
    device: Annotated[str, typer.Argument(help="Device name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Remove a device from a VM.

    Prompts for confirmation unless `--yes` is passed.

    **Examples:**

        vrg vm device delete web-01 tpm-0
        vrg vm device delete web-01 tpm-0 --yes
    """
    vctx, vm_obj = _get_vm(ctx, vm)
    device_key = _resolve_device(vm_obj, device)

    if not confirm_action(f"Delete device '{device}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vm_obj.devices.delete(device_key)
    output_success(f"Deleted device '{device}'", quiet=vctx.quiet)
