"""NAS local user management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="user",
    help=(
        "Manage local CIFS/SMB users on a NAS service — the user database"
        " Samba consults when a Windows, macOS, or Linux client authenticates"
        " to a CIFS share.\n\n"
        "NAS local users are per-service: each NAS service VM has its own"
        " independent user list and is selected with `--service`. These users"
        " are the identities referenced by the `valid_users`, `admin_users`,"
        " and `force_user` fields on CIFS shares (`vrg nas cifs`). NFS"
        " shares ignore this list — NFS authenticates by client UID/GID, not"
        " username. Use AD domain accounts instead of local users when the"
        " NAS is joined to Active Directory; see `nas-join-ad-domain` in the"
        " product guide.\n\n"
        "`--home-share` / `--home-drive` bind the user to a CIFS home"
        " directory. The home share must already exist on the service"
        " (create with `vrg nas cifs create`); once attached, it cannot be"
        " deleted until every referencing user is removed or repointed."
        " `--home-drive` is the Windows drive letter (e.g., `H`) mounted on"
        " login.\n\n"
        "Users resolve by name or hex `$key` within the scope of their NAS"
        " service. Ambiguous names exit with code 7 — disambiguate with the"
        " key. Use `-o json` with `--query` to pluck fields like `enabled`,"
        " `status`, `home_share_name`, or `service_name` for scripting.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List all NAS local users across services\n"
        "    vrg nas user list\n\n"
        "    # Scope to one service, or filter by enabled state\n"
        "    vrg nas user list --service my-nas\n"
        "    vrg nas user list --service my-nas --disabled\n\n"
        "    # Inspect one user as JSON for agents / scripting\n"
        "    vrg -o json nas user get jdoe\n\n"
        "    # Create a basic CIFS user\n"
        "    vrg nas user create --service my-nas \\\n"
        "        --name jdoe --password 's3cret!' \\\n"
        "        --displayname 'Jane Doe' --description 'Finance team'\n\n"
        "    # Create a user with a mapped home drive\n"
        "    vrg nas user create --service my-nas \\\n"
        "        --name jdoe --password 's3cret!' \\\n"
        "        --home-share home-jdoe --home-drive H\n\n"
        "    # Rotate a password / update attributes\n"
        "    vrg nas user update jdoe --password 'n3w-s3cret!'\n"
        "    vrg nas user update jdoe --displayname 'Jane D. Smith'\n\n"
        "    # Toggle access without destroying the account\n"
        "    vrg nas user disable jdoe\n"
        "    vrg nas user enable  jdoe\n\n"
        "    # Remove a user (confirms unless --yes)\n"
        "    vrg nas user delete jdoe --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The parent NAS service VM **must be running** for user management"
        " to take effect; changes made while the service is stopped apply on"
        " next start. Users authenticate only against CIFS/SMB shares — NFS"
        " clients are controlled via `allowed_hosts` and squash settings on"
        " the NFS share instead.\n\n"
        "Passwords are set server-side; the CLI has no password-reveal or"
        " hash-import operation. Pipe secrets from a vault rather than"
        " embedding them in shell history where possible.\n\n"
        "Deleting a user referenced by a CIFS home share is blocked until"
        " the share's `home_shares` link is cleared or the share itself is"
        " removed."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

NAS_USER_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("displayname", header="Display Name"),
    ColumnDef(
        "enabled",
        format_fn=format_bool_yn,
        style_map={"Yes": "green", "No": "red"},
    ),
    ColumnDef("service_name", header="Service"),
    ColumnDef(
        "status",
        style_map={"online": "green", "offline": "red", "error": "yellow"},
    ),
    ColumnDef("home_share_name", header="Home Share", wide_only=True),
    ColumnDef("home_drive", header="Drive", wide_only=True),
    ColumnDef("description", wide_only=True),
]


def _user_to_dict(user: Any) -> dict[str, Any]:
    """Convert a NAS user SDK object to a dict for output."""
    return {
        "$key": user.key,
        "name": user.name,
        "displayname": user.get("displayname", ""),
        "enabled": user.get("enabled"),
        "service_name": user.get("service_name"),
        "status": user.get("status"),
        "home_share_name": user.get("home_share_name"),
        "home_drive": user.get("home_drive"),
        "description": user.get("description", ""),
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    service: Annotated[
        str | None,
        typer.Option("--service", help="Filter by NAS service name or key"),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Filter by enabled state"),
    ] = None,
) -> None:
    """List all NAS local users.

    **Examples:**

        vrg nas user list
        vrg nas user list --service my-nas
        vrg nas user list --enabled
        vrg -o json nas user list
    """
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if service is not None:
        svc_key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")
        kwargs["service"] = svc_key
    if enabled is not None:
        kwargs["enabled"] = enabled

    users = vctx.client.nas_users.list(**kwargs)
    data = [_user_to_dict(u) for u in users]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=NAS_USER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="NAS user name or hex key")],
) -> None:
    """Get details of a NAS local user.

    **Examples:**

        vrg nas user get alice
        vrg -o json nas user get alice
    """
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_users, user, "NAS user")
    item = vctx.client.nas_users.get(key=key)
    output_result(
        _user_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    service: Annotated[
        str,
        typer.Option("--service", help="NAS service name or key"),
    ],
    name: Annotated[str, typer.Option("--name", "-n", help="Username")],
    password: Annotated[str, typer.Option("--password", help="User password")],
    displayname: Annotated[
        str | None,
        typer.Option("--displayname", help="Display name"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="User description"),
    ] = None,
    home_share: Annotated[
        str | None,
        typer.Option("--home-share", help="Home share name or key"),
    ] = None,
    home_drive: Annotated[
        str | None,
        typer.Option("--home-drive", help="Home drive letter (e.g., H)"),
    ] = None,
) -> None:
    """Create a new NAS local user.

    NAS local users authenticate against CIFS shares on this NAS
    service. They are distinct from VergeOS platform users and from
    AD/LDAP principals. Pass the password on the CLI only from trusted
    environments.

    **Examples:**

        vrg nas user create --service my-nas --name alice --password '***'
        vrg nas user create --service my-nas --name bob --password '***' \\
            --displayname "Bob Smith" --home-share home-bob --home-drive H
    """
    vctx = get_context(ctx)

    # Resolve service name to key
    svc_key = resolve_resource_id(vctx.client.nas_services, service, "NAS service")

    create_kwargs: dict[str, Any] = {
        "service": svc_key,
        "name": name,
        "password": password,
    }
    if displayname is not None:
        create_kwargs["displayname"] = displayname
    if description is not None:
        create_kwargs["description"] = description
    if home_share is not None:
        create_kwargs["home_share"] = home_share
    if home_drive is not None:
        create_kwargs["home_drive"] = home_drive

    result = vctx.client.nas_users.create(**create_kwargs)
    user_name = result.name if result else name
    user_key = result.key if result else "?"
    output_success(
        f"Created NAS user '{user_name}' (key: {user_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="NAS user name or hex key")],
    password: Annotated[
        str | None,
        typer.Option("--password", help="New password"),
    ] = None,
    displayname: Annotated[
        str | None,
        typer.Option("--displayname", help="Display name"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="User description"),
    ] = None,
    home_share: Annotated[
        str | None,
        typer.Option("--home-share", help="Home share name or key"),
    ] = None,
    home_drive: Annotated[
        str | None,
        typer.Option("--home-drive", help="Home drive letter (e.g., H)"),
    ] = None,
) -> None:
    """Update a NAS local user.

    Use `--password` to reset credentials. Other options update profile
    metadata without re-prompting for the password.

    **Examples:**

        vrg nas user update alice --password '***'
        vrg nas user update alice --displayname "Alice Jones"
        vrg nas user update alice --home-share home-alice --home-drive H
    """
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_users, user, "NAS user")

    kwargs: dict[str, Any] = {}
    if password is not None:
        kwargs["password"] = password
    if displayname is not None:
        kwargs["displayname"] = displayname
    if description is not None:
        kwargs["description"] = description
    if home_share is not None:
        kwargs["home_share"] = home_share
    if home_drive is not None:
        kwargs["home_drive"] = home_drive

    vctx.client.nas_users.update(key, **kwargs)
    output_success(f"Updated NAS user '{user}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="NAS user name or hex key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a NAS local user.

    Revokes the user's CIFS credentials. Files owned by the user on
    volumes are not deleted.

    **Examples:**

        vrg nas user delete alice
        vrg nas user delete alice --yes
    """
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_users, user, "NAS user")

    if not confirm_action(f"Delete NAS user '{user}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.nas_users.delete(key)
    output_success(f"Deleted NAS user '{user}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="NAS user name or hex key")],
) -> None:
    """Enable a NAS local user.

    **Examples:**

        vrg nas user enable alice
    """
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_users, user, "NAS user")
    vctx.client.nas_users.enable(key)
    output_success(f"Enabled NAS user '{user}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    user: Annotated[str, typer.Argument(help="NAS user name or hex key")],
) -> None:
    """Disable a NAS local user.

    Blocks the user from authenticating without deleting the account.

    **Examples:**

        vrg nas user disable alice
    """
    vctx = get_context(ctx)
    key = resolve_nas_resource(vctx.client.nas_users, user, "NAS user")
    vctx.client.nas_users.disable(key)
    output_success(f"Disabled NAS user '{user}'", quiet=vctx.quiet)
