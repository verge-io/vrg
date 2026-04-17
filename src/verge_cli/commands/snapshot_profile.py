"""Snapshot profile management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SNAPSHOT_PROFILE_COLUMNS
from verge_cli.commands import snapshot_profile_period
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="profile",
    help=(
        "Manage snapshot profiles (automated schedules for snapshot creation"
        " and retention).\n\n"
        "A **snapshot profile** is a named schedule that drives automatic"
        " snapshot creation and expiration. Each profile contains one or more"
        " *periods* (hourly, daily, weekly, monthly) with their own retention"
        " settings. The same profile can be attached to VMs, NAS volumes,"
        " outgoing site syncs, antivirus scans, and the system itself —"
        " giving a single place to define DR and backup cadence across"
        " workloads. VergeOS ships default profiles (System Snapshots, SOX,"
        " HIPAA, NAS Volume Syncs, Volume Antivirus Scan); custom profiles"
        " can be added alongside them.\n\n"
        "For structured output, pair any `list` or `get` with `-o json`."
        " Useful fields to `--query`: `name`, `description`, `$key`. Name"
        " resolution applies to `get`, `update`, and `delete` — ambiguous"
        " names raise exit code 7 (multiple matches). Manage a profile's"
        " periods (the actual schedule entries) via `vrg snapshot profile"
        " period ...`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List snapshot profiles\n"
        "    vrg snapshot profile list\n\n"
        "    # Inspect the default system profile as JSON\n"
        "    vrg -o json snapshot profile get System\\ Snapshots\n\n"
        "    # Create a custom profile, then add periods to it\n"
        "    vrg snapshot profile create --name webservers --description 'Web tier DR'\n"
        "    vrg snapshot profile period list webservers\n\n"
        "    # Rename a profile\n"
        "    vrg snapshot profile update webservers --name web-tier\n\n"
        "    # Delete a profile (detaches it from any resources that reference it)\n"
        "    vrg snapshot profile delete web-tier --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "A profile with no periods will never fire snapshots — add periods"
        " before assigning it to a workload. Profiles can be attached to"
        " VMs, NAS volumes, outgoing syncs, and antivirus scans; deleting a"
        " profile removes those schedule bindings but does not delete"
        " previously captured snapshots."
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)

app.add_typer(snapshot_profile_period.app, name="period")


def _profile_to_dict(profile: Any) -> dict[str, Any]:
    """Convert a SnapshotProfile object to a dict for output."""
    return {
        "$key": profile.key,
        "name": profile.name,
        "description": profile.get("description", ""),
    }


@app.command("list")
@handle_errors()
def profile_list(ctx: typer.Context) -> None:
    """List all snapshot profiles."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx,
            lambda c: c.snapshot_profiles.list(),
            _profile_to_dict,
            SNAPSHOT_PROFILE_COLUMNS,
        )
        return
    vctx = get_context(ctx)
    profiles = vctx.client.snapshot_profiles.list()
    data = [_profile_to_dict(p) for p in profiles]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SNAPSHOT_PROFILE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def profile_get(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
) -> None:
    """Get details of a snapshot profile."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.snapshot_profiles, profile, "Snapshot profile")
    profile_obj = vctx.client.snapshot_profiles.get(key)
    output_result(
        _profile_to_dict(profile_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def profile_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n", help="Profile name")],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Profile description"),
    ] = None,
) -> None:
    """Create a new snapshot profile."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {"name": name}
    if description is not None:
        kwargs["description"] = description

    result = vctx.client.snapshot_profiles.create(**kwargs)

    profile_name = result.name if result else name
    profile_key = result.key if result else "?"
    output_success(
        f"Created snapshot profile '{profile_name}' (key: {profile_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def profile_update(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New profile name")] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description"),
    ] = None,
) -> None:
    """Update a snapshot profile."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.snapshot_profiles, profile, "Snapshot profile")

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    vctx.client.snapshot_profiles.update(key, **kwargs)
    output_success(f"Updated snapshot profile '{profile}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def profile_delete(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a snapshot profile."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.snapshot_profiles, profile, "Snapshot profile")

    if not confirm_action(f"Delete snapshot profile '{profile}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.snapshot_profiles.delete(key)
    output_success(f"Deleted snapshot profile '{profile}'", quiet=vctx.quiet)
