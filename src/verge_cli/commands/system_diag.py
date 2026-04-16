"""System diagnostic bundle commands for Verge CLI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.status import Status

from verge_cli.columns import SYSTEM_DIAG_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import CliError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="diag",
    help="Manage system diagnostic bundles.",
    no_args_is_help=True,
)


def _resolve_diag(vctx: Any, name_or_key: str) -> Any:
    """Resolve a diagnostic by name or numeric key."""
    if name_or_key.isdigit():
        return vctx.client.system_diagnostics.get(key=int(name_or_key))
    return vctx.client.system_diagnostics.get(name=name_or_key)


def _diag_to_dict(diag: Any) -> dict[str, Any]:
    """Convert SystemDiagnostic to output dict."""
    ts = getattr(diag, "timestamp", None)
    if isinstance(ts, int) and ts > 0:
        ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    else:
        ts_str = str(ts) if ts else ""

    return {
        "$key": diag.key,
        "name": getattr(diag, "name", diag.get("name", "")),
        "status": getattr(diag, "status", diag.get("status", "")),
        "timestamp": ts_str,
        "description": getattr(diag, "description", diag.get("description", "")),
        "status_info": getattr(diag, "status_info", diag.get("status_info", "")),
    }


@app.command("list")
@handle_errors()
def diag_list(ctx: typer.Context) -> None:
    """List system diagnostic bundles."""
    vctx = get_context(ctx)
    diags = vctx.client.system_diagnostics.list()
    data = [_diag_to_dict(d) for d in diags]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SYSTEM_DIAG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def diag_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Unique diagnostic bundle name")],
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Description of the diagnostic."),
    ] = "",
    send_to_support: Annotated[
        bool,
        typer.Option("--send-to-support", help="Automatically send to Verge.io support."),
    ] = False,
    no_wait: Annotated[
        bool,
        typer.Option("--no-wait", help="Return immediately without waiting for completion."),
    ] = False,
) -> None:
    """Create a new system diagnostic bundle.

    By default, waits for the bundle to complete. Use --no-wait to
    return immediately and check status later with `vrg system diag get`.
    """
    vctx = get_context(ctx)

    diag = vctx.client.system_diagnostics.create(
        name=name,
        description=description,
        send2support=send_to_support,
    )

    if no_wait:
        output_success(
            f"Diagnostic '{name}' created (key: {diag.key}, status: {diag.status})",
            quiet=vctx.quiet,
            no_color=vctx.no_color,
        )
        return

    console = Console(stderr=True)
    with Status("Building diagnostic bundle...", console=console, spinner="dots"):
        diag = vctx.client.system_diagnostics.wait(diag.key, timeout=300)

    if diag.is_error:
        raise CliError(f"Diagnostic '{name}' failed: {diag.status_info or 'unknown error'}")

    output_success(
        f"Diagnostic '{name}' complete (key: {diag.key})",
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def diag_get(
    ctx: typer.Context,
    name_or_key: Annotated[str, typer.Argument(help="Diagnostic name or numeric key")],
) -> None:
    """Show details for a diagnostic bundle."""
    vctx = get_context(ctx)
    diag = _resolve_diag(vctx, name_or_key)
    data = _diag_to_dict(diag)

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("send")
@handle_errors()
def diag_send(
    ctx: typer.Context,
    name_or_key: Annotated[str, typer.Argument(help="Diagnostic name or numeric key")],
) -> None:
    """Send a diagnostic bundle to Verge.io support."""
    vctx = get_context(ctx)
    diag = _resolve_diag(vctx, name_or_key)

    vctx.client.system_diagnostics.send_to_support(diag.key)

    output_success(
        f"Diagnostic '{diag.name}' sent to support",
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def diag_delete(
    ctx: typer.Context,
    name_or_key: Annotated[str, typer.Argument(help="Diagnostic name or numeric key")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a diagnostic bundle."""
    vctx = get_context(ctx)
    diag = _resolve_diag(vctx, name_or_key)

    if not yes:
        confirm_action(f"Delete diagnostic '{diag.name}' (key: {diag.key})?")

    vctx.client.system_diagnostics.delete(diag.key)

    output_success(
        f"Diagnostic '{diag.name}' deleted",
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
