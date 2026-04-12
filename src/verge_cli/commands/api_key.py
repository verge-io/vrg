"""API key management commands for Verge CLI."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import API_KEY_COLUMNS, API_KEY_CREATED_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success, output_warning
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="api-key",
    help="Manage API keys.",
    no_args_is_help=True,
)


def _api_key_to_dict(key_obj: Any) -> dict[str, Any]:
    """Convert an APIKey SDK object to a dictionary for output."""
    return {
        "$key": int(key_obj.key),
        "name": key_obj.name,
        "user_name": key_obj.user_name,
        "description": key_obj.get("description", ""),
        "created": key_obj.get("created"),
        "expires": key_obj.get("expires"),
        "is_expired": key_obj.is_expired,
        "last_login": key_obj.get("last_login"),
        "last_login_ip": key_obj.get("last_login_ip", ""),
        "ip_allow_list": key_obj.ip_allow_list,
        "ip_deny_list": key_obj.ip_deny_list,
    }


def _api_key_created_to_dict(result: Any) -> dict[str, Any]:
    """Convert an APIKeyCreated response to a dictionary for output."""
    return {
        "$key": int(result.key),
        "name": result.name,
        "user_name": result.user_name,
        "secret": result.secret,
    }


@app.command("list")
@handle_errors()
def api_key_list(
    ctx: typer.Context,
    user: Annotated[
        str | None,
        typer.Option("--user", help="Filter by user (name or key)."),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
) -> None:
    """List API keys."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.api_keys.list(), _api_key_to_dict, API_KEY_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if filter is not None:
        kwargs["filter"] = filter
    if user is not None:
        # SDK accepts user as int key or str username
        if user.isdigit():
            kwargs["user"] = int(user)
        else:
            kwargs["user"] = user

    keys = vctx.client.api_keys.list(**kwargs)

    output_result(
        [_api_key_to_dict(k) for k in keys],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=API_KEY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def api_key_get(
    ctx: typer.Context,
    api_key: Annotated[str, typer.Argument(help="API key name or numeric key.")],
    user: Annotated[
        str | None,
        typer.Option("--user", help="User (required when looking up by name)."),
    ] = None,
) -> None:
    """Get an API key by key or name."""
    vctx = get_context(ctx)

    if api_key.isdigit():
        # Lookup by numeric key
        key_obj = vctx.client.api_keys.get(int(api_key))
    else:
        # Lookup by name — requires --user
        if user is None:
            typer.echo("Error: --user is required when looking up by name.", err=True)
            raise typer.Exit(2)
        # SDK accepts user as int or str
        user_ref: int | str
        if user.isdigit():
            user_ref = int(user)
        else:
            user_ref = user
        key_obj = vctx.client.api_keys.get(name=api_key, user=user_ref)

    output_result(
        _api_key_to_dict(key_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def api_key_create(
    ctx: typer.Context,
    user: Annotated[
        str,
        typer.Option("--user", help="User to create the API key for (name or key)."),
    ],
    name: Annotated[
        str,
        typer.Option("--name", "-n", help="Name for the API key."),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Description for the API key."),
    ] = None,
    expires_in: Annotated[
        str | None,
        typer.Option(
            "--expires-in",
            help="Duration until expiration (e.g. 30d, 1w, 3m, 1y, never).",
        ),
    ] = None,
    ip_allow: Annotated[
        str | None,
        typer.Option("--ip-allow", help="Comma-separated allowed IPs/CIDRs."),
    ] = None,
    ip_deny: Annotated[
        str | None,
        typer.Option("--ip-deny", help="Comma-separated denied IPs/CIDRs."),
    ] = None,
) -> None:
    """Create a new API key.

    The secret is only shown once at creation time.
    """
    vctx = get_context(ctx)

    # SDK accepts user as int or str
    user_ref: int | str
    if user.isdigit():
        user_ref = int(user)
    else:
        user_ref = user

    kwargs: dict[str, Any] = {
        "user": user_ref,
        "name": name,
    }
    if description is not None:
        kwargs["description"] = description
    if expires_in is not None:
        kwargs["expires_in"] = expires_in

    # Parse IP lists from comma-separated strings
    if ip_allow is not None:
        kwargs["ip_allow_list"] = [ip.strip() for ip in ip_allow.split(",") if ip.strip()]
    if ip_deny is not None:
        kwargs["ip_deny_list"] = [ip.strip() for ip in ip_deny.split(",") if ip.strip()]

    result = vctx.client.api_keys.create(**kwargs)

    output_success(f"Created API key '{result.name}' (key: {int(result.key)})", quiet=vctx.quiet)

    output_result(
        _api_key_created_to_dict(result),
        columns=API_KEY_CREATED_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )

    output_warning(
        "Store this secret securely — it cannot be retrieved again.",
        quiet=vctx.quiet,
    )


@app.command("delete")
@handle_errors()
def api_key_delete(
    ctx: typer.Context,
    api_key: Annotated[str, typer.Argument(help="API key name or numeric key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete an API key.

    Warning: this is permanent and the key will no longer be usable.
    """
    vctx = get_context(ctx)

    # Resolve key
    if api_key.isdigit():
        key = int(api_key)
    else:
        key = resolve_resource_id(vctx.client.api_keys, api_key, "API key")

    if not confirm_action(f"Delete API key {key}? This cannot be undone.", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.api_keys.delete(key)
    output_success(f"Deleted API key {key}", quiet=vctx.quiet)
