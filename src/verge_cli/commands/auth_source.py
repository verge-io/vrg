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
    help="Manage authentication sources (SSO/OAuth identity providers).",
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
    """List authentication sources."""
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
    """Get details of an authentication source."""
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
    """Create a new authentication source."""
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
    """Update an authentication source."""
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
    """Delete an authentication source."""
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

    Debug mode auto-disables after 1 hour.
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
    """Disable debug logging for an authentication source."""
    vctx = get_context(ctx)

    key = resolve_resource_id(vctx.client.auth_sources, auth_source, "Auth source")
    source = vctx.client.auth_sources.get(key)
    source.disable_debug()

    output_success(f"Debug disabled for '{source.name}'", quiet=vctx.quiet)
