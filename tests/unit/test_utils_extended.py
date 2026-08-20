"""Extended tests for utility functions (NAS resolver, wait helpers)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from verge_cli.errors import MultipleMatchesError, ResourceNotFoundError, TimeoutCliError
from verge_cli.utils import resolve_nas_resource, wait_for_state, wait_for_task


class TestResolveNasResource:
    """Tests for NAS resource resolution (hex key strings)."""

    def test_hex_key_returned_directly(self) -> None:
        """40-char hex key should be returned without API call."""
        manager = MagicMock()
        hex_key = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

        result = resolve_nas_resource(manager, hex_key, "NAS volume")

        assert result == hex_key
        manager.list.assert_not_called()

    def test_name_single_match_returns_key(self) -> None:
        """Single name match should return the hex key."""
        manager = MagicMock()
        vol = MagicMock()
        vol.name = "data-vol"
        vol.key = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        manager.list.return_value = [vol]

        result = resolve_nas_resource(manager, "data-vol", "NAS volume")

        assert result == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

    def test_name_no_match_raises_not_found(self) -> None:
        """No match should raise ResourceNotFoundError."""
        manager = MagicMock()
        manager.list.return_value = []

        with pytest.raises(ResourceNotFoundError, match="not found"):
            resolve_nas_resource(manager, "nonexistent", "NAS volume")

    def test_name_multiple_matches_raises_conflict(self) -> None:
        """Multiple name matches should raise MultipleMatchesError."""
        manager = MagicMock()
        vol1 = MagicMock()
        vol1.name = "data"
        vol1.key = "aaaa" + "0" * 36
        vol2 = MagicMock()
        vol2.name = "data"
        vol2.key = "bbbb" + "0" * 36
        manager.list.return_value = [vol1, vol2]

        with pytest.raises(MultipleMatchesError):
            resolve_nas_resource(manager, "data", "NAS volume")

    def test_list_error_raises_not_found(self) -> None:
        """List API error should be wrapped in ResourceNotFoundError."""
        manager = MagicMock()
        manager.list.side_effect = Exception("API Error")

        with pytest.raises(ResourceNotFoundError, match="Failed to list"):
            resolve_nas_resource(manager, "some-vol", "NAS volume")

    def test_handles_dict_responses(self) -> None:
        """Dict-style responses should be handled correctly."""
        manager = MagicMock()
        manager.list.return_value = [
            {"name": "data-vol", "$key": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"},
        ]

        result = resolve_nas_resource(manager, "data-vol", "NAS volume")

        assert result == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

    def test_handles_id_key_from_live_api(self) -> None:
        """Some string-key tables return id instead of $key in list views."""
        manager = MagicMock()
        manager.list.return_value = [
            {"name": "ocean", "id": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"},
        ]

        result = resolve_nas_resource(manager, "ocean", "theme")

        assert result == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def _make_resource(status: str) -> dict[str, str]:
    """Create a dict resource with the given status (avoids MagicMock getattr issues)."""
    return {"status": status}


class TestWaitForState:
    """Tests for wait_for_state helper."""

    def test_immediate_target_state(self) -> None:
        """Should return immediately if resource is already in target state."""
        resource = _make_resource("running")
        get_fn = MagicMock(return_value=resource)

        result = wait_for_state(get_fn, 1, "running", state_field="status", quiet=True)

        assert result is resource

    def test_reaches_target_after_polling(self) -> None:
        """Should poll until target state is reached."""
        stopped = _make_resource("stopped")
        running = _make_resource("running")

        call_count = 0

        def mock_get_fn(key: int) -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return stopped if call_count < 3 else running

        with patch("verge_cli.utils.time.sleep"):
            result = wait_for_state(mock_get_fn, 1, "running", state_field="status", quiet=True)

        assert result is running
        assert call_count == 3

    def test_multiple_target_states(self) -> None:
        """Should accept list of target states."""
        resource = _make_resource("offline")
        get_fn = MagicMock(return_value=resource)

        result = wait_for_state(get_fn, 1, ["stopped", "offline"], state_field="status", quiet=True)

        assert result is resource

    def test_timeout_raises_error(self) -> None:
        """Should raise TimeoutCliError when timeout exceeded."""
        resource = _make_resource("starting")
        get_fn = MagicMock(return_value=resource)

        with (
            patch("verge_cli.utils.time.sleep"),
            patch("verge_cli.utils.time.time", side_effect=[0, 301]),
        ):
            with pytest.raises(TimeoutCliError, match="Timeout"):
                wait_for_state(
                    get_fn,
                    1,
                    "running",
                    timeout=300,
                    state_field="status",
                    quiet=True,
                )

    def test_string_target_state(self) -> None:
        """Should accept a single string target state."""
        resource = _make_resource("stopped")
        get_fn = MagicMock(return_value=resource)

        result = wait_for_state(get_fn, 1, "stopped", state_field="status", quiet=True)

        assert result is resource


class TestWaitForTask:
    """Tests for wait_for_task helper."""

    def test_task_completes_successfully(self) -> None:
        """Should return task data on successful completion."""
        client = MagicMock()
        task = {"status": "complete", "error": None}
        client.tasks.get.return_value = task

        result = wait_for_task(client, 42, quiet=True)

        assert result == task

    def test_task_completed_status(self) -> None:
        """Should accept 'completed' status."""
        client = MagicMock()
        task = {"status": "completed", "error": None}
        client.tasks.get.return_value = task

        result = wait_for_task(client, 42, quiet=True)

        assert result == task

    def test_task_success_status(self) -> None:
        """Should accept 'success' status."""
        client = MagicMock()
        task = {"status": "success", "error": None}
        client.tasks.get.return_value = task

        result = wait_for_task(client, 42, quiet=True)

        assert result == task

    def test_task_failure_raises_error(self) -> None:
        """Should raise CliError on task failure."""
        from verge_cli.errors import CliError

        client = MagicMock()
        task = {"status": "error", "error": "Disk full"}
        client.tasks.get.return_value = task

        with pytest.raises(CliError, match="Disk full"):
            wait_for_task(client, 42, quiet=True)

    def test_task_failed_status(self) -> None:
        """Should raise on 'failed' status."""
        from verge_cli.errors import CliError

        client = MagicMock()
        task = {"status": "failed", "error": None}
        client.tasks.get.return_value = task

        with pytest.raises(CliError, match="Task failed"):
            wait_for_task(client, 42, quiet=True)

    def test_task_timeout(self) -> None:
        """Should raise TimeoutCliError when timeout exceeded."""
        client = MagicMock()
        task = {"status": "running", "error": None}
        client.tasks.get.return_value = task

        with (
            patch("verge_cli.utils.time.sleep"),
            patch("verge_cli.utils.time.time", side_effect=[0, 301]),
        ):
            with pytest.raises(TimeoutCliError, match="Timeout"):
                wait_for_task(client, 42, timeout=300, quiet=True)

    def test_task_polls_until_complete(self) -> None:
        """Should poll until task completes."""
        client = MagicMock()
        running = {"status": "running", "error": None}
        complete = {"status": "complete", "error": None}
        client.tasks.get.side_effect = [running, running, complete]

        with patch("verge_cli.utils.time.sleep"):
            result = wait_for_task(client, 42, quiet=True)

        assert result == complete
        assert client.tasks.get.call_count == 3

    def test_task_object_response(self) -> None:
        """Should handle object-style responses (non-dict)."""
        client = MagicMock()

        class TaskResult:
            def __init__(self) -> None:
                self.status = "complete"
                self.error = None
                self.key = 42

        task_obj = TaskResult()
        client.tasks.get.return_value = task_obj

        result = wait_for_task(client, 42, quiet=True)

        assert result["status"] == "complete"
        assert result["key"] == 42
