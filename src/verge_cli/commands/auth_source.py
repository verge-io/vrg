"""Authentication source management commands."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from verge_cli.columns import AUTH_SOURCE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_error, output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="auth-source",
    help=(
        "Manage external identity providers that authenticate users INTO"
        " VergeOS.\n\n"
        "An auth source delegates VergeOS login to an external OAuth2/OpenID"
        " Connect provider — Azure AD, Google, Okta, GitLab, or any generic"
        " OpenID/OAuth2 IdP. Users click the configured sign-in button on the"
        " VergeOS login page, authenticate at the provider, and return with a"
        " resolved local user record (optionally auto-created from the IdP's"
        " profile/group claims).\n\n"
        "This is the opposite direction of `vrg oidc`: auth-source = external"
        " IdP → VergeOS; oidc = VergeOS → external application. Don't confuse"
        " them.\n\n"
        "Use `-o json` for machine-readable output. `--query` on fields like"
        " `name`, `driver`, `show_on_login`, `debug`. `get --show-settings`"
        " includes the driver-specific `settings` blob (client ID, secret,"
        " endpoints, scopes) — omitted by default because it contains"
        " credentials.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List configured auth sources\n"
        "    vrg auth-source list\n\n"
        "    # Filter by driver type\n"
        "    vrg auth-source list --driver azure\n\n"
        "    # Inspect a source as JSON, including its settings blob\n"
        "    vrg -o json auth-source get corporate-sso --show-settings\n\n"
        "    # Create an Azure AD source\n"
        "    vrg auth-source create --name corporate-sso --driver azure \\\n"
        "        --tenant-id 11111111-2222-3333-4444-555555555555 \\\n"
        "        --client-id my-app-id --client-secret s3cret \\\n"
        "        --show-on-login --button-icon bi-microsoft\n\n"
        "    # Rotate the client secret\n"
        "    vrg auth-source update corporate-sso --client-secret new-s3cret\n\n"
        "    # Turn on debug logging while troubleshooting a failed login\n"
        "    vrg auth-source debug-on corporate-sso\n\n"
        "    # Remove a source (prompts for confirmation)\n"
        "    vrg auth-source delete corporate-sso\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "**Driver is immutable**: `--driver` (`azure`, `google`, `gitlab`,"
        " `okta`, `openid`, `oauth2`, `verge.io`) is set at creation and"
        " cannot be changed. To switch providers, delete and recreate the"
        " source.\n\n"
        "**Settings merge strategy**: `--client-id`, `--client-secret`,"
        " `--tenant-id`, `--scope`, `--redirect-uri`, and"
        " `--auto-create-users` are merged into the driver-specific"
        " `settings` object. `--settings-json` provides the base; individual"
        " flags override matching keys. For driver-specific fields not"
        " covered by a flag, pass the full JSON blob via `--settings-json`.\n\n"
        "**Debug auto-disables after 1 hour**: `debug-on` enables verbose"
        " logging for this source, then clears itself after 60 minutes to"
        " limit log volume. Use `debug-off` to turn it off earlier.\n\n"
        "**Name resolution**: commands that take `<auth-source>` accept the"
        " display name or numeric key. Ambiguous names exit with code 7.\n\n"
        "**Button styling controls login appearance**: `--show-on-login`,"
        " `--button-icon` (Bootstrap Icon class like `bi-google`),"
        " `--button-bg-color`, and `--button-text-color` configure how the"
        " sign-in button appears on the VergeOS login page.\n"
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


def _auth_source_to_dict(source: Any) -> dict[str, Any]:
    """Convert an AuthSource SDK object to a dictionary for output."""
    button_style = source.button_style if hasattr(source, "button_style") else {}
    return {
        "$key": int(source.key),
        "name": source.name,
        "driver": source.driver,
        "show_on_login": source.is_menu,
        "debug": source.is_debug_enabled,
        "button_icon": button_style.get("icon", ""),
        "button_bg_color": button_style.get("background_color", ""),
        "button_text_color": button_style.get("text_color", ""),
        "icon_color": button_style.get("icon_color", ""),
    }


def _build_settings(
    settings_json: str | None,
    client_id: str | None,
    client_secret: str | None,
    tenant_id: str | None,
    scope: str | None,
    redirect_uri: str | None,
    auto_create_users: bool | None,
) -> dict[str, Any] | None:
    """Build settings dict from JSON base + individual flags."""
    settings: dict[str, Any] = {}
    if settings_json:
        try:
            parsed = json.loads(settings_json)
        except json.JSONDecodeError as exc:
            output_error(f"Invalid JSON for --settings-json: {exc}")
            raise typer.Exit(2) from None
        settings = parsed

    flag_map: dict[str, Any] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant_id": tenant_id,
        "scope": scope,
        "redirect_uri": redirect_uri,
        "auto_create_users": auto_create_users,
    }
    for k, v in flag_map.items():
        if v is not None:
            settings[k] = v

    return settings if settings else None


@app.command("list")
@handle_errors()
def auth_source_list(
    ctx: typer.Context,
    driver: Annotated[
        str | None,
        typer.Option(
            "--driver",
            help="Filter by driver type (azure, google, gitlab, okta, openid, oauth2, verge.io).",
        ),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
) -> None:
    """List authentication sources.

    Examples:

        vrg auth-source list
        vrg auth-source list --driver azure
        vrg -o json auth-source list | jq '.[] | select(.show_on_login) | .name'

    Use `-A` / `--all-profiles` to fan out across every configured profile.
    Useful `--query` fields: `name`, `driver`, `show_on_login`, `debug`.
    The driver-specific `settings` blob is only included via
    `auth-source get --show-settings`.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.auth_sources.list(), _auth_source_to_dict, AUTH_SOURCE_COLUMNS
        )
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if driver is not None:
        kwargs["driver"] = driver
    if filter is not None:
        kwargs["filter"] = filter

    sources = vctx.client.auth_sources.list(**kwargs)

    output_result(
        [_auth_source_to_dict(s) for s in sources],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=AUTH_SOURCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def auth_source_get(
    ctx: typer.Context,
    auth_source: Annotated[str, typer.Argument(help="Auth source name or key.")],
    show_settings: Annotated[
        bool,
        typer.Option("--show-settings", help="Include sensitive settings in output."),
    ] = False,
) -> None:
    """Get details of an authentication source.

    Examples:

        vrg auth-source get corporate-sso
        vrg -o json auth-source get corporate-sso --show-settings
        vrg -o json auth-source get 4 --show-settings \\
            --query "settings.{client: client_id, tenant: tenant_id}"

    `--show-settings` includes the driver-specific `settings` blob
    (client ID, secret, endpoints, scopes). Omitted by default because
    it contains credentials. Resolves by name or numeric key; ambiguous
    names exit 7.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")
    source = vctx.client.auth_sources.get(key, include_settings=show_settings)

    result = _auth_source_to_dict(source)
    if show_settings:
        result["settings"] = source.settings

    output_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def auth_source_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Auth source display name.")],
    driver: Annotated[
        str,
        typer.Option(
            "--driver",
            help="Provider type (azure, google, gitlab, okta, openid, oauth2, verge.io).",
        ),
    ],
    client_id: Annotated[str | None, typer.Option("--client-id", help="OAuth client ID.")] = None,
    client_secret: Annotated[
        str | None, typer.Option("--client-secret", help="OAuth client secret.")
    ] = None,
    tenant_id: Annotated[str | None, typer.Option("--tenant-id", help="Azure tenant ID.")] = None,
    scope: Annotated[str | None, typer.Option("--scope", help="OAuth scopes.")] = None,
    redirect_uri: Annotated[
        str | None, typer.Option("--redirect-uri", help="OAuth redirect URI.")
    ] = None,
    auto_create_users: Annotated[
        bool | None,
        typer.Option("--auto-create-users/--no-auto-create-users", help="Auto-create users."),
    ] = None,
    show_on_login: Annotated[
        bool, typer.Option("--show-on-login", help="Show on login page.")
    ] = False,
    button_icon: Annotated[
        str | None,
        typer.Option("--button-icon", help="Bootstrap Icon class (e.g., bi-google)."),
    ] = None,
    button_bg_color: Annotated[
        str | None, typer.Option("--button-bg-color", help="Button background CSS color.")
    ] = None,
    button_text_color: Annotated[
        str | None, typer.Option("--button-text-color", help="Button text CSS color.")
    ] = None,
    settings_json: Annotated[
        str | None,
        typer.Option("--settings-json", help="Raw JSON string for driver-specific settings."),
    ] = None,
) -> None:
    """Create a new authentication source.

    Examples:

        vrg auth-source create --name corporate-sso --driver azure \\
            --tenant-id 11111111-2222-3333-4444-555555555555 \\
            --client-id my-app-id --client-secret s3cret \\
            --show-on-login --button-icon bi-microsoft
        vrg auth-source create --name google-sso --driver google \\
            --client-id xxx.apps.googleusercontent.com \\
            --client-secret s3cret --auto-create-users
        vrg auth-source create --name custom-idp --driver openid \\
            --settings-json '{"issuer_url":"https://idp.example.com"}'

    `--driver` is immutable after creation (`azure`, `google`, `gitlab`,
    `okta`, `openid`, `oauth2`, `verge.io`). Individual flags override
    matching keys in `--settings-json`; for driver-specific fields not
    covered by a flag, pass the full JSON blob.
    """
    vctx = get_context(ctx)

    settings = _build_settings(
        settings_json, client_id, client_secret, tenant_id, scope, redirect_uri, auto_create_users
    )

    kwargs: dict[str, Any] = {
        "name": name,
        "driver": driver,
    }
    if settings is not None:
        kwargs["settings"] = settings
    if show_on_login:
        kwargs["menu"] = True
    if button_icon is not None:
        kwargs["button_fa_icon"] = button_icon
    if button_bg_color is not None:
        kwargs["button_background_color"] = button_bg_color
    if button_text_color is not None:
        kwargs["button_color"] = button_text_color

    source = vctx.client.auth_sources.create(**kwargs)

    output_success(f"Created auth source '{source.name}' (key: {source.key})", quiet=vctx.quiet)

    output_result(
        _auth_source_to_dict(source),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def auth_source_update(
    ctx: typer.Context,
    auth_source: Annotated[str, typer.Argument(help="Auth source name or key.")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New display name.")] = None,
    client_id: Annotated[str | None, typer.Option("--client-id", help="OAuth client ID.")] = None,
    client_secret: Annotated[
        str | None, typer.Option("--client-secret", help="OAuth client secret.")
    ] = None,
    tenant_id: Annotated[str | None, typer.Option("--tenant-id", help="Azure tenant ID.")] = None,
    scope: Annotated[str | None, typer.Option("--scope", help="OAuth scopes.")] = None,
    redirect_uri: Annotated[
        str | None, typer.Option("--redirect-uri", help="OAuth redirect URI.")
    ] = None,
    auto_create_users: Annotated[
        bool | None,
        typer.Option("--auto-create-users/--no-auto-create-users", help="Auto-create users."),
    ] = None,
    show_on_login: Annotated[
        bool | None,
        typer.Option("--show-on-login/--no-show-on-login", help="Show on login page."),
    ] = None,
    button_icon: Annotated[
        str | None,
        typer.Option("--button-icon", help="Bootstrap Icon class."),
    ] = None,
    button_bg_color: Annotated[
        str | None, typer.Option("--button-bg-color", help="Button background CSS color.")
    ] = None,
    button_text_color: Annotated[
        str | None, typer.Option("--button-text-color", help="Button text CSS color.")
    ] = None,
    settings_json: Annotated[
        str | None,
        typer.Option("--settings-json", help="Raw JSON string for driver-specific settings."),
    ] = None,
) -> None:
    """Update an authentication source.

    Examples:

        vrg auth-source update corporate-sso --client-secret new-s3cret
        vrg auth-source update corporate-sso --no-show-on-login
        vrg auth-source update corporate-sso --button-bg-color '#0078d4'

    Pass at least one field to change; calling without any option exits 2.
    `--driver` cannot be changed here — delete and recreate the source
    to switch providers.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")

    settings = _build_settings(
        settings_json, client_id, client_secret, tenant_id, scope, redirect_uri, auto_create_users
    )

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if settings is not None:
        kwargs["settings"] = settings
    if show_on_login is not None:
        kwargs["menu"] = show_on_login
    if button_icon is not None:
        kwargs["button_fa_icon"] = button_icon
    if button_bg_color is not None:
        kwargs["button_background_color"] = button_bg_color
    if button_text_color is not None:
        kwargs["button_color"] = button_text_color

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    source = vctx.client.auth_sources.update(key, **kwargs)

    output_success(f"Updated auth source '{source.name}'", quiet=vctx.quiet)

    output_result(
        _auth_source_to_dict(source),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def auth_source_delete(
    ctx: typer.Context,
    auth_source: Annotated[str, typer.Argument(help="Auth source name or key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete an authentication source.

    Examples:

        vrg auth-source delete corporate-sso
        vrg auth-source delete corporate-sso -y
        vrg auth-source delete 4 -y

    **Destructive.** Users currently authenticated via this source keep
    their existing sessions, but future logins through it will fail.
    Local users whose passwords still work continue to authenticate.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")
    source = vctx.client.auth_sources.get(key)

    if not confirm_action(f"Delete auth source '{source.name}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.auth_sources.delete(key)
    output_success(f"Deleted auth source '{source.name}'", quiet=vctx.quiet)


@app.command("debug-on")
@handle_errors()
def auth_source_debug_on(
    ctx: typer.Context,
    auth_source: Annotated[str, typer.Argument(help="Auth source name or key.")],
) -> None:
    """Enable debug logging for an authentication source.

    Examples:

        vrg auth-source debug-on corporate-sso
        vrg auth-source debug-on 4

    Debug mode auto-disables after 1 hour to limit log volume. Use
    `auth-source debug-off` to turn it off earlier. Useful when
    troubleshooting a failed login flow — inspect `vrg log` afterwards
    for the emitted diagnostic events.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")
    source = vctx.client.auth_sources.get(key)
    source.enable_debug()

    output_success(
        f"Debug enabled for '{source.name}' (auto-disables after 1 hour)",
        quiet=vctx.quiet,
    )


@app.command("debug-off")
@handle_errors()
def auth_source_debug_off(
    ctx: typer.Context,
    auth_source: Annotated[str, typer.Argument(help="Auth source name or key.")],
) -> None:
    """Disable debug logging for an authentication source.

    Examples:

        vrg auth-source debug-off corporate-sso
        vrg auth-source debug-off 4

    Clears debug logging earlier than the 1-hour auto-disable. Safe to
    call when debug is already off.
    """
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")
    source = vctx.client.auth_sources.get(key)
    source.disable_debug()

    output_success(f"Debug disabled for '{source.name}'", quiet=vctx.quiet)
