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
    help=(
        "Inspect VergeOS vSAN storage tiers.\n\n"
        "VergeOS pools every physical drive across cluster nodes into a single"
        " vSAN, partitioned into **tiers 0-5** by performance class. Tier 0"
        " holds vSAN metadata; tiers 1-5 hold user data, typically ordered"
        " from fastest (NVMe) to slowest (archive HDD). VM drives and NAS"
        " volumes target a **preferred tier**; vSAN places data there when"
        " capacity allows and falls back to the next available tier otherwise."
        " Deduplication, redundancy, and repair run automatically per tier.\n\n"
        "This group is read-only — tiers are defined by node hardware and"
        " installation parameters, not by CLI commands. Use `-o json` with"
        " `list`, `get`, or `summary` to surface the raw tier metrics"
        " (`capacity_gb`, `used_gb`, `free_gb`, `used_percent`, `dedupe_ratio`,"
        " `read_ops`, `write_ops`) for monitoring or capacity planning.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every storage tier with utilization\n"
        "    vrg storage list\n\n"
        "    # Fetch tier 1 details as JSON\n"
        "    vrg -o json storage get 1\n\n"
        "    # Aggregate capacity across all tiers\n"
        "    vrg storage summary\n\n"
        "    # Extract just the free space per tier for scripting\n"
        "    vrg -o json storage list --query '[].{tier: tier, free_gb: free_gb}'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Tier 0 is reserved for vSAN metadata and is not a target for VM"
        " drives or NAS volumes. Use tier numbers 1-5 when configuring drive"
        " placement via `vrg vm drive create --tier N`.\n\n"
        "`used_percent` reflects actual physical usage. VergeOS supports thin"
        " provisioning, so allocated capacity may exceed physical usage — key"
        " on `used_percent` and `free_gb` for alarm thresholds rather than"
        " allocation totals."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
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
    """List all storage tiers.

    Examples:

        vrg storage list
        vrg -o json storage list
        vrg -o json storage list --query "[].{tier: tier, free_gb: free_gb}"

    Use `-A` / `--all-profiles` to fan out across every configured profile.
    """
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
    """Get details of a storage tier.

    Examples:

        vrg storage get 1
        vrg -o json storage get 2
        vrg -o json storage get 1 --query "{used: used_percent, free: free_gb}"

    Numeric arguments are treated as tier numbers (0-5); non-numeric values
    are resolved by name and exit 7 on ambiguous matches.
    """
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
    """Show aggregate storage summary across all tiers.

    Examples:

        vrg storage summary
        vrg -o json storage summary
        vrg -o json storage summary --query "{total: capacity_gb, free: free_gb}"

    Totals capacity, usage, and dedupe figures across every tier in the vSAN.
    """
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
