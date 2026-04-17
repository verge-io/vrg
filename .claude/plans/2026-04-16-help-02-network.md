# Help Text Improvement: `vrg network`

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Network command group and all subcommands (network, rule, dns, host, alias, diag, query, dashboard)
**Depends on:** help-00-root (must be done first to enable `rich_markup_mode="markdown"` on the main app)

---

## Conventions (apply to all help text in this plan)

### Where help text lives

- **Group apps** (`typer.Typer()`): Help goes in the `help=` parameter. The callback docstring is ignored when `help=` is set — keep callback docstrings to one line (e.g., `"""Manage virtual machines."""`).
- **Leaf commands** (`@app.command()`): Help comes from the function docstring. This is the only place Typer reads it.
- Every `typer.Typer()` must have `rich_markup_mode="markdown"` so markdown renders in terminal output.

### Section order for group `help=` strings

1. **Description** (1-3 sentences): What this resource is in VergeOS and why it matters. Not just "Manage X."
2. **Agent guidance** (1-2 sentences): Which flags produce machine-readable output, what fields are useful to `--query`, any gotchas.
3. **Examples** (3-6 invocations): Real commands showing common workflows. Use `---` markdown separator before and after.
4. **Notes** (optional): Behavioral quirks, ordering of operations, required preconditions.

### Section order for leaf command docstrings

1. **One-line summary** (what the command does).
2. **1-3 examples** showing invocation with typical arguments.
3. **Behavioral note** (optional): e.g., "This is a destructive operation" or "Requires the VM to be stopped."

### Quality bar

- Examples must use realistic resource names (e.g., `web-01`, `internal-net`, `tier-2`), not placeholders like `<name>`.
- Every group must mention `-o json` for structured output somewhere.
- Exit code 7 (multiple matches) should be mentioned where name resolution applies.
- Match the voice of showboat/tracecc: plain English, no filler, designed for agents to parse.

### Commit discipline

Make atomic commits as you go — one commit per logical unit of work (e.g., one
subgroup file complete, or all leaf docstrings in a file). Do not batch all
changes into a single commit at the end. Run tests before each commit.

## Overview

Networking in VergeOS is software-defined — every virtual network is actually an LXC container running in its own network namespace with built-in routing, firewall, DHCP, and DNS. This is non-obvious and critical for agents to understand. Currently the help just says "Manage virtual networks."

## What VergeOS networks are (source from docs)

A VergeOS virtual network (vNet) is a software-defined Layer 3 network with integrated firewall (nftables), DHCP, DNS, and routing. Network types include internal (workload isolation), external (physical uplink), core (inter-network routing), and DMZ. Firewall rules must be explicitly applied after creation with `apply-rules`. DNS changes require `apply-dns`.

## Source files to modify

| File | Current help |
|------|-------------|
| `commands/network.py` | "Manage virtual networks." |
| `commands/network_rule.py` | "Manage network firewall rules." |
| `commands/network_dns.py` | "Manage DNS zones and records." |
| `commands/network_host.py` | "Manage network DNS/DHCP host overrides." |
| `commands/network_alias.py` | "Manage network IP aliases." |
| `commands/network_diag.py` | "Network diagnostics and statistics." |
| `commands/network_query.py` | "Run diagnostic queries on a network." |
| `commands/network_dashboard.py` | "Network dashboard." (or similar) |

## Examples to include

```
# List all networks
vrg network list

# Get network details
vrg -o json network get internal-prod

# Create an internal network
vrg network create --name app-tier --network 10.0.1.0/24

# Firewall rules (create, then apply)
vrg network rule list internal-prod
vrg network rule create internal-prod --action accept --protocol tcp --port 443 --direction incoming
vrg network apply-rules internal-prod

# DNS management
vrg network dns list internal-prod
vrg network apply-dns internal-prod

# DHCP static leases
vrg network host list internal-prod

# Network diagnostics
vrg network diag ping internal-prod --target 10.0.1.5
vrg network diag traceroute internal-prod --target 8.8.8.8

# Check network status including pending changes
vrg network status internal-prod
```

### Behavioral notes

```
Notes:
  Firewall rule changes are staged, not live. After creating, updating,
  or deleting rules, run "vrg network apply-rules <network>" to activate
  them. Similarly, DNS changes require "vrg network apply-dns <network>".

  Use "vrg network status <network>" to see whether a network has pending
  rule or DNS changes that need to be applied.

  Networks are identified by name or numeric key.
```

## Documentation references

- Wiki vNet architecture: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/vnet-architecture.md`
- Wiki vNet lifecycle: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/vnet-lifecycle.md`
- Wiki firewall rules: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/firewall-rules.md`
- Wiki DNS config: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/dns-configuration.md`
- Wiki DHCP/IP: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/dhcp-ip-management.md`
- Public docs networks: `/Volumes/HOME/projects/docs/docs/product-guide/networks/`
- Public docs network rules: `/Volumes/HOME/projects/docs/docs/product-guide/networks/network-rules.md`
- Public docs network concepts: `/Volumes/HOME/projects/docs/docs/product-guide/networks/network-concepts.md`

## Checklist

- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network.py` with description + examples + notes
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_rule.py` (emphasize apply-rules workflow)
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_dns.py` (emphasize apply-dns workflow)
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_host.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_alias.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_diag.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `network_query.py`
- [ ] Add examples to leaf command docstrings (Typer reads these as help text for `@app.command()` functions)
- [ ] Test all help output renders correctly
- [ ] Commit changes
