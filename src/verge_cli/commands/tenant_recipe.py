"""Tenant recipe management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.commands import tenant_recipe_instance, tenant_recipe_log
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource

app = typer.Typer(
    name="tenant-recipe",
    help="Manage tenant recipes.",
    no_args_is_help=True,
)

app.add_typer(tenant_recipe_instance.app, name="instance")
app.add_typer(tenant_recipe_log.app, name="log")

TENANT_RECIPE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description", wide_only=True),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map={"Y": "green", "-": "red"}),
    ColumnDef("version", wide_only=True),
]


def _recipe_to_dict(recipe: Any) -> dict[str, Any]:
    """Convert a TenantRecipe SDK object to a dict for output."""
    return {
        "$key": recipe.key,
        "name": recipe.name,
        "description": recipe.get("description", ""),
        "enabled": recipe.get("enabled"),
        "version": recipe.get("version", ""),
        "icon": recipe.get("icon", ""),
        "preserve_certs": recipe.get("preserve_certs"),
    }


def _parse_set_args(set_args: list[str]) -> dict[str, str]:
    """Parse KEY=VALUE pairs into a dict.

    Splits on the first ``=`` so values containing ``=`` are preserved.
    """
    result: dict[str, str] = {}
    for item in set_args:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid --set format: '{item}'. Expected KEY=VALUE.")
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _resolve_tenant_recipe(vctx: Any, identifier: str) -> str:
    """Resolve a tenant recipe identifier to a hex key."""
    return resolve_nas_resource(
        vctx.client.tenant_recipes,
        identifier,
        resource_type="tenant recipe",
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
) -> None:
    """List tenant recipes."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.tenant_recipes.list(), _recipe_to_dict, TENANT_RECIPE_COLUMNS
        )
        return
    vctx = get_context(ctx)
    recipes = vctx.client.tenant_recipes.list()
    data = [_recipe_to_dict(r) for r in recipes]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Tenant recipe name or key.")],
) -> None:
    """Get a tenant recipe by name or key."""
    vctx = get_context(ctx)
    key = _resolve_tenant_recipe(vctx, recipe)
    item = vctx.client.tenant_recipes.get(key)
    output_result(
        _recipe_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Tenant recipe name or key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New recipe name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description."),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option("--version", help="New version string."),
    ] = None,
    icon: Annotated[
        str | None,
        typer.Option("--icon", help="Recipe icon."),
    ] = None,
    preserve_certs: Annotated[
        bool | None,
        typer.Option("--preserve-certs/--no-preserve-certs", help="Preserve certificates."),
    ] = None,
) -> None:
    """Update a tenant recipe."""
    vctx = get_context(ctx)
    key = _resolve_tenant_recipe(vctx, recipe)
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if version is not None:
        kwargs["version"] = version
    if icon is not None:
        kwargs["icon"] = icon
    if preserve_certs is not None:
        kwargs["preserve_certs"] = preserve_certs
    result = vctx.client.tenant_recipes.update(key, **kwargs)
    output_result(
        _recipe_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TENANT_RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tenant recipe '{recipe}' updated.")


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Tenant recipe name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a tenant recipe."""
    vctx = get_context(ctx)
    key = _resolve_tenant_recipe(vctx, recipe)
    if not confirm_action(f"Delete tenant recipe '{recipe}'?", yes=yes):
        raise typer.Abort()
    vctx.client.tenant_recipes.delete(key)
    output_success(f"Tenant recipe '{recipe}' deleted.")


@app.command("download")
@handle_errors()
def download_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Tenant recipe name or key.")],
) -> None:
    """Download a tenant recipe from the catalog repository."""
    vctx = get_context(ctx)
    key = _resolve_tenant_recipe(vctx, recipe)
    vctx.client.tenant_recipes.download(key)
    output_success(f"Tenant recipe '{recipe}' downloaded.")


@app.command("deploy")
@handle_errors()
def deploy_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Tenant recipe name or key.")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name for the deployed tenant.")],
    set_args: Annotated[
        list[str] | None,
        typer.Option("--set", help="Answer in KEY=VALUE format (repeatable)."),
    ] = None,
) -> None:
    """Deploy a tenant recipe to create a new tenant."""
    vctx = get_context(ctx)
    key = _resolve_tenant_recipe(vctx, recipe)
    answers: dict[str, str] | None = None
    if set_args:
        answers = _parse_set_args(set_args)
    instance = vctx.client.tenant_recipes.deploy(key, name, answers=answers)
    inst_data = {
        "$key": int(instance.key),
        "name": instance.name,
        "recipe_name": instance.get("recipe_name", ""),
    }
    output_result(
        inst_data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tenant recipe '{recipe}' deployed as '{name}'.")
