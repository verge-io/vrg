"""Multi-profile operations for Verge CLI.

Supports running list commands across all configured profiles,
aggregating results with a profile column.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

from verge_cli.auth import get_client
from verge_cli.columns import ColumnDef
from verge_cli.config import apply_env_overrides, load_config
from verge_cli.output import output_result

PROFILE_COLUMN = ColumnDef("_profile", header="Profile", default_style="cyan")


def list_all_profiles(
    ctx: typer.Context,
    fetch_fn: Callable[..., list[Any]],
    to_dict_fn: Callable[[Any], dict[str, Any]],
    columns: list[ColumnDef],
) -> None:
    """Run a list operation across all configured profiles.

    Creates a client for each profile, calls fetch_fn to get resources,
    converts each with to_dict_fn, and outputs aggregated results with
    a profile column prepended.

    Args:
        ctx: Typer context with output settings in ctx.obj.
        fetch_fn: Callable that takes a VergeClient and returns list of resources.
        to_dict_fn: Callable that converts a resource to an output dict.
        columns: Column definitions for the resource type.
    """
    obj = ctx.obj
    config = load_config()
    console = Console(stderr=True)

    # Collect all profile names
    profile_names: list[str] = ["default"]
    profile_names.extend(sorted(config.profiles.keys()))

    all_data: list[dict[str, Any]] = []
    errors: list[tuple[str, str]] = []

    for name in profile_names:
        profile_config = config.get_profile(name)
        profile_config = apply_env_overrides(profile_config)

        if not profile_config.host:
            errors.append((name, "no host configured"))
            continue

        try:
            client = get_client(profile_config)
            items = fetch_fn(client)
            for item in items:
                row = to_dict_fn(item)
                row["_profile"] = name
                all_data.append(row)
        except typer.Exit:
            errors.append((name, "authentication or connection failed"))
        except Exception as e:
            errors.append((name, str(e)))

    # Report errors to stderr
    if errors and not obj.get("quiet"):
        for name, msg in errors:
            console.print(f"[yellow]Warning:[/yellow] profile '{name}': {msg}")

    # Prepend profile column
    output_columns = [PROFILE_COLUMN, *columns]

    output_result(
        all_data,
        output_format=obj["output_format"],
        query=obj["query"],
        columns=output_columns,
        quiet=obj["quiet"],
        no_color=obj["no_color"],
    )
