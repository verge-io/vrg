"""Node query commands for Verge CLI."""

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
    help=(
        "Run live diagnostic queries **on** a node — network probes, drive"
        " SMART, hardware inventory, IPMI/BMC readings, and an escape hatch"
        " for anything else the node agent exposes.\n\n"
        "Each subcommand tells the target node to execute a specific probe"
        " (`ping`, `smartctl`, `ipmi-sensor`, etc.) and streams the result"
        " back. The work happens on the node itself, so answers reflect"
        " that node's real kernel, NICs, drives, and baseboard — not the"
        " controller running `vrg`. Use this when a node is misbehaving"
        " and you want to reach into it without SSH.\n\n"
        "Queries are grouped by purpose:\n\n"
        "- **Network** — `ping`, `dns`, `traceroute`, `arp`, `arp-scan`,"
        " `tcpdump`. Run these from a node's perspective to prove where"
        " isolation starts.\n"
        "- **Storage** — `smartctl` (read SMART attributes), `smartctl-test`"
        " (start a self-test), `lsblk` (enumerate block devices).\n"
        "- **Hardware** — `dmidecode` for SMBIOS/DMI inventory (DIMM slots,"
        " board, chassis serials).\n"
        "- **IPMI / BMC** — `ipmi-sensor` (temps, fans, voltages), `ipmi-sel`"
        " (System Event Log), `ipmi-fru` (Field Replaceable Unit data),"
        " `ipmi-lan` (BMC network config), `ipmi-chassis` (power/intrusion"
        " state).\n"
        "- **Escape hatch** — `run <query_type>` for query types without a"
        " dedicated subcommand (e.g. `ip`, `bridge`, `top`, `top_if`,"
        " `logs`, `whatsmyip`, `eth-tool`, `fabric`, `bonding`).\n\n"
        "Every query takes a **node** (name or numeric key) as its first"
        " argument and a `--timeout` in seconds. Default timeouts vary by"
        " query type (30s for quick reads, 60s for SMART, 120s for"
        " tcpdump).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Network: prove node1 can reach a gateway\n"
        "    vrg node query ping node1 10.0.0.1\n"
        "    vrg node query traceroute node1 8.8.8.8\n"
        "    vrg node query dns node1 example.com\n\n"
        "    # Capture 50 packets on a specific interface with a BPF filter\n"
        "    vrg node query tcpdump node1 -i eth0 -c 50 -f 'port 443'\n\n"
        "    # Storage: SMART health for a specific drive\n"
        "    vrg node query smartctl node1 /dev/sda\n"
        "    vrg node query smartctl-test node1 /dev/sda\n"
        "    vrg node query lsblk node1\n\n"
        "    # Hardware and BMC\n"
        "    vrg node query dmidecode node1\n"
        "    vrg node query ipmi-sensor node1\n"
        "    vrg node query ipmi-sel node1\n\n"
        "    # Escape hatch with structured params\n"
        '    vrg node query run node1 ip --params \'{"cmd": "addr"}\'\n\n'
        "    # JSON output for scripts and agents\n"
        "    vrg -o json node query ipmi-sensor node1\n"
        "    vrg -o json node query smartctl node1 /dev/sda --query 'smart_status'\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The node argument is resolved by name or numeric key. Ambiguous"
        " names exit 7 — pass the numeric key to disambiguate.\n\n"
        "Queries are synchronous: `vrg` blocks until the node returns a"
        " result or `--timeout` elapses. Raise `--timeout` for slow"
        " hardware (long SMART extended tests, large packet captures)."
        " A timed-out query exits 9.\n\n"
        "Result shape varies by query type — most return a JSON object"
        " that `--query` (JMESPath) and `-o json` can pick apart. Use"
        " `run` to reach query types that do not have a dedicated"
        " subcommand; pass query-specific parameters as a JSON object via"
        " `--params`.\n\n"
        "IPMI subcommands only return data on nodes with a reachable BMC"
        " and correctly configured IPMI credentials. A blank `ipmi-lan`"
        " result usually means the node has no BMC or the BMC is on a"
        " segregated management network the node cannot reach."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@app.command("ping")
@handle_errors()
def query_ping(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    target: Annotated[str, typer.Argument(help="Target host or IP address")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Ping a host from a node.

    Examples:

        vrg node query ping node1 10.0.0.1
        vrg node query ping node1 example.com --timeout 10
        vrg -o json node query ping node1 8.8.8.8

    Proves reachability from the node's own network stack — not the
    controller. Exits 9 on timeout.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
    name: Annotated[str, typer.Argument(help="Hostname to resolve")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Resolve a DNS name from a node.

    Examples:

        vrg node query dns node1 example.com
        vrg -o json node query dns node1 my-tenant.internal

    Uses the node's configured resolver — useful when confirming whether
    a tenant vNet's DNS is reaching the right nameserver.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
    target: Annotated[str, typer.Argument(help="Target host or IP address")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 60,
) -> None:
    """Trace route to a host from a node.

    Examples:

        vrg node query traceroute node1 8.8.8.8
        vrg node query traceroute node1 my-vm.tenant --timeout 90

    Default timeout 60s — raise for long paths or slow intermediate hops.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
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
    """Capture packets on a node.

    Examples:

        # Capture 50 HTTPS packets on eth0
        vrg node query tcpdump node1 -i eth0 -c 50 -f 'port 443'

        # Watch broadcast storms on the vSAN fabric
        vrg node query tcpdump node1 -i fabric0 -f 'broadcast' --timeout 30

        # JSON for automated diff
        vrg -o json node query tcpdump node1 -c 100

    Synchronous — `vrg` blocks until the capture completes or `--timeout`
    (default 120s) elapses. Exits 9 on timeout.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    params: dict[str, Any] = {}
    if interface is not None:
        params["interface"] = interface
    if count is not None:
        params["count"] = count
    if filter is not None:
        params["filter"] = filter

    result = run_query(
        node_obj.queries,
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show ARP table for a node.

    Examples:

        vrg node query arp node1
        vrg -o json node query arp node1 | jq '.[] | select(.state == "REACHABLE")'

    Snapshot of the node's L2 neighbor table. Use `arp-scan` to actively
    probe for unknown peers.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Scan for hosts via ARP from a node.

    Examples:

        vrg node query arp-scan node1
        vrg -o json node query arp-scan node1

    Active probe — sends ARP requests on the node's connected segments and
    reports responding IPs/MACs. Useful for finding unknown devices or
    confirming a VM's NIC is answering ARP.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
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


@app.command("smartctl")
@handle_errors()
def query_smartctl(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    device: Annotated[str, typer.Argument(help="Device path (e.g. /dev/sda)")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 60,
) -> None:
    """Show SMART health and attributes for a drive.

    Examples:

        vrg node query smartctl node1 /dev/sda
        vrg -o json node query smartctl node1 /dev/sda --query smart_status

    Reads the drive's SMART attributes from the node. Non-SMART-capable
    devices (some NVMe namespaces, USB-attached disks) may return empty.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "smartctl",
        {"path": device},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Reading SMART data for {device}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("smartctl-test")
@handle_errors()
def query_smartctl_test(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    device: Annotated[str, typer.Argument(help="Device path (e.g. /dev/sda)")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 60,
) -> None:
    """Initiate a SMART self-test on a drive.

    Examples:

        vrg node query smartctl-test node1 /dev/sda

    Starts the self-test in the background on the node — the command
    returns once the test is launched. Poll with `smartctl` to read
    progress and final status.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "smartctl-test",
        {"path": device},
        timeout=timeout,
        quiet=vctx.quiet,
        label=f"Starting SMART test on {device}...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("lsblk")
@handle_errors()
def query_lsblk(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """List block devices on a node.

    Examples:

        vrg node query lsblk node1
        vrg -o json node query lsblk node1

    Enumerates drives, partitions, and mountpoints from the node's
    perspective — the canonical way to discover device paths before
    running `smartctl`.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "lsblk",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Listing block devices...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("dmidecode")
@handle_errors()
def query_dmidecode(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show DMI/SMBIOS hardware information for a node.

    Examples:

        vrg node query dmidecode node1
        vrg -o json node query dmidecode node1 --query baseboard

    Reads SMBIOS tables: chassis serial, motherboard, DIMM slots and
    populations, BIOS version. Useful for hardware audits and RMA
    paperwork without SSH access.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "dmidecode",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading hardware info...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipmi-sensor")
@handle_errors()
def query_ipmi_sensor(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show IPMI sensor readings for a node.

    Examples:

        vrg node query ipmi-sensor node1
        vrg -o json node query ipmi-sensor node1 | jq '.[] | select(.name | contains("Temp"))'

    Live temperatures, fan speeds, and voltages from the BMC. Empty
    output usually means no reachable BMC or missing IPMI credentials.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "ipmi-sensor",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading IPMI sensors...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipmi-sel")
@handle_errors()
def query_ipmi_sel(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show IPMI System Event Log for a node.

    Examples:

        vrg node query ipmi-sel node1
        vrg -o json node query ipmi-sel node1 | jq '.[] | select(.severity == "critical")'

    BMC-persisted event history: thermal events, ECC errors, power
    transitions. Clear it through the BMC interface, not this CLI.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "ipmi-sel",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading IPMI event log...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipmi-fru")
@handle_errors()
def query_ipmi_fru(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show IPMI FRU (Field Replaceable Unit) data for a node.

    Examples:

        vrg node query ipmi-fru node1
        vrg -o json node query ipmi-fru node1

    Chassis, product, and board serial/part numbers from the BMC's FRU
    inventory. Cross-reference with `dmidecode` when diagnosing labeling
    mismatches.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "ipmi-fru",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading IPMI FRU data...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipmi-lan")
@handle_errors()
def query_ipmi_lan(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show IPMI LAN configuration for a node.

    Examples:

        vrg node query ipmi-lan node1
        vrg -o json node query ipmi-lan node1 --query ip_address

    BMC network settings (IP, netmask, gateway, VLAN). A blank result
    usually means the BMC is on a segregated management network the node
    cannot reach from its own OS.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "ipmi-lan",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading IPMI LAN config...",
    )

    output_query_result(
        result,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("ipmi-chassis")
@handle_errors()
def query_ipmi_chassis(
    ctx: typer.Context,
    node: Annotated[str, typer.Argument(help="Node name or key")],
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 30,
) -> None:
    """Show IPMI chassis status for a node.

    Examples:

        vrg node query ipmi-chassis node1
        vrg -o json node query ipmi-chassis node1 --query power_state

    Power state, front panel LEDs, chassis intrusion, and restore policy
    as reported by the BMC.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    result = run_query(
        node_obj.queries,
        "ipmi-chassis",
        timeout=timeout,
        quiet=vctx.quiet,
        label="Reading IPMI chassis status...",
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
    node: Annotated[str, typer.Argument(help="Node name or key")],
    query_type: Annotated[str, typer.Argument(help="Query type (e.g. ip, bridge, top, logs)")],
    params: Annotated[
        str | None,
        typer.Option("--params", "-p", help="Query parameters as JSON object."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", help="Max seconds to wait for result."),
    ] = 120,
) -> None:
    """Run an arbitrary query type on a node.

    Escape hatch for query types without dedicated commands (ip, bridge,
    top, top_if, logs, whatsmyip, eth-tool, fabric, bonding, etc.).

    Examples:

        # Show IP addresses via `ip addr`
        vrg node query run node1 ip --params '{"cmd": "addr"}'

        # Live top view of the node's userspace
        vrg node query run node1 top --timeout 60

        # Bond status for vSAN fabric
        vrg node query run node1 bonding

        # Tail node logs
        vrg node query run node1 logs --params '{"service": "vsand"}'

    Pass query-specific parameters as a JSON object via `--params`.
    Invalid JSON exits 8. Timed-out queries exit 9.
    """
    vctx = get_context(ctx)
    node_key = resolve_resource_id(vctx.client.nodes, node, "node")
    node_obj = vctx.client.nodes.get(node_key)

    parsed_params: dict[str, Any] | None = None
    if params:
        try:
            parsed_params = json_mod.loads(params)
        except json_mod.JSONDecodeError as e:
            raise CliError(f"Invalid JSON for --params: {e}") from e

    result = run_query(
        node_obj.queries,
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
