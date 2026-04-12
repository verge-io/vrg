"""Billing and usage report commands."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="billing",
    help="Billing and usage reports.",
    no_args_is_help=True,
)

BILLING_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("created", header="Created", format_fn=format_epoch),
    ColumnDef("from", header="From", format_fn=format_epoch),
    ColumnDef("to", header="To", format_fn=format_epoch),
    ColumnDef("used_cores", header="Used Cores"),
    ColumnDef("total_cores", header="Total Cores"),
    ColumnDef("running_machines", header="Running VMs"),
    ColumnDef("used_ram_gb", header="Used RAM (GB)"),
    ColumnDef("total_ram_gb", header="Total RAM (GB)"),
    ColumnDef("total_storage_used_gb", header="Storage Used (GB)", wide_only=True),
    ColumnDef("total_storage_total_gb", header="Storage Total (GB)", wide_only=True),
    ColumnDef("online_nodes", header="Online Nodes", wide_only=True),
    ColumnDef("description", wide_only=True),
]

SUMMARY_COLUMNS: list[ColumnDef] = [
    ColumnDef("record_count", header="Records"),
    ColumnDef("avg_cpu_utilization", header="Avg CPU %"),
    ColumnDef("peak_cpu_cores", header="Peak CPU Cores"),
    ColumnDef("avg_ram_utilization", header="Avg RAM %"),
    ColumnDef("peak_ram_gb", header="Peak RAM (GB)"),
    ColumnDef("avg_storage_used_gb", header="Avg Storage (GB)"),
    ColumnDef("peak_storage_used_gb", header="Peak Storage (GB)"),
]


def _parse_datetime(value: str) -> int:
    """Parse an ISO datetime string to epoch int.

    Accepts "2026-01-01" or "2026-01-01T00:00:00".
    """
    dt = datetime.fromisoformat(value)
    return int(dt.timestamp())


def _billing_to_dict(record: Any) -> dict[str, Any]:
    """Convert SDK BillingRecord to output dict."""
    return {
        "$key": int(record.key),
        "created": record.created_epoch,
        "from": record.from_epoch,
        "to": record.to_epoch,
        "used_cores": record.used_cores,
        "total_cores": record.total_cores,
        "online_nodes": record.online_nodes,
        "running_machines": record.running_machines,
        "used_ram_gb": record.used_ram_gb,
        "total_ram_gb": record.total_ram_gb,
        "total_storage_used_gb": record.total_storage_used_gb,
        "total_storage_total_gb": record.total_storage_total_gb,
        "description": record.description,
    }


def _summary_to_dict(summary: Any) -> dict[str, Any]:
    """Convert SDK billing summary to output dict.

    The SDK returns a plain dict for summaries.
    """
    if isinstance(summary, dict):
        return {
            k: summary.get(k)
            for k in (
                "record_count",
                "avg_cpu_utilization",
                "peak_cpu_cores",
                "avg_ram_utilization",
                "peak_ram_gb",
                "avg_storage_used_gb",
                "peak_storage_used_gb",
            )
        }
    return {
        "record_count": summary.record_count,
        "avg_cpu_utilization": summary.avg_cpu_utilization,
        "peak_cpu_cores": summary.peak_cpu_cores,
        "avg_ram_utilization": summary.avg_ram_utilization,
        "peak_ram_gb": summary.peak_ram_gb,
        "avg_storage_used_gb": summary.avg_storage_used_gb,
        "peak_storage_used_gb": summary.peak_storage_used_gb,
    }


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Start date (ISO format, e.g. 2026-01-01).",
        ),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option(
            "--until",
            help="End date (ISO format, e.g. 2026-02-01).",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = None,
) -> None:
    """List billing records."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.billing.list(), _billing_to_dict, BILLING_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if since is not None:
        kwargs["since"] = _parse_datetime(since)
    if until is not None:
        kwargs["until"] = _parse_datetime(until)
    if limit is not None:
        kwargs["limit"] = limit

    records = vctx.client.billing.list(**kwargs)

    output_result(
        [_billing_to_dict(r) for r in records],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=BILLING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def get(
    ctx: typer.Context,
    key: Annotated[
        int,
        typer.Argument(help="Billing record key (numeric ID)."),
    ],
) -> None:
    """Get a billing record by key."""
    vctx = get_context(ctx)
    record = vctx.client.billing.get(key)

    output_result(
        _billing_to_dict(record),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=BILLING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def generate(
    ctx: typer.Context,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt.",
        ),
    ] = False,
) -> None:
    """Generate a new billing record."""
    if not confirm_action("Generate a new billing record?", yes=yes):
        return

    vctx = get_context(ctx)
    vctx.client.billing.generate()
    output_success(
        "Billing record generated.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def latest(
    ctx: typer.Context,
) -> None:
    """Get the most recent billing record."""
    vctx = get_context(ctx)
    record = vctx.client.billing.get_latest()

    output_result(
        _billing_to_dict(record),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=BILLING_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def summary(
    ctx: typer.Context,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            help="Start date (ISO format, e.g. 2026-01-01).",
        ),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option(
            "--until",
            help="End date (ISO format, e.g. 2026-02-01).",
        ),
    ] = None,
) -> None:
    """Show billing usage summary."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if since is not None:
        kwargs["since"] = _parse_datetime(since)
    if until is not None:
        kwargs["until"] = _parse_datetime(until)

    data = vctx.client.billing.get_summary(**kwargs)

    output_result(
        _summary_to_dict(data),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=SUMMARY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
