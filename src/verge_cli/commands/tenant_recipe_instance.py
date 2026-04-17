"""Tenant recipe instance management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="instance",
    help=(
        "Manage tenant recipe instances — tenants deployed from a recipe.\n\n"
        "A **tenant recipe instance** is the link between a deployed tenant"
        " and the tenant recipe it was created from. Every"
        " `vrg tenant-recipe deploy` produces an instance row that records"
        " the source recipe and the answer values supplied at deploy time"
        " (admin credentials, hostnames, IP addresses, node CPU/RAM,"
        " etc.).\n\n"
        "Instances are tracking metadata, not the tenant itself. Deleting"
        " an instance only detaches the tenant from its recipe; the"
        " tenant — including its VMs, networks, users, and storage —"
        " keeps running. To remove the tenant, use `vrg tenant delete`."
        " A recipe with any attached instances cannot be deleted until the"
        " instances are detached.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every tenant recipe instance on the system\n"
        "    vrg tenant-recipe instance list\n\n"
        "    # Filter instances to a specific tenant recipe\n"
        "    vrg tenant-recipe instance list --recipe customer-baseline\n\n"
        "    # Inspect an instance as JSON (includes recipe + key)\n"
        "    vrg -o json tenant-recipe instance get acme-corp\n\n"
        "    # Detach an instance from its recipe (the tenant is not deleted)\n"
        "    vrg tenant-recipe instance delete acme-corp --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Instances are referenced by name or numeric key. When a name"
        " matches multiple instances, vrg prints all matches and exits"
        " with code 7 — use the key to disambiguate.\n\n"
        "Use `--recipe NAME_OR_KEY` on `list` to scope output to a single"
        " tenant recipe. Detaching an instance leaves the tenant fully"
        " functional but breaks the link the parent recipe uses to track"
        " deployments — recipe republish notifications no longer reach"
        " that tenant."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

TENANT_RECIPE_INSTANCE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("recipe_name", header="Recipe"),
]


def _instance_to_dict(inst: Any) -> dict[str, Any]:
    """Convert a TenantRecipeInstance SDK object to a dict for output."""
    return {
        "$key": int(inst.key),
        "name": inst.name,
        "recipe_name": inst.get("recipe_name", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    recipe: Annotated[
        str | None,
        typer.Option("--recipe", help="Filter by tenant recipe name or key."),
    ] = None,
) -> None:
    """List tenant recipe instances.

    Examples:

        vrg tenant-recipe instance list
        vrg tenant-recipe instance list --recipe customer-baseline
        vrg -o json tenant-recipe instance list --query "[].name"

    Useful `--query` fields: `name`, `recipe_name`. Without `--recipe`,
    returns instances across every tenant recipe on the system.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if recipe is not None:
        recipe_key = resolve_nas_resource(
            vctx.client.tenant_recipes,
            recipe,
            resource_type="tenant recipe",
        )
        kwargs["recipe"] = recipe_key
    instances = vctx.client.tenant_recipe_instances.list(**kwargs)
    data = [_instance_to_dict(i) for i in instances]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_RECIPE_INSTANCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    instance: Annotated[str, typer.Argument(help="Instance name or key.")],
) -> None:
    """Get a tenant recipe instance by name or key.

    Examples:

        vrg tenant-recipe instance get acme-corp
        vrg -o json tenant-recipe instance get 42

    Resolves `instance` by name or numeric key. Ambiguous names exit
    with code 7 — use the key to disambiguate.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(
        vctx.client.tenant_recipe_instances, instance, "tenant recipe instance"
    )
    item = vctx.client.tenant_recipe_instances.get(key=key)
    output_result(
        _instance_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_RECIPE_INSTANCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    instance: Annotated[str, typer.Argument(help="Instance name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a tenant recipe instance (removes tracking only).

    Examples:

        vrg tenant-recipe instance delete acme-corp
        vrg tenant-recipe instance delete acme-corp --yes

    Detaches the tenant from its recipe. The tenant — including its
    VMs, networks, users, and storage — keeps running. To remove the
    tenant, use `vrg tenant delete`.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(
        vctx.client.tenant_recipe_instances, instance, "tenant recipe instance"
    )
    if not confirm_action(
        f"Delete instance '{instance}'? This removes tracking only.",
        yes=yes,
    ):
        raise typer.Abort()
    vctx.client.tenant_recipe_instances.delete(key)
    output_success(f"Instance '{instance}' deleted.")
