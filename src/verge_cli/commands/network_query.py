"""Network query commands for Verge CLI."""

from __future__ import annotations

import json as json_mod
from typing import Annotated, Any

import typer

from verge_cli.commands._query_helpers import output_query_result, run_query
from verge_cli.context import get_context
from verge_cli.errors import CliError, handle_errors
from verge_cli.utils import resolve_resource_id

app = typer.Typer(
    name="query",
    help="Run diagnostic queries on a network.",
    no_args_is_help=True,
)


@app.command("ping")
@handle_errors()
def query_ping(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    target: Annotated[str, typer.Argument(help="Target host or IP address")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Ping a host from a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "ping",
        {"host": target},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Running ping to {target}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("dns")
@handle_errors()
def query_dns(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    name: Annotated[str, typer.Argument(help="Hostname to resolve")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Resolve a DNS name from a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "dns",
        {"name": name},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Resolving {name}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("traceroute")
@handle_errors()
def query_traceroute(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    target: Annotated[str, typer.Argument(help="Target host or IP address")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 60,
) -> None:
    """Trace route to a host from a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "traceroute",
        {"host": target},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Running traceroute to {target}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("tcpdump")
@handle_errors()
def query_tcpdump(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    interface: Annotated[
        str | None,
        typer.Option("--interface", "-i", help="Network interface to capture on."),
    ] = None,
    count: Annotated[
        int | None,
        typer.Option("--count", "-c", help="Number of packets to capture."),
    ] = None,
    filter: Annotated[
        str | None,
        typer.Option("--filter", "-f", help="BPF filter expression."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 120,
) -> None:
    """Capture packets on a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    params: dict[str, Any] = {}
    if interface is not None:
        params["interface"] = interface
    if count is not None:
        params["count"] = count
    if filter is not None:
        params["filter"] = filter

    result = run_query(
        net_obj.queries,
        "tcpdump",
        params or None,
        timeout=timeout,
        quiet=vctx.quiet,
        label="Capturing packets...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("arp")
@handle_errors()
def query_arp(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show ARP table for a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "arp",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Fetching ARP table...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("arp-scan")
@handle_errors()
def query_arp_scan(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Scan for hosts via ARP on a network."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "arp-scan",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Running ARP scan...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("firewall")
@handle_errors()
def query_firewall(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show nftables firewall rules for a network."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "firewall",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Fetching firewall rules...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("trace")
@handle_errors()
def query_trace(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Run nftables packet trace on a network."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "trace",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Running packet trace...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("nmap")
@handle_errors()
def query_nmap(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    target: Annotated[str, typer.Argument(help="Target host, IP, or CIDR range")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 120,
) -> None:
    """Run nmap scan from a network's virtual router."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "nmap",
        {"host": target},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Running nmap scan on {target}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("tcp-connect")
@handle_errors()
def query_tcp_connect(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    host: Annotated[str, typer.Argument(help="Target host or IP address")],
    port: Annotated[int, typer.Argument(help="Target port number")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Test TCP connectivity to a host and port from a network."""
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    result = run_query(
        net_obj.queries,
        "tcp_connect",
        {"host": host, "port": port},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Testing TCP connection to {host}:{port}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("run")
@handle_errors()
def query_run(
    ctx: typer.Context,
    network: Annotated[str, typer.Argument(help="Network name or key")],
    query_type: Annotated[str, typer.Argument(help="Query type (e.g. ip, logs, top, frr)")],
    params: Annotated[
        str | None,
        typer.Option("--params", "-p", help="Query parameters as JSON object."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 120,
) -> None:
    """Run an arbitrary query type on a network.

    Escape hatch for query types without dedicated commands (ip, logs,
    top, top_if, ipsec, whatsmyip, frr, dhcp_release_renew, wireguard).
    """
    vctx = get_context(ctx)
    net_key = resolve_resource_id(vctx.client.networks, network, "network")
    net_obj = vctx.client.networks.get(net_key)

    parsed_params: dict[str, Any] | None = None
    if params:
        try:
            parsed_params = json_mod.loads(params)
        except json_mod.JSONDecodeError as e:
            raise CliError(f"Invalid JSON for --params: {e}") from e

    result = run_query(
        net_obj.queries,
        query_type,
        parsed_params,
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Running {query_type}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
