"""Configuration management for Verge CLI."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


CONFIG_DIR = Path.home() / ".vrg"
CONFIG_FILE = CONFIG_DIR / "config.toml"

# Environment variable names
ENV_HOST = "VERGE_HOST"
ENV_TOKEN = "VERGE_TOKEN"
ENV_API_KEY = "VERGE_API_KEY"
ENV_USERNAME = "VERGE_USERNAME"
ENV_PASSWORD = "VERGE_PASSWORD"
ENV_PROFILE = "VERGE_PROFILE"
ENV_VERIFY_SSL = "VERGE_VERIFY_SSL"
ENV_TIMEOUT = "VERGE_TIMEOUT"
ENV_OUTPUT = "VERGE_OUTPUT"


class OutputFormat(str, Enum):
    table = "table"
    wide = "wide"
    json = "json"
    csv = "csv"


@dataclass
class ProfileConfig:
    """Configuration for a single profile."""

    host: str | None = None
    token: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True
    output: str = "table"
    timeout: int = 30

    def __post_init__(self) -> None:
        """Validate values used by every config entry point."""
        try:
            self.output = OutputFormat(self.output).value
        except ValueError:
            choices = ", ".join(item.value for item in OutputFormat)
            raise ValueError(
                f"Invalid output format '{self.output}'; choose from: {choices}"
            ) from None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {}
        if self.host is not None:
            result["host"] = self.host
        if self.token is not None:
            result["token"] = self.token
        if self.api_key is not None:
            result["api_key"] = self.api_key
        if self.username is not None:
            result["username"] = self.username
        if self.password is not None:
            result["password"] = self.password
        result["verify_ssl"] = self.verify_ssl
        result["output"] = self.output
        result["timeout"] = self.timeout
        return result


@dataclass
class Config:
    """Full configuration with default and named profiles."""

    default: ProfileConfig = field(default_factory=ProfileConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    default_profile_name: str | None = None

    def get_profile(self, name: str | None = None) -> ProfileConfig:
        """Get a profile by name, falling back to default.

        If no name is provided, uses the default_profile_name from config,
        then falls back to the [default] section.
        """
        effective_name = name
        if effective_name is None:
            effective_name = self.default_profile_name

        if effective_name is None or effective_name == "default":
            return self.default
        if effective_name in self.profiles:
            return self.profiles[effective_name]
        raise ValueError(f"Profile '{effective_name}' not found in config")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result: dict[str, Any] = {"default": self.default.to_dict()}
        if self.profiles:
            result["profile"] = {name: profile.to_dict() for name, profile in self.profiles.items()}
        return result


def load_config(path: Path | None = None) -> Config:
    """Load configuration from TOML file.

    Args:
        path: Path to config file. Defaults to ~/.vrg/config.toml.

    Returns:
        Config object with loaded values.
    """
    config_path = path or CONFIG_FILE

    if not config_path.exists():
        return Config()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    default_data = data.get("default", {})
    default_profile = ProfileConfig(
        host=default_data.get("host"),
        token=default_data.get("token"),
        api_key=default_data.get("api_key"),
        username=default_data.get("username"),
        password=default_data.get("password"),
        verify_ssl=default_data.get("verify_ssl", True),
        output=default_data.get("output", "table"),
        timeout=default_data.get("timeout", 30),
    )

    profiles: dict[str, ProfileConfig] = {}
    # Support both "profile" and "profiles" keys for compatibility
    profile_data = data.get("profile", data.get("profiles", {}))
    for name, pdata in profile_data.items():
        profiles[name] = ProfileConfig(
            host=pdata.get("host"),
            token=pdata.get("token"),
            api_key=pdata.get("api_key"),
            username=pdata.get("username"),
            password=pdata.get("password"),
            verify_ssl=pdata.get("verify_ssl", True),
            output=pdata.get("output", "table"),
            timeout=pdata.get("timeout", 30),
        )

    # Get the default profile name from config
    default_profile_name = data.get("default_profile")

    return Config(
        default=default_profile, profiles=profiles, default_profile_name=default_profile_name
    )


def save_config(config: Config, path: Path | None = None) -> None:
    """Save configuration to TOML file.

    Args:
        config: Config object to save.
        path: Path to config file. Defaults to ~/.vrg/config.toml.
    """
    config_path = path or CONFIG_FILE

    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "wb") as f:
        tomli_w.dump(config.to_dict(), f)


def apply_env_overrides(profile: ProfileConfig) -> ProfileConfig:
    """Apply environment variable overrides to a profile.

    Environment variables take precedence over config file values.

    Args:
        profile: Base profile configuration.

    Returns:
        New ProfileConfig with environment overrides applied.
    """
    return ProfileConfig(
        host=os.environ.get(ENV_HOST, profile.host),
        token=os.environ.get(ENV_TOKEN, profile.token),
        api_key=os.environ.get(ENV_API_KEY, profile.api_key),
        username=os.environ.get(ENV_USERNAME, profile.username),
        password=os.environ.get(ENV_PASSWORD, profile.password),
        verify_ssl=_parse_bool_env(ENV_VERIFY_SSL, profile.verify_ssl),
        output=os.environ.get(ENV_OUTPUT, profile.output),
        timeout=_parse_int_env(ENV_TIMEOUT, profile.timeout),
    )


def _parse_bool_env(name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _parse_int_env(name: str, default: int) -> int:
    """Parse an integer environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_effective_config(profile_name: str | None = None) -> ProfileConfig:
    """Get the effective configuration with all overrides applied.

    Resolution order:
    1. Environment variables (highest priority)
    2. Named profile from config file (if specified)
    3. Default profile from config file

    Args:
        profile_name: Profile name, or None for default.

    Returns:
        ProfileConfig with all overrides applied.
    """
    # Check for profile override from environment
    effective_profile = profile_name or os.environ.get(ENV_PROFILE)

    config = load_config()
    profile = config.get_profile(effective_profile)
    return apply_env_overrides(profile)
