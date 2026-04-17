"""Update branch commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="branch",
    help=(
        "View update branches published by configured update sources.\n\n"
        "An *update branch* is a named release train hosted on an update"
        " source — similar to an APT release codename. The branch scopes"
        " which package set is visible: `stable` exposes GA releases,"
        " `beta` exposes pre-release builds, and so on. The active branch"
        " is stored in `update_settings.branch` and determines what"
        " `vrg update available list` returns after the next check.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `name`, `description`. Looking up by name returns exit 6 (not"
        " found) or exit 7 (multiple matches) when ambiguous — pass the"
        " numeric `$key` to disambiguate.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all branches published by configured sources\n"
        "    vrg update branch list\n\n"
        "    # Inspect one branch as JSON\n"
        "    vrg -o json update branch get stable\n\n"
        "    # Look up a branch by numeric key\n"
        "    vrg update branch get 2\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`vrg update branch` is read-only. To switch which branch is"
        " active, update `update_settings.branch` and run `vrg update"
        " check` to refresh the available-package list against the new"
        " release train."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

BRANCH_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description"),
    ColumnDef("created", wide_only=True),
]


def _branch_to_dict(branch: Any) -> dict[str, Any]:
    """Convert an UpdateBranch SDK object to a dict for output."""
    return {
        "$key": int(branch.key),
        "name": branch.name,
        "description": branch.get("description", ""),
        "created": branch.get("created", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter_expr: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
) -> None:
    """List update branches.

    Examples:

        vrg update branch list
        vrg -o json update branch list
        vrg update branch list --filter "name eq 'stable'"

    Useful `--query` fields: `name`, `description`, `created`. The
    active branch is whichever one is currently referenced in
    `update_settings.branch`.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter_expr is not None:
        kwargs["filter"] = filter_expr
    branches = vctx.client.update_branches.list(**kwargs)
    data = [_branch_to_dict(b) for b in branches]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=BRANCH_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    identifier: Annotated[str, typer.Argument(help="Branch key or name.")],
) -> None:
    """Get an update branch by key or name.

    Examples:

        vrg update branch get stable
        vrg update branch get 2
        vrg -o json update branch get stable

    Name lookups exit 6 (not found) or exit 7 (multiple matches) when
    the same branch name is published by more than one source — pass
    the numeric `$key` to disambiguate.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.update_branches, identifier, "Update branch")
    branch = vctx.client.update_branches.get(key=key)
    output_result(
        _branch_to_dict(branch),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=BRANCH_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
