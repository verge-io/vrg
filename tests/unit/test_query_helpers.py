"""Tests for shared query helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pyvergeos.exceptions import VergeTimeoutError

from verge_cli.commands._query_helpers import output_query_result, run_query
from verge_cli.errors import CliError


def _make_result(
    *,
    result: str = "PING output here",
    status: str = "complete",
    is_error: bool = False,
    is_complete: bool = True,
    query_type: str = "ping",
    command: str = "ping -c 4 8.8.8.8",
    key: str = "abc123",
) -> MagicMock:
    """Build a mock QueryResult with the given properties."""
    mock = MagicMock()
    mock.result = result
    mock.status = status
    mock.is_error = is_error
    mock.is_complete = is_complete
    mock.query_type = query_type
    mock.command = command
    mock.key = key
    return mock


def _make_manager(result: MagicMock | None = None, side_effect: Exception | None = None) -> MagicMock:
    """Build a mock QueryManager."""
    mgr = MagicMock()
    if side_effect:
        mgr.run.side_effect = side_effect
    else:
        mgr.run.return_value = result or _make_result()
    return mgr


# --- run_query tests ---


def test_run_query_success() -> None:
    """run_query returns QueryResult on success."""
    expected = _make_result()
    mgr = _make_manager(expected)

    result = run_query(mgr, "ping", {"host": "8.8.8.8"}, quiet=True)

    assert result is expected
    mgr.run.assert_called_once_with("ping", {"host": "8.8.8.8"}, timeout=120)


def test_run_query_passes_params() -> None:
    """params dict and timeout are forwarded to manager.run()."""
    mgr = _make_manager()
    params = {"host": "10.0.0.1", "count": 4}

    run_query(mgr, "ping", params, timeout=30, quiet=True)

    mgr.run.assert_called_once_with("ping", params, timeout=30)


def test_run_query_error_status() -> None:
    """QueryResult with is_error=True raises CliError."""
    bad_result = _make_result(
        status="error",
        is_error=True,
        is_complete=False,
        result="Host unreachable",
    )
    mgr = _make_manager(bad_result)

    with pytest.raises(CliError, match="Host unreachable"):
        run_query(mgr, "ping", quiet=True)


def test_run_query_timeout_propagates() -> None:
    """VergeTimeoutError from SDK propagates without being caught."""
    mgr = _make_manager(side_effect=VergeTimeoutError("timed out"))

    with pytest.raises(VergeTimeoutError, match="timed out"):
        run_query(mgr, "ping", quiet=True)


@patch("verge_cli.commands._query_helpers.Status")
def test_run_query_quiet_no_spinner(mock_status: MagicMock) -> None:
    """quiet=True skips the spinner context manager."""
    mgr = _make_manager()

    run_query(mgr, "ping", quiet=True)

    mock_status.assert_not_called()


@patch("verge_cli.commands._query_helpers.Status")
def test_run_query_with_spinner(mock_status: MagicMock) -> None:
    """quiet=False uses the Status spinner."""
    mgr = _make_manager()
    mock_status.return_value.__enter__ = MagicMock(return_value=None)
    mock_status.return_value.__exit__ = MagicMock(return_value=False)

    run_query(mgr, "ping", quiet=False, label="Running ping...")

    mock_status.assert_called_once()
    assert mock_status.call_args[0][0] == "Running ping..."


# --- output_query_result tests ---


def test_output_default_prints_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Default format prints result.result to console."""
    result = _make_result(result="64 bytes from 8.8.8.8: icmp_seq=1 ttl=118")

    output_query_result(result, output_format="table", no_color=True)

    captured = capsys.readouterr()
    assert "64 bytes from 8.8.8.8" in captured.out


def test_output_json_emits_dict(capsys: pytest.CaptureFixture[str]) -> None:
    """JSON format emits structured dict with query metadata."""
    result = _make_result(
        result="PING output",
        query_type="ping",
        status="complete",
        command="ping -c 4 8.8.8.8",
        key="abc123",
    )

    output_query_result(result, output_format="json", no_color=True)

    import json

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["query_type"] == "ping"
    assert data["status"] == "complete"
    assert data["result"] == "PING output"
    assert data["command"] == "ping -c 4 8.8.8.8"
    assert data["key"] == "abc123"


def test_output_quiet_prints_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Quiet mode prints result.result as plain text."""
    result = _make_result(result="traceroute output here")

    output_query_result(result, quiet=True)

    captured = capsys.readouterr()
    assert captured.out.strip() == "traceroute output here"
