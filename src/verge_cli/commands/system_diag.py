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
    help=(
        "Create and manage system diagnostic bundles.\n\n"
        "A system diagnostic bundle is a comprehensive snapshot of cloud"
        " state used for troubleshooting and support escalations — system"
        " and kernel logs, hardware inventory (dmidecode, lspci, lshw,"
        " SMART data), vSAN cluster and per-node state, network fabric"
        " details, and container/tenant log collection. Bundles are"
        " produced by the on-node `diagnostics` tool and stored on the"
        " cluster under `/vsan/vol/tmp/diags/`. They can be sent directly"
        " to Verge.io support from the CLI.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `name`, `status`, `timestamp`, `description`, `status_info`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List existing diagnostic bundles (newest first)\n"
        "    vrg system diag list\n\n"
        "    # Create a bundle and wait for completion (default)\n"
        "    vrg system diag create support-2026-04-17 \\\n"
        '        --description "vSAN rebalance investigation"\n\n'
        "    # Create and auto-send to Verge.io support\n"
        "    vrg system diag create support-2026-04-17 \\\n"
        "        --send-to-support\n\n"
        "    # Kick off the bundle but don't block\n"
        "    vrg system diag create support-2026-04-17 --no-wait\n\n"
        "    # Inspect a bundle's current state\n"
        "    vrg -o json system diag get support-2026-04-17\n\n"
        "    # Send an existing bundle to support\n"
        "    vrg system diag send support-2026-04-17\n\n"
        "    # Remove a bundle\n"
        "    vrg system diag delete support-2026-04-17 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Bundle creation can take several minutes on large clusters — it"
        " touches every node and collects vSAN, hardware, and log data."
        " Running without `--no-wait` streams a spinner and returns when"
        " the bundle reaches a terminal state; the default timeout is 300"
        " seconds.\n\n"
        "Diagnostics are resolved by name or numeric key. If multiple"
        " bundles share a name, name lookup fails with exit code 7"
        " (conflict) — use the numeric key instead. `--send-to-support`"
        " requires outbound connectivity from the cloud to Verge.io; on"
        " air-gap systems, download the bundle from the UI and upload it"
        " through the support portal."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
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
    """List system diagnostic bundles.

    Examples:

        vrg system diag list
        vrg -o json system diag list
        vrg -o json system diag list --query "[?status=='error']"

    Lists bundles newest-first. Useful `--query` fields: `name`,
    `status`, `timestamp`, `description`, `status_info`.
    """
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

    Examples:

        vrg system diag create support-2026-04-17
        vrg system diag create support-2026-04-17 \\
            --description "vSAN rebalance investigation"
        vrg system diag create support-2026-04-17 --send-to-support
        vrg system diag create support-2026-04-17 --no-wait

    Bundle creation can take several minutes on large clusters — it
    touches every node and collects vSAN, hardware, and log data. By
    default, waits for completion (300s timeout) with a spinner. Use
    `--no-wait` to return immediately and poll status later with
    `vrg system diag get`.
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
    """Show details for a diagnostic bundle.

    Examples:

        vrg system diag get support-2026-04-17
        vrg system diag get 42
        vrg -o json system diag get support-2026-04-17

    Accepts bundle name or numeric `$key`. Ambiguous name matches
    exit with code 7 — use the key instead.
    """
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
    """Send a diagnostic bundle to Verge.io support.

    Examples:

        vrg system diag send support-2026-04-17
        vrg system diag send 42

    Requires outbound connectivity from the cloud to Verge.io. On
    air-gap systems, download the bundle from the UI and upload it
    through the support portal instead.
    """
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
    """Delete a diagnostic bundle.

    Examples:

        vrg system diag delete support-2026-04-17
        vrg system diag delete support-2026-04-17 --yes
        vrg system diag delete 42 -y

    Destructive — removes the bundle files from
    `/vsan/vol/tmp/diags/`. Pass `--yes` / `-y` to skip the
    confirmation prompt (useful in scripts).
    """
    vctx = get_context(ctx)
    diag = _resolve_diag(vctx, name_or_key)

    if not confirm_action(f"Delete diagnostic '{diag.name}' (key: {diag.key})?", yes=yes):
        return

    vctx.client.system_diagnostics.delete(diag.key)

    output_success(
        f"Diagnostic '{diag.name}' deleted",
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
