"""Unit tests for configuration management."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from verge_cli.config import (
    Config,
    ProfileConfig,
    apply_env_overrides,
    load_config,
    save_config,
)


class TestProfileConfig:
    """Tests for ProfileConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        profile = ProfileConfig()
        assert profile.host is None
        assert profile.token is None
        assert profile.api_key is None
        assert profile.username is None
        assert profile.password is None
        assert profile.verify_ssl is True
        assert profile.output == "table"
        assert profile.timeout == 30

    def test_to_dict_excludes_none(self) -> None:
        """Test to_dict excludes None credential values."""
        profile = ProfileConfig(host="https://test.com", token="abc123")
        result = profile.to_dict()

        assert result["host"] == "https://test.com"
        assert result["token"] == "abc123"
        assert "api_key" not in result
        assert "username" not in result
        assert "password" not in result
        assert result["verify_ssl"] is True
        assert result["output"] == "table"
        assert result["timeout"] == 30

    def test_rejects_invalid_output(self) -> None:
        """Invalid output formats should fail at the shared config boundary."""
        with pytest.raises(ValueError, match="Invalid output format 'yaml'"):
            ProfileConfig(output="yaml")


class TestConfig:
    """Tests for Config dataclass."""

    def test_get_profile_default(self) -> None:
        """Test getting default profile."""
        config = Config(default=ProfileConfig(host="https://default.com"))

        profile = config.get_profile()
        assert profile.host == "https://default.com"

        profile = config.get_profile("default")
        assert profile.host == "https://default.com"

    def test_get_profile_named(self) -> None:
        """Test getting a named profile."""
        config = Config(
            default=ProfileConfig(host="https://default.com"),
            profiles={"dev": ProfileConfig(host="https://dev.com")},
        )

        profile = config.get_profile("dev")
        assert profile.host == "https://dev.com"

    def test_get_profile_not_found(self) -> None:
        """Test getting a non-existent profile raises error."""
        config = Config()

        with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
            config.get_profile("nonexistent")


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Test loading from non-existent file returns empty config."""
        config = load_config(tmp_path / "nonexistent.toml")

        assert config.default.host is None
        assert len(config.profiles) == 0

    def test_load_valid_config(self, sample_config_file: Path) -> None:
        """Test loading a valid config file."""
        config = load_config(sample_config_file)

        assert config.default.host == "https://verge.example.com"
        assert config.default.token == "test-token-12345"
        assert config.default.verify_ssl is True

        assert "dev" in config.profiles
        assert config.profiles["dev"].host == "https://192.168.1.100"
        assert config.profiles["dev"].username == "admin"
        assert config.profiles["dev"].verify_ssl is False

    def test_load_rejects_invalid_output(self, tmp_path: Path) -> None:
        """Invalid output formats in config.toml should be rejected."""
        config_path = tmp_path / "config.toml"
        config_path.write_text('[default]\noutput = "yaml"\n')

        with pytest.raises(ValueError, match="Invalid output format 'yaml'"):
            load_config(config_path)


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test saving and loading config produces identical result."""
        config_path = tmp_path / ".vrg" / "config.toml"

        original = Config(
            default=ProfileConfig(
                host="https://test.com",
                token="my-token",
                output="json",
            ),
            profiles={
                "prod": ProfileConfig(
                    host="https://prod.com",
                    api_key="prod-key",
                )
            },
        )

        save_config(original, config_path)
        loaded = load_config(config_path)

        assert loaded.default.host == original.default.host
        assert loaded.default.token == original.default.token
        assert loaded.default.output == original.default.output
        assert loaded.profiles["prod"].host == original.profiles["prod"].host
        assert loaded.profiles["prod"].api_key == original.profiles["prod"].api_key


class TestEnvOverrides:
    """Tests for environment variable overrides."""

    def test_env_overrides_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VERGE_HOST overrides config value."""
        monkeypatch.setenv("VERGE_HOST", "https://env-host.com")

        profile = ProfileConfig(host="https://config-host.com")
        result = apply_env_overrides(profile)

        assert result.host == "https://env-host.com"

    def test_env_overrides_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VERGE_TOKEN overrides config value."""
        monkeypatch.setenv("VERGE_TOKEN", "env-token")

        profile = ProfileConfig(token="config-token")
        result = apply_env_overrides(profile)

        assert result.token == "env-token"

    def test_env_overrides_verify_ssl(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VERGE_VERIFY_SSL overrides config value."""
        monkeypatch.setenv("VERGE_VERIFY_SSL", "false")

        profile = ProfileConfig(verify_ssl=True)
        result = apply_env_overrides(profile)

        assert result.verify_ssl is False

    def test_env_overrides_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test VERGE_TIMEOUT overrides config value."""
        monkeypatch.setenv("VERGE_TIMEOUT", "60")

        profile = ProfileConfig(timeout=30)
        result = apply_env_overrides(profile)

        assert result.timeout == 60

    def test_env_rejects_invalid_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """VERGE_OUTPUT should use the same validation as config files."""
        monkeypatch.setenv("VERGE_OUTPUT", "yaml")

        with pytest.raises(ValueError, match="Invalid output format 'yaml'"):
            apply_env_overrides(ProfileConfig())

    def test_no_env_uses_config(self) -> None:
        """Test that config values are used when no env vars are set."""
        # Clear relevant env vars
        for var in ["VERGE_HOST", "VERGE_TOKEN", "VERGE_VERIFY_SSL"]:
            os.environ.pop(var, None)

        profile = ProfileConfig(
            host="https://config-host.com",
            token="config-token",
        )
        result = apply_env_overrides(profile)

        assert result.host == "https://config-host.com"
        assert result.token == "config-token"
