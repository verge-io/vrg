# Help Text Improvement: `vrg node` and `vrg cluster`

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Node command group (node, node nic, node lldp, node query) and Cluster command group
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

Nodes are physical servers running VergeOS. Clusters are logical groupings of nodes. Currently "Manage nodes." and "Manage clusters." — no context on node types or what operations are meaningful.

## What nodes and clusters are (source from docs)

A node is an individual physical server running VergeOS. Node types: Controller (manages the cluster — API, UI, orchestration), Compute (runs workloads), Storage (provides vSAN capacity), or HCI (all three). A cluster is a logical grouping of nodes that defines compute scheduling, storage pooling, and availability boundaries. The first two nodes are controllers; additional nodes expand capacity.

## Source files to modify

| File | Current help |
|------|-------------|
| `commands/node.py` | "Manage nodes." |
| `commands/node_nic.py` | "Manage node NICs." |
| `commands/node_lldp.py` | "Manage node LLDP." |
| `commands/node_query.py` | "Run diagnostic queries on a node." |
| `commands/cluster.py` | "Manage clusters." |

## Examples to include

```
# List nodes with status
vrg node list

# Get node details
vrg -o json node get node-1

# Node NICs and LLDP
vrg node nic list node-1
vrg node lldp list node-1

# Node diagnostics
vrg node query network node-1
vrg node query storage node-1

# Cluster info
vrg cluster list
vrg cluster get default
```

### Behavioral notes

```
Notes:
  Nodes are physical servers. Controller nodes (typically the first two)
  run the management plane. Additional nodes are compute, storage, or HCI.

  Node operations can affect running workloads. Putting a node in
  maintenance mode triggers VM migration to other nodes.
```

## Documentation references

- Wiki node entity: `/Volumes/HOME/verge-vault/VergeOS/wiki/entities/node.md`
- Wiki cluster entity: `/Volumes/HOME/verge-vault/VergeOS/wiki/entities/cluster.md`
- Wiki node types: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/node-types.md`
- Wiki node lifecycle: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/node-lifecycle.md`
- Wiki node configuration: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/node-configuration.md`
- Wiki cluster formation: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/cluster-formation.md`
- Wiki node management overview: `/Volumes/HOME/verge-vault/VergeOS/wiki/overviews/node-management.md`

## Checklist

- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `node.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `cluster.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `node_nic.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `node_lldp.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `node_query.py`
- [x] Add examples to leaf command docstrings (Typer reads these as help text for `@app.command()` functions)
- [x] Test all help output renders correctly
- [x] Commit changes
