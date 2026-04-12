"""Permission management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import PERMISSION_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="permission",
    help="Manage permissions.",
    no_args_is_help=True,
)


def _permission_to_dict(perm: Any) -> dict[str, Any]:
    """Convert a Permission SDK object to a dictionary for output."""
    return {
        "$key": int(perm.key),
        "identity_name": perm.identity_name,
        "table": perm.table,
        "row_key": perm.row_key,
        "row_display": perm.row_display if perm.row_key != 0 else "(all)",
        "is_table_level": perm.is_table_level,
        "can_list": perm.can_list,
        "can_read": perm.can_read,
        "can_create": perm.can_create,
        "can_modify": perm.can_modify,
        "can_delete": perm.can_delete,
        "has_full_control": perm.has_full_control,
    }


@app.command("list")
@handle_errors()
def permission_list(
    ctx: typer.Context,
    user: Annotated[
        str | None,
        typer.Option("--user", help="Filter by user (name or key)."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", help="Filter by group (name or key)."),
    ] = None,
    table: Annotated[
        str | None,
        typer.Option("--table", help="Filter by resource table (e.g. vms, vnets, /)."),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
) -> None:
    """List permissions."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.permissions.list(), _permission_to_dict, PERMISSION_COLUMNS
        )
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if table is not None:
        kwargs["table"] = table

    # Resolve user/group to keys for SDK call
    if user is not None:
        user_key = resolve_resource_id(vctx.client.users, user, "User")
        kwargs["user"] = user_key
    if group is not None:
        group_key = resolve_resource_id(vctx.client.groups, group, "Group")
        kwargs["group"] = group_key

    perms = vctx.client.permissions.list(**kwargs)

    output_result(
        [_permission_to_dict(p) for p in perms],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=PERMISSION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def permission_get(
    ctx: typer.Context,
    id: Annotated[int, typer.Argument(help="Permission key (numeric).")],
) -> None:
    """Get a permission by key."""
    vctx = get_context(ctx)

    perm = vctx.client.permissions.get(id)

    output_result(
        _permission_to_dict(perm),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("grant")
@handle_errors()
def permission_grant(
    ctx: typer.Context,
    table: Annotated[
        str,
        typer.Option("--table", "-t", help="Resource table (e.g. vms, vnets, /)."),
    ],
    user: Annotated[
        str | None,
        typer.Option("--user", help="User to grant to (name or key)."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", help="Group to grant to (name or key)."),
    ] = None,
    row: Annotated[
        int,
        typer.Option("--row", help="Specific resource key (0 = all)."),
    ] = 0,
    can_list: Annotated[
        bool,
        typer.Option("--list/--no-list", help="Grant list permission."),
    ] = False,
    can_read: Annotated[
        bool,
        typer.Option("--read/--no-read", help="Grant read permission."),
    ] = False,
    can_create: Annotated[
        bool,
        typer.Option("--create/--no-create", help="Grant create permission."),
    ] = False,
    can_modify: Annotated[
        bool,
        typer.Option("--modify/--no-modify", help="Grant modify permission."),
    ] = False,
    can_delete: Annotated[
        bool,
        typer.Option("--delete/--no-delete", help="Grant delete permission."),
    ] = False,
    full_control: Annotated[
        bool,
        typer.Option("--full-control", help="Grant all permissions."),
    ] = False,
) -> None:
    """Grant a permission to a user or group."""
    vctx = get_context(ctx)

    # Validate: must specify exactly one of user or group
    if user is None and group is None:
        typer.echo("Error: must specify --user or --group.", err=True)
        raise typer.Exit(2)
    if user is not None and group is not None:
        typer.echo("Error: specify only one of --user or --group.", err=True)
        raise typer.Exit(2)

    # If no permission flags given and not full-control, default to --list only
    if not full_control and not any([can_list, can_read, can_create, can_modify, can_delete]):
        can_list = True

    # Resolve identity
    kwargs: dict[str, Any] = {
        "table": table,
        "row_key": row,
        "can_list": can_list,
        "can_read": can_read,
        "can_create": can_create,
        "can_modify": can_modify,
        "can_delete": can_delete,
        "full_control": full_control,
    }

    if user is not None:
        user_key = resolve_resource_id(vctx.client.users, user, "User")
        kwargs["user"] = user_key
    if group is not None:
        group_key = resolve_resource_id(vctx.client.groups, group, "Group")
        kwargs["group"] = group_key

    perm = vctx.client.permissions.grant(**kwargs)

    output_success(f"Granted permission (key: {int(perm.key)})", quiet=vctx.quiet)

    output_result(
        _permission_to_dict(perm),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("revoke")
@handle_errors()
def permission_revoke(
    ctx: typer.Context,
    id: Annotated[int, typer.Argument(help="Permission key to revoke.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Revoke (delete) a permission."""
    vctx = get_context(ctx)

    if not confirm_action(f"Revoke permission {id}?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.permissions.revoke(id)
    output_success(f"Revoked permission {id}", quiet=vctx.quiet)


@app.command("revoke-all")
@handle_errors()
def permission_revoke_all(
    ctx: typer.Context,
    user: Annotated[
        str | None,
        typer.Option("--user", help="Revoke all permissions for this user (name or key)."),
    ] = None,
    group: Annotated[
        str | None,
        typer.Option("--group", help="Revoke all permissions for this group (name or key)."),
    ] = None,
    table: Annotated[
        str | None,
        typer.Option("--table", help="Only revoke permissions for this table."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Revoke all permissions for a user or group."""
    vctx = get_context(ctx)

    # Validate: must specify exactly one of user or group
    if user is None and group is None:
        typer.echo("Error: must specify --user or --group.", err=True)
        raise typer.Exit(2)
    if user is not None and group is not None:
        typer.echo("Error: specify only one of --user or --group.", err=True)
        raise typer.Exit(2)

    identity_label = user if user is not None else group
    identity_type = "user" if user is not None else "group"
    table_label = f" on table '{table}'" if table else ""

    if not confirm_action(
        f"Revoke all permissions for {identity_type} '{identity_label}'{table_label}?",
        yes=yes,
    ):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    if user is not None:
        user_key = resolve_resource_id(vctx.client.users, user, "User")
        count = vctx.client.permissions.revoke_for_user(user_key, table=table)
    else:
        assert group is not None
        group_key = resolve_resource_id(vctx.client.groups, group, "Group")
        count = vctx.client.permissions.revoke_for_group(group_key, table=table)

    output_success(
        f"Revoked {count} permission(s) for {identity_type} '{identity_label}'{table_label}",
        quiet=vctx.quiet,
    )
