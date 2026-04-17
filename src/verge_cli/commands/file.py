"""Media catalog file management commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TransferSpeedColumn,
)

from verge_cli.columns import ColumnDef
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success

# File type constants — mirrors the SDK's FILE_TYPES
FILE_TYPES: dict[str, str] = {
    "iso": "ISO",
    "img": "IMG (Raw Disk Image)",
    "qcow": "QCOW (Legacy QEMU)",
    "qcow2": "QCOW2 (QEMU, Xen)",
    "qed": "QED (KVM)",
    "raw": "Raw (Binary Disc Image)",
    "vdi": "VDI (VirtualBox)",
    "vhd": "VHD/VPC (Legacy Hyper-V)",
    "vhdx": "VHDX (Hyper-V)",
    "vmdk": "VMDK (VMware)",
    "ova": "OVA (VMware, VirtualBox)",
    "ovf": "OVF (VMware, VirtualBox)",
    "vmx": "VMX (VMware)",
    "ybvm": "Verge.io Virtual Machine",
    "nvram": "NVRAM",
    "zip": "ZIP",
}

# Fields to request from the API for complete file details
_FILE_FIELDS = [
    "$key",
    "name",
    "type",
    "description",
    "filesize",
    "allocated_bytes",
    "used_bytes",
    "preferred_tier",
    "modified",
    "creator",
]

app = typer.Typer(
    name="file",
    rich_markup_mode="markdown",
    help=(
        "Manage the vSAN media catalog — ISOs, disk images, and VM"
        " appliance packages.\n\n"
        "The files subsystem stores binary content directly on the vSAN"
        " without a NAS Service VM. Entries include install ISOs, VM disk"
        " images (`qcow2`, `vmdk`, `vhdx`, `raw`, `img`, …), appliance"
        " packages (`ova`, `ovf`, `ybvm`), Cloud-Init payloads, and NVRAM."
        " File type is auto-detected from the extension at upload time."
        " Each file is a vSAN object with metadata for size, used bytes,"
        " and a preferred vSAN tier (1–5). Files typically serve as media"
        " sources for VM drives created via `vrg vm` or templates.\n\n"
        "Use `-o json` for structured output, `-o wide` to include"
        " description, allocated/used capacity, creator, and modified"
        " timestamp, and `--query` to pluck fields (e.g., `--query"
        " \"[?type=='iso'].name\"`). Files are addressable by `$key`"
        " (numeric) or `name`; an ambiguous name yields exit code 7"
        " (multiple matches).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List catalog entries, filter by type\n"
        "    vrg file list\n"
        "    vrg file list --type iso\n"
        "    vrg -o json file list --type qcow2\n\n"
        "    # Fetch details for one file\n"
        "    vrg file get ubuntu-22.04.iso\n"
        "    vrg -o json file get 4821\n\n"
        "    # Upload a local ISO (progress bar on TTY)\n"
        "    vrg file upload ubuntu-22.04.iso\n"
        "    vrg file upload ./golden.qcow2 --name golden-v2 \\\n"
        "        --description 'Base image v2' --tier 2\n\n"
        "    # Download a file from the catalog\n"
        "    vrg file download ubuntu-22.04.iso --destination ./iso\n\n"
        "    # Rename, retag, retier\n"
        "    vrg file update golden-v2 --description 'Promoted' --tier 1\n\n"
        "    # Delete (prompts unless --yes)\n"
        "    vrg file delete old-template.qcow2 --yes\n\n"
        "    # Show the list of auto-detected file types\n"
        "    vrg file types\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "File type is derived from the extension; unknown extensions land"
        " in the `unknown` bucket. `--tier` sets `preferred_tier` (1–5);"
        " changing it on an existing file triggers live migration between"
        " vSAN tiers. Deletion is blocked while any `machine_drives`"
        " record references the file as its media source — detach or"
        " delete the dependent VM drive first. The vSAN enforces a"
        " system-wide cap of 50,000 file records and a per-file ceiling"
        " of 256 TiB. Uploads and downloads show a Rich progress bar when"
        " stderr is a TTY; otherwise they run silently, which is the"
        " default for scripts and CI."
    ),
    no_args_is_help=True,
)


def _format_gb(value: Any, *, for_csv: bool = False) -> str:
    """Format a GB value to 2 decimal places."""
    if value:
        return f"{value:.2f}"
    return "0.00"


FILE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("type", header="Type"),
    ColumnDef(
        "size_gb",
        header="Size (GB)",
        format_fn=_format_gb,
    ),
    ColumnDef("preferred_tier", header="Tier"),
    ColumnDef("description", wide_only=True),
    ColumnDef(
        "allocated_gb",
        header="Allocated (GB)",
        wide_only=True,
        format_fn=_format_gb,
    ),
    ColumnDef(
        "used_gb",
        header="Used (GB)",
        wide_only=True,
        format_fn=_format_gb,
    ),
    ColumnDef("creator", wide_only=True),
    ColumnDef("modified", wide_only=True),
]

FILE_TYPE_COLUMNS: list[ColumnDef] = [
    ColumnDef("type", header="Type"),
    ColumnDef("description", header="Description"),
]


def _file_to_dict(obj: Any) -> dict[str, Any]:
    """Convert SDK File object to output dict."""
    return {
        "$key": int(obj.key),
        "name": obj.name,
        "type": obj.file_type,
        "description": obj.description,
        "size_gb": obj.size_gb,
        "allocated_gb": obj.allocated_gb,
        "used_gb": obj.used_gb,
        "preferred_tier": obj.preferred_tier,
        "creator": obj.creator,
        "modified": str(obj.modified) if obj.modified else "",
    }


def _file_type_to_dict(type_key: str, type_desc: str) -> dict[str, str]:
    """Convert FILE_TYPES entry to output dict."""
    return {
        "type": type_key,
        "description": type_desc,
    }


def _make_progress() -> Progress:
    """Create a Rich progress bar for file transfers."""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=Console(stderr=True),
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    file_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter by file type (iso, qcow2, vmdk, ova, etc.)"),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Maximum number of results"),
    ] = None,
    offset: Annotated[
        int | None,
        typer.Option("--offset", help="Skip N results"),
    ] = None,
) -> None:
    """List files in the media catalog."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if file_type is not None:
        kwargs["file_type"] = file_type.lower()
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset

    files = vctx.client.files.list(**kwargs)
    data = [_file_to_dict(f) for f in files]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=FILE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="File name or key")],
) -> None:
    """Get details of a file."""
    from verge_cli.utils import resolve_resource_id

    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.files, identifier, "File")
    item = vctx.client.files.get(key, fields=_FILE_FIELDS)
    output_result(
        _file_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("upload")
@handle_errors()
def upload_cmd(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(help="Local file path to upload")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Override file name in catalog"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="File description"),
    ] = None,
    tier: Annotated[
        int | None,
        typer.Option("--tier", help="Preferred storage tier (1-5)"),
    ] = None,
) -> None:
    """Upload a file to the media catalog."""
    vctx = get_context(ctx)

    # Validate file exists before calling SDK
    if not path.exists():
        typer.echo(f"Error: File not found: {path}", err=True)
        raise typer.Exit(1)
    if not path.is_file():
        typer.echo(f"Error: Not a file: {path}", err=True)
        raise typer.Exit(1)

    kwargs: dict[str, Any] = {"path": str(path)}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if tier is not None:
        kwargs["tier"] = tier

    # Use progress bar if connected to a terminal
    if sys.stderr.isatty():
        with _make_progress() as progress:
            task = progress.add_task("Uploading", total=path.stat().st_size)

            def progress_callback(uploaded: int, total: int) -> None:
                progress.update(task, completed=uploaded, total=total)

            kwargs["progress_callback"] = progress_callback
            result = vctx.client.files.upload(**kwargs)
    else:
        result = vctx.client.files.upload(**kwargs)

    output_result(
        _file_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("download")
@handle_errors()
def download_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="File name or key")],
    destination: Annotated[
        Path,
        typer.Option("--destination", help="Target directory for download"),
    ] = Path("."),
    filename: Annotated[
        str | None,
        typer.Option("--filename", help="Override downloaded filename"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing file"),
    ] = False,
) -> None:
    """Download a file from the media catalog."""
    from verge_cli.utils import resolve_resource_id

    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.files, identifier, "File")

    kwargs: dict[str, Any] = {
        "key": key,
        "destination": str(destination),
        "overwrite": overwrite,
    }
    if filename is not None:
        kwargs["filename"] = filename

    # Use progress bar if connected to a terminal
    if sys.stderr.isatty():
        with _make_progress() as progress:
            task = progress.add_task("Downloading", total=None)

            def progress_callback(downloaded: int, total: int) -> None:
                progress.update(task, completed=downloaded, total=total)

            kwargs["progress_callback"] = progress_callback
            result_path = vctx.client.files.download(**kwargs)
    else:
        result_path = vctx.client.files.download(**kwargs)

    output_success(f"Downloaded to {result_path}", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="File name or key")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New file name"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="File description"),
    ] = None,
    tier: Annotated[
        int | None,
        typer.Option("--tier", help="Preferred storage tier (1-5)"),
    ] = None,
) -> None:
    """Update a file's metadata."""
    from verge_cli.utils import resolve_resource_id

    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.files, identifier, "File")

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if tier is not None:
        kwargs["preferred_tier"] = tier

    vctx.client.files.update(key, **kwargs)
    output_success(f"Updated file '{identifier}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="File name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a file from the media catalog."""
    from verge_cli.utils import confirm_action, resolve_resource_id

    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.files, identifier, "File")

    if not confirm_action(f"Delete file '{identifier}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.files.delete(key)
    output_success(f"Deleted file '{identifier}'", quiet=vctx.quiet)


@app.command("types")
@handle_errors()
def types_cmd(
    ctx: typer.Context,
) -> None:
    """List supported file types."""
    vctx = get_context(ctx)
    data = [_file_type_to_dict(k, v) for k, v in FILE_TYPES.items()]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=FILE_TYPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
