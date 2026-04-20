"""Webhook management commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from verge_cli.columns import ColumnDef, format_bool_yn, format_epoch
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="webhook",
    rich_markup_mode="markdown",
    help=(
        "Manage webhook integrations that push HTTP POST messages to"
        " external systems.\n\n"
        "A webhook defines the target URL, authorization, custom headers,"
        " timeout, and retry count. On its own a webhook does nothing —"
        " it is the delivery channel for a *task*, which supplies the"
        " JSON payload, and an *event*, which decides when that task"
        " fires. One webhook can back many tasks, and one task can be"
        " triggered by many events. Supported auth types are `bearer`,"
        " `api_key`, `basic`, and `none`; payloads may interpolate"
        " `${DATE}`, `${TIMESTAMP}`, `${RANDOM}`, and `${NAME}`. Use the"
        " `send` action to push a one-off test message, and `history`"
        " to inspect prior delivery attempts.\n\n"
        "Use `-o json` for structured output and `--query` to pluck"
        " fields (e.g., `--query [].name`), or pipe through jq for filtering."
        " Webhooks resolve by `$key` (numeric) or `name`; an ambiguous"
        " name yields exit code 7 (multiple matches). `list` honors"
        " `--all-profiles` / `-A` to fan out across every configured"
        " CLI profile.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Inventory, filtered by auth type\n"
        "    vrg webhook list\n"
        "    vrg webhook list --auth-type bearer\n"
        "    vrg -o json webhook list\n\n"
        "    # Inspect a specific webhook\n"
        "    vrg webhook get slack-alerts\n\n"
        "    # Create a bearer-auth webhook to Slack with a custom header\n"
        "    vrg webhook create --name slack-alerts \\\n"
        "        --url https://hooks.slack.com/services/T00/B00/XYZ \\\n"
        "        --auth-type bearer --auth-value $SLACK_TOKEN \\\n"
        "        --header 'X-Env:prod' --timeout 10 --retries 3\n\n"
        "    # Update an existing webhook\n"
        "    vrg webhook update slack-alerts --url https://hooks.slack.com/services/T00/B01/NEW\n\n"
        "    # Send a test payload and review deliveries\n"
        '    vrg webhook send slack-alerts -m \'{"text":"ping from vrg"}\'\n'
        "    vrg webhook history --webhook slack-alerts --failed\n\n"
        "    # Revoke\n"
        "    vrg webhook delete slack-alerts --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Webhook delivery is defined by the task/event chain — wire the"
        " webhook to a task (`vrg task create` with object type `webhook`"
        " and action `send`), then bind that task to an event via"
        " `vrg task event create`. `--allow-insecure` disables TLS"
        " verification and is intended for self-signed endpoints in"
        " test/dev only. `timeout` must be 3 seconds or greater. The"
        " webhook feature requires VergeOS 26.0 or later."
    ),
    no_args_is_help=True,
)

WEBHOOK_STATUS_STYLES: dict[str, str] = {
    "Sent": "green",
    "Error": "red bold",
    "Queued": "yellow",
    "Running": "cyan",
}

WEBHOOK_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("url"),
    ColumnDef("authorization_type", header="Auth Type"),
    ColumnDef("is_insecure", header="Insecure", format_fn=format_bool_yn),
    ColumnDef("timeout", wide_only=True),
    ColumnDef("retries", wide_only=True),
]

HISTORY_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("webhook_key", header="Webhook"),
    ColumnDef(
        "status_display",
        header="Status",
        style_map=WEBHOOK_STATUS_STYLES,
    ),
    ColumnDef("status_info", header="Info", wide_only=True),
    ColumnDef("last_attempt", header="Last Attempt", format_fn=format_epoch),
    ColumnDef("created", header="Created", format_fn=format_epoch),
]


def _webhook_to_dict(wh: Any) -> dict[str, Any]:
    """Convert SDK Webhook object to output dict."""
    return {
        "$key": int(wh.key),
        "name": wh.name,
        "url": wh.url,
        "authorization_type": wh.authorization_type_display,
        "is_insecure": wh.is_insecure,
        "timeout": wh.timeout,
        "retries": wh.retries,
    }


def _history_to_dict(h: Any) -> dict[str, Any]:
    """Convert SDK WebhookHistory object to output dict."""
    return {
        "$key": int(h.key),
        "webhook_key": int(h.webhook_key),
        "status_display": h.status_display,
        "status_info": h.status_info,
        "last_attempt": h.last_attempt_at.timestamp() if h.last_attempt_at else None,
        "created": h.created_at.timestamp() if h.created_at else None,
    }


def _parse_headers(header_list: list[str] | None) -> dict[str, str] | None:
    """Parse header strings ('Name:Value') into a dict."""
    if not header_list:
        return None
    headers: dict[str, str] = {}
    for h in header_list:
        if ":" not in h:
            msg = f"Invalid header format '{h}'. Expected 'Name:Value'."
            raise typer.BadParameter(msg)
        name, value = h.split(":", 1)
        headers[name.strip()] = value.strip()
    return headers


@app.command("list")
@handle_errors()
def list_cmd(
    ctx: typer.Context,
    auth_type: Annotated[
        str | None,
        typer.Option(
            "--auth-type",
            help="Filter by authorization type.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = None,
) -> None:
    """List webhooks."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(ctx, lambda c: c.webhooks.list(), _webhook_to_dict, WEBHOOK_COLUMNS)
        return
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if auth_type is not None:
        kwargs["auth_type"] = auth_type
    if limit is not None:
        kwargs["limit"] = limit

    webhooks = vctx.client.webhooks.list(**kwargs)

    output_result(
        [_webhook_to_dict(w) for w in webhooks],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=WEBHOOK_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def get(
    ctx: typer.Context,
    webhook: Annotated[
        str,
        typer.Argument(help="Webhook name or key."),
    ],
) -> None:
    """Get webhook details."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.webhooks, webhook, "webhook")
    item = vctx.client.webhooks.get(key)

    output_result(
        _webhook_to_dict(item),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=WEBHOOK_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command()
@handle_errors()
def create(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Option(
            "--name",
            help="Webhook name.",
        ),
    ],
    url: Annotated[
        str,
        typer.Option(
            "--url",
            help="Webhook URL.",
        ),
    ],
    auth_type: Annotated[
        str | None,
        typer.Option(
            "--auth-type",
            help="Authorization type (e.g. none, basic, bearer).",
        ),
    ] = None,
    auth_value: Annotated[
        str | None,
        typer.Option(
            "--auth-value",
            help="Authorization value (token or credentials).",
        ),
    ] = None,
    header: Annotated[
        list[str] | None,
        typer.Option(
            "--header",
            help="Custom header in 'Name:Value' format (repeatable).",
        ),
    ] = None,
    allow_insecure: Annotated[
        bool,
        typer.Option(
            "--allow-insecure",
            help="Allow insecure (non-TLS) connections.",
        ),
    ] = False,
    timeout: Annotated[
        int | None,
        typer.Option(
            "--timeout",
            help="Request timeout in seconds.",
        ),
    ] = None,
    retries: Annotated[
        int | None,
        typer.Option(
            "--retries",
            help="Number of retry attempts.",
        ),
    ] = None,
) -> None:
    """Create a new webhook."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {
        "name": name,
        "url": url,
    }
    if auth_type is not None:
        kwargs["auth_type"] = auth_type
    if auth_value is not None:
        kwargs["auth_value"] = auth_value
    headers = _parse_headers(header)
    if headers is not None:
        kwargs["headers"] = headers
    if allow_insecure:
        kwargs["allow_insecure"] = True
    if timeout is not None:
        kwargs["timeout"] = timeout
    if retries is not None:
        kwargs["retries"] = retries

    result = vctx.client.webhooks.create(**kwargs)
    output_success(
        f"Webhook '{name}' created (key={int(result.key)}).",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def update(
    ctx: typer.Context,
    webhook: Annotated[
        str,
        typer.Argument(help="Webhook name or key."),
    ],
    name: Annotated[
        str | None,
        typer.Option(
            "--name",
            help="New webhook name.",
        ),
    ] = None,
    url: Annotated[
        str | None,
        typer.Option(
            "--url",
            help="New webhook URL.",
        ),
    ] = None,
    auth_type: Annotated[
        str | None,
        typer.Option(
            "--auth-type",
            help="Authorization type.",
        ),
    ] = None,
    auth_value: Annotated[
        str | None,
        typer.Option(
            "--auth-value",
            help="Authorization value.",
        ),
    ] = None,
    header: Annotated[
        list[str] | None,
        typer.Option(
            "--header",
            help="Custom header in 'Name:Value' format (repeatable).",
        ),
    ] = None,
    allow_insecure: Annotated[
        bool | None,
        typer.Option(
            "--allow-insecure/--no-allow-insecure",
            help="Allow insecure connections.",
        ),
    ] = None,
    timeout: Annotated[
        int | None,
        typer.Option(
            "--timeout",
            help="Request timeout in seconds.",
        ),
    ] = None,
    retries: Annotated[
        int | None,
        typer.Option(
            "--retries",
            help="Number of retry attempts.",
        ),
    ] = None,
) -> None:
    """Update an existing webhook."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.webhooks, webhook, "webhook")

    kwargs: dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if url is not None:
        kwargs["url"] = url
    if auth_type is not None:
        kwargs["auth_type"] = auth_type
    if auth_value is not None:
        kwargs["auth_value"] = auth_value
    headers = _parse_headers(header)
    if headers is not None:
        kwargs["headers"] = headers
    if allow_insecure is not None:
        kwargs["allow_insecure"] = allow_insecure
    if timeout is not None:
        kwargs["timeout"] = timeout
    if retries is not None:
        kwargs["retries"] = retries

    vctx.client.webhooks.update(key, **kwargs)
    output_success(
        f"Webhook '{webhook}' updated.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def delete(
    ctx: typer.Context,
    webhook: Annotated[
        str,
        typer.Argument(help="Webhook name or key."),
    ],
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt.",
        ),
    ] = False,
) -> None:
    """Delete a webhook."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.webhooks, webhook, "webhook")

    if not confirm_action(f"Delete webhook '{webhook}'?", yes=yes):
        return

    vctx.client.webhooks.delete(key)
    output_success(
        f"Webhook '{webhook}' deleted.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def send(
    ctx: typer.Context,
    webhook: Annotated[
        str,
        typer.Argument(help="Webhook name or key."),
    ],
    message: Annotated[
        str | None,
        typer.Option(
            "--message",
            "-m",
            help="JSON message body to send.",
        ),
    ] = None,
) -> None:
    """Send a test message to a webhook."""
    vctx = get_context(ctx)
    key = resolve_resource_id(vctx.client.webhooks, webhook, "webhook")

    kwargs: dict[str, Any] = {}
    if message is not None:
        kwargs["message"] = message

    vctx.client.webhooks.send(key, **kwargs)
    output_success(
        f"Message sent to webhook '{webhook}'.",
        quiet=vctx.quiet,
    )


@app.command()
@handle_errors()
def history(
    ctx: typer.Context,
    webhook: Annotated[
        str | None,
        typer.Option(
            "--webhook",
            "-w",
            help="Filter by webhook name or key.",
        ),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by status.",
        ),
    ] = None,
    pending: Annotated[
        bool,
        typer.Option(
            "--pending",
            help="Show only pending deliveries.",
        ),
    ] = False,
    failed: Annotated[
        bool,
        typer.Option(
            "--failed",
            help="Show only failed deliveries.",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            help="Maximum number of results.",
        ),
    ] = None,
) -> None:
    """Show webhook delivery history."""
    vctx = get_context(ctx)

    kwargs: dict[str, Any] = {}
    if webhook is not None:
        wh_key = resolve_resource_id(vctx.client.webhooks, webhook, "webhook")
        kwargs["webhook_key"] = wh_key
    if status is not None:
        kwargs["status"] = status
    if pending:
        kwargs["pending"] = True
    if failed:
        kwargs["failed"] = True
    if limit is not None:
        kwargs["limit"] = limit

    entries = vctx.client.webhooks.history(**kwargs)

    output_result(
        [_history_to_dict(e) for e in entries],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=HISTORY_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
