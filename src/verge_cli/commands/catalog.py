"""Catalog management commands (parent app + catalog CRUD)."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.commands import catalog_log, catalog_repo
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="catalog",
    help=(
        "Manage catalogs — named collections of VM and tenant recipes inside"
        " a repository.\n\n"
        "A **catalog** groups related recipes within a repository so operators"
        " can organize templates by purpose (e.g., one catalog for Windows VM"
        " recipes, another for Linux, another for tenant recipes). Every"
        " catalog belongs to exactly one **repository** (`vrg catalog repo`)"
        " and controls who can see its recipes through a **publishing scope**."
        "\n\n"
        "Hierarchy: **Repository → Catalog → Recipe → Section → Question**."
        " Use `vrg catalog repo` for repositories, `vrg recipe` / `vrg"
        " tenant-recipe` for the recipes themselves, and `vrg catalog log`"
        " for per-catalog audit entries.\n\n"
        "Publishing scope controls visibility:\n\n"
        "- `private` — only this VergeOS system can see the recipes\n"
        "- `tenant` — this system and its own tenants\n"
        "- `global` — this system, its tenants, and external federated systems\n"
        "- `none` — disabled, not available anywhere\n\n"
        "A system supports up to 5,000 catalogs across all repositories.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List catalogs across all repositories\n"
        "    vrg catalog list\n\n"
        "    # Filter to one repository\n"
        "    vrg catalog list --repo MarketPlace\n\n"
        "    # Inspect a catalog as JSON (shows repo, scope, enabled state)\n"
        "    vrg -o json catalog get windows-server\n\n"
        "    # Create a private catalog in the default Local repository\n"
        "    vrg catalog create --name internal-templates --repo Local \\\n"
        "        --description 'Hardened internal VM recipes'\n\n"
        "    # Share an existing catalog with tenants\n"
        "    vrg catalog update windows-server --publishing-scope tenant\n\n"
        "    # Disable a catalog without deleting it\n"
        "    vrg catalog disable windows-server\n\n"
        "    # Manage repositories (the parent containers)\n"
        "    vrg catalog repo list\n"
        "    vrg catalog repo refresh MarketPlace\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Catalog keys are SHA-1-derived **hex strings**, not integers — a"
        " catalog identified by name resolves to a hex key internally. Pass"
        " either the catalog name or the hex key to `get`/`update`/`delete`."
        " When a name matches multiple catalogs vrg prints all matches and"
        " exits with code 7 — use the hex key to disambiguate.\n\n"
        "The `repository` field is **read-only after creation** — a catalog"
        " cannot be moved to a different repository. Delete and recreate it"
        " in the target repository instead.\n\n"
        "Remote repositories (type `remote`, `remote-git`, `yottabyte`,"
        " `provider`) are managed on the source system — catalogs discovered"
        " through them appear in `list` but must be modified at the source."
        " Local catalogs live in repositories of type `local`."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Register sub-commands
app.add_typer(catalog_repo.app, name="repo")
app.add_typer(catalog_log.app, name="log")

CATALOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("repository", header="Repository"),
    ColumnDef("publishing_scope", header="Scope"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map={"Y": "green", "-": "red"}),
    ColumnDef("description", wide_only=True),
    ColumnDef("created", wide_only=True),
]


def _catalog_to_dict(catalog: Any) -> dict[str, Any]:
    """Convert a Catalog SDK object to a dict for output."""
    return {
        "$key": catalog.key,  # hex string, not int
        "name": catalog.name,
        "repository": catalog.get("repository", ""),
        "description": catalog.get("description", ""),
        "publishing_scope": catalog.get("publishing_scope", ""),
        "enabled": catalog.get("enabled"),
        "created": catalog.get("created", ""),
    }


def _resolve_catalog(vctx: Any, identifier: str) -> str:
    """Resolve catalog identifier to hex key."""
    return resolve_nas_resource(
        vctx.client.catalogs,
        identifier,
        resource_type="catalog",
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    repo: Annotated[
        str | None,
        typer.Option("--repo", help="Filter by repository name or key."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled state."),
    ] = None,
) -> None:
    """List catalogs.

    Examples:

        vrg catalog list
        vrg catalog list --repo MarketPlace --enabled
        vrg -o json catalog list \\
            | jq '.[] | select(.publishing_scope == "global") | .name'

    Useful `--query` fields: `name`, `repository`, `publishing_scope`,
    `enabled`, `description`. Use `--filter` for server-side OData
    filtering. Works with `--all-profiles` to list across every
    configured profile.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.catalogs.list(), _catalog_to_dict, CATALOG_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if repo is not None:
        repo_key = resolve_resource_id(
            vctx.client.catalog_repositories,
            repo,
            "Catalog repository",
        )
        kwargs["repository"] = repo_key
    if enabled is not None:
        kwargs["enabled"] = enabled
    catalogs = vctx.client.catalogs.list(**kwargs)
    data = [_catalog_to_dict(c) for c in catalogs]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    catalog: Annotated[str, typer.Argument(help="Catalog name or hex key.")],
) -> None:
    """Get a catalog by name or key.

    Examples:

        vrg catalog get windows-server
        vrg -o json catalog get windows-server
        vrg -o json catalog get 8f3a...0b2c

    Resolves `catalog` by name or SHA-1 hex key. Ambiguous names exit
    with code 7 — use the hex key to disambiguate.
    """
    vctx = get_context(ctx)
    key = _resolve_catalog(vctx, catalog)
    item = vctx.client.catalogs.get(key)
    output_result(
        _catalog_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", help="Catalog name.")],
    repo: Annotated[str, typer.Option("--repo", help="Repository name or key.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="Catalog description."),
    ] = None,
    publishing_scope: Annotated[
        str,
        typer.Option("--publishing-scope", help="Publishing scope (private/global/tenant)."),
    ] = "private",
    enabled: Annotated[
        bool,
        typer.Option("--enabled/--no-enabled", help="Enable the catalog."),
    ] = True,
) -> None:
    """Create a new catalog.

    Examples:

        vrg catalog create --name internal-templates --repo Local
        vrg catalog create --name windows-images --repo Local \\
            --description 'Hardened Windows VM recipes' \\
            --publishing-scope tenant

    `--publishing-scope` accepts `private` (this system only), `tenant`
    (system + its tenants), `global` (system + tenants + federated),
    or `none` (disabled). The `--repo` association is **read-only after
    creation** — catalogs cannot be moved between repositories.
    """
    vctx = get_context(ctx)
    repo_key = resolve_resource_id(
        vctx.client.catalog_repositories,
        repo,
        "Catalog repository",
    )
    kwargs: dict[str, Any] = {
        "name": name,
        "repository": repo_key,
        "publishing_scope": publishing_scope,
        "enabled": enabled,
    }
    if description is not None:
        kwargs["description"] = description
    result = vctx.client.catalogs.create(**kwargs)
    output_result(
        _catalog_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Catalog '{name}' created.", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    catalog: Annotated[str, typer.Argument(help="Catalog name or hex key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", help="New catalog name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    publishing_scope: Annotated[
        str | None,
        typer.Option("--publishing-scope", help="New publishing scope."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Enable or disable catalog."),
    ] = None,
) -> None:
    """Update a catalog.

    Examples:

        vrg catalog update windows-server --publishing-scope tenant
        vrg catalog update windows-server --description 'Retired 2024-Q4'
        vrg catalog update windows-server --name windows-retired

    Only flags you pass are changed. `repository` cannot be updated —
    delete and recreate the catalog in the target repository instead.
    """
    vctx = get_context(ctx)
    key = _resolve_catalog(vctx, catalog)
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if publishing_scope is not None:
        kwargs["publishing_scope"] = publishing_scope
    if enabled is not None:
        kwargs["enabled"] = enabled
    result = vctx.client.catalogs.update(key, **kwargs)
    output_result(
        _catalog_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CATALOG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Catalog '{catalog}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    catalog: Annotated[str, typer.Argument(help="Catalog name or hex key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Delete a catalog.

    Examples:

        vrg catalog delete internal-templates
        vrg catalog delete internal-templates --yes

    Recipes inside the catalog must be removed (or moved) before
    deletion — otherwise the API returns an error. To temporarily hide
    a catalog without deleting, use `vrg catalog disable` instead.
    """
    vctx = get_context(ctx)
    key = _resolve_catalog(vctx, catalog)
    if not confirm_action(f"Delete catalog '{catalog}'?", yes=yes):
        raise typer.Abort()
    vctx.client.catalogs.delete(key)
    output_success(f"Catalog '{catalog}' deleted.", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    catalog: Annotated[str, typer.Argument(help="Catalog name or hex key.")],
) -> None:
    """Enable a catalog.

    Examples:

        vrg catalog enable windows-server
        vrg catalog enable 8f3a...0b2c

    Makes the catalog's recipes visible again according to its
    publishing scope. Equivalent to `vrg catalog update <catalog>
    --enabled`.
    """
    vctx = get_context(ctx)
    key = _resolve_catalog(vctx, catalog)
    vctx.client.catalogs.update(key, enabled=True)
    output_success(f"Catalog '{catalog}' enabled.", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    catalog: Annotated[str, typer.Argument(help="Catalog name or hex key.")],
) -> None:
    """Disable a catalog.

    Examples:

        vrg catalog disable windows-server
        vrg catalog disable 8f3a...0b2c

    Hides the catalog's recipes without deleting them. Deployed
    instances keep running; new deploys cannot pick recipes from a
    disabled catalog. Re-enable with `vrg catalog enable`.
    """
    vctx = get_context(ctx)
    key = _resolve_catalog(vctx, catalog)
    vctx.client.catalogs.update(key, enabled=False)
    output_success(f"Catalog '{catalog}' disabled.", quiet=vctx.quiet)
