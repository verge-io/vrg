"""Update source management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="source",
    help=(
        "Manage update sources — remote servers that publish VergeOS"
        " `ybpkg` packages.\n\n"
        "An *update source* is a row in `update_sources`: a URL pointing"
        " at a VergeOS update server, optionally protected by a user and"
        " password. Multiple sources can be configured, but only one is"
        " *active* at a time — the active source is named in"
        " `update_settings.source` and determines which branches and"
        " packages `vrg update check` sees. Authoring a source does not"
        " activate it; use `vrg update configure --source <key>` to"
        " switch.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `name`, `url`, `enabled`, `last_refreshed`, `last_updated`."
        " Looking up by name returns exit 6 (not found) or exit 7 (multiple"
        " matches) when ambiguous — pass the numeric `$key` to disambiguate.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List configured sources\n"
        "    vrg update source list\n\n"
        "    # Scope to enabled sources only\n"
        "    vrg update source list --enabled\n\n"
        "    # Inspect one source as JSON\n"
        "    vrg -o json update source get verge-updates\n\n"
        "    # Check refresh/download/install status for a source\n"
        "    vrg update source status verge-updates\n\n"
        "    # Add a new authenticated mirror\n"
        "    vrg update source create --name internal-mirror \\\n"
        "        --url https://updates.internal.example.com \\\n"
        "        --user deploy --password $UPDATE_TOKEN\n\n"
        "    # Disable a source without deleting it\n"
        "    vrg update source update verge-updates --disabled\n\n"
        "    # Remove a source (requires confirmation)\n"
        "    vrg update source delete legacy-mirror\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Creating or editing a source does not change which source is"
        " active. Run `vrg update configure --source <key>` to switch,"
        " then `vrg update check` to repopulate the candidate package list"
        " against the new source.\n\n"
        "`vrg update source status` reports the current pipeline stage"
        " for a source: `idle`, `refreshing`, `downloading`, `installing`,"
        " `applying`, or `error`. Wait for `idle` before starting another"
        " operation against the same source."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

SOURCE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("url"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map={"Y": "green", "-": "red"}),
    ColumnDef("description", wide_only=True),
    ColumnDef("last_refreshed", header="Last Refreshed", wide_only=True),
    ColumnDef("last_updated", header="Last Updated", wide_only=True),
]

SOURCE_STATUS_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef(
        "status",
        style_map={
            "idle": "green",
            "refreshing": "yellow",
            "downloading": "cyan",
            "installing": "yellow",
            "applying": "yellow",
            "error": "red",
        },
    ),
    ColumnDef("info"),
    ColumnDef("nodes_updated", header="Nodes Updated"),
    ColumnDef("last_update", header="Last Update"),
]


def _source_to_dict(source: Any) -> dict[str, Any]:
    """Convert UpdateSource SDK object to dict for output."""
    return {
        "$key": int(source.key),
        "name": source.name,
        "description": source.get("description", ""),
        "url": source.get("url", ""),
        "enabled": source.get("enabled"),
        "last_updated": source.get("last_updated", ""),
        "last_refreshed": source.get("last_refreshed", ""),
    }


def _source_status_to_dict(status: Any) -> dict[str, Any]:
    """Convert UpdateSourceStatus SDK object to dict for output."""
    return {
        "$key": int(status.key),
        "status": status.get("status", ""),
        "info": status.get("info", ""),
        "nodes_updated": status.get("nodes_updated", ""),
        "last_update": status.get("last_update", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled state."),
    ] = None,
) -> None:
    """List update sources.

    Examples:

        vrg update source list
        vrg update source list --enabled
        vrg update source list --disabled
        vrg -o json update source list | jq '.[] | select(.enabled == "Y") | .name'
        vrg -A update source list

    Useful `--query` fields: `name`, `url`, `enabled`,
    `last_refreshed`, `last_updated`. `-A` lists sources across every
    configured profile in parallel.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.update_sources.list(), _source_to_dict, SOURCE_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if enabled is not None:
        kwargs["enabled"] = enabled
    sources = vctx.client.update_sources.list(**kwargs)
    data = [_source_to_dict(s) for s in sources]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SOURCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Update source ID or name.")],
) -> None:
    """Get an update source by ID or name.

    Examples:

        vrg update source get verge-updates
        vrg update source get 1
        vrg -o json update source get verge-updates

    Name lookups exit 6 (not found) or exit 7 (multiple matches) —
    pass the numeric `$key` to disambiguate.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_sources, source, "Update source")
    item = vctx.client.update_sources.get(key)
    output_result(
        _source_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SOURCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Source name.")],
    url: Annotated[str, typer.Option("--url", help="Update server URL.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Source description."),
    ] = None,
    user: Annotated[
        str | None,
        typer.Option("--user", help="Authentication username."),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option("--password", help="Authentication password."),
    ] = None,
    enabled: Annotated[
        bool,
        typer.Option("--enabled/--no-enabled", help="Enable the source."),
    ] = True,
) -> None:
    """Create a new update source.

    Examples:

        vrg update source create --name verge-updates \\
            --url https://updates.verge.io

        vrg update source create --name internal-mirror \\
            --url https://updates.internal.example.com \\
            --user deploy --password $UPDATE_TOKEN

        vrg update source create --name legacy --url https://old.example.com \\
            --no-enabled

    Creating a source does not activate it. Switch the active source
    with `vrg update configure --source <key>`, then run
    `vrg update check` to repopulate the candidate package list.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {
        "name": name,
        "url": url,
        "enabled": enabled,
    }
    if description is not None:
        kwargs["description"] = description
    if user is not None:
        kwargs["user"] = user
    if password is not None:
        kwargs["password"] = password
    result = vctx.client.update_sources.create(**kwargs)
    output_result(
        _source_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SOURCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Update source '{name}' created.", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Update source ID or name.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New source name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", help="New URL."),
    ] = None,
    user: Annotated[
        str | None,
        typer.Option("--user", help="New username."),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option("--password", help="New password."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Enable or disable source."),
    ] = None,
) -> None:
    """Update an update source.

    Examples:

        vrg update source update verge-updates --description "Primary mirror"
        vrg update source update internal-mirror --url https://new.example.com
        vrg update source update legacy --disabled
        vrg update source update internal-mirror --user deploy --password $TOKEN

    Only flags you pass are changed. Disabling the active source does
    not switch to a different one — pair with
    `vrg update configure --source <key>` when migrating mirrors.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_sources, source, "Update source")
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if url is not None:
        kwargs["url"] = url
    if user is not None:
        kwargs["user"] = user
    if password is not None:
        kwargs["password"] = password
    if enabled is not None:
        kwargs["enabled"] = enabled
    result = vctx.client.update_sources.update(key, **kwargs)
    output_result(
        _source_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SOURCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Update source '{source}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Update source ID or name.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete an update source.

    Examples:

        vrg update source delete legacy-mirror
        vrg update source delete legacy-mirror --yes

    Destructive. Deleting the currently active source leaves
    `update_settings.source` dangling — switch to another source via
    `vrg update configure --source <key>` before deleting the one in
    use.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_sources, source, "Update source")
    if not confirm_action(f"Delete update source '{source}'?", yes=yes):
        raise typer.Abort()
    vctx.client.update_sources.delete(key)
    output_success(f"Update source '{source}' deleted.", quiet=vctx.quiet)


@app.command("status")
@handle_errors()
def status_cmd(
    ctx: typer.Context,
    source: Annotated[str, typer.Argument(help="Update source ID or name.")],
) -> None:
    """Show update source status.

    Examples:

        vrg update source status verge-updates
        vrg update source status 1
        vrg -o json update source status verge-updates

    Reports the source's current pipeline stage: `idle`, `refreshing`,
    `downloading`, `installing`, `applying`, or `error`. Useful
    `--query` fields: `status`, `info`, `nodes_updated`,
    `last_update`. Wait for `idle` before starting another operation
    against the same source.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_sources, source, "Update source")
    status = vctx.client.update_sources.get_status(key)
    output_result(
        _source_status_to_dict(status),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SOURCE_STATUS_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
