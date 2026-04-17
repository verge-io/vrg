"""VM import management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef
from verge_cli.commands import vm_import_log
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource

app = typer.Typer(
    name="import",
    help=(
        "Manage VM import jobs from OVA/OVF and other formats.\n\n"
        "VM imports convert external virtual machine packages (OVA, OVF, VMDK)"
        " into native VergeOS VMs. An import job defines the source, conversion"
        " options (drive interface, NIC interface, MAC preservation), and"
        " preferred storage tier. Use `start` to begin the conversion and"
        " `log` to monitor progress.\n\n"
        "Use `-o json` for structured output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg vm import list\n\n"
        "    vrg vm import create --name migrate-web --file 42\n\n"
        "    vrg vm import start migrate-web\n\n"
        "    vrg vm import cancel migrate-web\n\n"
        "    vrg vm import delete migrate-web --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Import jobs run asynchronously. Use `vrg vm import log` to view"
        " conversion progress and errors. By default, MAC addresses are"
        " preserved and drive formats are converted to native vSAN format."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(vm_import_log.app, name="log")

VM_IMPORT_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status"),
    ColumnDef("file", wide_only=True),
    ColumnDef("volume", wide_only=True),
    ColumnDef("preserve_macs", header="Preserve MACs", wide_only=True),
]


def _import_to_dict(imp: Any) -> dict[str, Any]:
    """Convert a VmImport SDK object to a dict for output."""
    return {
        "$key": imp.key,
        "name": imp.name,
        "status": imp.get("status", ""),
        "file": imp.get("file", ""),
        "volume": imp.get("volume", ""),
        "preserve_macs": imp.get("preserve_macs"),
        "preserve_drive_format": imp.get("preserve_drive_format"),
        "preferred_tier": imp.get("preferred_tier", ""),
        "no_optical_drives": imp.get("no_optical_drives"),
        "override_drive_interface": imp.get("override_drive_interface", ""),
        "override_nic_interface": imp.get("override_nic_interface", ""),
        "cleanup_on_delete": imp.get("cleanup_on_delete"),
    }


def _resolve_import(vctx: Any, identifier: str) -> str:
    """Resolve a VM import identifier to a hex key."""
    return resolve_nas_resource(
        vctx.client.vm_imports,
        identifier,
        resource_type="VM import",
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
) -> None:
    """List VM import jobs.

    **Examples:**

        vrg vm import list
        vrg -o json vm import list
    """
    vctx = get_context(ctx)
    imports = vctx.client.vm_imports.list()
    data = [_import_to_dict(i) for i in imports]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_IMPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    vm_import: Annotated[str, typer.Argument(help="VM import name or key.")],
) -> None:
    """Get a VM import job by name or key.

    **Examples:**

        vrg vm import get migrate-web
        vrg -o json vm import get 42
    """
    vctx = get_context(ctx)
    key = _resolve_import(vctx, vm_import)
    item = vctx.client.vm_imports.get(key)
    output_result(
        _import_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_IMPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Import job name.")],
    file: Annotated[
        int | None,
        typer.Option("--file", help="File key (integer) for the import source."),
    ] = None,
    volume: Annotated[
        str | None,
        typer.Option("--volume", help="Volume name or path for import source."),
    ] = None,
    volume_path: Annotated[
        str | None,
        typer.Option("--volume-path", help="Path within the volume."),
    ] = None,
    shared_object: Annotated[
        int | None,
        typer.Option("--shared-object", help="Shared object key."),
    ] = None,
    preserve_macs: Annotated[
        bool,
        typer.Option("--preserve-macs/--no-preserve-macs", help="Preserve MAC addresses."),
    ] = True,
    preserve_drive_format: Annotated[
        bool,
        typer.Option(
            "--preserve-drive-format/--no-preserve-drive-format",
            help="Preserve drive format.",
        ),
    ] = False,
    preferred_tier: Annotated[
        str | None,
        typer.Option("--preferred-tier", help="Preferred storage tier."),
    ] = None,
    no_optical_drives: Annotated[
        bool,
        typer.Option("--no-optical-drives", help="Skip optical drives during import."),
    ] = False,
    override_drive_interface: Annotated[
        str | None,
        typer.Option("--override-drive-interface", help="Override drive interface type."),
    ] = None,
    override_nic_interface: Annotated[
        str | None,
        typer.Option("--override-nic-interface", help="Override NIC interface type."),
    ] = None,
    cleanup_on_delete: Annotated[
        bool,
        typer.Option(
            "--cleanup-on-delete/--no-cleanup-on-delete",
            help="Clean up imported resources on delete.",
        ),
    ] = True,
) -> None:
    """Create a new VM import job.

    Provide a source via `--file` (media catalog key) or `--volume` + `--volume-path`.
    The job is created but not started — use `vrg vm import start` to begin.

    **Examples:**

        vrg vm import create --name migrate-web --file 42
        vrg vm import create --name migrate-db --volume backups --volume-path db-server.ova
        vrg vm import create --name migrate-win --file 42 --override-drive-interface virtio-scsi
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "name": name,
        "preserve_macs": preserve_macs,
        "preserve_drive_format": preserve_drive_format,
        "no_optical_drives": no_optical_drives,
        "cleanup_on_delete": cleanup_on_delete,
    }
    if file is not None:
        kwargs["file"] = file
    if volume is not None:
        kwargs["volume"] = volume
    if volume_path is not None:
        kwargs["volume_path"] = volume_path
    if shared_object is not None:
        kwargs["shared_object"] = shared_object
    if preferred_tier is not None:
        kwargs["preferred_tier"] = preferred_tier
    if override_drive_interface is not None:
        kwargs["override_drive_interface"] = override_drive_interface
    if override_nic_interface is not None:
        kwargs["override_nic_interface"] = override_nic_interface
    result = vctx.client.vm_imports.create(**kwargs)
    output_result(
        _import_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_IMPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"VM import '{name}' created.")


@app.command("start")
@handle_errors()
def start_cmd(
    ctx: typer.Context,
    vm_import: Annotated[str, typer.Argument(help="VM import name or key.")],
) -> None:
    """Start a VM import job.

    Runs asynchronously. Use `vrg vm import log` to monitor progress.

    **Examples:**

        vrg vm import start migrate-web
    """
    vctx = get_context(ctx)
    key = _resolve_import(vctx, vm_import)
    vctx.client.vm_imports.start_import(key)
    output_success(f"VM import '{vm_import}' started.")


@app.command("cancel")
@handle_errors()
def cancel_cmd(
    ctx: typer.Context,
    vm_import: Annotated[str, typer.Argument(help="VM import name or key.")],
) -> None:
    """Cancel a running VM import job.

    **Examples:**

        vrg vm import cancel migrate-web
    """
    vctx = get_context(ctx)
    key = _resolve_import(vctx, vm_import)
    vctx.client.vm_imports.abort_import(key)
    output_success(f"VM import '{vm_import}' cancelled.")


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    vm_import: Annotated[str, typer.Argument(help="VM import name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a VM import job.

    **Examples:**

        vrg vm import delete migrate-web
        vrg vm import delete migrate-web --yes
    """
    vctx = get_context(ctx)
    key = _resolve_import(vctx, vm_import)
    if not confirm_action(f"Delete VM import '{vm_import}'?", yes=yes):
        raise typer.Abort()
    vctx.client.vm_imports.delete(key)
    output_success(f"VM import '{vm_import}' deleted.")
