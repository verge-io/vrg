"""OIDC application user ACL commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import OIDC_USER_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="user",
    help=(
        "Manage the allowed-users ACL on an OIDC application.\n\n"
        "When an OIDC application has `restrict_access` enabled, only users"
        " on this whitelist (or members of an allowed group) may authenticate"
        " through it. The ACL has no effect while `restrict_access` is off.\n\n"
        "Use `-o json` for machine-readable output. `--query` on fields like"
        " `user_key`, `user_display`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List allowed users on an application\n"
        "    vrg oidc user list partner-portal\n\n"
        "    # Add a user by name or key\n"
        "    vrg oidc user add partner-portal deploy-bot\n"
        "    vrg oidc user add partner-portal 42\n\n"
        "    # Remove a user (prompts for confirmation)\n"
        "    vrg oidc user remove partner-portal deploy-bot\n\n"
        "    # Dump the ACL as JSON\n"
        "    vrg -o json oidc user list partner-portal\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "**Turn on `restrict_access` first.** Adding a user to the ACL while"
        " `restrict_access` is off has no gating effect — the whitelist is"
        " only consulted when restriction is enabled. Enable it with"
        " `vrg oidc update <app> --restrict-access`.\n\n"
        "**`remove` accepts user name, user key, or ACL entry key.** The"
        " command resolves whichever form you provide to the underlying ACL"
        " entry and deletes it.\n\n"
        "**Name resolution**: the `<oidc-app>` and `<user>` arguments accept"
        " names or numeric keys. Ambiguous names exit with code 7.\n"
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


def _resolve_oidc_app(client: Any, identifier: str) -> int:
    """Resolve OIDC application identifier (key or name) to key."""
    if identifier.isdigit():
        oidc_app = client.oidc_applications.get(key=int(identifier))
    else:
        oidc_app = client.oidc_applications.get(name=identifier)
    return int(oidc_app.key)


def _oidc_user_to_dict(entry: Any) -> dict[str, Any]:
    """Convert SDK OIDC user ACL entry to output dict."""
    return {
        "$key": int(entry.key),
        "user_key": entry.get("user"),
        "user_display": entry.get("user_display", ""),
    }


def _find_acl_entry(entries: list[Any], member_key: int, member_field: str) -> int:
    """Find ACL entry key by member key."""
    for entry in entries:
        if entry.get(member_field) == member_key:
            return int(entry.key)
    raise ResourceNotFoundError(f"No ACL entry found for {member_field} key {member_key}")


@app.command("list")
@handle_errors()
def oidc_user_list(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
) -> None:
    """List allowed users for an OIDC application.

    Examples:

        vrg oidc user list partner-portal
        vrg -o json oidc user list partner-portal
        vrg -o json oidc user list partner-portal --query "[].user_display"

    Shows only explicit user ACL entries — group membership grants are
    managed through `vrg oidc group list`. ACL has no effect until
    `restrict_access` is enabled on the application.
    """
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    users_mgr = vctx.client.oidc_applications.allowed_users(app_key)
    entries = users_mgr.list()

    output_result(
        [_oidc_user_to_dict(e) for e in entries],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_USER_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("add")
@handle_errors()
def oidc_user_add(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    user: Annotated[str, typer.Argument(help="User name or key to add.")],
) -> None:
    """Add a user to the OIDC application's allowed list.

    Examples:

        vrg oidc user add partner-portal deploy-bot
        vrg oidc user add partner-portal 17
        vrg oidc user add 7 alice

    Entries take effect only when the application has `restrict_access`
    enabled. Enable it with
    `vrg oidc update <app> --restrict-access` first. Ambiguous names
    exit 7.
    """
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    user_key = resolve_resource_id(vctx.client.users, user, "User")

    users_mgr = vctx.client.oidc_applications.allowed_users(app_key)
    users_mgr.add(user_key=user_key)

    output_success(f"Added user '{user}' to OIDC application", quiet=vctx.quiet)


@app.command("remove")
@handle_errors()
def oidc_user_remove(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    user_or_key: Annotated[str, typer.Argument(help="User name/key or ACL entry key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Remove a user from the OIDC application's allowed list.

    Examples:

        vrg oidc user remove partner-portal deploy-bot
        vrg oidc user remove partner-portal 17 -y
        vrg oidc user remove 7 alice -y

    Accepts user name, user key, or ACL entry key — all three resolve
    to the same underlying entry. Ambiguous names exit 7.
    """
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    users_mgr = vctx.client.oidc_applications.allowed_users(app_key)

    # Resolve entry key: try as user first, then as direct entry key
    if user_or_key.isdigit():
        # Could be user key or ACL entry key — try user key first
        user_key = int(user_or_key)
        entries = users_mgr.list()
        matching = [e for e in entries if e.get("user") == user_key]
        if matching:
            entry_key = int(matching[0].key)
        else:
            # Treat as direct ACL entry key
            entry_key = user_key
    else:
        # Resolve user name
        user_key = resolve_resource_id(vctx.client.users, user_or_key, "User")
        entries = users_mgr.list()
        entry_key = _find_acl_entry(entries, user_key, "user")

    if not confirm_action(f"Remove user '{user_or_key}' from OIDC application?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    users_mgr.delete(entry_key)
    output_success(f"Removed user '{user_or_key}' from OIDC application", quiet=vctx.quiet)
