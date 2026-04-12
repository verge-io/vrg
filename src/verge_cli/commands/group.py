"""Group management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import GROUP_COLUMNS, GROUP_MEMBER_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="group",
    help="Manage groups.",
    no_args_is_help=True,
)

member_app = typer.Typer(
    name="member",
    help="Manage group members.",
    no_args_is_help=True,
)

app.add_typer(member_app, name="member")


def _group_to_dict(group: Any) -> dict[str, Any]:
    """Convert a Group SDK object to a dictionary for output."""
    return {
        "$key": int(group.key),
        "name": group.name,
        "description": group.get("description", ""),
        "email": group.get("email", ""),
        "enabled": group.is_enabled,
        "member_count": group.get("member_count", 0),
        "created": group.get("created"),
    }


def _member_to_dict(member: Any) -> dict[str, Any]:
    """Convert a GroupMember SDK object to a dictionary for output."""
    return {
        "$key": int(member.key),
        "member_name": member.member_name or "",
        "member_type": member.member_type or "",
        "member_key": int(member.member_key) if member.member_key is not None else None,
    }


# ---------------------------------------------------------------------------
# Group CRUD commands
# ---------------------------------------------------------------------------


@app.command("list")
@handle_errors()
def group_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled/disabled status."),
    ] = None,
) -> None:
    """List groups."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.groups.list(), _group_to_dict, GROUP_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if enabled is not None:
        kwargs["enabled"] = enabled

    groups = vctx.client.groups.list(**kwargs)

    output_result(
        [_group_to_dict(g) for g in groups],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def group_get(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
) -> None:
    """Get details of a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    group_obj = vctx.client.groups.get(key)

    output_result(
        _group_to_dict(group_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def group_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Group name.")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Group description.")
    ] = None,
    email: Annotated[str | None, typer.Option("--email", help="Group email address.")] = None,
    disabled: Annotated[bool, typer.Option("--disabled", help="Create group as disabled.")] = False,
) -> None:
    """Create a new group."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "enabled": not disabled,
    }

    if description is not None:
        kwargs["description"] = description
    if email is not None:
        kwargs["email"] = email

    group_obj = vctx.client.groups.create(**kwargs)

    output_success(f"Created group '{group_obj.name}' (key: {group_obj.key})", quiet=vctx.quiet)

    output_result(
        _group_to_dict(group_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def group_update(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New group name.")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description.")
    ] = None,
    email: Annotated[str | None, typer.Option("--email", help="New email address.")] = None,
) -> None:
    """Update a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if email is not None:
        kwargs["email"] = email

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    group_obj = vctx.client.groups.update(key, **kwargs)

    output_success(f"Updated group '{group_obj.name}'", quiet=vctx.quiet)

    output_result(
        _group_to_dict(group_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def group_delete(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    group_obj = vctx.client.groups.get(key)

    if not confirm_action(f"Delete group '{group_obj.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.groups.delete(key)
    output_success(f"Deleted group '{group_obj.name}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def group_enable(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
) -> None:
    """Enable a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    group_obj = vctx.client.groups.enable(key)

    output_success(f"Enabled group '{group_obj.name}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def group_disable(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
) -> None:
    """Disable a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    group_obj = vctx.client.groups.disable(key)

    output_success(f"Disabled group '{group_obj.name}'", quiet=vctx.quiet)


# ---------------------------------------------------------------------------
# Group member sub-commands
# ---------------------------------------------------------------------------


@member_app.command("list")
@handle_errors()
def member_list(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
) -> None:
    """List members of a group."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    members = vctx.client.groups.members(key).list()

    output_result(
        [_member_to_dict(m) for m in members],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GROUP_MEMBER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@member_app.command("add")
@handle_errors()
def member_add(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
    user: Annotated[
        str | None,
        typer.Option("--user", help="User name or key to add."),
    ] = None,
    member_group: Annotated[
        str | None,
        typer.Option("--group", help="Group name or key to add as member."),
    ] = None,
) -> None:
    """Add a user or group to a group."""
    vctx = get_context(ctx)

    if not user and not member_group:
        typer.echo("Error: specify --user or --group.", err=True)
        raise typer.Exit(2)
    if user and member_group:
        typer.echo("Error: specify only one of --user or --group.", err=True)
        raise typer.Exit(2)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    member_mgr = vctx.client.groups.members(key)

    if user:
        user_key = resolve_resource_id(vctx.client.users, user, "User")
        member_obj = member_mgr.add_user(user_key)
        output_success(
            f"Added user '{member_obj.member_name}' to group (key: {key})",
            quiet=vctx.quiet,
        )
    else:
        assert member_group is not None
        mg_key = resolve_resource_id(vctx.client.groups, member_group, "Group")
        member_obj = member_mgr.add_group(mg_key)
        output_success(
            f"Added group '{member_obj.member_name}' to group (key: {key})",
            quiet=vctx.quiet,
        )


@member_app.command("remove")
@handle_errors()
def member_remove(
    ctx: typer.Context,
    group: Annotated[str, typer.Argument(help="Group name or key.")],
    user: Annotated[
        str | None,
        typer.Option("--user", help="User name or key to remove."),
    ] = None,
    member_group: Annotated[
        str | None,
        typer.Option("--group", help="Group name or key to remove."),
    ] = None,
) -> None:
    """Remove a user or group from a group."""
    vctx = get_context(ctx)

    if not user and not member_group:
        typer.echo("Error: specify --user or --group.", err=True)
        raise typer.Exit(2)
    if user and member_group:
        typer.echo("Error: specify only one of --user or --group.", err=True)
        raise typer.Exit(2)

    key = resolve_resource_id(vctx.client.groups, group, "Group")
    member_mgr = vctx.client.groups.members(key)

    if user:
        user_key = resolve_resource_id(vctx.client.users, user, "User")
        member_mgr.remove_user(user_key)
        output_success(f"Removed user from group (key: {key})", quiet=vctx.quiet)
    else:
        assert member_group is not None
        mg_key = resolve_resource_id(vctx.client.groups, member_group, "Group")
        member_mgr.remove_group(mg_key)
        output_success(f"Removed group from group (key: {key})", quiet=vctx.quiet)
