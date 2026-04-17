# Help Text Improvement: `vrg recipe`, `vrg tenant-recipe`, `vrg catalog`

**Date:** 2026-04-16
**Status:** Draft
**Scope:** Recipe, tenant-recipe, and catalog command groups
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

Recipes and catalogs are VergeOS's templating and marketplace system. Currently "Manage VM recipes." / "Manage catalog repositories and catalogs." — no context on what recipes actually are.

## What these are (source from docs)

- **Recipes**: Customizable templates for creating VMs or tenants. A recipe defines a base configuration plus custom questions (forms) that users fill in during provisioning. Recipes have sections (logical groupings) and questions (input fields).
- **Tenant recipes**: Same concept but for provisioning tenants instead of VMs.
- **Catalogs**: Collections of recipes organized into groups. A catalog belongs to a repository.
- **Catalog repositories**: Top-level containers for catalogs, can be shared across sites.

## Source files to modify

| File | Current help |
|------|-------------|
| `commands/recipe.py` | "Manage VM recipes." |
| `commands/recipe_section.py` | "Manage recipe sections." |
| `commands/recipe_question.py` | "Manage recipe questions." |
| `commands/recipe_instance.py` | "Manage recipe instances." |
| `commands/recipe_log.py` | "Manage recipe logs." |
| `commands/tenant_recipe.py` | "Manage tenant recipes." |
| `commands/tenant_recipe_instance.py` | "Manage tenant recipe instances." |
| `commands/catalog.py` | "Manage catalog repositories and catalogs." |
| `commands/catalog_repo.py` | "Manage catalog repositories." |
| `commands/catalog_log.py` | "Manage catalog logs." |
| `commands/catalog_repo_log.py` | "Manage catalog repository logs." |

## Examples to include

```
# List VM recipes
vrg recipe list

# Get recipe details (shows sections and questions)
vrg -o json recipe get ubuntu-server

# Recipe instances (VMs created from recipes)
vrg recipe instance list ubuntu-server

# Catalog repos and catalogs
vrg catalog repo list
vrg catalog list
```

### Behavioral notes

```
Notes:
  Recipes are templates with user-facing questions. They are different
  from .vrg.yaml template files — recipes are managed within VergeOS
  and presented through the UI, while templates are local YAML files
  used by the CLI.

  Hierarchy: Repository → Catalog → Recipe → Sections → Questions.
```

## Documentation references

- Public docs recipes overview: `/Volumes/HOME/projects/docs/docs/product-guide/automation/recipes-overview.md`
- Public docs VM recipes: `/Volumes/HOME/projects/docs/docs/product-guide/automation/vm-recipes.md`
- Public docs tenant recipes: `/Volumes/HOME/projects/docs/docs/product-guide/automation/tenant-recipes.md`
- Public docs recipes organization: `/Volumes/HOME/projects/docs/docs/product-guide/automation/recipes-organization.md`
- Public docs marketplace: `/Volumes/HOME/projects/docs/docs/product-guide/automation/marketplace-vm-recipes.md`
- Wiki catalog system: `/Volumes/HOME/verge-vault/VergeOS/wiki/concepts/catalog-system.md`

## Checklist

- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `recipe.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `recipe_instance.py`
- [x] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `recipe_log.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `recipe_question.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `recipe_section.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `tenant_recipe.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `tenant_recipe_instance.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `tenant_recipe_log.py`
- [ ] Update `help=` and add `rich_markup_mode="markdown"` on `typer.Typer()` in `catalog.py` and `catalog_repo.py`
- [ ] Add examples to leaf command docstrings (Typer reads these as help text for `@app.command()` functions)
- [ ] Test all help output renders correctly
- [ ] Commit changes
