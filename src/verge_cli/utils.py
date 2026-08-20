"""Utility functions for Verge CLI."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from rich.console import Console
from rich.status import Status

from verge_cli.errors import MultipleMatchesError, ResourceNotFoundError, TimeoutCliError

if TYPE_CHECKING:
    from pyvergeos import VergeClient

_HEX_KEY_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ResourceManager(Protocol):
    """Protocol for pyvergeos resource managers.

    This protocol is designed to be compatible with pyvergeos SDK managers
    (VMManager, NetworkManager, etc.) which have explicit keyword arguments
    rather than **kwargs in their method signatures.

    Note: We use `list` and `get` with minimal signatures to maximize
    compatibility with SDK managers that have specific keyword arguments.
    """

    def list(self) -> list[Any]: ...
    def get(self, key: int | None = ...) -> Any: ...


def resolve_resource_id(
    manager: ResourceManager,
    identifier: str,
    resource_type: str = "resource",
) -> int:
    """Resolve a name or ID to a resource key.

    Args:
        manager: pyvergeos resource manager (e.g., client.vms).
        identifier: Either a numeric key or a resource name.
        resource_type: Type name for error messages (e.g., "VM", "network").

    Returns:
        Resource key (int).

    Raises:
        ResourceNotFoundError: No resource matches.
        MultipleMatchesError: Multiple resources match name.
    """
    # Search by name first (handles both named and numeric names)
    try:
        resources = manager.list()
    except Exception as e:
        raise ResourceNotFoundError(f"Failed to list {resource_type}s: {e}") from e

    # Filter by name
    matches = []
    for resource in resources:
        # Handle both dict and object responses
        if isinstance(resource, dict):
            name = resource.get("name", "")
            key = resource.get("$key", resource.get("key"))
        else:
            name = getattr(resource, "name", "")
            key = getattr(resource, "key", getattr(resource, "$key", None))

        if name == identifier:
            matches.append({"name": name, "$key": key})

    if len(matches) == 1:
        return matches[0]["$key"]

    if len(matches) > 1:
        # Multiple matches - raise conflict error with details
        raise MultipleMatchesError(resource_type, identifier, matches)

    # No name match found - if identifier is numeric, treat as key
    if identifier.isdigit():
        return int(identifier)

    raise ResourceNotFoundError(f"{resource_type} '{identifier}' not found")


def resolve_nas_resource(
    manager: Any,
    identifier: str,
    resource_type: str = "resource",
) -> str:
    """Resolve a name or hex key to a NAS resource key.

    NAS resources (volumes, shares, users, syncs) use 40-character
    hex string keys instead of integer keys.

    Args:
        manager: pyvergeos NAS resource manager.
        identifier: Either a 40-char hex key or a resource name.
        resource_type: Type name for error messages.

    Returns:
        Resource key (str, 40-char hex).

    Raises:
        ResourceNotFoundError: No resource matches.
        MultipleMatchesError: Multiple resources match name.
    """
    # If it looks like a hex key, use it directly
    if _HEX_KEY_PATTERN.match(identifier):
        return identifier

    # Search by name
    try:
        resources = manager.list()
    except Exception as e:
        raise ResourceNotFoundError(f"Failed to list {resource_type}s: {e}") from e

    matches = []
    for resource in resources:
        if isinstance(resource, dict):
            name = resource.get("name", "")
            key = resource.get("$key", resource.get("key", resource.get("id")))
        else:
            name = getattr(resource, "name", "")
            key = getattr(resource, "key", getattr(resource, "$key", None))

        if name == identifier:
            matches.append({"name": name, "$key": key})

    if len(matches) == 1:
        return str(matches[0]["$key"])

    if len(matches) > 1:
        raise MultipleMatchesError(resource_type, identifier, matches)

    raise ResourceNotFoundError(f"{resource_type} '{identifier}' not found")


def wait_for_state(
    get_resource: Callable[..., Any],
    resource_key: int,
    target_state: str | list[str],
    timeout: int = 300,
    interval: float = 2.0,
    backoff: float = 1.5,
    max_interval: float = 10.0,
    state_field: str = "status",
    resource_type: str = "resource",
    quiet: bool = False,
) -> Any:
    """Wait for a resource to reach a target state.

    Uses exponential backoff to reduce API load.
    Shows spinner via rich.status.Status.

    Args:
        get_resource: Function to get the resource (e.g., client.vms.get).
        resource_key: Key of the resource to monitor.
        target_state: Target state(s) to wait for.
        timeout: Maximum wait time in seconds.
        interval: Initial polling interval in seconds.
        backoff: Exponential backoff factor.
        max_interval: Maximum polling interval.
        state_field: Field name containing the state.
        resource_type: Type name for status messages.
        quiet: Suppress spinner output.

    Returns:
        The resource object in the target state.

    Raises:
        TimeoutCliError: If timeout is reached before target state.
    """
    if isinstance(target_state, str):
        target_states = [target_state]
    else:
        target_states = target_state

    start_time = time.time()
    current_interval = interval
    console = Console()

    def get_state(resource: Any) -> str:
        if isinstance(resource, dict):
            return resource.get(state_field, "")
        return getattr(resource, state_field, "")

    spinner_ctx = Status(
        f"Waiting for {resource_type} to reach state: {', '.join(target_states)}...",
        console=console,
        spinner="dots",
    )

    try:
        if not quiet:
            spinner_ctx.start()

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TimeoutCliError(
                    f"Timeout waiting for {resource_type} to reach state "
                    f"{', '.join(target_states)} after {timeout}s"
                )

            resource = get_resource(resource_key)
            current_state = get_state(resource)

            if not quiet:
                spinner_ctx.update(
                    f"Waiting for {resource_type}... "
                    f"(current: {current_state}, target: {', '.join(target_states)})"
                )

            if current_state in target_states:
                return resource

            time.sleep(current_interval)
            current_interval = min(current_interval * backoff, max_interval)

    finally:
        if not quiet:
            spinner_ctx.stop()


def wait_for_task(
    client: VergeClient,
    task_key: int,
    timeout: int = 300,
    quiet: bool = False,
) -> dict[str, Any]:
    """Wait for a task to complete.

    Args:
        client: VergeClient instance.
        task_key: Key of the task to monitor.
        timeout: Maximum wait time in seconds.
        quiet: Suppress spinner output.

    Returns:
        The completed task data.

    Raises:
        TimeoutCliError: If timeout is reached.
        CliError: If task fails.
    """
    from verge_cli.errors import CliError

    start_time = time.time()
    interval = 1.0
    backoff = 1.5
    max_interval = 5.0
    console = Console()

    spinner_ctx = Status(
        "Waiting for task to complete...",
        console=console,
        spinner="dots",
    )

    try:
        if not quiet:
            spinner_ctx.start()

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TimeoutCliError(f"Timeout waiting for task {task_key} after {timeout}s")

            task = client.tasks.get(task_key)

            # Handle both dict and object responses
            if isinstance(task, dict):
                status = task.get("status", "")
                error = task.get("error")
            else:
                status = getattr(task, "status", "")
                error = getattr(task, "error", None)

            if not quiet:
                spinner_ctx.update(f"Task status: {status}")

            # Check for completion states
            if status in ("complete", "completed", "success"):
                return task if isinstance(task, dict) else task.__dict__

            if status in ("error", "failed"):
                error_msg = error or "Task failed"
                raise CliError(f"Task {task_key} failed: {error_msg}")

            time.sleep(interval)
            interval = min(interval * backoff, max_interval)

    finally:
        if not quiet:
            spinner_ctx.stop()


def confirm_action(
    message: str,
    default: bool = False,
    yes: bool = False,
) -> bool:
    """Prompt for confirmation before destructive actions.

    Args:
        message: Confirmation message.
        default: Default response if user just presses Enter.
        yes: Skip confirmation (for --yes flag).

    Returns:
        True if confirmed, False otherwise.
    """
    if yes:
        return True

    import typer

    return typer.confirm(message, default=default)
