"""Storage tier management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import STORAGE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="storage",
    help="Manage storage tiers.",
    no_args_is_help=True,
)


def _tier_to_dict(tier: Any) -> dict[str, Any]:
    """Convert a StorageTier object to a dict for output.

    Uses SDK property access for computed fields (capacity_gb, used_gb, etc.)
    since the raw .get() only returns raw API fields like 'capacity' (bytes).
    """
    return {
        "$key": tier.key,
        "tier": tier.tier,
        "description": tier.description,
        "capacity_gb": tier.capacity_gb,
        "used_gb": tier.used_gb,
        "free_gb": tier.free_gb,
        "used_percent": tier.used_percent,
        "dedupe_ratio": tier.dedupe_ratio,
        "dedupe_savings_percent": tier.dedupe_savings_percent,
        "read_ops": tier.read_ops,
        "write_ops": tier.write_ops,
    }


@app.command("list")
@handle_errors()
def storage_list(
    ctx: typer.Context,
) -> None:
    """List all storage tiers."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.storage_tiers.list(), _tier_to_dict, STORAGE_COLUMNS
        )
        return
    vctx = get_context(ctx)

    tiers = vctx.client.storage_tiers.list()
    data = [_tier_to_dict(t) for t in tiers]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=STORAGE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def storage_get(
    ctx: typer.Context,
    tier: Annotated[str, typer.Argument(help="Storage tier number or key")],
) -> None:
    """Get details of a storage tier."""
    vctx = get_context(ctx)

    # Storage tiers are identified by tier number (0-5).
    # If the identifier is numeric, use the tier= keyword for reliable lookup.
    if tier.isdigit():
        tier_obj = vctx.client.storage_tiers.get(tier=int(tier))
    else:
        key = resolve_resource_id(vctx.client.storage_tiers, tier, "Storage tier")
        tier_obj = vctx.client.storage_tiers.get(key)

    output_result(
        _tier_to_dict(tier_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("summary")
@handle_errors()
def storage_summary(
    ctx: typer.Context,
) -> None:
    """Show aggregate storage summary across all tiers."""
    vctx = get_context(ctx)

    summary = vctx.client.storage_tiers.get_summary()

    # Summary returns a dict or dict-like object
    if isinstance(summary, dict):
        data = summary
    else:
        data = dict(summary) if hasattr(summary, "__iter__") else {"result": str(summary)}

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
