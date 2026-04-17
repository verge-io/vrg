"""Recipe log management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_nas_resource

app = typer.Typer(
    name="log",
    help=(
        "View VM recipe activity logs — the audit trail for recipe"
        " operations.\n\n"
        "Every recipe action (download, publish, edit, deploy, update)"
        " writes an entry capturing the level, message, timestamp, and the"
        " user who triggered it. Use these logs to diagnose failed"
        " downloads, trace who changed a recipe, or confirm that a deploy"
        " ran end-to-end.\n\n"
        "Logs are read-only — there is no create, update, or delete."
        " Entries are retained per-recipe and trimmed by the server over"
        " time, so pull relevant entries promptly when debugging.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Show recent log entries across every recipe\n"
        "    vrg recipe log list\n\n"
        "    # Filter to a single recipe by name or hex key\n"
        "    vrg recipe log list --recipe ubuntu-server\n\n"
        "    # Emit JSON for downstream parsing (level, text, timestamp, user)\n"
        "    vrg -o json recipe log list --recipe ubuntu-server\n\n"
        "    # Query only warnings and errors with jq-style projection\n"
        "    vrg -o json recipe log list --query \"[?level!='message']\"\n\n"
        "    # Inspect a specific log entry by its numeric key\n"
        "    vrg recipe log get 4217\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`--recipe` accepts either a recipe name or its 40-character hex"
        " key. When a name matches multiple recipes, vrg prints all matches"
        " and exits with code 7 — use the hex key to disambiguate.\n\n"
        "Log levels observed: `message`, `warning`, `error`, `critical`."
        " Timestamps are returned in microseconds by the API and normalized"
        " to seconds for display."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

RECIPE_LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("level"),
    ColumnDef("text", header="Message"),
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("user", wide_only=True),
]


def _log_to_dict(log: Any) -> dict[str, Any]:
    """Convert a VmRecipeLog SDK object to a dict for output."""
    # Timestamp is in microseconds in the SDK — convert to seconds for format_epoch
    ts = log.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 1e12:
        ts = ts / 1e6
    return {
        "$key": int(log.key),
        "level": log.get("level", ""),
        "text": log.get("text", ""),
        "timestamp": ts,
        "user": log.get("user", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    recipe: Annotated[
        str | None,
        typer.Option("--recipe", help="Filter by recipe name or key."),
    ] = None,
) -> None:
    """List recipe operation logs.

    Examples:

        vrg recipe log list
        vrg recipe log list --recipe ubuntu-server
        vrg -o json recipe log list --query "[?level!='message']"

    Log levels: `message`, `warning`, `error`, `critical`. Timestamps
    are normalized to seconds. Without `--recipe`, returns entries
    across every recipe on the system.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if recipe is not None:
        recipe_key = resolve_nas_resource(
            vctx.client.vm_recipes,
            recipe,
            resource_type="recipe",
        )
        kwargs["vm_recipe"] = recipe_key
    logs = vctx.client.vm_recipe_logs.list(**kwargs)
    data = [_log_to_dict(entry) for entry in logs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    log: Annotated[str, typer.Argument(help="Log entry key.")],
) -> None:
    """Get a recipe log entry by key.

    Examples:

        vrg recipe log get 4217
        vrg -o json recipe log get 4217

    `log` must be a numeric key (found via `vrg recipe log list`).
    """
    vctx = get_context(ctx)
    key = int(log)
    item = vctx.client.vm_recipe_logs.get(key=key)
    output_result(
        _log_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_LOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
