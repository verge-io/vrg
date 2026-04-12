"""VM recipe management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.commands import recipe_instance, recipe_log, recipe_question, recipe_section
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="recipe",
    help="Manage VM recipes.",
    no_args_is_help=True,
)

app.add_typer(recipe_instance.app, name="instance")
app.add_typer(recipe_log.app, name="log")
app.add_typer(recipe_question.app, name="question")
app.add_typer(recipe_section.app, name="section")

RECIPE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description", wide_only=True),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map={"Y": "green", "-": "red"}),
    ColumnDef("notes", wide_only=True),
]


def _recipe_to_dict(recipe: Any) -> dict[str, Any]:
    """Convert a VmRecipe SDK object to a dict for output."""
    return {
        "$key": recipe.key,
        "name": recipe.name,
        "description": recipe.get("description", ""),
        "enabled": recipe.get("enabled"),
        "notes": recipe.get("notes", ""),
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


def _resolve_recipe(vctx: Any, identifier: str) -> str:
    """Resolve a recipe identifier to a hex key."""
    return resolve_nas_resource(
        vctx.client.vm_recipes,
        identifier,
        resource_type="recipe",
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    catalog: Annotated[
        str | None,
        typer.Option("--catalog", help="Filter by catalog name."),
    ] = None,
    downloaded: Annotated[
        bool | None,
        typer.Option("--downloaded/--not-downloaded", help="Filter by downloaded state."),
    ] = None,
) -> None:
    """List VM recipes."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.vm_recipes.list(), _recipe_to_dict, RECIPE_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if catalog is not None:
        kwargs["catalog"] = catalog
    if downloaded is not None:
        kwargs["downloaded"] = downloaded
    recipes = vctx.client.vm_recipes.list(**kwargs)
    data = [_recipe_to_dict(r) for r in recipes]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
) -> None:
    """Get a VM recipe by name or key."""
    vctx = get_context(ctx)
    key = _resolve_recipe(vctx, recipe)
    item = vctx.client.vm_recipes.get(key)
    output_result(
        _recipe_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Recipe name.")],
    vm: Annotated[str, typer.Option("--vm", help="Source VM name or key to base the recipe on.")],
    catalog: Annotated[
        str | None,
        typer.Option("--catalog", help="Catalog name or key."),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option("--version", help="Recipe version string."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Recipe description."),
    ] = None,
    notes: Annotated[
        str | None,
        typer.Option("--notes", help="Recipe notes/documentation."),
    ] = None,
    enabled: Annotated[
        bool,
        typer.Option("--enabled/--no-enabled", help="Enable the recipe."),
    ] = True,
) -> None:
    """Create a new VM recipe from an existing VM."""
    vctx = get_context(ctx)
    vm_key = resolve_resource_id(vctx.client.vms, vm, "vm")
    kwargs: dict[str, Any] = {"name": name, "vm": vm_key}
    if catalog is not None:
        # Catalog keys are 40-char hex strings; resolve name if needed
        is_hex_key = len(catalog) == 40 and all(c in "0123456789abcdef" for c in catalog.lower())
        if is_hex_key:
            kwargs["catalog"] = catalog
        else:
            kwargs["catalog"] = resolve_nas_resource(
                vctx.client.catalogs, catalog, resource_type="catalog"
            )
    if version is not None:
        kwargs["version"] = version
    if description is not None:
        kwargs["description"] = description
    if notes is not None:
        kwargs["notes"] = notes
    kwargs["enabled"] = enabled
    created = vctx.client.vm_recipes.create(**kwargs)
    # POST only returns $key; fetch full object for display
    result = vctx.client.vm_recipes.get(created.key)
    output_result(
        _recipe_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Recipe '{name}' created from VM '{vm}'.")


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
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
) -> None:
    """Update a VM recipe."""
    vctx = get_context(ctx)
    key = _resolve_recipe(vctx, recipe)
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if version is not None:
        kwargs["version"] = version
    result = vctx.client.vm_recipes.update(key, **kwargs)
    output_result(
        _recipe_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Recipe '{recipe}' updated.")


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a VM recipe."""
    vctx = get_context(ctx)
    key = _resolve_recipe(vctx, recipe)
    if not confirm_action(f"Delete recipe '{recipe}'?", yes=yes):
        raise typer.Abort()
    vctx.client.vm_recipes.delete(key)
    output_success(f"Recipe '{recipe}' deleted.")


@app.command("download")
@handle_errors()
def download_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
) -> None:
    """Download a recipe from the catalog repository."""
    vctx = get_context(ctx)
    key = _resolve_recipe(vctx, recipe)
    vctx.client.vm_recipes.download(key)
    output_success(f"Recipe '{recipe}' downloaded.")


@app.command("deploy")
@handle_errors()
def deploy_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name for the deployed VM.")],
    set_args: Annotated[
        list[str] | None,
        typer.Option("--set", help="Answer in KEY=VALUE format (repeatable)."),
    ] = None,
    auto_update: Annotated[
        bool,
        typer.Option("--auto-update", help="Auto-update when recipe is updated."),
    ] = False,
) -> None:
    """Deploy a VM recipe to create a new VM."""
    vctx = get_context(ctx)
    key = _resolve_recipe(vctx, recipe)
    answers: dict[str, str] | None = None
    if set_args:
        answers = _parse_set_args(set_args)
    instance = vctx.client.vm_recipes.deploy(key, name, answers=answers, auto_update=auto_update)
    inst_data = {
        "$key": int(instance.key),
        "name": instance.name,
        "recipe_name": instance.get("recipe_name", ""),
        "auto_update": instance.get("auto_update"),
    }
    output_result(
        inst_data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Recipe '{recipe}' deployed as '{name}'.")
