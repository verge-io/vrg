"""OIDC application group ACL commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import OIDC_GROUP_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import ResourceNotFoundError, handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="group",
    help=(
        "Manage the allowed-groups ACL on an OIDC application.\n\n"
        "When an OIDC application has `restrict_access` enabled, any member"
        " of a group on this whitelist may authenticate through it (in"
        " addition to any individually allowed users). The ACL has no"
        " effect while `restrict_access` is off. Groups provisioned from an"
        " upstream auth source are eligible just like local groups.\n\n"
        "Use `-o json` for machine-readable output. `--query` on fields like"
        " `group_key`, `group_display`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List allowed groups on an application\n"
        "    vrg oidc group list partner-portal\n\n"
        "    # Add a group by name or key\n"
        "    vrg oidc group add partner-portal platform-eng\n"
        "    vrg oidc group add partner-portal 12\n\n"
        "    # Remove a group (prompts for confirmation)\n"
        "    vrg oidc group remove partner-portal platform-eng\n\n"
        "    # Dump the ACL as JSON\n"
        "    vrg -o json oidc group list partner-portal\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "**Turn on `restrict_access` first.** Adding a group while"
        " `restrict_access` is off has no gating effect — the whitelist is"
        " only consulted when restriction is enabled. Enable it with"
        " `vrg oidc update <app> --restrict-access`.\n\n"
        "**`remove` accepts group name, group key, or ACL entry key.** The"
        " command resolves whichever form you provide to the underlying ACL"
        " entry and deletes it.\n\n"
        "**Name resolution**: the `<oidc-app>` and `<group>` arguments"
        " accept names or numeric keys. Ambiguous names exit with code 7.\n"
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


def _oidc_group_to_dict(entry: Any) -> dict[str, Any]:
    """Convert SDK OIDC group ACL entry to output dict."""
    return {
        "$key": int(entry.key),
        "group_key": entry.get("group"),
        "group_display": entry.get("group_display", ""),
    }


def _find_acl_entry(entries: list[Any], member_key: int, member_field: str) -> int:
    """Find ACL entry key by member key."""
    for entry in entries:
        if entry.get(member_field) == member_key:
            return int(entry.key)
    raise ResourceNotFoundError(f"No ACL entry found for {member_field} key {member_key}")


@app.command("list")
@handle_errors()
def oidc_group_list(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
) -> None:
    """List allowed groups for an OIDC application."""
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    groups_mgr = vctx.client.oidc_applications.allowed_groups(app_key)
    entries = groups_mgr.list()

    output_result(
        [_oidc_group_to_dict(e) for e in entries],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=OIDC_GROUP_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("add")
@handle_errors()
def oidc_group_add(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    group: Annotated[str, typer.Argument(help="Group name or key to add.")],
) -> None:
    """Add a group to the OIDC application's allowed list."""
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    group_key = resolve_resource_id(vctx.client.groups, group, "Group")

    groups_mgr = vctx.client.oidc_applications.allowed_groups(app_key)
    groups_mgr.add(group_key=group_key)

    output_success(f"Added group '{group}' to OIDC application", quiet=vctx.quiet)


@app.command("remove")
@handle_errors()
def oidc_group_remove(
    ctx: typer.Context,
    oidc_app: Annotated[str, typer.Argument(help="OIDC application name or key.")],
    group_or_key: Annotated[str, typer.Argument(help="Group name/key or ACL entry key.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Remove a group from the OIDC application's allowed list."""
    vctx = get_context(ctx)
    app_key = _resolve_oidc_app(vctx.client, oidc_app)
    groups_mgr = vctx.client.oidc_applications.allowed_groups(app_key)

    # Resolve entry key: try as group first, then as direct entry key
    if group_or_key.isdigit():
        # Could be group key or ACL entry key — try group key first
        group_key = int(group_or_key)
        entries = groups_mgr.list()
        matching = [e for e in entries if e.get("group") == group_key]
        if matching:
            entry_key = int(matching[0].key)
        else:
            # Treat as direct ACL entry key
            entry_key = group_key
    else:
        # Resolve group name
        group_key = resolve_resource_id(vctx.client.groups, group_or_key, "Group")
        entries = groups_mgr.list()
        entry_key = _find_acl_entry(entries, group_key, "group")

    if not confirm_action(f"Remove group '{group_or_key}' from OIDC application?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    groups_mgr.delete(entry_key)
    output_success(f"Removed group '{group_or_key}' from OIDC application", quiet=vctx.quiet)
