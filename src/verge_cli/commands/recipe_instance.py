"""Recipe instance management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="instance",
    help=(
        "Manage VM recipe instances — VMs deployed from a recipe.\n\n"
        "A **recipe instance** is the link between a deployed VM and the"
        " recipe it was created from. Every `vrg recipe deploy` produces an"
        " instance row that records the source recipe, the answer values"
        " supplied at deploy time, and whether the VM should auto-update"
        " when the recipe is republished.\n\n"
        "Instances are tracking metadata, not the VM itself. Deleting an"
        " instance only detaches the VM from its recipe; the VM keeps"
        " running. To remove the VM, use `vrg vm delete`. A recipe with"
        " any attached instances cannot be deleted until the instances are"
        " detached.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every recipe instance on the system\n"
        "    vrg recipe instance list\n\n"
        "    # Filter instances to a specific recipe\n"
        "    vrg recipe instance list --recipe ubuntu-server\n\n"
        "    # Inspect an instance as JSON (includes recipe + auto-update flag)\n"
        "    vrg -o json recipe instance get web-02\n\n"
        "    # Detach an instance from its recipe (the VM is not deleted)\n"
        "    vrg recipe instance delete web-02 --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Instances are referenced by name or numeric key. When a name"
        " matches multiple instances, vrg prints all matches and exits with"
        " code 7 — use the key to disambiguate.\n\n"
        "Instances created with `--auto-update` are re-templated when the"
        " source recipe is republished. Instances without auto-update stay"
        " on the recipe version they were deployed from."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

RECIPE_INSTANCE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("recipe_name", header="Recipe"),
    ColumnDef("auto_update", header="Auto Update", format_fn=format_bool_yn, wide_only=True),
]


def _instance_to_dict(inst: Any) -> dict[str, Any]:
    """Convert a VmRecipeInstance SDK object to a dict for output."""
    return {
        "$key": int(inst.key),
        "name": inst.name,
        "recipe_name": inst.get("recipe_name", ""),
        "auto_update": inst.get("auto_update"),
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
    """List deployed recipe instances."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if recipe is not None:
        recipe_key = resolve_nas_resource(
            vctx.client.vm_recipes,
            recipe,
            resource_type="recipe",
        )
        kwargs["recipe"] = recipe_key
    instances = vctx.client.vm_recipe_instances.list(**kwargs)
    data = [_instance_to_dict(i) for i in instances]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_INSTANCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    instance: Annotated[str, typer.Argument(help="Instance name or key.")],
) -> None:
    """Get a recipe instance by name or key."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.vm_recipe_instances, instance, "recipe instance")
    item = vctx.client.vm_recipe_instances.get(key=key)
    output_result(
        _instance_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_INSTANCE_COLUMNS,
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
    """Delete a recipe instance (removes tracking only, not the VM)."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.vm_recipe_instances, instance, "recipe instance")
    if not confirm_action(
        f"Delete instance '{instance}'? This removes tracking only — the VM is not deleted.",
        yes=yes,
    ):
        raise typer.Abort()
    vctx.client.vm_recipe_instances.delete(key)
    output_success(f"Instance '{instance}' deleted.")
