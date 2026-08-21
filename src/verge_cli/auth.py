"""Authentication utilities for Verge CLI."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer
from pyvergeos import VergeClient
from pyvergeos.exceptions import AuthenticationError, VergeConnectionError

from verge_cli.config import ProfileConfig

if TYPE_CHECKING:
    pass


def get_client(
    config: ProfileConfig,
    *,
    # CLI overrides (highest priority)
    host: str | None = None,
    token: str | None = None,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> VergeClient:
    """Create an authenticated VergeClient.

    Credential resolution order:
    1. CLI arguments (host, token, api_key, username, password)
    2. Config file values (already in config with env overrides applied)
    3. Interactive prompt (if TTY and no credentials found)

    Auth method priority:
    1. Bearer token (token or api_key)
    2. Basic auth (username + password)

    Args:
        config: ProfileConfig with values from config file + env overrides.
        host: CLI override for host.
        token: CLI override for bearer token.
        api_key: CLI override for API key.
        username: CLI override for username.
        password: CLI override for password.

    Returns:
        Authenticated VergeClient instance.

    Raises:
        typer.Exit: On authentication or connection error.
    """
    # Resolve host (CLI > config)
    effective_host = host or config.host

    if not effective_host:
        if sys.stdin.isatty():
            effective_host = typer.prompt("VergeOS host")
        else:
            typer.echo(
                "Error: No host specified. Use --host or configure with 'vrg configure setup'.",
                err=True,
            )
            raise typer.Exit(3)

    # Normalize host - pyvergeos expects just hostname, not URL
    if effective_host.startswith("https://"):
        effective_host = effective_host[8:]
    elif effective_host.startswith("http://"):
        effective_host = effective_host[7:]
    # Strip trailing slash if present
    effective_host = effective_host.rstrip("/")

    # Resolve credentials (CLI > config)
    effective_token = token or api_key or config.token or config.api_key
    effective_username = username or config.username
    effective_password = password or config.password

    # If no credentials, prompt interactively
    if not effective_token and not (effective_username and effective_password):
        if sys.stdin.isatty():
            typer.echo("No credentials found. Please provide authentication:")
            if typer.confirm("Use token authentication?", default=True):
                effective_token = typer.prompt("API token")
            else:
                effective_username = typer.prompt("Username")
                effective_password = typer.prompt("Password", hide_input=True)
        else:
            typer.echo(
                "Error: No credentials specified. Use --token or configure with 'vrg configure setup'.",
                err=True,
            )
            raise typer.Exit(4)

    # Create client with appropriate auth method
    try:
        if effective_token:
            client = VergeClient(
                host=effective_host,
                token=effective_token,
                verify_ssl=config.verify_ssl,
                timeout=config.timeout,
            )
        else:
            client = VergeClient(
                host=effective_host,
                username=effective_username,
                password=effective_password,
                verify_ssl=config.verify_ssl,
                timeout=config.timeout,
            )
        return client

    except AuthenticationError as e:
        typer.echo(f"Error: Authentication failed: {e}", err=True)
        raise typer.Exit(4) from None

    except VergeConnectionError as e:
        typer.echo(f"Error: Connection failed: {e}", err=True)
        raise typer.Exit(10) from None
