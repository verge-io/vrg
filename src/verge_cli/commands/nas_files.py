"""NAS volume file browser commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_nas_resource

app = typer.Typer(
    name="files",
    help=(
        "Browse files and directories inside a NAS volume — read-only"
        " inspection of volume contents without mounting the share from a"
        " client.\n\n"
        "This group drives the `volume_browser` endpoint: the NAS service VM"
        " walks the volume filesystem and returns a listing. It is useful for"
        " verifying that expected files are present (e.g., after a snapshot"
        " restore, sync, or migration), auditing share layouts, or locating a"
        " file before building CIFS/NFS rules around its path. It does **not**"
        " transfer file contents — there is no `cat`, `download`, `upload`,"
        " `delete`, or `mkdir`. For data access, mount the share via CIFS or"
        " NFS on a client.\n\n"
        "Volumes are referenced by name or 40-char hex `$key`. Ambiguous names"
        " exit with code 7 — disambiguate with the key. Paths use forward"
        " slashes with `/` as the volume root (e.g., `/`, `/documents`,"
        " `/archive/2025`).\n\n"
        "`--extensions` filters results to matching file extensions"
        " (comma-separated, no dots — e.g., `txt,log,csv`); it does not affect"
        " directories. `--sort` reorders results by a field name supported by"
        " the browser (`name`, `size`, `date`). Use `-o json` to pipe"
        " directory listings into scripts or agents, and `--query` to extract"
        " individual fields such as `name`, `type`, `size`, or `modified`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List the root of a volume\n"
        "    vrg nas files list shared-data\n\n"
        "    # List a subdirectory by path\n"
        "    vrg nas files list shared-data --path /documents\n\n"
        "    # Filter by extension, sort by size\n"
        "    vrg nas files list shared-data \\\n"
        "        --path /logs --extensions log,gz --sort size\n\n"
        "    # JSON output for scripting / agent consumption\n"
        "    vrg -o json nas files list shared-data --path /archive/2025\n\n"
        "    # Project just file names with --query\n"
        "    vrg -o json nas files list shared-data --query '[].name'\n\n"
        "    # Look up a specific file or directory\n"
        "    vrg nas files get shared-data /documents/report.pdf\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The parent NAS service VM **must be running** and the volume must be"
        " `online` (mounted) for browsing to succeed — a stopped service or an"
        " `offline` volume returns an error. Start the service with"
        " `vrg nas service start` and enable the volume with"
        " `vrg nas volume enable` if needed.\n\n"
        "The volume browser is **asynchronous**: the CLI submits a browse job,"
        " polls for completion, then returns entries. Large directories may"
        " take several seconds; the default timeout is 30s. Results are capped"
        " at 1,000 entries per request — paginate with narrower paths or"
        " `--extensions` if you need more.\n\n"
        "Snapshots can be browsed via their auto-mounted path (enable"
        " **Automatically Mount Snapshots** on the parent volume) — they"
        " appear as subdirectories that this command can list like any other"
        " path."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

NAS_FILE_COLUMNS: list[ColumnDef] = [
    ColumnDef("name"),
    ColumnDef("type", style_map={"directory": "blue bold", "file": ""}),
    ColumnDef("size_display", header="Size"),
    ColumnDef("modified", header="Modified", format_fn=format_epoch),
]


def _format_size(size_bytes: int | float) -> str:
    """Format bytes to human-readable size."""
    b = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{int(b)} {unit}" if unit == "B" else f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _file_to_dict(f: Any) -> dict[str, Any]:
    """Convert NASVolumeFile (dict-based) to output dict."""
    if isinstance(f, dict):
        size = f.get("size", 0) or 0
        return {
            "name": f.get("name"),
            "type": f.get("type"),
            "size": size,
            "size_display": f.get("size_display", _format_size(size)),
            "modified": f.get("date"),
        }
    size = getattr(f, "size", 0) or 0
    return {
        "name": f.name,
        "type": getattr(f, "type", None),
        "size": size,
        "size_display": getattr(f, "size_display", _format_size(size)),
        "modified": getattr(f, "date", None),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
    path: Annotated[
        str,
        typer.Option("--path", "-p", help="Directory path to list"),
    ] = "/",
    extensions: Annotated[
        str | None,
        typer.Option(
            "--extensions", help="Comma-separated file extensions to filter (e.g., txt,log,csv)"
        ),
    ] = None,
    sort: Annotated[
        str | None,
        typer.Option("--sort", help="Sort field (e.g., name, size, date)"),
    ] = None,
) -> None:
    """List files and directories in a NAS volume.

    Read-only browser for files on a NAS volume. Uses the NAS service's
    mounted view, so the service VM must be running.

    **Examples:**

        vrg nas files list shared-data
        vrg nas files list shared-data --path /reports
        vrg nas files list shared-data --extensions txt,log,csv
        vrg -o json nas files list shared-data --path /backups --sort date
    """
    vctx = get_context(ctx)
    vol_key = resolve_nas_resource(vctx.client.nas_volumes, volume, "NAS volume")
    file_mgr = vctx.client.nas_volumes.files(vol_key)

    kwargs: dict[str, Any] = {"path": path}
    if extensions is not None:
        kwargs["extensions"] = extensions
    if sort is not None:
        kwargs["sort"] = sort

    files = file_mgr.list(**kwargs)
    data = [_file_to_dict(f) for f in files]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NAS_FILE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    volume: Annotated[str, typer.Argument(help="NAS volume name or hex key")],
    path: Annotated[str, typer.Argument(help="File or directory path")],
) -> None:
    """Get details of a specific file or directory.

    Returns metadata (size, owner, permissions, mtime) for a single
    path on a NAS volume.

    **Examples:**

        vrg nas files get shared-data /reports/2026-q1.pdf
        vrg -o json nas files get shared-data /
    """
    vctx = get_context(ctx)
    vol_key = resolve_nas_resource(vctx.client.nas_volumes, volume, "NAS volume")
    file_mgr = vctx.client.nas_volumes.files(vol_key)

    item = file_mgr.get(path=path)
    output_result(
        _file_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
