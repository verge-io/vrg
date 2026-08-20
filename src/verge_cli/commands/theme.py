"""Theme management commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, NoReturn

import click
import typer
from pyvergeos.resources.base import ResourceManager, ResourceObject

from verge_cli.columns import BOOL_STYLES, ColumnDef, format_bool_yn, format_epoch
from verge_cli.commands.recipe import _parse_set_args
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource

app = typer.Typer(
    name="theme",
    help=(
        "Manage VergeOS UI themes. Themes control the UI color palette and branding. "
        "Use repeatable `--set PROPERTY=VALUE` options to set CSS color definitions, "
        "and `export` / `import` to move themes between systems as JSON."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


# ponytail: use the SDK's generic CRUD manager until pyvergeos exposes client.themes.
class _ThemeManager(ResourceManager[ResourceObject]):
    _endpoint = "themes"


THEME_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("based_on", header="Based On"),
    ColumnDef("type"),
    ColumnDef("description", wide_only=True),
    ColumnDef("system_created", header="System", format_fn=format_bool_yn, wide_only=True),
    ColumnDef("modified", format_fn=format_epoch, wide_only=True),
    ColumnDef("created", format_fn=format_epoch, wide_only=True),
]


def _manager(client: Any) -> Any:
    return _ThemeManager(client)


def _theme_to_dict(theme: Any) -> dict[str, Any]:
    return {
        "$key": theme.get("$key", theme.get("id")),
        "name": theme.get("name", ""),
        "description": theme.get("description", ""),
        "enabled": theme.get("enabled"),
        "based_on": theme.get("based_on", ""),
        "type": theme.get("type", ""),
        "system_created": theme.get("system_created", False),
        "logo_large": theme.get("logo_large", ""),
        "logo_small": theme.get("logo_small", ""),
        "logo_favicon": theme.get("logo_favicon", ""),
        "definitions": theme.get("definitions", []),
        "modified": theme.get("modified"),
        "created": theme.get("created"),
    }


def _resolve(manager: Any, identifier: str) -> str:
    return resolve_nas_resource(manager, identifier, "theme")


def _usage_error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(2)


def _definitions(values: list[str] | None) -> list[dict[str, str]]:
    try:
        parsed = _parse_set_args(values or [])
    except click.BadParameter as exc:
        _usage_error(str(exc))
    return [{"property": property_name, "value": value} for property_name, value in parsed.items()]


def _get_with_definitions(manager: Any, identifier: str) -> Any:
    key = _resolve(manager, identifier)
    return manager.get(key, fields=["$key", "most", "definitions[most]"])


def _export_payload(theme: Any) -> dict[str, Any]:
    return {
        "name": theme.get("name", ""),
        "description": theme.get("description", ""),
        "enabled": theme.get("enabled", True),
        "based_on": theme.get("based_on", "light"),
        "set_definitions": [
            {"property": item.get("property", ""), "value": item.get("value", "")}
            for item in theme.get("definitions", [])
        ],
    }


def _import_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        _usage_error("Theme JSON must contain an object.")
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        _usage_error("Theme JSON requires a non-empty string 'name'.")
    if data.get("based_on") not in ("light", "dark"):
        _usage_error("Theme JSON 'based_on' must be 'light' or 'dark'.")
    if "enabled" in data and not isinstance(data["enabled"], bool):
        _usage_error("Theme JSON 'enabled' must be a boolean.")
    definitions = data.get("set_definitions", [])
    if not isinstance(definitions, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("property"), str)
        and isinstance(item.get("value"), str)
        for item in definitions
    ):
        _usage_error(
            "Theme JSON 'set_definitions' must be a list of string property/value objects."
        )
    return {
        key: data[key]
        for key in ("name", "description", "enabled", "based_on", "set_definitions")
        if key in data
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    filter_expr: Annotated[
        str | None, typer.Option("--filter", help="OData filter expression.")
    ] = None,
) -> None:
    """List themes."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda client: _manager(client).list(), _theme_to_dict, THEME_COLUMNS
        )
        return
    vctx = get_context(ctx)
    kwargs = {"filter": filter_expr} if filter_expr is not None else {}
    themes = _manager(vctx.client).list(**kwargs)
    output_result(
        [_theme_to_dict(theme) for theme in themes],
        columns=THEME_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
) -> None:
    """Get a theme, including its color definitions."""
    vctx = get_context(ctx)
    item = _get_with_definitions(_manager(vctx.client), theme)
    output_result(
        _theme_to_dict(item),
        columns=THEME_COLUMNS,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Theme name.")],
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Theme description.")
    ] = None,
    based_on: Annotated[
        str,
        typer.Option(
            "--based-on",
            help="Base system theme.",
            click_type=click.Choice(["light", "dark"]),
        ),
    ] = "light",
    enabled: Annotated[bool, typer.Option("--enabled/--disabled", help="Enable the theme.")] = True,
    definition: Annotated[
        list[str] | None,
        typer.Option("--set", help="Color definition as PROPERTY=VALUE (repeatable)."),
    ] = None,
) -> None:
    """Create a custom theme."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {"name": name, "based_on": based_on, "enabled": enabled}
    if description is not None:
        kwargs["description"] = description
    if definition:
        kwargs["set_definitions"] = _definitions(definition)
    result = _manager(vctx.client).create(**kwargs)
    output_success(
        f"Created theme '{result.get('name', name)}' (key: {result.get('$key', result.get('id', '?'))})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New theme name.")] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New description.")
    ] = None,
    enabled: Annotated[
        bool | None, typer.Option("--enabled/--disabled", help="Enable or disable the theme.")
    ] = None,
    definition: Annotated[
        list[str] | None,
        typer.Option(
            "--set",
            help="Set PROPERTY=VALUE; use an empty value to restore the base value (repeatable).",
        ),
    ] = None,
) -> None:
    """Update a custom theme."""
    vctx = get_context(ctx)
    manager = _manager(vctx.client)
    key = _resolve(manager, theme)
    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if enabled is not None:
        kwargs["enabled"] = enabled
    if definition:
        kwargs["set_definitions"] = _definitions(definition)
    if not kwargs:
        _usage_error("Specify at least one field to update.")
    manager.update(key, **kwargs)
    output_success(f"Updated theme '{theme}'", quiet=vctx.quiet)


def _set_enabled(ctx: typer.Context, theme: str, enabled: bool) -> None:
    vctx = get_context(ctx)
    manager = _manager(vctx.client)
    manager.update(_resolve(manager, theme), enabled=enabled)
    output_success(f"{'Enabled' if enabled else 'Disabled'} theme '{theme}'", quiet=vctx.quiet)


@app.command("enable")
@handle_errors()
def enable_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
) -> None:
    """Enable a theme."""
    _set_enabled(ctx, theme, True)


@app.command("disable")
@handle_errors()
def disable_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
) -> None:
    """Disable a theme."""
    _set_enabled(ctx, theme, False)


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Delete a custom theme."""
    vctx = get_context(ctx)
    manager = _manager(vctx.client)
    key = _resolve(manager, theme)
    if not confirm_action(f"Delete theme '{theme}'?", yes=yes):
        return
    manager.delete(key)
    output_success(f"Deleted theme '{theme}'", quiet=vctx.quiet)


