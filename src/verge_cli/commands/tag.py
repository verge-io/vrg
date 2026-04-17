"""Tag management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.commands import tag_category
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="tag",
    help=(
        "Manage tags and tag categories on VergeOS.\n\n"
        "**Tags** are metadata labels attached to platform objects (VMs,"
        " networks, tenants, nodes, users, volumes, etc.) for classification,"
        " search, and filtering. Every tag belongs to a **category** that"
        " controls which object types the tag is allowed to be applied to"
        " (e.g., a category with `taggable_vms=true` may tag VMs). A category"
        " with `single_tag_selection=true` enforces mutual exclusivity —"
        " only one tag from that category may be attached to a given object"
        " at a time.\n\n"
        "This group manages tag **definitions** (categories, tags) and"
        " membership assignments. Use `vrg tag category` for category"
        " management. Tag attachment is also exposed on individual resource"
        " commands (e.g., `vrg vm tag <vm> <tag>`).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every tag and its category\n"
        "    vrg tag list\n\n"
        "    # Machine-readable output for agents\n"
        "    vrg -o json tag list\n\n"
        "    # Narrow to one category\n"
        "    vrg tag list --category Environment\n\n"
        "    # Inspect a single tag (name or numeric $key)\n"
        "    vrg tag get production\n"
        "    vrg tag get production --category Environment\n\n"
        "    # Create a tag inside an existing category\n"
        "    vrg tag create --name production --category Environment \\\n"
        "        --description 'Production workloads'\n\n"
        "    # Attach / detach a tag on any taggable resource\n"
        "    vrg tag assign production vm web-01\n"
        "    vrg tag unassign production vm web-01\n\n"
        "    # List every object currently carrying a tag\n"
        "    vrg tag members production\n"
        "    vrg tag members production --type vm\n\n"
        "    # Manage categories\n"
        "    vrg tag category list\n"
        "    vrg tag category create --name Owner --taggable-vms\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Tags and categories are referenced by **name** or **numeric key**"
        " (`$key`). Tag names are unique only within a category — pass"
        " `--category` on `get` when the same tag name is reused across"
        " categories. Ambiguous name resolution exits with code 7.\n\n"
        "Valid resource types for `assign` / `unassign` / `members --type`:"
        " `vm`, `network`, `node`, `tenant`, `user`, `cluster`, `site`,"
        " `group`, `volume`. The target category must have the corresponding"
        " `taggable_*` flag enabled or the assignment will be rejected.\n\n"
        "Deleting a tag cascades to its membership rows (objects stop"
        " carrying the tag). Deleting a category cascades to its tags and"
        " their members. There is no soft-delete — run `vrg tag members"
        " <tag>` first if you need a reference of what will be affected."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Register tag category as a sub-command
app.add_typer(tag_category.app, name="category")

TAG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("category_name", header="Category"),
    ColumnDef("description", wide_only=True),
    ColumnDef("created", format_fn=format_epoch, wide_only=True),
]

TAG_MEMBER_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("resource_type", header="Type"),
    ColumnDef("resource_key", header="Resource Key"),
    ColumnDef("resource_name", header="Resource Name"),
]

# Map user-friendly resource type names to SDK values
RESOURCE_TYPE_MAP: dict[str, str] = {
    "vm": "vms",
    "network": "vnets",
    "node": "nodes",
    "tenant": "tenants",
    "user": "users",
    "cluster": "clusters",
    "site": "sites",
    "group": "groups",
    "volume": "volumes",
}

# Reverse map for display
_SDK_TO_DISPLAY: dict[str, str] = {v: k for k, v in RESOURCE_TYPE_MAP.items()}


def _tag_to_dict(tag: Any) -> dict[str, Any]:
    """Convert a Tag SDK object to a dict for output."""
    return {
        "$key": int(tag.key),
        "name": tag.name,
        "category_name": tag.category_name or "",
        "description": tag.description or "",
        "created": tag.created,
    }


def _member_to_dict(member: Any) -> dict[str, Any]:
    """Convert a TagMember SDK object to a dict for output."""
    resource_type = member.resource_type or ""
    display_type = _SDK_TO_DISPLAY.get(resource_type, resource_type)
    return {
        "$key": int(member.key),
        "resource_type": display_type,
        "resource_key": member.resource_key or "",
        "resource_name": getattr(member, "resource_name", "") or "",
    }


def _resolve_tag(vctx: Any, identifier: str) -> int:
    """Resolve a tag identifier to a key.

    If the identifier is numeric, return it directly.
    Otherwise, use resolve_resource_id on client.tags.
    """
    return resolve_resource_id(vctx.client.tags, identifier, "Tag")


def _resolve_target_resource(
    vctx: Any, resource_type_cli: str, resource_id: str
) -> tuple[str, int]:
    """Resolve a target resource type and ID for assign/unassign.

    Returns:
        Tuple of (sdk_resource_type, resource_key).
    """
    sdk_type = RESOURCE_TYPE_MAP.get(resource_type_cli.lower())
    if sdk_type is None:
        valid_types = ", ".join(sorted(RESOURCE_TYPE_MAP.keys()))
        raise typer.BadParameter(
            f"Invalid resource type '{resource_type_cli}'. Valid types: {valid_types}"
        )

    # Resolve the resource ID to a key
    # Get the appropriate manager for the resource type
    manager_map: dict[str, str] = {
        "vms": "vms",
        "vnets": "networks",
        "nodes": "nodes",
        "tenants": "tenants",
        "users": "users",
        "clusters": "clusters",
        "sites": "sites",
        "groups": "groups",
        "volumes": "volumes",
    }
    manager_attr = manager_map.get(sdk_type, sdk_type)
    manager = getattr(vctx.client, manager_attr, None)
    if manager is None:
        # If we can't resolve, try treating as numeric
        if resource_id.isdigit():
            return sdk_type, int(resource_id)
        raise typer.BadParameter(
            f"Cannot resolve '{resource_type_cli}' resources. Please use a numeric key."
        )
    resource_key = resolve_resource_id(manager, resource_id, resource_type_cli)
    return sdk_type, resource_key


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter_expr: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option("--category", help="Filter by category name or key."),
    ] = None,
) -> None:
    """List tags.

    Examples:

        vrg tag list
        vrg tag list --category Environment
        vrg -o json tag list --query "[?category_name=='Environment'].name"

    Useful `--query` fields: `name`, `category_name`, `description`.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.tags.list(), _tag_to_dict, TAG_COLUMNS)
        return
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if filter_expr is not None:
        kwargs["filter"] = filter_expr
    if category is not None:
        # Try numeric first
        if category.isdigit():
            kwargs["category_key"] = int(category)
        else:
            kwargs["category_name"] = category
    tags = vctx.client.tags.list(**kwargs)
    output_result(
        [_tag_to_dict(t) for t in tags],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    category: Annotated[
        str | None,
        typer.Option("--category", help="Category name or key (for name lookup)."),
    ] = None,
) -> None:
    """Get a tag by name or key.

    Examples:

        vrg tag get production
        vrg tag get production --category Environment
        vrg -o json tag get 42

    Tag names are unique only within a category. Pass `--category` when
    the same tag name is reused across categories — otherwise ambiguous
    matches exit with code 7.
    """
    vctx = get_context(ctx)
    if tag.isdigit():
        item = vctx.client.tags.get(int(tag))
    else:
        # Name lookup — optionally scoped to category
        get_kwargs: dict[str, Any] = {"name": tag}
        if category is not None:
            if category.isdigit():
                get_kwargs["category_key"] = int(category)
            else:
                get_kwargs["category_name"] = category
        item = vctx.client.tags.get(**get_kwargs)
    output_result(
        _tag_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Tag name.")],
    category: Annotated[
        str,
        typer.Option("--category", "-c", help="Category name or key."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Tag description."),
    ] = None,
) -> None:
    """Create a new tag.

    Examples:

        vrg tag create --name production --category Environment
        vrg tag create -n staging -c Environment \\
            -d "Pre-production workloads"

    The category must already exist (`vrg tag category create`) and
    have the relevant `taggable_*` flag set for whatever resource type
    you intend to tag.
    """
    vctx = get_context(ctx)
    cat_key = resolve_resource_id(vctx.client.tag_categories, category, "Tag category")
    kwargs: dict[str, Any] = {"name": name, "category_key": cat_key}
    if description is not None:
        kwargs["description"] = description
    result = vctx.client.tags.create(**kwargs)
    output_result(
        _tag_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tag '{name}' created.", quiet=vctx.quiet)


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New tag name."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description."),
    ] = None,
) -> None:
    """Update a tag.

    Examples:

        vrg tag update production --description "Production workloads only"
        vrg tag update staging --name pre-prod

    Only `--name` and `--description` are editable here. To move a tag
    between categories, delete and recreate it.
    """
    vctx = get_context(ctx)
    key = _resolve_tag(vctx, tag)
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    result = vctx.client.tags.update(key, **kwargs)
    output_result(
        _tag_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Tag '{tag}' updated.", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a tag.

    Examples:

        vrg tag delete production
        vrg tag delete production --yes

    Destructive: cascades to every membership row — objects currently
    carrying this tag will stop carrying it. Run `vrg tag members
    <tag>` first to see what will be affected.
    """
    vctx = get_context(ctx)
    key = _resolve_tag(vctx, tag)
    if not confirm_action(f"Delete tag '{tag}'?", yes=yes):
        raise typer.Abort()
    vctx.client.tags.delete(key)
    output_success(f"Tag '{tag}' deleted.", quiet=vctx.quiet)


@app.command("assign")
@handle_errors()
def assign_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (vm, network, node, tenant, user, cluster, site, group, volume)."
        ),
    ],
    resource_id: Annotated[str, typer.Argument(help="Resource name or key.")],
) -> None:
    """Assign a tag to a resource.

    Examples:

        vrg tag assign production vm web-01
        vrg tag assign tier-2 network internal-net
        vrg tag assign owned-by-platform tenant acme

    Valid resource types: `vm`, `network`, `node`, `tenant`, `user`,
    `cluster`, `site`, `group`, `volume`. The tag's category must have
    the corresponding `taggable_*` flag enabled or the assignment is
    rejected. If the category is `single_tag_selection`, an existing
    tag from that category on the same object is replaced.
    """
    vctx = get_context(ctx)
    tag_key = _resolve_tag(vctx, tag)
    sdk_type, res_key = _resolve_target_resource(vctx, resource_type, resource_id)
    members_mgr = vctx.client.tags.members(tag_key)
    members_mgr.add(sdk_type, res_key)
    output_success(f"Tag '{tag}' assigned to {resource_type} '{resource_id}'.")


@app.command("unassign")
@handle_errors()
def unassign_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    resource_type: Annotated[
        str,
        typer.Argument(
            help="Resource type (vm, network, node, tenant, user, cluster, site, group, volume)."
        ),
    ],
    resource_id: Annotated[str, typer.Argument(help="Resource name or key.")],
) -> None:
    """Unassign a tag from a resource.

    Examples:

        vrg tag unassign production vm web-01
        vrg tag unassign tier-2 network internal-net

    Idempotent per call — removing a tag that isn't currently attached
    still exits 0. Valid resource types match `assign`.
    """
    vctx = get_context(ctx)
    tag_key = _resolve_tag(vctx, tag)
    sdk_type, res_key = _resolve_target_resource(vctx, resource_type, resource_id)
    members_mgr = vctx.client.tags.members(tag_key)
    members_mgr.remove_resource(sdk_type, res_key)
    output_success(f"Tag '{tag}' unassigned from {resource_type} '{resource_id}'.")


@app.command("members")
@handle_errors()
def members_cmd(
    ctx: typer.Context,
    tag: Annotated[str, typer.Argument(help="Tag name or key.")],
    resource_type: Annotated[
        str | None,
        typer.Option("--type", help="Filter by resource type."),
    ] = None,
) -> None:
    """List resources tagged with a tag.

    Examples:

        vrg tag members production
        vrg tag members production --type vm
        vrg -o json tag members production --query "[].resource_name"

    Useful `--query` fields: `resource_type`, `resource_key`,
    `resource_name`. Filter with `--type` to narrow to a single object
    type.
    """
    vctx = get_context(ctx)
    tag_key = _resolve_tag(vctx, tag)
    members_mgr = vctx.client.tags.members(tag_key)
    kwargs: dict[str, Any] = {}
    if resource_type is not None:
        # Convert CLI type name to SDK type name
        sdk_type = RESOURCE_TYPE_MAP.get(resource_type.lower())
        if sdk_type is None:
            valid_types = ", ".join(sorted(RESOURCE_TYPE_MAP.keys()))
            raise typer.BadParameter(
                f"Invalid resource type '{resource_type}'. Valid types: {valid_types}"
            )
        kwargs["resource_type"] = sdk_type
    members = members_mgr.list(**kwargs)
    output_result(
        [_member_to_dict(m) for m in members],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=TAG_MEMBER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
