"""Shared helpers for async query commands (network, node, service container, tenant node)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.status import Status

from verge_cli.errors import CliError
from verge_cli.output import output_result

if TYPE_CHECKING:
    from pyvergeos.resources.queries import (
        QueryManager,
        QueryResult,
    )


def run_query(
    query_manager: QueryManager,
    query_type: str,
    params: dict[str, Any] | None = None,
    timeout: float = 120,
    quiet: bool = False,
    label: str = "Running query...",
) -> QueryResult:
    """Submit an async query and wait for completion with a spinner.

    Args:
        query_manager: Any QueryManager subclass (VNet, Node, etc.).
        query_type: Query type string (e.g. "ping", "tcpdump").
        params: Query parameters dict.
        timeout: Max seconds to wait.
        quiet: If True, skip the spinner.
        label: Spinner text (e.g. "Running ping...").

    Returns:
        Completed QueryResult.

    Raises:
        CliError: If the query returns an error status.
        VergeTimeoutError: Propagated from SDK if query times out.
    """
    if quiet:
        result = query_manager.run(query_type, params, timeout=timeout)
    else:
        console = Console(stderr=True)
        with Status(label, console=console, spinner="dots"):
            result = query_manager.run(query_type, params, timeout=timeout)

    if result.is_error:
        raise CliError(result.result or f"Query '{query_type}' failed")

    return result


def output_query_result(
    result: QueryResult,
    output_format: str = "table",
    query: str | None = None,
    quiet: bool = False,
    no_color: bool = False,
) -> None:
    """Display query result in the requested format.

    Default/table format prints the raw result text (command output like
    ping, traceroute, etc.). JSON format emits a structured dict.

    Args:
        result: Completed QueryResult.
        output_format: Output format ("table", "json", etc.).
        query: Optional dot-notation query for field extraction.
        quiet: If True, print only the result text.
        no_color: Disable colored output.
    """
    if quiet:
        if result.result:
            print(result.result)
        return

    if output_format == "json":
        data = {
            "query_type": result.query_type,
            "status": result.status,
            "result": result.result,
            "command": result.command,
            "key": result.key,
        }
        output_result(
            data,
            output_format="json",
            query=query,
            no_color=no_color,
        )
        return

    # Default: print the result text directly
    console = Console(no_color=no_color)
    if result.result:
        console.print(result.result, highlight=False)
