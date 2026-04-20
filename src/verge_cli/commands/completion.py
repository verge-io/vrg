"""Shell completion script generation."""

from __future__ import annotations

import typer
from typer._completion_shared import Shells, get_completion_script

SHELL_NAMES = {s.value for s in Shells}

app = typer.Typer(
    name="completion",
    rich_markup_mode="markdown",
    help=(
        "Emit shell completion scripts for `vrg`.\n\n"
        "Prints a shell-specific script to stdout that, once sourced by"
        " your shell, enables tab completion for commands, options, and"
        " arguments. Supported shells: bash, zsh, fish, powershell.\n\n"
        "This is a utility group — no API calls, no profile needed, and"
        " no structured output. Agents don't typically need this; it's"
        " for interactive humans tuning their shell. Scripts go to stdout"
        " so you redirect them yourself.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # bash\n"
        "    vrg completion show bash >> ~/.bashrc\n\n"
        "    # zsh (into your fpath)\n"
        '    vrg completion show zsh > "${fpath[1]}/_vrg"\n\n'
        "    # fish\n"
        "    vrg completion show fish > ~/.config/fish/completions/vrg.fish\n\n"
        "    # PowerShell\n"
        "    vrg completion show powershell >> $PROFILE\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Passing an unknown shell exits with code 2 (usage). Reload your"
        " shell (or `source` the rc file) after installing the script."
    ),
    no_args_is_help=True,
)


@app.command("show")
def show(
    shell: str = typer.Argument(help=f"Shell type ({', '.join(sorted(SHELL_NAMES))})."),
) -> None:
    """Print the completion script for a given shell.

    Redirect the output to the appropriate file for your shell:

        vrg completion show bash >> ~/.bashrc

        vrg completion show zsh > "${fpath[1]}/_vrg"

        vrg completion show fish > ~/.config/fish/completions/vrg.fish

        vrg completion show powershell >> $PROFILE

    Exits with code 2 if the shell name is unknown.
    """
    shell_lower = shell.lower()
    if shell_lower not in SHELL_NAMES:
        typer.echo(
            f"Error: Unknown shell '{shell}'. Supported: {', '.join(sorted(SHELL_NAMES))}",
            err=True,
        )
        raise typer.Exit(code=2)
    script = get_completion_script(prog_name="vrg", complete_var="_VRG_COMPLETE", shell=shell_lower)
    typer.echo(script, nl=False)