@app.command("export")
@handle_errors()
def export_cmd(
    ctx: typer.Context,
    theme: Annotated[str, typer.Argument(help="Theme name or 40-character key.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="Destination JSON file.")],
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Export a portable theme JSON file."""
    if file.exists() and not force:
        _usage_error(f"File already exists: {file}. Use --force to overwrite it.")
    vctx = get_context(ctx)
    item = _get_with_definitions(_manager(vctx.client), theme)
    file.write_text(json.dumps(_export_payload(item), indent=2, sort_keys=True) + "\n")
    output_success(f"Exported theme '{theme}' to {file}", quiet=vctx.quiet)


@app.command("import")
@handle_errors()
def import_cmd(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Argument(help="Theme JSON file.", exists=True, dir_okay=False, readable=True),
    ],
    name: Annotated[
        str | None, typer.Option("--name", "-n", help="Override the exported theme name.")
    ] = None,
) -> None:
    """Create a theme from an exported JSON file."""
    try:
        payload = _import_payload(json.loads(file.read_text()))
    except json.JSONDecodeError as exc:
        _usage_error(f"Invalid theme JSON: {exc}")
    if name is not None:
        payload["name"] = name
    vctx = get_context(ctx)
    result = _manager(vctx.client).create(**payload)
    output_success(
        f"Imported theme '{result.get('name', payload['name'])}' "
        f"(key: {result.get('$key', result.get('id', '?'))})",
        quiet=vctx.quiet,
    )
