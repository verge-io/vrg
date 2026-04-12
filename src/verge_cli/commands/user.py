"""User management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import USER_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="user",
    help="Manage users.",
    no_args_is_help=True,
)


def _user_to_dict(user: Any) -> dict[str, Any]:
    """Convert a User SDK object to a dictionary for output."""
    return {
        "$key": int(user.key),
        "name": user.name,
        "displayname": user.get("displayname", ""),
        "email": user.get("email", ""),
        "user_type": str(user.user_type_display),
        "enabled": user.is_enabled,
        "last_login": user.get("last_login"),
        "two_factor_enabled": bool(user.two_factor_enabled),
        "is_locked": bool(user.is_locked),
        "auth_source_name": user.auth_source_name or "",
        "created": user.get("created"),
        "ssh_keys": user.get("ssh_keys", ""),
    }


@app.command("list")
@handle_errors()
def user_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled/disabled status."),
    ] = None,
    user_type: Annotated[
        str | None,
        typer.Option("--type", help="Filter by user type (normal, api, vdi)."),
    ] = None,
) -> None:
    """List users."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.users.list(), _user_to_dict, USER_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if enabled is not None:
        kwargs["enabled"] = enabled
    if user_type is not None:
        kwargs["user_type"] = user_type

    users = vctx.client.users.list(**kwargs)

    output_result(
        [_user_to_dict(u) for u in users],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=USER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def user_get(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User name or key.")],
) -> None:
    """Get details of a user."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.users, user, "User")
    user_obj = vctx.client.users.get(key)

    output_result(
        _user_to_dict(user_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def user_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Username.")],
    password: Annotated[str, typer.Option("--password", help="User password.")],
    displayname: Annotated[str | None, typer.Option("--displayname", help="Display name.")] = None,
    email: Annotated[str | None, typer.Option("--email", help="Email address.")] = None,
    user_type: Annotated[
        str, typer.Option("--type", help="User type (normal, api, vdi).")
    ] = "normal",
    disabled: Annotated[bool, typer.Option("--disabled", help="Create user as disabled.")] = False,
    change_password: Annotated[
        bool, typer.Option("--change-password", help="Require password change on next login.")
    ] = False,
    physical_access: Annotated[
        bool, typer.Option("--physical-access", help="Enable console/SSH access (admin).")
    ] = False,
    two_factor: Annotated[
        bool, typer.Option("--two-factor", help="Enable two-factor authentication.")
    ] = False,
    two_factor_type: Annotated[
        str, typer.Option("--two-factor-type", help="2FA type (email, authenticator).")
    ] = "email",
    ssh_keys: Annotated[
        str | None, typer.Option("--ssh-keys", help="SSH public keys (newline or comma separated).")
    ] = None,
) -> None:
    """Create a new user."""
    vctx = get_context(ctx)

    # Validate 2FA requirements
    if two_factor and not email:
        typer.echo("Error: --email is required when enabling --two-factor.", err=True)
        raise typer.Exit(8)

    kwargs: dict[str, Any] = {
        "name": name,
        "password": password,
        "user_type": user_type,
        "enabled": not disabled,
        "change_password": change_password,
        "physical_access": physical_access,
        "two_factor_enabled": two_factor,
        "two_factor_type": two_factor_type,
    }

    if displayname is not None:
        kwargs["displayname"] = displayname
    if email is not None:
        kwargs["email"] = email
    if ssh_keys is not None:
        kwargs["ssh_keys"] = ssh_keys

    user_obj = vctx.client.users.create(**kwargs)

    output_success(f"Created user '{user_obj.name}' (key: {user_obj.key})", quiet=vctx.quiet)

    output_result(
        _user_to_dict(user_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def user_update(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User name or key.")],
    displayname: Annotated[
        str | None, typer.Option("--displayname", help="New display name.")
    ] = None,
    email: Annotated[str | None, typer.Option("--email", help="New email address.")] = None,
    password: Annotated[str | None, typer.Option("--password", help="New password.")] = None,
    change_password: Annotated[
        bool | None,
        typer.Option("--change-password/--no-change-password", help="Require password change."),
    ] = None,
    physical_access: Annotated[
        bool | None,
        typer.Option("--physical-access/--no-physical-access", help="Console/SSH access."),
    ] = None,
    two_factor: Annotated[
        bool | None,
        typer.Option("--two-factor/--no-two-factor", help="Two-factor authentication."),
    ] = None,
    two_factor_type: Annotated[
        str | None, typer.Option("--two-factor-type", help="2FA type (email, authenticator).")
    ] = None,
    ssh_keys: Annotated[str | None, typer.Option("--ssh-keys", help="SSH public keys.")] = None,
) -> None:
    """Update a user."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.users, user, "User")

    kwargs: dict[str, Any] = {}
    if displayname is not None:
        kwargs["displayname"] = displayname
    if email is not None:
        kwargs["email"] = email
    if password is not None:
        kwargs["password"] = password
    if change_password is not None:
        kwargs["change_password"] = change_password
    if physical_access is not None:
        kwargs["physical_access"] = physical_access
    if two_factor is not None:
        kwargs["two_factor_enabled"] = two_factor
    if two_factor_type is not None:
        kwargs["two_factor_type"] = two_factor_type
    if ssh_keys is not None:
        kwargs["ssh_keys"] = ssh_keys

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    user_obj = vctx.client.users.update(key, **kwargs)

    output_success(f"Updated user '{user_obj.name}'", quiet=vctx.quiet)

    output_result(
        _user_to_dict(user_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def user_delete(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User name or key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete a user."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.users, user, "User")
    user_obj = vctx.client.users.get(key)

    if not confirm_action(f"Delete user '{user_obj.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.users.delete(key)
    output_success(f"Deleted user '{user_obj.name}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def user_enable(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User name or key.")],
) -> None:
    """Enable a user account."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.users, user, "User")
    user_obj = vctx.client.users.enable(key)

    output_success(f"Enabled user '{user_obj.name}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def user_disable(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="User name or key.")],
) -> None:
    """Disable a user account."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.users, user, "User")
    user_obj = vctx.client.users.disable(key)

    output_success(f"Disabled user '{user_obj.name}'", quiet=vctx.quiet)
