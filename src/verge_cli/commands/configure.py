"""Configuration commands for Verge CLI."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from verge_cli.config import (
    CONFIG_FILE,
    ProfileConfig,
    get_effective_config,
    load_config,
    save_config,
)

app = typer.Typer(
    name="configure",
    rich_markup_mode="markdown",
    help=(
        "Manage CLI credentials and defaults in `~/.vrg/config.toml`.\n\n"
        "This is where you point `vrg` at a VergeOS cluster and give it"
        " credentials. A profile holds a host URL, one auth credential"
        " (bearer token, API key, or username/password), and per-profile"
        " defaults for output format, SSL verification, and request"
        " timeout. The file contains a `[default]` section plus zero or"
        " more named `[profile.<name>]` sections; select a named profile"
        " at runtime with `--profile <name>` or `VERGE_PROFILE`. If you"
        " have never run `vrg` before, start here.\n\n"
        "This group does not call the VergeOS API — it only reads/writes"
        " the local TOML file. `show` and `list` print tables intended"
        " for humans; there is no `-o json` support on this group."
        " `show` masks secrets by default (last-4 redaction); pass"
        " `--show-secrets` to reveal them.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # First-time setup (prompts for host, auth, defaults)\n"
        "    vrg configure setup\n\n"
        "    # Add a second profile for another cluster\n"
        "    vrg configure setup --profile prod\n\n"
        "    # List every profile in the config file\n"
        "    vrg configure list\n\n"
        "    # Show the effective config (after env-var overrides)\n"
        "    vrg configure show\n\n"
        "    # Show a specific profile with secrets revealed\n"
        "    vrg configure show --profile prod --show-secrets\n\n"
        "    # Use a named profile for one command without editing config\n"
        "    vrg --profile prod vm list\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Credential precedence, highest wins: CLI flags (`--host`,"
        " `--token`, …) > environment variables (`VERGE_HOST`,"
        " `VERGE_TOKEN`, `VERGE_API_KEY`, `VERGE_USERNAME`,"
        " `VERGE_PASSWORD`, `VERGE_PROFILE`, `VERGE_VERIFY_SSL`,"
        " `VERGE_TIMEOUT`, `VERGE_OUTPUT`) > named profile > `[default]`"
        " profile > interactive prompt (TTY only). Auth priority within"
        " a profile: bearer token, then API key, then basic auth. The"
        " config file is plain TOML — secrets are stored unencrypted, so"
        " protect `~/.vrg/config.toml` like an SSH key and prefer bearer"
        " tokens or env vars for CI. Exit code 3 means config-file"
        " error (e.g., unknown profile)."
    ),
    no_args_is_help=True,
)

console = Console()


@app.command(name="setup")
def configure_setup(
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile name to configure.",
    ),
) -> None:
    """Interactive configuration setup."""
    config = load_config()

    # Get existing profile or create new one
    if profile == "default":
        existing = config.default
    else:
        existing = config.profiles.get(profile, ProfileConfig())

    console.print(f"\n[bold]Configuring profile: {profile}[/bold]\n")

    # Prompt for values with defaults
    host = typer.prompt(
        "VergeOS host URL",
        default=existing.host or "",
        show_default=bool(existing.host),
    )

    console.print("\n[dim]Authentication (leave blank to skip)[/dim]")
    console.print("[dim]Priority: Bearer token > API key > Basic auth[/dim]\n")

    token = typer.prompt(
        "Bearer token",
        default="",
        show_default=False,
    )

    api_key = ""
    username = ""
    password = ""

    if not token:
        api_key = typer.prompt(
            "API key",
            default="",
            show_default=False,
        )

        if not api_key:
            username = typer.prompt(
                "Username",
                default=existing.username or "",
                show_default=bool(existing.username),
            )
            if username:
                password = typer.prompt(
                    "Password",
                    default="",
                    hide_input=True,
                    show_default=False,
                )

    verify_ssl = typer.confirm(
        "Verify SSL certificates",
        default=existing.verify_ssl,
    )

    output_format = typer.prompt(
        "Default output format",
        default=existing.output,
        show_default=True,
    )

    timeout = typer.prompt(
        "Request timeout (seconds)",
        default=str(existing.timeout),
        show_default=True,
    )

    # Build new profile
    new_profile = ProfileConfig(
        host=host if host else None,
        token=token if token else None,
        api_key=api_key if api_key else None,
        username=username if username else None,
        password=password if password else None,
        verify_ssl=verify_ssl,
        output=output_format,
        timeout=int(timeout),
    )

    # Update config
    if profile == "default":
        config.default = new_profile
    else:
        config.profiles[profile] = new_profile

    # Save config
    save_config(config)
    console.print(f"\n[green]Configuration saved to {CONFIG_FILE}[/green]")


@app.command(name="show")
def configure_show(
    ctx: typer.Context,
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="Profile name to show (default: effective config).",
    ),
    show_secrets: bool = typer.Option(
        False,
        "--show-secrets",
        help="Show secret values (tokens, passwords).",
    ),
) -> None:
    """Display current configuration."""
    if profile:
        config = load_config()
        try:
            profile_config = config.get_profile(profile)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(3) from None
        title = f"Profile: {profile}"
    elif ctx.obj and ctx.obj.get("profile"):
        profile_config = ctx.obj["config"]
        title = "Effective Configuration"
    else:
        profile_config = get_effective_config()
        title = "Effective Configuration"

    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    def mask_secret(value: str | None) -> str:
        if value is None:
            return "[dim]not set[/dim]"
        if show_secrets:
            return value
        if len(value) <= 8:
            return "********"
        return value[:4] + "..." + value[-4:]

    table.add_row("Host", profile_config.host or "[dim]not set[/dim]")
    table.add_row("Token", mask_secret(profile_config.token))
    table.add_row("API Key", mask_secret(profile_config.api_key))
    table.add_row("Username", profile_config.username or "[dim]not set[/dim]")
    table.add_row("Password", mask_secret(profile_config.password))
    table.add_row("Verify SSL", str(profile_config.verify_ssl))
    table.add_row("Output", profile_config.output)
    table.add_row("Timeout", f"{profile_config.timeout}s")

    console.print()
    console.print(table)
    console.print()

    if not profile:
        console.print(f"[dim]Config file: {CONFIG_FILE}[/dim]")


@app.command(name="list")
def configure_list() -> None:
    """List all configured profiles."""
    config = load_config()

    table = Table(title="Profiles", show_header=True, header_style="bold")
    table.add_column("Profile", style="cyan")
    table.add_column("Host")
    table.add_column("Auth Type")

    def get_auth_type(p: ProfileConfig) -> str:
        if p.token:
            return "Bearer token"
        if p.api_key:
            return "API key"
        if p.username:
            return "Basic auth"
        return "[dim]not configured[/dim]"

    table.add_row(
        "default",
        config.default.host or "[dim]not set[/dim]",
        get_auth_type(config.default),
    )

    for name, profile in config.profiles.items():
        table.add_row(
            name,
            profile.host or "[dim]not set[/dim]",
            get_auth_type(profile),
        )

    console.print()
    console.print(table)
    console.print()
