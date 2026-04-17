"""Recipe question management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_nas_resource, resolve_resource_id

app = typer.Typer(
    name="question",
    help=(
        "Manage VM recipe questions — the input fields users answer when"
        " deploying a recipe.\n\n"
        "Each **question** collects one piece of data at deploy time and"
        " stores the answer under its `name`, which scripts and cloud-init"
        " templates reference as a variable. Question `type` controls how"
        " the value is entered and validated: `string`, `bool`, `num`,"
        " `password`, `list`, `hidden`, and several database-backed types."
        " Every question belongs to a **section** (see `vrg recipe section`)"
        " that groups related inputs on the form.\n\n"
        "Some questions — such as drive size and NIC selection — are"
        " created automatically from the recipe's base VM. Additional"
        " questions are added to collect application-specific values like"
        " usernames, license keys, or cloud-init URLs.\n\n"
        "After editing questions, the parent recipe must be republished"
        " before remote systems and tenants see the changes. See"
        " `vrg recipe republish`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every question on a recipe\n"
        "    vrg recipe question list ubuntu-server\n\n"
        "    # Filter to questions in a single section\n"
        "    vrg recipe question list ubuntu-server --section networking\n\n"
        "    # Inspect a question as JSON (includes type, default, validation)\n"
        "    vrg -o json recipe question get ubuntu-server admin_password\n\n"
        "    # Add a required string question in the `general` section\n"
        "    vrg recipe question create ubuntu-server \\\n"
        "      --name hostname --section general --type string \\\n"
        "      --display 'Hostname' --required\n\n"
        "    # Add a dropdown with preset options\n"
        "    vrg recipe question create ubuntu-server \\\n"
        "      --name tier --section general --type list \\\n"
        "      --display 'Service Tier' \\\n"
        "      --list-options 'small=Small,medium=Medium,large=Large'\n\n"
        "    # Change a question's default value and reorder it\n"
        "    vrg recipe question update ubuntu-server hostname \\\n"
        "      --default web-01 --order 10\n\n"
        "    # Delete a question\n"
        "    vrg recipe question delete ubuntu-server old_field --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "The first argument is always the recipe (name or 40-character hex"
        " key). Questions are then addressed by their `name` or numeric key."
        " When a recipe or question name matches multiple records, vrg"
        " prints the matches and exits with code 7 — use the key to"
        " disambiguate.\n\n"
        "`--name` is the scripting variable and must be alpha-numeric (no"
        " spaces or punctuation). `--display` is the UI label shown to"
        " users; `--hint` is placeholder text inside the field; `--note`"
        " renders below the field; `--help-text` is the hover tooltip.\n\n"
        "`--list-options` takes comma-separated `key=value` pairs — the key"
        " is stored as the answer, the value is shown in the dropdown."
        " `--min`/`--max` apply to numeric types, and `--regex` applies a"
        " validation pattern to string input."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

RECIPE_QUESTION_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("display", header="Label"),
    ColumnDef("type"),
    ColumnDef("required", format_fn=format_bool_yn),
    ColumnDef("default", wide_only=True),
    ColumnDef("hint", wide_only=True),
]


def _question_to_dict(question: Any) -> dict[str, Any]:
    """Convert a RecipeQuestion SDK object to a dict for output."""
    return {
        "$key": int(question.key),
        "name": question.name,
        "display": question.get("display", ""),
        "type": question.get("type"),
        "required": question.get("required"),
        "default": question.get("default", ""),
        "hint": question.get("hint", ""),
    }


def _parse_list_options(options_str: str) -> dict[str, str]:
    """Parse comma-separated key=value pairs into a dict.

    Example: ``"small=Small,medium=Medium,large=Large"``
    """
    result: dict[str, str] = {}
    for item in options_str.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise typer.BadParameter(
                f"Invalid --list-options format: '{item}'. Expected key=value."
            )
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _resolve_recipe(vctx: Any, identifier: str) -> str:
    """Resolve a recipe identifier to a hex key."""
    return resolve_nas_resource(
        vctx.client.vm_recipes,
        identifier,
        resource_type="recipe",
    )


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    section: Annotated[
        str | None,
        typer.Option("--section", help="Filter by section name or key."),
    ] = None,
) -> None:
    """List questions for a recipe.

    Examples:

        vrg recipe question list ubuntu-server
        vrg recipe question list ubuntu-server --section networking
        vrg -o json recipe question list ubuntu-server \\
            --query "[?required].name"

    Useful `--query` fields: `name`, `display`, `type`, `required`,
    `default`, `hint`. Question `name` is the variable used in scripts
    and cloud-init templates.
    """
    vctx = get_context(ctx)
    recipe_key = _resolve_recipe(vctx, recipe)
    recipe_ref = f"vm_recipes/{recipe_key}"
    kwargs: dict[str, Any] = {"recipe_ref": recipe_ref}
    if section is not None:
        section_key = resolve_resource_id(vctx.client.recipe_sections, section, "recipe section")
        kwargs["section"] = section_key
    questions = vctx.client.recipe_questions.list(**kwargs)
    data = [_question_to_dict(q) for q in questions]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_QUESTION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def get_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    question: Annotated[str, typer.Argument(help="Question name or key.")],
) -> None:
    """Get a recipe question by name or key.

    Examples:

        vrg recipe question get ubuntu-server hostname
        vrg -o json recipe question get ubuntu-server admin_password

    Both arguments resolve by name or key. Ambiguous names exit with
    code 7 — use keys to disambiguate.
    """
    vctx = get_context(ctx)
    _resolve_recipe(vctx, recipe)  # Validate recipe exists
    question_key = resolve_resource_id(vctx.client.recipe_questions, question, "recipe question")
    item = vctx.client.recipe_questions.get(key=question_key)
    output_result(
        _question_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_QUESTION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def create_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    name: Annotated[str, typer.Option("--name", "-n", help="Variable name for the question.")],
    section: Annotated[str, typer.Option("--section", help="Section name or key.")],
    type: Annotated[
        str, typer.Option("--type", help="Question type (string, bool, num, password, list, etc.).")
    ],
    display: Annotated[str | None, typer.Option("--display", help="UI label.")] = None,
    hint: Annotated[str | None, typer.Option("--hint", help="Placeholder text.")] = None,
    help_text: Annotated[str | None, typer.Option("--help-text", help="Tooltip text.")] = None,
    note: Annotated[str | None, typer.Option("--note", help="Below-field text.")] = None,
    default: Annotated[str | None, typer.Option("--default", help="Default value.")] = None,
    required: Annotated[
        bool, typer.Option("--required/--no-required", help="Whether the question is required.")
    ] = False,
    readonly: Annotated[
        bool, typer.Option("--readonly/--no-readonly", help="Whether the question is read-only.")
    ] = False,
    min_value: Annotated[
        int | None, typer.Option("--min", help="Minimum for numeric types.")
    ] = None,
    max_value: Annotated[
        int | None, typer.Option("--max", help="Maximum for numeric types.")
    ] = None,
    regex: Annotated[str | None, typer.Option("--regex", help="Validation pattern.")] = None,
    list_options: Annotated[
        str | None,
        typer.Option("--list-options", help="Comma-separated key=value pairs for list type."),
    ] = None,
) -> None:
    """Create a new recipe question.

    Examples:

        vrg recipe question create ubuntu-server \\
            --name hostname --section general --type string \\
            --display 'Hostname' --required

        vrg recipe question create ubuntu-server \\
            --name tier --section general --type list \\
            --display 'Service Tier' \\
            --list-options 'small=Small,medium=Medium,large=Large'

        vrg recipe question create ubuntu-server \\
            --name cpu_count --section resources --type num \\
            --display 'vCPUs' --default 2 --min 1 --max 16

    `--name` is the variable name used by scripts and must be
    alpha-numeric. `--type` accepts `string`, `bool`, `num`, `password`,
    `list`, `hidden`, and database-backed types. The recipe must be
    republished for changes to reach tenants.
    """
    vctx = get_context(ctx)
    recipe_key = _resolve_recipe(vctx, recipe)
    recipe_ref = f"vm_recipes/{recipe_key}"
    section_key = resolve_resource_id(vctx.client.recipe_sections, section, "recipe section")
    kwargs: dict[str, Any] = {}
    if display is not None:
        kwargs["display"] = display
    if hint is not None:
        kwargs["hint"] = hint
    if help_text is not None:
        kwargs["help_text"] = help_text
    if note is not None:
        kwargs["note"] = note
    if default is not None:
        kwargs["default"] = default
    kwargs["required"] = required
    kwargs["readonly"] = readonly
    if min_value is not None:
        kwargs["min_value"] = min_value
    if max_value is not None:
        kwargs["max_value"] = max_value
    if regex is not None:
        kwargs["regex"] = regex
    if list_options is not None:
        kwargs["list_options"] = _parse_list_options(list_options)
    result = vctx.client.recipe_questions.create(
        name=name,
        recipe_ref=recipe_ref,
        section=section_key,
        question_type=type,
        **kwargs,
    )
    output_result(
        _question_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_QUESTION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Question '{name}' created.")


@app.command("update")
@handle_errors()
def update_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    question: Annotated[str, typer.Argument(help="Question name or key.")],
    display: Annotated[str | None, typer.Option("--display", help="New UI label.")] = None,
    hint: Annotated[str | None, typer.Option("--hint", help="New placeholder text.")] = None,
    help_text: Annotated[str | None, typer.Option("--help-text", help="New tooltip text.")] = None,
    note: Annotated[str | None, typer.Option("--note", help="New below-field text.")] = None,
    default: Annotated[str | None, typer.Option("--default", help="New default value.")] = None,
    required: Annotated[
        bool | None,
        typer.Option("--required/--no-required", help="Set required state."),
    ] = None,
    readonly: Annotated[
        bool | None,
        typer.Option("--readonly/--no-readonly", help="Set read-only state."),
    ] = None,
    min_value: Annotated[int | None, typer.Option("--min", help="New minimum.")] = None,
    max_value: Annotated[int | None, typer.Option("--max", help="New maximum.")] = None,
    order: Annotated[int | None, typer.Option("--order", help="Display order.")] = None,
) -> None:
    """Update a recipe question.

    Examples:

        vrg recipe question update ubuntu-server hostname \\
            --default web-01 --order 10
        vrg recipe question update ubuntu-server admin_password \\
            --required
        vrg recipe question update ubuntu-server cpu_count --min 2 --max 32

    Only flags you pass are changed. Republish the recipe after edits
    for tenants to see the new question configuration.
    """
    vctx = get_context(ctx)
    _resolve_recipe(vctx, recipe)  # Validate recipe exists
    question_key = resolve_resource_id(vctx.client.recipe_questions, question, "recipe question")
    kwargs: dict[str, Any] = {}
    if display is not None:
        kwargs["display"] = display
    if hint is not None:
        kwargs["hint"] = hint
    if help_text is not None:
        kwargs["help_text"] = help_text
    if note is not None:
        kwargs["note"] = note
    if default is not None:
        kwargs["default"] = default
    if required is not None:
        kwargs["required"] = required
    if readonly is not None:
        kwargs["readonly"] = readonly
    if min_value is not None:
        kwargs["min_value"] = min_value
    if max_value is not None:
        kwargs["max_value"] = max_value
    if order is not None:
        kwargs["orderid"] = order
    result = vctx.client.recipe_questions.update(question_key, **kwargs)
    output_result(
        _question_to_dict(result),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=RECIPE_QUESTION_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
    output_success(f"Question '{question}' updated.")


@app.command("delete")
@handle_errors()
def delete_cmd(
    ctx: typer.Context,
    recipe: Annotated[str, typer.Argument(help="Recipe name or key.")],
    question: Annotated[str, typer.Argument(help="Question name or key.")],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation."),
    ] = False,
) -> None:
    """Delete a recipe question.

    Examples:

        vrg recipe question delete ubuntu-server old_field
        vrg recipe question delete ubuntu-server old_field --yes

    Deployed instances that answered this question keep their stored
    answer, but new deploys will no longer prompt for it. Republish the
    recipe after deletion.
    """
    vctx = get_context(ctx)
    _resolve_recipe(vctx, recipe)  # Validate recipe exists
    question_key = resolve_resource_id(vctx.client.recipe_questions, question, "recipe question")
    if not confirm_action(f"Delete question '{question}'?", yes=yes):
        raise typer.Abort()
    vctx.client.recipe_questions.delete(question_key)
    output_success(f"Question '{question}' deleted.")
