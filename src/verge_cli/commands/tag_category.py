"""Tag category management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="category",
    help=(
        "Manage tag categories on VergeOS.\n\n"
        "Tag **categories** are the schema layer above individual tags. Every"
        " tag must belong to a category, and the category controls **which"
        " object types** the tag may be applied to (VMs, networks, volumes,"
        " nodes, tenants, users, clusters, sites, groups) via its"
        " `taggable_*` flags. A category with `single_tag_selection=true`"
        " enforces mutual exclusivity — a given object may carry at most one"
        " tag from that category at a time (e.g., an `Environment` category"
        " where a VM is either `prod`, `staging`, or `dev` but never"
        " two).\n\n"
        "Use this group to create the category first, then create tags"
        " inside it with `vrg tag create --category <name>`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every category and what it can tag\n"
        "    vrg tag category list\n\n"
        "    # Machine-readable output for agents\n"
        "    vrg -o json tag category list\n\n"
        "    # Inspect a single category (name or numeric $key)\n"
        "    vrg tag category get Environment\n\n"
        "    # Create an exclusive category that applies only to VMs\n"
        "    vrg tag category create --name Environment \\\n"
        "        --taggable-vms --single-selection\n\n"
        "    # Create a multi-target category (VMs and networks)\n"
        "    vrg tag category create --name Owner \\\n"
        "        --taggable-vms --taggable-networks \\\n"
        "        --description 'Team ownership labels'\n\n"
        "    # Widen an existing category to also tag tenants\n"
        "    vrg tag category update Owner --taggable-tenants\n\n"
        "    # Delete a category (cascades — see notes)\n"
        "    vrg tag category delete Owner\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Categories are referenced by **name** or **numeric key** (`$key`)."
        " Ambiguous name resolution exits with code 7.\n\n"
        "A category's `taggable_*` flags must match the target resource at"
        " assignment time. Attempting `vrg tag assign mytag vm web-01` when"
        " the tag's category does not have `taggable_vms=true` is"
        " rejected.\n\n"
        "Deleting a category **cascades** to every tag inside it and every"
        " membership row attached to those tags (objects stop carrying the"
        " tags). There is no soft-delete — inspect `vrg tag list --category"
        " <name>` and `vrg tag members <tag>` first if you need a reference"
        " of what will be removed."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

TAG_CATEGORY_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef(
        "single_selection",
        header="Single Select",
        format_fn=format_bool_yn,
    ),
    ColumnDef("taggable_types", header="Taggable Types"),
    ColumnDef("description", wide_only=True),
    ColumnDef("created", format_fn=format_epoch, wide_only=True),
]

# Attribute names on the SDK TagCategory object for taggable checks.
# The property names on the SDK object differ from the raw API fields.
_TAGGABLE_ATTRS: list[tuple[str, str]] = [
    ("taggable_vms", "vms"),
    ("taggable_networks", "networks"),
    ("taggable_volumes", "volumes"),
    ("taggable_nodes", "nodes"),
    ("taggable_tenants", "tenants"),
    ("taggable_users", "users"),
    ("taggable_clusters", "clusters"),
    ("taggable_sites", "sites"),
    ("taggable_groups", "groups"),
]


def _category_to_dict(cat: Any) -> dict[str, Any]:
    """Convert a TagCategory SDK object to a dict for output."""
    taggable: list[str] = []
    for attr, display in _TAGGABLE_ATTRS:
        if getattr(cat, attr, False):
            taggable.append(display)
    return {
        "$key": int(cat.key),
        "name": cat.name,
        "description": cat.description or "",
        "single_selection": cat.is_single_tag_selection,
        "taggable_types": ", ".join(taggable) if taggable else "none",
        "created": cat.created,
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
    """List tag categories.

    Examples:

        vrg tag category list
        vrg -o json tag category list
        vrg -o json tag category list --query "[?single_selection].name"

    Useful `--query` fields: `name`, `single_selection`,
    `taggable_types`, `description`.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.tag_categories.list(), _category_to_dict, TAG_CATEGORY_COLUMNS
        )
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter_expr is not None:
        kwargs["filter"] = filter_expr
    categories = vctx.client.tag_categories.list(**kwargs)
    output_result(
        [_category_to_dict(c) for c in categories],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_CATEGORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    category: Annotated[str, typer.Argument(help="Category name or key.")],
) -> None:
    """Get a tag category by name or key.

    Examples:

        vrg tag category get Environment
        vrg -o json tag category get 3

    Resolves by name or numeric `$key`. Ambiguous names exit with
    code 7 — use the key to disambiguate.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tag_categories, category, "Tag category")
    item = vctx.client.tag_categories.get(key)
    output_result(
        _category_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_CATEGORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Category name.")],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Category description."),
    ] = None,
    single_selection: Annotated[
        bool,
        typer.Option(
            "--single-selection/--no-single-selection",
            help="Only one tag from this category per resource.",
        ),
    ] = False,
    taggable_vms: Annotated[
        bool,
        typer.Option("--taggable-vms/--no-taggable-vms", help="Allow tagging VMs."),
    ] = False,
    taggable_networks: Annotated[
        bool,
        typer.Option(
            "--taggable-networks/--no-taggable-networks",
            help="Allow tagging networks.",
        ),
    ] = False,
    taggable_volumes: Annotated[
        bool,
        typer.Option(
            "--taggable-volumes/--no-taggable-volumes",
            help="Allow tagging volumes.",
        ),
    ] = False,
    taggable_nodes: Annotated[
        bool,
        typer.Option(
            "--taggable-nodes/--no-taggable-nodes",
            help="Allow tagging nodes.",
        ),
    ] = False,
    taggable_tenants: Annotated[
        bool,
        typer.Option(
            "--taggable-tenants/--no-taggable-tenants",
            help="Allow tagging tenants.",
        ),
    ] = False,
    taggable_users: Annotated[
        bool,
        typer.Option(
            "--taggable-users/--no-taggable-users",
            help="Allow tagging users.",
        ),
    ] = False,
    taggable_clusters: Annotated[
        bool,
        typer.Option(
            "--taggable-clusters/--no-taggable-clusters",
            help="Allow tagging clusters.",
        ),
    ] = False,
    taggable_sites: Annotated[
        bool,
        typer.Option(
            "--taggable-sites/--no-taggable-sites",
            help="Allow tagging sites.",
        ),
    ] = False,
    taggable_groups: Annotated[
        bool,
        typer.Option(
            "--taggable-groups/--no-taggable-groups",
            help="Allow tagging groups.",
        ),
    ] = False,
) -> None:
    """Create a new tag category.

    Examples:

        # Mutually-exclusive environment category for VMs only
        vrg tag category create --name Environment \\
            --taggable-vms --single-selection

        # Multi-target ownership category
        vrg tag category create --name Owner \\
            --taggable-vms --taggable-networks \\
            --description "Team ownership labels"

    At least one `--taggable-*` flag should be set — a category with no
    taggable types cannot be assigned to any object. Use
    `--single-selection` to enforce that an object carries at most one
    tag from this category at a time.
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {"name": name}
    if description is not None:
        kwargs["description"] = description
    if single_selection:
        kwargs["single_tag_selection"] = True
    if taggable_vms:
        kwargs["taggable_vms"] = True
    if taggable_networks:
        kwargs["taggable_networks"] = True
    if taggable_volumes:
        kwargs["taggable_volumes"] = True
    if taggable_nodes:
        kwargs["taggable_nodes"] = True
    if taggable_tenants:
        kwargs["taggable_tenants"] = True
    if taggable_users:
        kwargs["taggable_users"] = True
    if taggable_clusters:
        kwargs["taggable_clusters"] = True
    if taggable_sites:
        kwargs["taggable_sites"] = True
    if taggable_groups:
        kwargs["taggable_groups"] = True
    result = vctx.client.tag_categories.create(**kwargs)
    output_result(
        _category_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_CATEGORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tag category '{name}' created.", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    category: Annotated[str, typer.Argument(help="Category name or key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New category name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description."),
    ] = None,
    single_selection: Annotated[
        bool | None,
        typer.Option(
            "--single-selection/--no-single-selection",
            help="Single tag selection mode.",
        ),
    ] = None,
    taggable_vms: Annotated[
        bool | None,
        typer.Option("--taggable-vms/--no-taggable-vms", help="Allow tagging VMs."),
    ] = None,
    taggable_networks: Annotated[
        bool | None,
        typer.Option(
            "--taggable-networks/--no-taggable-networks",
            help="Allow tagging networks.",
        ),
    ] = None,
    taggable_volumes: Annotated[
        bool | None,
        typer.Option(
            "--taggable-volumes/--no-taggable-volumes",
            help="Allow tagging volumes.",
        ),
    ] = None,
    taggable_nodes: Annotated[
        bool | None,
        typer.Option(
            "--taggable-nodes/--no-taggable-nodes",
            help="Allow tagging nodes.",
        ),
    ] = None,
    taggable_tenants: Annotated[
        bool | None,
        typer.Option(
            "--taggable-tenants/--no-taggable-tenants",
            help="Allow tagging tenants.",
        ),
    ] = None,
    taggable_users: Annotated[
        bool | None,
        typer.Option(
            "--taggable-users/--no-taggable-users",
            help="Allow tagging users.",
        ),
    ] = None,
    taggable_clusters: Annotated[
        bool | None,
        typer.Option(
            "--taggable-clusters/--no-taggable-clusters",
            help="Allow tagging clusters.",
        ),
    ] = None,
    taggable_sites: Annotated[
        bool | None,
        typer.Option(
            "--taggable-sites/--no-taggable-sites",
            help="Allow tagging sites.",
        ),
    ] = None,
    taggable_groups: Annotated[
        bool | None,
        typer.Option(
            "--taggable-groups/--no-taggable-groups",
            help="Allow tagging groups.",
        ),
    ] = None,
) -> None:
    """Update a tag category.

    Examples:

        # Widen Owner to also tag tenants
        vrg tag category update Owner --taggable-tenants

        # Rename and adjust description
        vrg tag category update Env --name Environment \\
            --description "Deployment environment"

        # Toggle exclusivity off
        vrg tag category update Environment --no-single-selection

    Only flags passed on the command line are changed — omitting a
    `--taggable-*` flag leaves its current value alone. Narrowing a
    category (e.g., removing `--taggable-vms`) does not automatically
    detach existing tags from VMs.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tag_categories, category, "Tag category")
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if single_selection is not None:
        kwargs["single_tag_selection"] = single_selection
    if taggable_vms is not None:
        kwargs["taggable_vms"] = taggable_vms
    if taggable_networks is not None:
        kwargs["taggable_networks"] = taggable_networks
    if taggable_volumes is not None:
        kwargs["taggable_volumes"] = taggable_volumes
    if taggable_nodes is not None:
        kwargs["taggable_nodes"] = taggable_nodes
    if taggable_tenants is not None:
        kwargs["taggable_tenants"] = taggable_tenants
    if taggable_users is not None:
        kwargs["taggable_users"] = taggable_users
    if taggable_clusters is not None:
        kwargs["taggable_clusters"] = taggable_clusters
    if taggable_sites is not None:
        kwargs["taggable_sites"] = taggable_sites
    if taggable_groups is not None:
        kwargs["taggable_groups"] = taggable_groups
    result = vctx.client.tag_categories.update(key, **kwargs)
    output_result(
        _category_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_CATEGORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tag category '{category}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    category: Annotated[str, typer.Argument(help="Category name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a tag category.

    Examples:

        vrg tag category delete Owner
        vrg tag category delete Owner --yes

    Destructive: cascades to every tag inside the category and to
    every membership row on those tags. Inspect
    `vrg tag list --category <name>` and `vrg tag members <tag>`
    before deleting if you need a reference of what will be removed.
    """
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.tag_categories, category, "Tag category")
    if not confirm_action(f"Delete tag category '{category}'?", yes=yes):
        raise typer.Abort()
    vctx.client.tag_categories.delete(key)
    output_success(f"Tag category '{category}' deleted.", quiet=vctx.quiet)
