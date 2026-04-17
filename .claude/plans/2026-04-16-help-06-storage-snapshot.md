# Help Text Improvement: `vrg storage` and `vrg snapshot`

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Storage command group, Snapshot command group (snapshot, snapshot-profile, snapshot-profile period)
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

Storage tiers and cloud snapshots are core infrastructure concepts. Currently "Manage storage tiers." and "Manage cloud snapshots." — no context on what tiers are or the snapshot hierarchy.

## What these are (source from docs)

**Storage tiers**: VergeOS vSAN pools all physical drives across cluster nodes into up to 5 tiers (Tier 1 = NVMe/fastest through Tier 5 = archive/slowest). Tiers define performance classes for VM drives and NAS volumes. The vSAN handles deduplication, redundancy, and repair automatically.

**Cloud snapshots**: System-wide point-in-time captures of the entire VergeOS environment (all VMs, tenants, configurations). Used for backup and disaster recovery. Up to 2,048 per system. Distinct from VM snapshots (per-VM) and NAS volume snapshots (per-volume).

**Snapshot profiles**: Automated schedules for creating and retaining snapshots. A profile has periods (daily, weekly, monthly) each with retention counts.

## Source files to modify

| File | Current help |
|------|-------------|
| `commands/storage.py` | "Manage storage tiers." |
| `commands/snapshot.py` | "Manage cloud snapshots." |
| `commands/snapshot_profile.py` | "Manage snapshot profiles." |
| `commands/snapshot_profile_period.py` | "Manage snapshot profile periods." |

## Examples to include

```
# Storage tiers
vrg storage list
vrg -o json storage get 1

# Cloud snapshots (system-wide)
vrg snapshot list
vrg snapshot create --name before-upgrade
vrg snapshot delete 42

# Snapshot profiles (automated schedules)
vrg snapshot-profile list
vrg snapshot-profile get default
vrg snapshot-profile period list default
```

### Behavioral notes

```
Notes:
  Cloud snapshots capture the entire system state — all VMs, tenants,
  and configurations. For per-VM snapshots, use "vrg vm snapshot".
  For NAS volume snapshots, use "vrg nas volume-snapshot".

  Storage tiers are numbered 1-5 (fastest to slowest). Tier assignment
  determines performance characteristics for VM drives and NAS volumes.
```

## Documentation references

- Wiki vSAN storage: `/Volumes/HOME/verge-vault/VergeOS/wiki/overviews/storage.md`
- Wiki storage tiers: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/storage-tiers.md`
- Wiki vSAN data architecture: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/vsan-data-architecture.md`
- Wiki cloud snapshots: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/cloud-snapshot.md`
- Wiki snapshot management: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/snapshot-management.md`
- Wiki snapshot profiles: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/snapshot-profiles.md`
- Public docs snapshots: `/Volumes/HOME/projects/docs/docs/product-guide/backup-dr/snapshots-overview.md`
- Public docs snapshot profiles: `/Volumes/HOME/projects/docs/docs/product-guide/backup-dr/snapshot-profiles.md`
- Public docs system snapshots: `/Volumes/HOME/projects/docs/docs/product-guide/backup-dr/system-snapshots.md`
- Public docs vSAN: `/Volumes/HOME/projects/docs/docs/product-guide/vsan/`

## Checklist

- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `storage.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `snapshot.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `snapshot_profile.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `snapshot_profile_period.py`
- [ ] Add examples to leaf command docstrings (Typer reads these as help text for `@app.command()` functions)
- [ ] Test all help output renders correctly
- [ ] Commit changes
