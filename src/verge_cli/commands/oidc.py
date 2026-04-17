"""OIDC application management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import OIDC_APP_COLUMNS
from verge_cli.commands import oidc_group, oidc_log, oidc_user
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success, output_warning
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="oidc",
    help=(
        "Manage OIDC applications that let VergeOS act AS an OpenID Connect"
        " identity provider for external applications.\n\n"
        "An OIDC application registers a third-party client (another VergeOS"
        " system, a web app, a portal) so it can delegate login to this"
        " VergeOS system. The external app redirects users to VergeOS, which"
        " authenticates them against the local user directory (or a chained"
        " upstream auth source) and returns an ID token. This is how MSPs"
        " centralize login across tenants and how VergeOS clusters federate"
        " SSO.\n\n"
        "This is the opposite direction of `vrg auth-source`: oidc = VergeOS"
        " → external application; auth-source = external IdP → VergeOS."
        " Don't confuse them.\n\n"
        "Use `-o json` for machine-readable output. `--query` on fields like"
        " `name`, `client_id`, `enabled`, `restrict_access`. `client_secret`"
        " is hidden by default — pass `--show-secret` on `get` to reveal it."
        " `well_known_configuration` is the `.well-known/openid-configuration`"
        " discovery URL external clients auto-configure from; show it with"
        " `--show-well-known`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List OIDC applications\n"
        "    vrg oidc list\n\n"
        "    # Show only enabled applications as JSON\n"
        "    vrg -o json oidc list --enabled\n\n"
        "    # Register a new application (client_id/secret auto-generated)\n"
        "    vrg oidc create --name partner-portal \\\n"
        "        --redirect-uri https://portal.example.com/callback\n\n"
        "    # Inspect an application including its client_secret\n"
        "    vrg -o json oidc get partner-portal --show-secret\n\n"
        "    # Restrict access to specific users/groups and manage the ACL\n"
        "    vrg oidc update partner-portal --restrict-access\n"
        "    vrg oidc user add partner-portal deploy-bot\n"
        "    vrg oidc group add partner-portal platform-eng\n\n"
        "    # Review audit logs for an application\n"
        "    vrg oidc log list partner-portal --errors\n\n"
        "    # Disable without deleting\n"
        "    vrg oidc disable partner-portal\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "**client_id and client_secret are locked after creation.** Both are"
        " auto-generated. `client_id` never changes. To rotate the secret you"
        " must delete and recreate the application — there is no rotation"
        " command.\n\n"
        "**Redirect URIs support wildcards.** Pass comma-separated values to"
        " `--redirect-uri`; wildcards like `https://*.example.com/callback`"
        " are allowed. The server stores them newline-delimited internally.\n\n"
        "**`--restrict-access` gates the ACL subcommands.** When enabled,"
        " only users/groups added via `vrg oidc user add` and `vrg oidc"
        " group add` may authenticate. When disabled, any enabled VergeOS"
        " user can authenticate through the application.\n\n"
        "**`--force-auth-source` skips the IdP picker.** Users sent to this"
        " application are redirected straight to the specified auth source"
        " instead of seeing the VergeOS login page's provider selector.\n\n"
        "**`--map-user` collapses all logins to one identity.** Every"
        " successful authentication is mapped to the specified user account."
        " Useful for service integrations that need a fixed VergeOS identity"
        " regardless of who logged in. A user referenced as `map_user`"
        " cannot be deleted until the reference is cleared.\n\n"
        "**Name resolution**: commands that take `<oidc-app>` accept the"
        " application name or numeric key. Ambiguous names exit with code"
        " 7.\n"
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

app.add_typer(oidc_user.app, name="user")
app.add_typer(oidc_group.app, name="group")
app.add_typer(oidc_log.app, name="log")


def _resolve_oidc_app(client: Any, identifier: str) -> int:
    """Resolve OIDC application identifier (key or name) to key."""
    if identifier.isdigit():
        oidc_app = client.oidc_applications.get(key=int(identifier))
    else:
        oidc_app = client.oidc_applications.get(name=identifier)
    return int(oidc_app.key)


def _oidc_app_to_dict(
    oidc_app: Any,
    include_secret: bool = False,
    include_well_known: bool = False,
) -> dict[str, Any]:
    """Convert SDK OidcApplication object to output dict."""
    result: dict[str, Any] = {
        "$key": int(oidc_app.key),
        "name": oidc_app.name,
        "description": oidc_app.get("description", ""),
        "client_id": oidc_app.get("client_id", ""),
        "enabled": oidc_app.is_enabled,
        "restrict_access": oidc_app.is_access_restricted,
        "redirect_uris": oidc_app.redirect_uris,
        "redirect_uris_display": (
            ", ".join(oidc_app.redirect_uris) if oidc_app.redirect_uris else ""
        ),
        "scopes": ", ".join(oidc_app.scopes),
        "scope_profile": oidc_app.get("scope_profile", True),
        "scope_email": oidc_app.get("scope_email", True),
        "scope_groups": oidc_app.get("scope_groups", True),
        "force_auth_source": oidc_app.force_auth_source_key,
        "force_auth_source_display": oidc_app.get("force_auth_source", ""),
        "map_user": oidc_app.map_user_key,
        "created": oidc_app.get("created"),
    }
    if include_secret:
        result["client_secret"] = oidc_app.get("client_secret", "")
    if include_well_known:
        wk = oidc_app.get("well_known_configuration", "")
        if wk:
            result["well_known_configuration"] = wk
    return result


@app.command("list")
@handle_errors()
def oidc_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    enabled: Annotated[
        bool,
        typer.Option("--enabled", help="Show only enabled applications."),
    ] = False,
    disabled: Annotated[
        bool,
        typer.Option("--disabled", help="Show only disabled applications."),
    ] = False,
) -> None:
    """List OIDC applications."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.oidc_applications.list(), _oidc_app_to_dict, OIDC_APP_COLUMNS
        )
        return
    vctx = get_context(ctx)

    if enabled and disabled:
        typer.echo("Error: --enabled and --disabled are mutually exclusive.", err=True)
        raise typer.Exit(2)

    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if enabled:
        kwargs["enabled"] = True
    elif disabled:
        kwargs["enabled"] = False

    apps = vctx.client.oidc_applications.list(**kwargs)

    output_result(
        [_oidc_app_to_dict(a) for a in apps],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_APP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def oidc_get(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    show_secret: Annotated[
        bool,
        typer.Option("--show-secret", help="Include client_secret in output."),
    ] = False,
    show_well_known: Annotated[
        bool,
        typer.Option("--show-well-known", help="Include well-known configuration URL."),
    ] = False,
) -> None:
    """Get OIDC application details."""
    vctx = get_context(ctx)

    if oidc_app.isdigit():
        app_obj = vctx.client.oidc_applications.get(
            key=int(oidc_app),
            include_secret=show_secret,
            include_well_known=show_well_known,
        )
    else:
        app_obj = vctx.client.oidc_applications.get(
            name=oidc_app,
            include_secret=show_secret,
            include_well_known=show_well_known,
        )

    output_result(
        _oidc_app_to_dict(
            app_obj,
            include_secret=show_secret,
            include_well_known=show_well_known,
        ),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_APP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def oidc_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Application name.")],
    redirect_uri: Annotated[
        str | None,
        typer.Option("--redirect-uri", help="Comma-separated redirect URIs."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Application description."),
    ] = None,
    disabled: Annotated[
        bool,
        typer.Option("--disabled", help="Create in disabled state."),
    ] = False,
    restrict_access: Annotated[
        bool,
        typer.Option("--restrict-access", help="Restrict to allowed users/groups."),
    ] = False,
    force_auth_source: Annotated[
        str | None,
        typer.Option("--force-auth-source", help="Auth source name or key for auto-redirect."),
    ] = None,
    map_user: Annotated[
        str | None,
        typer.Option("--map-user", help="User name or key to map all logins to."),
    ] = None,
    scope_profile: Annotated[
        bool | None,
        typer.Option("--scope-profile/--no-scope-profile", help="Grant profile scope."),
    ] = None,
    scope_email: Annotated[
        bool | None,
        typer.Option("--scope-email/--no-scope-email", help="Grant email scope."),
    ] = None,
    scope_groups: Annotated[
        bool | None,
        typer.Option("--scope-groups/--no-scope-groups", help="Grant groups scope."),
    ] = None,
) -> None:
    """Create a new OIDC application.

    The client_secret is generated automatically and shown once at creation time.
    Unlike API keys, the secret CAN be retrieved later with 'vrg oidc get --show-secret'.
    """
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "enabled": not disabled,
    }

    # Parse redirect URIs from comma-separated string
    if redirect_uri is not None:
        uris = [u.strip() for u in redirect_uri.split(",") if u.strip()]
        kwargs["redirect_uri"] = uris

    if description is not None:
        kwargs["description"] = description

    if restrict_access:
        kwargs["restrict_access"] = True

    # Resolve force_auth_source if provided
    if force_auth_source is not None:
        auth_source_key = resolve_resource_id(
            vctx.client.auth_sources, force_auth_source, "Auth source"
        )
        kwargs["force_auth_source"] = auth_source_key

    # Resolve map_user if provided
    if map_user is not None:
        user_key = resolve_resource_id(vctx.client.users, map_user, "User")
        kwargs["map_user"] = user_key

    if scope_profile is not None:
        kwargs["scope_profile"] = scope_profile
    if scope_email is not None:
        kwargs["scope_email"] = scope_email
    if scope_groups is not None:
        kwargs["scope_groups"] = scope_groups

    app_obj = vctx.client.oidc_applications.create(**kwargs)

    output_success(
        f"Created OIDC application '{name}' (key: {int(app_obj.key)})",
        quiet=vctx.quiet,
    )

    output_result(
        _oidc_app_to_dict(app_obj, include_secret=True, include_well_known=True),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )

    output_warning(
        "Store the client_secret securely. It can be retrieved later with "
        "'vrg oidc get --show-secret'.",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def oidc_update(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New application name."),
    ] = None,
    redirect_uri: Annotated[
        str | None,
        typer.Option("--redirect-uri", help="Comma-separated redirect URIs."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description."),
    ] = None,
    enabled: Annotated[
        bool | None,
        typer.Option("--enabled/--disabled", help="Enable or disable."),
    ] = None,
    restrict_access: Annotated[
        bool | None,
        typer.Option(
            "--restrict-access/--no-restrict-access",
            help="Restrict to allowed users/groups.",
        ),
    ] = None,
    force_auth_source: Annotated[
        str | None,
        typer.Option("--force-auth-source", help="Auth source name or key."),
    ] = None,
    map_user: Annotated[
        str | None,
        typer.Option("--map-user", help="User name or key to map logins to."),
    ] = None,
    scope_profile: Annotated[
        bool | None,
        typer.Option("--scope-profile/--no-scope-profile", help="Grant profile scope."),
    ] = None,
    scope_email: Annotated[
        bool | None,
        typer.Option("--scope-email/--no-scope-email", help="Grant email scope."),
    ] = None,
    scope_groups: Annotated[
        bool | None,
        typer.Option("--scope-groups/--no-scope-groups", help="Grant groups scope."),
    ] = None,
) -> None:
    """Update an OIDC application.

    Note: client_id and client_secret cannot be changed. To get a new secret,
    delete and recreate the application.
    """
    vctx = get_context(ctx)

    key = _resolve_oidc_app(vctx.client, oidc_app)

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if redirect_uri is not None:
        uris = [u.strip() for u in redirect_uri.split(",") if u.strip()]
        kwargs["redirect_uri"] = uris
    if description is not None:
        kwargs["description"] = description
    if enabled is not None:
        kwargs["enabled"] = enabled
    if restrict_access is not None:
        kwargs["restrict_access"] = restrict_access

    # Resolve force_auth_source if provided
    if force_auth_source is not None:
        auth_source_key = resolve_resource_id(
            vctx.client.auth_sources, force_auth_source, "Auth source"
        )
        kwargs["force_auth_source"] = auth_source_key

    # Resolve map_user if provided
    if map_user is not None:
        user_key = resolve_resource_id(vctx.client.users, map_user, "User")
        kwargs["map_user"] = user_key

    if scope_profile is not None:
        kwargs["scope_profile"] = scope_profile
    if scope_email is not None:
        kwargs["scope_email"] = scope_email
    if scope_groups is not None:
        kwargs["scope_groups"] = scope_groups

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    app_obj = vctx.client.oidc_applications.update(key, **kwargs)

    output_success(f"Updated OIDC application (key: {key})", quiet=vctx.quiet)

    output_result(
        _oidc_app_to_dict(app_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def oidc_delete(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete an OIDC application."""
    vctx = get_context(ctx)

    key = _resolve_oidc_app(vctx.client, oidc_app)

    # Fetch for confirmation message
    app_obj = vctx.client.oidc_applications.get(key=key)
    app_name = str(app_obj.name)

    if not confirm_action(f"Delete OIDC application '{app_name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.oidc_applications.delete(key)
    output_success(f"Deleted OIDC application '{app_name}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def oidc_enable(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
) -> None:
    """Enable an OIDC application."""
    vctx = get_context(ctx)

    key = _resolve_oidc_app(vctx.client, oidc_app)
    app_obj = vctx.client.oidc_applications.get(key=key)
    app_obj.enable()

    output_success(f"Enabled OIDC application '{app_obj.name}'", quiet=vctx.quiet)


@app.command("disable")
@handle_errors()
def oidc_disable(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
) -> None:
    """Disable an OIDC application."""
    vctx = get_context(ctx)

    key = _resolve_oidc_app(vctx.client, oidc_app)
    app_obj = vctx.client.oidc_applications.get(key=key)
    app_obj.disable()

    output_success(f"Disabled OIDC application '{app_obj.name}'", quiet=vctx.quiet)
