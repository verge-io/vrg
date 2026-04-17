"""OIDC application log commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import OIDC_LOG_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result

app = typer.Typer(
    name="log",
    help=(
        "View per-application audit logs for OIDC applications.\n\n"
        "Every CRUD operation and authentication attempt against an OIDC"
        " application is recorded in its audit log. Use this to trace who"
        " authenticated through the application, which configuration"
        " changes were made and by whom, and to surface authorization or"
        " token-exchange errors when a client integration breaks.\n\n"
        "Use `-o json` for machine-readable output. `--query` on fields"
        " like `timestamp`, `level`, `user_display`, `text`, `is_error`,"
        " `is_warning`. `--limit` defaults to 50 — raise it when searching"
        " back through history.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Recent activity for an application\n"
        "    vrg oidc log list partner-portal\n\n"
        "    # Only errors (level=error or critical)\n"
        "    vrg oidc log list partner-portal --errors\n\n"
        "    # Only warnings\n"
        "    vrg oidc log list partner-portal --warnings\n\n"
        "    # Filter by specific level and raise the limit\n"
        "    vrg oidc log list partner-portal --level audit --limit 500\n\n"
        "    # Pull the full log as JSON for offline review\n"
        "    vrg -o json oidc log list partner-portal --limit 1000\n\n"
        "    # Fetch a specific entry by key\n"
        "    vrg oidc log get partner-portal 8421\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "**Log levels**: `audit`, `message`, `warning`, `error`, `critical`."
        " `--errors` matches `error` and `critical`; `--warnings` matches"
        " `warning`. These flags are mutually exclusive with `--level`.\n\n"
        "**Logs are per-application, not global.** The `<oidc-app>`"
        " argument scopes results to one application's log stream. For"
        " system-wide authentication events, look at `vrg log` and"
        " `vrg alarm` instead.\n\n"
        "**Name resolution**: the `<oidc-app>` argument accepts the"
        " application name or numeric key. Ambiguous names exit with code"
        " 7.\n"
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


def _resolve_oidc_app(client: Any, identifier: str) -> int:
    """Resolve OIDC application identifier (key or name) to key."""
    if identifier.isdigit():
        oidc_app = client.oidc_applications.get(key=int(identifier))
    else:
        oidc_app = client.oidc_applications.get(name=identifier)
    return int(oidc_app.key)


def _oidc_log_to_dict(log: Any) -> dict[str, Any]:
    """Convert SDK OIDC log entry to output dict."""
    return {
        "$key": int(log.key),
        "timestamp": log.get("timestamp"),
        "level": log.get("level", ""),
        "text": log.get("text", ""),
        "user": log.get("user"),
        "user_display": log.get("user_display", ""),
        "application_key": log.application_key,
        "is_error": log.is_error,
        "is_warning": log.is_warning,
    }


@app.command("list")
@handle_errors()
def oidc_log_list(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    level: Annotated[
        str | None,
        typer.Option(
            "--level",
            help="Filter by log level (audit, message, warning, error, critical).",
        ),
    ] = None,
    errors: Annotated[
        bool,
        typer.Option("--errors", help="Show only error and critical entries."),
    ] = False,
    warnings: Annotated[
        bool,
        typer.Option("--warnings", help="Show only warning entries."),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of log entries."),
    ] = 50,
) -> None:
    """List OIDC application logs."""
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    logs_mgr = vctx.client.oidc_applications.logs(app_key)

    if errors:
        entries = logs_mgr.list_errors(limit=limit)
    elif warnings:
        entries = logs_mgr.list_warnings(limit=limit)
    elif level == "audit":
        entries = logs_mgr.list_audits(limit=limit)
    elif level is not None:
        entries = logs_mgr.list(level=level, limit=limit)
    else:
        entries = logs_mgr.list(limit=limit)

    output_result(
        [_oidc_log_to_dict(e) for e in entries],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def oidc_log_get(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    log_id: Annotated[int, typer.Argument(help="Log entry key.")],
) -> None:
    """Get a specific OIDC application log entry."""
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    logs_mgr = vctx.client.oidc_applications.logs(app_key)
    log_entry = logs_mgr.get(key=log_id)

    output_result(
        _oidc_log_to_dict(log_entry),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
