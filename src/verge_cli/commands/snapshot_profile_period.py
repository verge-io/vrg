"""Snapshot profile period sub-resource commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import SNAPSHOT_PROFILE_PERIOD_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="period",
    help=(
        "Manage the schedule entries inside a snapshot profile.\n\n"
        "A **period** is a single scheduled rule on a parent"
        " [snapshot profile](#) — it fires snapshots at a given frequency"
        " and controls how long those snapshots are kept. A profile with"
        " no periods never fires, so periods are where the actual cadence"
        " and retention live. Frequencies are `hourly`, `daily`, `weekly`,"
        " `monthly`, or `yearly`; `retention` is expressed in seconds"
        " (e.g., 86400 for 1 day). Fields ignored by lower frequencies"
        " (e.g., `hour` on an hourly period) are forced to defaults.\n\n"
        "Every command takes the parent profile as its first argument"
        " (name or numeric key). Pair any `list` or `get` with `-o json`"
        " for structured output; useful fields to `--query`: `name`,"
        " `frequency`, `retention`, `min_snapshots`, `max_tier`,"
        " `quiesce`, `immutable`. Period name resolution on `get`,"
        " `update`, and `delete` raises exit code 7 when a name matches"
        " more than one period — use the numeric `$key` in that case.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List periods on the default system profile\n"
        "    vrg snapshot profile period list System\\ Snapshots\n\n"
        "    # Inspect a single period as JSON\n"
        "    vrg -o json snapshot profile period get webservers Hourly\n\n"
        "    # Add an hourly period: fires at :00, keeps for 24h, keeps >=2\n"
        "    vrg snapshot profile period create webservers \\\n"
        "      --name Hourly --frequency hourly --retention 86400 \\\n"
        "      --min-snapshots 2\n\n"
        "    # Add a weekly period on Sunday at 03:00, retained 30 days\n"
        "    vrg snapshot profile period create webservers \\\n"
        "      --name Weekly --frequency weekly --retention 2592000 \\\n"
        "      --day-of-week sun --hour 3 --minute 0\n\n"
        "    # Toggle quiesce (application-consistent VM snapshots)\n"
        "    vrg snapshot profile period update webservers Daily --quiesce\n\n"
        "    # Remove a period\n"
        "    vrg snapshot profile period delete webservers Hourly --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "`quiesce` and `max_tier` apply only to VM and NAS volume"
        " snapshots — they are ignored on system (cloud) snapshot"
        " profiles. `immutable` applies only to system snapshot periods."
        " `quiesce` requires the VergeOS guest agent inside the VM; when"
        " the agent is absent the snapshot proceeds as crash-consistent."
        " `min_snapshots` overrides `retention` — the minimum count is"
        " kept even after expiration. Deleting a period stops future"
        " firings but does not delete snapshots already created by it."
    ),
    rich_markup_mode="markdown",
    no_args_is_help=True,
)


def _get_profile(ctx: typer.Context, profile_identifier: str) -> tuple[Any, int]:
    """Resolve profile and return (vctx, profile_key)."""
    vctx = get_context(ctx)
    profile_key = resolve_resource_id(
        vctx.client.snapshot_profiles, profile_identifier, "Snapshot profile"
    )
    return vctx, profile_key


def _resolve_period(period_mgr: Any, identifier: str) -> int:
    """Resolve a period name or key to an integer key."""
    if identifier.isdigit():
        return int(identifier)
    periods = period_mgr.list()
    matches = [p for p in periods if p.name == identifier]
    if len(matches) == 1:
        return int(matches[0].key)
    if len(matches) > 1:
        typer.echo(
            f"Error: Multiple periods match '{identifier}'. Use a numeric key.",
            err=True,
        )
        raise typer.Exit(7)
    typer.echo(f"Error: Period '{identifier}' not found.", err=True)
    raise typer.Exit(6)


def _period_to_dict(period: Any) -> dict[str, Any]:
    """Convert a SnapshotProfilePeriod object to a dict for output."""
    return {
        "$key": period.key,
        "name": period.name,
        "frequency": period.get("frequency"),
        "retention": period.get("retention"),
        "min_snapshots": period.get("min_snapshots"),
        "max_tier": period.get("max_tier"),
        "minute": period.get("minute"),
        "hour": period.get("hour"),
        "day_of_week": period.get("day_of_week", "any"),
        "quiesce": period.get("quiesce", False),
        "immutable": period.get("immutable", False),
        "skip_missed": period.get("skip_missed", False),
    }


@app.command("list")
@handle_errors()
def period_list(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
) -> None:
    """List periods for a snapshot profile.

    Examples:

        vrg snapshot profile period list webservers
        vrg -o json snapshot profile period list System\\ Snapshots
        vrg -o json snapshot profile period list webservers --query "[].{name: name, freq: frequency}"

    Resolves `profile` by name or numeric key. Ambiguous names exit 7.
    """
    vctx, profile_key = _get_profile(ctx, profile)
    periods = vctx.client.snapshot_profiles.periods(profile_key).list()
    data = [_period_to_dict(p) for p in periods]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SNAPSHOT_PROFILE_PERIOD_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def period_get(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    period: Annotated[str, typer.Argument(help="Period name or key")],
) -> None:
    """Get details of a snapshot profile period.

    Examples:

        vrg snapshot profile period get webservers Hourly
        vrg -o json snapshot profile period get webservers Weekly
        vrg -o json snapshot profile period get webservers 12 --query "retention"

    Both `profile` and `period` resolve by name or numeric key. If a
    period name matches more than one entry, the command exits 7 — pass
    the numeric `$key` to disambiguate.
    """
    vctx, profile_key = _get_profile(ctx, profile)
    period_mgr = vctx.client.snapshot_profiles.periods(profile_key)
    period_key = _resolve_period(period_mgr, period)
    period_obj = period_mgr.get(period_key)
    output_result(
        _period_to_dict(period_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def period_create(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    name: Annotated[str, typer.Option("--name", "-n", help="Period name")],
    frequency: Annotated[
        str,
        typer.Option(
            "--frequency",
            "-f",
            help="Frequency: hourly, daily, weekly, monthly, yearly",
        ),
    ],
    retention: Annotated[
        int,
        typer.Option("--retention", help="Retention in seconds (0 = never expires)"),
    ],
    minute: Annotated[int, typer.Option("--minute", help="Minute of the hour (0-59)")] = 0,
    hour: Annotated[int, typer.Option("--hour", help="Hour of the day (0-23)")] = 0,
    day_of_week: Annotated[
        str,
        typer.Option("--day-of-week", help="Day of week (e.g., mon, tue, any)"),
    ] = "any",
    day_of_month: Annotated[
        int, typer.Option("--day-of-month", help="Day of the month (0-31, 0=any)")
    ] = 0,
    quiesce: Annotated[
        bool,
        typer.Option("--quiesce", help="Quiesce filesystem before snapshot"),
    ] = False,
    immutable: Annotated[
        bool,
        typer.Option("--immutable", help="Make snapshots immutable"),
    ] = False,
    min_snapshots: Annotated[
        int,
        typer.Option("--min-snapshots", help="Minimum snapshots to keep"),
    ] = 1,
    max_tier: Annotated[
        int,
        typer.Option("--max-tier", help="Maximum storage tier"),
    ] = 1,
    skip_missed: Annotated[
        bool,
        typer.Option("--skip-missed", help="Skip missed snapshot windows"),
    ] = False,
) -> None:
    """Create a period in a snapshot profile.

    Examples:

        # Hourly firing at :00, retained 24h, keep at least 2
        vrg snapshot profile period create webservers \\
          --name Hourly --frequency hourly --retention 86400 --min-snapshots 2

        # Weekly Sunday at 03:00, retained 30 days
        vrg snapshot profile period create webservers \\
          --name Weekly --frequency weekly --retention 2592000 \\
          --day-of-week sun --hour 3 --minute 0

        # Monthly immutable period on the 1st at 04:00
        vrg snapshot profile period create compliance \\
          --name Monthly --frequency monthly --retention 31536000 \\
          --day-of-month 1 --hour 4 --immutable

    `retention` is in seconds (0 = never expires). `quiesce` and
    `max_tier` apply only to VM / NAS volume snapshot profiles;
    `immutable` applies only to system snapshot profiles. Fields that
    don't apply to the chosen frequency are forced to defaults.
    """
    vctx, profile_key = _get_profile(ctx, profile)
    period_mgr = vctx.client.snapshot_profiles.periods(profile_key)

    result = period_mgr.create(
        name=name,
        frequency=frequency,
        retention=retention,
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        quiesce=quiesce,
        immutable=immutable,
        min_snapshots=min_snapshots,
        max_tier=max_tier,
        skip_missed=skip_missed,
    )

    period_name = result.name if result else name
    period_key = result.key if result else "?"
    output_success(
        f"Created period '{period_name}' (key: {period_key})",
        quiet=vctx.quiet,
    )


@app.command("update")
@handle_errors()
def period_update(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    period: Annotated[str, typer.Argument(help="Period name or key")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New period name")] = None,
    frequency: Annotated[
        str | None,
        typer.Option("--frequency", "-f", help="New frequency"),
    ] = None,
    retention: Annotated[
        int | None,
        typer.Option("--retention", help="Retention in seconds"),
    ] = None,
    minute: Annotated[
        int | None, typer.Option("--minute", help="Minute of the hour (0-59)")
    ] = None,
    hour: Annotated[int | None, typer.Option("--hour", help="Hour of the day (0-23)")] = None,
    day_of_week: Annotated[
        str | None,
        typer.Option("--day-of-week", help="Day of week"),
    ] = None,
    day_of_month: Annotated[
        int | None,
        typer.Option("--day-of-month", help="Day of the month (0-31)"),
    ] = None,
    quiesce: Annotated[
        bool | None,
        typer.Option("--quiesce/--no-quiesce", help="Quiesce filesystem"),
    ] = None,
    immutable: Annotated[
        bool | None,
        typer.Option("--immutable/--no-immutable", help="Make snapshots immutable"),
    ] = None,
    min_snapshots: Annotated[
        int | None,
        typer.Option("--min-snapshots", help="Minimum snapshots to keep"),
    ] = None,
    max_tier: Annotated[
        int | None,
        typer.Option("--max-tier", help="Maximum storage tier"),
    ] = None,
    skip_missed: Annotated[
        bool | None,
        typer.Option("--skip-missed/--no-skip-missed", help="Skip missed windows"),
    ] = None,
) -> None:
    """Update a snapshot profile period.

    Examples:

        # Enable quiesce on an existing daily period
        vrg snapshot profile period update webservers Daily --quiesce

        # Extend retention to 60 days
        vrg snapshot profile period update webservers Weekly --retention 5184000

        # Move the weekly period to Saturday at 02:30
        vrg snapshot profile period update webservers Weekly \\
          --day-of-week sat --hour 2 --minute 30

    Only fields supplied are updated. If no options are given the command
    exits 2. Period name collisions exit 7 — use the numeric `$key` to
    disambiguate.
    """
    vctx, profile_key = _get_profile(ctx, profile)
    period_mgr = vctx.client.snapshot_profiles.periods(profile_key)
    period_key = _resolve_period(period_mgr, period)

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if frequency is not None:
        kwargs["frequency"] = frequency
    if retention is not None:
        kwargs["retention"] = retention
    if minute is not None:
        kwargs["minute"] = minute
    if hour is not None:
        kwargs["hour"] = hour
    if day_of_week is not None:
        kwargs["day_of_week"] = day_of_week
    if day_of_month is not None:
        kwargs["day_of_month"] = day_of_month
    if quiesce is not None:
        kwargs["quiesce"] = quiesce
    if immutable is not None:
        kwargs["immutable"] = immutable
    if min_snapshots is not None:
        kwargs["min_snapshots"] = min_snapshots
    if max_tier is not None:
        kwargs["max_tier"] = max_tier
    if skip_missed is not None:
        kwargs["skip_missed"] = skip_missed

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    period_mgr.update(period_key, **kwargs)
    output_success(f"Updated period '{period}'", quiet=vctx.quiet)


@app.command("delete")
@handle_errors()
def period_delete(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile name or key")],
    period: Annotated[str, typer.Argument(help="Period name or key")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Delete a snapshot profile period.

    Examples:

        vrg snapshot profile period delete webservers Hourly --yes
        vrg snapshot profile period delete webservers 12

    This is a destructive operation. Deleting a period stops future
    firings but does not delete snapshots already captured by it.
    Ambiguous period names exit 7.
    """
    vctx, profile_key = _get_profile(ctx, profile)
    period_mgr = vctx.client.snapshot_profiles.periods(profile_key)
    period_key = _resolve_period(period_mgr, period)

    if not confirm_action(f"Delete period '{period}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    period_mgr.delete(period_key)
    output_success(f"Deleted period '{period}'", quiet=vctx.quiet)
