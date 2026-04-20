"""Update package commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result

app = typer.Typer(
    name="package",
    help=(
        "View installed update packages on the local system.\n\n"
        "An *installed package* is a record in `update_packages` — the"
        " local catalog of ybpkg payloads that have been extracted and"
        " applied to this VergeOS cluster. Each row tracks the package"
        " name, installed version, type (squashfs/tgz/vdb/gguf), and the"
        " branch it was sourced from.\n\n"
        "This is the *state* side of the update pipeline (what's on disk"
        " right now). For *candidate* packages that could be installed"
        " next, see `vrg update available`. For update history and the"
        " events that produced the current state, see `vrg update log`.\n\n"
        "Use `-o json` for structured output. Useful fields to `--query`:"
        " `name`, `version`, `type`, `optional`, `branch`. Packages are"
        " keyed by name (strings), so `vrg update package get <name>`"
        " takes the name directly and returns exit 6 if no match.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every installed package\n"
        "    vrg update package list\n\n"
        "    # Scope to packages installed from a specific branch\n"
        "    vrg update package list --branch 1\n\n"
        "    # Inspect one package as JSON\n"
        "    vrg -o json update package get verge-os\n\n"
        "    # Extract just name and version for scripting\n"
        "    vrg -o json update package list --query '[].[name,version]'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`vrg update package` is read-only. To change what is installed,"
        " drive the pipeline: `vrg update check` → `vrg update download`"
        " → `vrg update install` (or `vrg update apply` for the full cycle).\n\n"
        "Optional packages (`optional: Y`) are components that ship with"
        " a branch but are not applied unless explicitly selected."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

PACKAGE_COLUMNS: list[ColumnDef] = [
    ColumnDef("name"),
    ColumnDef("version"),
    ColumnDef("type"),
    ColumnDef("optional", format_fn=format_bool_yn),
    ColumnDef("description", wide_only=True),
    ColumnDef("branch", wide_only=True),
    ColumnDef("modified", wide_only=True),
]


def _package_to_dict(pkg: Any) -> dict[str, Any]:
    """Convert an UpdatePackage SDK object to a dict for output."""
    return {
        "name": pkg.name,
        "version": pkg.get("version", ""),
        "type": pkg.get("type", ""),
        "optional": pkg.get("optional"),
        "description": pkg.get("description", ""),
        "branch": pkg.get("branch", ""),
        "modified": pkg.get("modified", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter_expr: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    branch: Annotated[
        int | None,
        typer.Option("--branch", help="Filter by branch key."),
    ] = None,
) -> None:
    """List installed update packages.

    Examples:

        vrg update package list
        vrg update package list --branch 1
        vrg -o json update package list
        vrg -o json update package list --query "[].[name,version]"

    Useful `--query` fields: `name`, `version`, `type`, `optional`,
    `branch`. The `type` column identifies the payload format
    (squashfs, tgz, vdb, gguf).
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter_expr is not None:
        kwargs["filter"] = filter_expr
    if branch is not None:
        kwargs["branch"] = branch
    packages = vctx.client.update_packages.list(**kwargs)
    data = [_package_to_dict(p) for p in packages]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=PACKAGE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Package name.")],
) -> None:
    """Get an installed update package by name.

    Examples:

        vrg update package get verge-os
        vrg -o json update package get verge-os

    Installed packages are keyed by name (string), so the argument is
    passed directly to the SDK — no numeric lookup. Exit 6 if the
    package isn't installed.
    """
    vctx = get_context(ctx)
    # Package keys are strings (name), not integers — pass directly
    pkg = vctx.client.update_packages.get(key=name)
    output_result(
        _package_to_dict(pkg),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=PACKAGE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
