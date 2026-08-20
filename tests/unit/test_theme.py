"""Tests for theme commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from verge_cli.cli import app

THEME_KEY = "a" * 40


def _theme(**overrides: Any) -> dict[str, Any]:
    theme = {
        "$key": THEME_KEY,
        "id": THEME_KEY,
        "name": "ocean",
        "description": "Ocean colors",
        "enabled": True,
        "based_on": "dark",
        "system_created": False,
        "type": "local",
        "logo_large": "logo.svg",
        "logo_small": "logo-sm.svg",
        "logo_favicon": "favicon.ico",
        "definitions": [
            {"property": "--color-primary", "value": "#006994"},
        ],
        "modified": 1_700_000_000,
        "created": 1_699_000_000,
    }
    theme.update(overrides)
    return theme


def test_theme_list(cli_runner, mock_client):
    mock_client._request.return_value = [_theme()]

    result = cli_runner.invoke(app, ["theme", "list"])

    assert result.exit_code == 0
    assert "ocean" in result.output
    mock_client._request.assert_called_once_with("GET", "themes", params={})


def test_theme_get_by_name_includes_definitions(cli_runner, mock_client):
    mock_client._request.side_effect = [[_theme()], _theme()]

    result = cli_runner.invoke(app, ["-o", "json", "theme", "get", "ocean"])

    assert result.exit_code == 0
    assert json.loads(result.output)["definitions"][0]["property"] == "--color-primary"
    mock_client._request.assert_called_with(
        "GET",
        f"themes/{THEME_KEY}",
        params={"fields": "$key,most,definitions[most]"},
    )


def test_theme_get_by_hex_key_skips_list(cli_runner, mock_client):
    mock_client._request.return_value = _theme()

    result = cli_runner.invoke(app, ["theme", "get", THEME_KEY])

    assert result.exit_code == 0
    assert mock_client._request.call_count == 1


def test_theme_create_with_definitions(cli_runner, mock_client):
    mock_client._request.return_value = _theme()

    result = cli_runner.invoke(
        app,
        [
            "theme",
            "create",
            "--name",
            "ocean",
            "--based-on",
            "dark",
            "--description",
            "Ocean colors",
            "--set",
            "--color-primary=#006994",
        ],
    )

    assert result.exit_code == 0
    mock_client._request.assert_called_once_with(
        "POST",
        "themes",
        json_data={
            "name": "ocean",
            "based_on": "dark",
            "enabled": True,
            "description": "Ocean colors",
            "set_definitions": [{"property": "--color-primary", "value": "#006994"}],
        },
    )


def test_theme_update(cli_runner, mock_client):
    mock_client._request.side_effect = [[_theme()], _theme(description="Updated")]

    result = cli_runner.invoke(
        app,
        ["theme", "update", "ocean", "--description", "Updated", "--set", "--color-primary="],
    )

    assert result.exit_code == 0
    mock_client._request.assert_called_with(
        "PUT",
        f"themes/{THEME_KEY}",
        json_data={
            "description": "Updated",
            "set_definitions": [{"property": "--color-primary", "value": ""}],
        },
    )


def test_theme_update_requires_change(cli_runner, mock_client):
    mock_client._request.return_value = [_theme()]

    result = cli_runner.invoke(app, ["theme", "update", "ocean"])

    assert result.exit_code == 2
    assert "Specify at least one field" in result.output


@pytest.mark.parametrize(("command", "enabled"), [("enable", True), ("disable", False)])
def test_theme_enable_disable(cli_runner, mock_client, command, enabled):
    mock_client._request.side_effect = [[_theme()], _theme(enabled=enabled)]

    result = cli_runner.invoke(app, ["theme", command, "ocean"])

    assert result.exit_code == 0
    mock_client._request.assert_called_with(
        "PUT", f"themes/{THEME_KEY}", json_data={"enabled": enabled}
    )


def test_theme_delete(cli_runner, mock_client):
    mock_client._request.side_effect = [[_theme()], None]

    result = cli_runner.invoke(app, ["theme", "delete", "ocean", "--yes"])

    assert result.exit_code == 0
    mock_client._request.assert_called_with("DELETE", f"themes/{THEME_KEY}")


def test_theme_export_import_round_trip(cli_runner, mock_client, tmp_path: Path):
    export_file = tmp_path / "ocean.json"
    mock_client._request.side_effect = [[_theme()], _theme()]

    export_result = cli_runner.invoke(app, ["theme", "export", "ocean", "--file", str(export_file)])

    assert export_result.exit_code == 0
    payload = json.loads(export_file.read_text())
    assert payload == {
        "name": "ocean",
        "description": "Ocean colors",
        "enabled": True,
        "based_on": "dark",
        "set_definitions": [{"property": "--color-primary", "value": "#006994"}],
    }

    mock_client._request.reset_mock(side_effect=True)
    mock_client._request.return_value = _theme(name="ocean-copy")
    import_result = cli_runner.invoke(
        app, ["theme", "import", str(export_file), "--name", "ocean-copy"]
    )

    assert import_result.exit_code == 0
    mock_client._request.assert_called_once_with(
        "POST", "themes", json_data={**payload, "name": "ocean-copy"}
    )


def test_theme_export_refuses_to_overwrite(cli_runner, mock_client, tmp_path: Path):
    export_file = tmp_path / "ocean.json"
    export_file.write_text("keep")

    result = cli_runner.invoke(app, ["theme", "export", "ocean", "-f", str(export_file)])

    assert result.exit_code == 2
    assert export_file.read_text() == "keep"
    mock_client._request.assert_not_called()


def test_theme_import_rejects_invalid_json(cli_runner, mock_client, tmp_path: Path):
    import_file = tmp_path / "bad.json"
    import_file.write_text('{"name": "bad", "based_on": "blue"}')

    result = cli_runner.invoke(app, ["theme", "import", str(import_file)])

    assert result.exit_code == 2
    assert "must be 'light' or 'dark'" in result.output
    mock_client._request.assert_not_called()
