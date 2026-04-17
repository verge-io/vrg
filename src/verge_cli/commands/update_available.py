"""Update available package commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="available",
    help=(
        "View available update packages discovered on the active source.\n\n"
        "An *available package* is one entry in `update_source_packages` —"
        " the package list returned by the remote update source for the"
        " currently selected branch. Entries appear after `vrg update check`"
        " queries the source; until then this list is empty or stale.\n\n"
        "Each entry has a `downloaded` flag indicating whether its binary"
        " files have been fetched locally. Pending packages still need to"
        " be pulled with `vrg update download` before `vrg update install`"
        " can apply them. Use `--downloaded` and `--pending` to split the"
        " list, or `--source` / `--branch` to scope to a specific origin"
        " when more than one source is configured.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `name`, `version`, `downloaded`, `optional`, `branch`, `source`."
        " Looking up by name returns exit 6 (not found) or exit 7 (multiple"
        " matches) when ambiguous — pass the numeric `$key` to disambiguate.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every available package on the active source\n"
        "    vrg update available list\n\n"
        "    # Show only packages still pending download\n"
        "    vrg update available list --pending\n\n"
        "    # Show packages already downloaded but not yet installed\n"
        "    vrg update available list --downloaded\n\n"
        "    # Filter by a specific source and branch\n"
        "    vrg update available list --source 1 --branch 2\n\n"
        "    # Inspect one package as JSON\n"
        "    vrg -o json update available get verge-os\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Run `vrg update check` to refresh this list against the remote"
        " source. The list reflects what was last reported by the source —"
        " it does not auto-poll on every command.\n\n"
        "`vrg update available` is read-only. To act on a package, use"
        " `vrg update download`, `vrg update install`, or `vrg update apply`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

AVAILABLE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("version"),
    ColumnDef(
        "downloaded",
        format_fn=format_bool_yn,
        style_map={"Y": "green", "-": "dim"},
    ),
    ColumnDef("optional", format_fn=format_bool_yn),
    ColumnDef("description", wide_only=True),
    ColumnDef("branch", wide_only=True),
    ColumnDef("source", wide_only=True),
]


def _available_to_dict(pkg: Any) -> dict[str, Any]:
    """Convert an UpdateSourcePackage SDK object to a dict for output."""
    return {
        "$key": int(pkg.key),
        "name": pkg.name,
        "version": pkg.get("version", ""),
        "downloaded": pkg.get("downloaded"),
        "optional": pkg.get("optional"),
        "description": pkg.get("description", ""),
        "branch": pkg.get("branch", ""),
        "source": pkg.get("source", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    source: Annotated[
        int | None,
        typer.Option("--source", help="Filter by source key."),
    ] = None,
    branch: Annotated[
        int | None,
        typer.Option("--branch", help="Filter by branch key."),
    ] = None,
    downloaded: Annotated[
        bool,
        typer.Option("--downloaded", help="Show only downloaded packages."),
    ] = False,
    pending: Annotated[
        bool,
        typer.Option("--pending", help="Show only pending (not downloaded) packages."),
    ] = False,
) -> None:
    """List available update packages from sources.

    Examples:

        vrg update available list
        vrg update available list --pending
        vrg update available list --downloaded
        vrg update available list --source 1 --branch 2
        vrg -o json update available list --query "[?downloaded=='Y'].name"

    Reflects the candidate set from the last `vrg update check`.
    `--downloaded` and `--pending` are mutually exclusive. Useful
    `--query` fields: `name`, `version`, `downloaded`, `optional`,
    `branch`, `source`.
    """
    vctx = get_context(ctx)

    if downloaded and pending:
        raise typer.BadParameter("--downloaded and --pending are mutually exclusive.")

    if downloaded:
        packages = vctx.client.update_source_packages.list_downloaded()
    elif pending:
        packages = vctx.client.update_source_packages.list_pending()
    else:
        kwargs: dict[str, Any] = {}
        if source is not None:
            kwargs["source"] = source
        if branch is not None:
            kwargs["branch"] = branch
        packages = vctx.client.update_source_packages.list(**kwargs)

    data = [_available_to_dict(p) for p in packages]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=AVAILABLE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Package key or name.")],
) -> None:
    """Get an available update package by key or name.

    Examples:

        vrg update available get verge-os
        vrg update available get 42
        vrg -o json update available get verge-os

    Name lookups exit 6 when nothing matches or exit 7 when the same
    name appears on multiple sources/branches — pass the numeric
    `$key` to disambiguate.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_source_packages, identifier, "Available package")
    pkg = vctx.client.update_source_packages.get(key=key)
    output_result(
        _available_to_dict(pkg),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=AVAILABLE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
