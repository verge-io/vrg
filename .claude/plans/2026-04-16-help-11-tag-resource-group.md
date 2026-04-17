# Help Text Improvement: `vrg tag` and `vrg resource-group`

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Tag and resource-group command groups
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

Tags and resource groups serve different purposes that aren't obvious from the names. Currently "Manage tags and tag categories." / "Manage resource groups for device passthrough."

## What these are (source from docs)

- **Tags**: Metadata labels applied to resources (VMs, networks, tenants, etc.) for organization and filtering. Tags belong to categories (e.g., "environment" category with "prod", "staging", "dev" tags).
- **Resource groups**: Collections of physical devices (GPUs, NICs, USB devices) configured for passthrough to VMs. Not related to tagging — this is about hardware device assignment.

## Source files to modify

| File | Current help |
|------|-------------|
| `commands/tag.py` | "Manage tags and tag categories." |
| `commands/tag_category.py` | "Manage tag categories." |
| `commands/resource_group.py` | "Manage resource groups for device passthrough." |

## Examples to include

```
# Tags
vrg tag list
vrg tag category list

# Tag a VM (done via vrg vm tag, not here)
# This group manages tag definitions, not assignments

# Resource groups (hardware passthrough)
vrg resource-group list
vrg -o json resource-group get gpu-pool
```

### Behavioral notes

```
Notes:
  Tag management (vrg tag) defines tag categories and tag values.
  To assign tags to resources, use the resource's own tag command
  (e.g., "vrg vm tag <vm> --tag <tag>").

  Resource groups are for physical device passthrough (GPUs, SR-IOV
  NICs). They are not related to tags or logical grouping.
```

## Documentation references

- Wiki (no dedicated tag concept page — check if covered elsewhere)
- Public docs (check product-guide for tag documentation)
- Wiki GPU passthrough: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/gpu-passthrough.md`

## Checklist

- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `tag.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `tag_category.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `resource_group.py`
- [x] Add examples to leaf command docstrings (Typer reads these as help text for `@app.command()` functions)
- [x] Test all help output renders correctly
- [x] Commit changes
