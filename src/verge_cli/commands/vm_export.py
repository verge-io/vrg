"""VM export management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.commands import vm_export_stats
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="export",
    help=(
        "Manage VM export configurations and jobs.\n\n"
        "VM exports create portable copies of VMs from a vSAN volume. An"
        " export configuration defines which volume to export from and how"
        " many exports to retain. Use `start` to kick off an export job and"
        " `stats` to monitor progress.\n\n"
        "Use `-o json` for structured output.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    vrg vm export list\n\n"
        "    vrg vm export create --volume 5 --quiesced\n\n"
        "    vrg vm export start my-export --name nightly-2026-04-16\n\n"
        "    vrg vm export stop my-export\n\n"
        "    vrg vm export cleanup my-export\n\n"
        "    vrg vm export delete my-export --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Export jobs run asynchronously. Use `vrg vm export stats` to check"
        " progress and status of export runs."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(vm_export_stats.app, name="stats")

VM_EXPORT_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("volume_name", header="Volume"),
    ColumnDef("status"),
    ColumnDef("quiesced", format_fn=format_bool_yn, wide_only=True),
    ColumnDef("create_current", header="Create Current", format_fn=format_bool_yn, wide_only=True),
    ColumnDef("max_exports", header="Max Exports", wide_only=True),
]


def _export_to_dict(exp: Any) -> dict[str, Any]:
    """Convert a VolumeVmExport SDK object to a dict for output."""
    return {
        "$key": int(exp.key),
        "volume_name": exp.get("volume_name", "") or exp.get("volume_display", ""),
        "status": exp.get("status", ""),
        "volume": exp.get("volume", ""),
        "quiesced": exp.get("quiesced"),
        "create_current": exp.get("create_current"),
        "max_exports": exp.get("max_exports", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
) -> None:
    """List VM export configurations.

    **Examples:**

        vrg vm export list
        vrg -o json vm export list
    """
    vctx = get_context(ctx)
    exports = vctx.client.volume_vm_exports.list()
    data = [_export_to_dict(e) for e in exports]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_EXPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    export: Annotated[str, typer.Argument(help="VM export name or key.")],
) -> None:
    """Get a VM export configuration by name or key.

    **Examples:**

        vrg vm export get my-export
        vrg -o json vm export get 42
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.volume_vm_exports, export, "VM export")
    item = vctx.client.volume_vm_exports.get(key=key)
    output_result(
        _export_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_EXPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    volume: Annotated[int, typer.Option("--volume", help="Volume key (integer).")],
    quiesced: Annotated[
        bool,
        typer.Option("--quiesced/--no-quiesced", help="Quiesce VMs before export."),
    ] = False,
    create_current: Annotated[
        bool,
        typer.Option(
            "--create-current/--no-create-current",
            help="Create current snapshot before export.",
        ),
    ] = False,
    max_exports: Annotated[
        int | None,
        typer.Option("--max-exports", help="Maximum number of exports to retain."),
    ] = None,
) -> None:
    """Create a new VM export configuration.

    **Examples:**

        vrg vm export create --volume 5
        vrg vm export create --volume 5 --quiesced --max-exports 7
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "volume": volume,
        "quiesced": quiesced,
        "create_current": create_current,
    }
    if max_exports is not None:
        kwargs["max_exports"] = max_exports
    result = vctx.client.volume_vm_exports.create(**kwargs)
    output_result(
        _export_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=VM_EXPORT_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success("VM export created.")


@app.command("start")
@handle_errors()
def start_cmd(
    ctx: typer.Context,
    export: Annotated[str, typer.Argument(help="VM export name or key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Export run name."),
    ] = None,
    vms: Annotated[
        str | None,
        typer.Option("--vms", help="Comma-separated list of VM keys to export."),
    ] = None,
) -> None:
    """Start a VM export job.

    Runs asynchronously. Use `vrg vm export stats` to monitor progress.

    **Examples:**

        vrg vm export start my-export
        vrg vm export start my-export --name nightly-2026-04-16
        vrg vm export start my-export --vms 1,2,3
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.volume_vm_exports, export, "VM export")
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if vms is not None:
        kwargs["vms"] = [int(v.strip()) for v in vms.split(",")]
    vctx.client.volume_vm_exports.start_export(int(key), **kwargs)
    output_success(f"VM export '{export}' started.")


@app.command("stop")
@handle_errors()
def stop_cmd(
    ctx: typer.Context,
    export: Annotated[str, typer.Argument(help="VM export name or key.")],
) -> None:
    """Stop a running VM export job.

    **Examples:**

        vrg vm export stop my-export
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.volume_vm_exports, export, "VM export")
    vctx.client.volume_vm_exports.stop_export(int(key))
    output_success(f"VM export '{export}' stopped.")


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    export: Annotated[str, typer.Argument(help="VM export name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a VM export configuration.

    **Examples:**

        vrg vm export delete my-export
        vrg vm export delete my-export --yes
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.volume_vm_exports, export, "VM export")
    if not confirm_action(f"Delete VM export '{export}'?", yes=yes):
        raise typer.Abort()
    vctx.client.volume_vm_exports.delete(key)
    output_success(f"VM export '{export}' deleted.")


@app.command("cleanup")
@handle_errors()
def cleanup_cmd(
    ctx: typer.Context,
    export: Annotated[str, typer.Argument(help="VM export name or key.")],
) -> None:
    """Clean up exported files for a VM export.

    Removes the exported files from storage without deleting the
    export configuration itself.

    **Examples:**

        vrg vm export cleanup my-export
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.volume_vm_exports, export, "VM export")
    vctx.client.volume_vm_exports.cleanup_exports(int(key))
    output_success(f"VM export '{export}' cleaned up.")
