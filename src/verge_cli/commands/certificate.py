"""Certificate management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from verge_cli.columns import CERTIFICATE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="certificate",
    help=(
        "Manage TLS/SSL certificates on VergeOS.\n\n"
        "Certificates secure the VergeOS web UI and API — every system runs"
        " HTTPS and must be configured with at least one certificate. VergeOS"
        " supports three types: **self-signed** (auto-generated on install,"
        " kept for local console fallback on the `Verge-API` interface),"
        " **letsencrypt** (ACME-based, requires a publicly resolvable domain"
        " and auto-renews), and **manual** (uploaded PEM files from any"
        " CA). Since v26, a system may carry multiple certificates bound to"
        " different listeners.\n\n"
        "Certificates are referenced by numeric `$key` or by **domain**"
        " — there is no separate `name` field. Use `-o json` for parsing;"
        " useful fields for `--query` include `$key`, `domain`, `type`,"
        " `valid`, and `days_until_expiry`. The `expires` field is a Unix"
        " epoch. Two or more certificates sharing a domain raise exit"
        " code 7 (multiple matches) on `get`, `update`, `delete`, and"
        " `renew` — disambiguate by numeric `$key`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List every certificate\n"
        "    vrg certificate list\n\n"
        "    # Machine-readable output for agents\n"
        "    vrg -o json certificate list\n\n"
        "    # Narrow the list\n"
        "    vrg certificate list --type letsencrypt\n"
        "    vrg certificate list --expiring-in 30\n"
        "    vrg certificate list --expired\n\n"
        "    # Inspect one certificate (by $key or domain)\n"
        "    vrg -o json certificate get verge.example.com\n"
        "    vrg certificate get 1 --show-keys\n\n"
        "    # Request a Let's Encrypt certificate\n"
        "    vrg certificate create --type letsencrypt \\\n"
        "        --domain verge.example.com --contact-user 3 --agree-tos\n\n"
        "    # Install a CA-issued certificate from PEM files\n"
        "    vrg certificate import --domain verge.example.com \\\n"
        "        --public-key ./fullchain.pem --private-key ./privkey.pem\n\n"
        "    # Force-renew a certificate (self-signed regenerates, Let's\n"
        "    # Encrypt triggers ACME immediately)\n"
        "    vrg certificate renew verge.example.com --force\n\n"
        "    # Delete a certificate (cannot be undone)\n"
        "    vrg certificate delete old.example.com --yes\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Use `create` for self-signed and Let's Encrypt certificates, and"
        " `import` for manual certificates — `create --type manual` is"
        " rejected because PEM file arguments only exist on `import`."
        " `renew` regenerates self-signed certificates and triggers ACME"
        " renewal for Let's Encrypt; manual certificates cannot be renewed"
        " (upload replacement keys via `update` instead). `--show-keys` on"
        " `get` includes the PEM public key, private key, and chain in the"
        " output — treat that output as sensitive."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

# Map CLI type names to SDK cert_type parameter values
_CLI_TYPE_TO_SDK: dict[str, str] = {
    "self-signed": "SelfSigned",
    "letsencrypt": "LetsEncrypt",
    "manual": "Manual",
}


def _resolve_certificate(client: Any, identifier: str) -> int:
    """Resolve certificate identifier (key or domain) to key.

    Certificates use domain-based lookup instead of name-based resolve_resource_id.
    """
    if identifier.isdigit():
        cert = client.certificates.get(key=int(identifier))
    else:
        cert = client.certificates.get(domain=identifier)
    return int(cert.key)


def _read_pem_file(path: str) -> str:
    """Read PEM file contents."""
    file_path = Path(path)
    if not file_path.exists():
        raise typer.BadParameter(f"File not found: {path}")
    return file_path.read_text()


def _cert_to_dict(cert: Any, include_keys: bool = False) -> dict[str, Any]:
    """Convert SDK Certificate object to output dict."""
    result: dict[str, Any] = {
        "$key": int(cert.key),
        "domain": cert.domain,
        "domain_list": cert.get("domainlist", ""),
        "description": cert.get("description", ""),
        "type": cert.get("type", ""),
        "type_display": cert.cert_type_display,
        "key_type": cert.get("key_type", ""),
        "key_type_display": cert.key_type_display,
        "valid": cert.is_valid,
        "days_until_expiry": cert.days_until_expiry,
        "expires": cert.get("expires"),
        "created": cert.get("created"),
        "autocreated": cert.get("autocreated", False),
    }
    if include_keys:
        result["public"] = cert.get("public", "")
        result["private"] = cert.get("private", "")
        result["chain"] = cert.get("chain", "")
    return result


@app.command("list")
@handle_errors()
def cert_list(
    ctx: typer.Context,
    filter: Annotated[
        str | None,
        typer.Option("--filter", help="OData filter expression."),
    ] = None,
    cert_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by type (manual, letsencrypt, self-signed).",
        ),
    ] = None,
    valid: Annotated[
        bool,
        typer.Option("--valid", help="Show only valid (non-expired) certificates."),
    ] = False,
    expired: Annotated[
        bool,
        typer.Option("--expired", help="Show only expired certificates."),
    ] = False,
    expiring_in: Annotated[
        int | None,
        typer.Option("--expiring-in", help="Show certificates expiring within N days."),
    ] = None,
) -> None:
    """List certificates.

    Examples:

        vrg certificate list
        vrg -o json certificate list
        vrg certificate list --type letsencrypt
        vrg certificate list --expiring-in 30
        vrg certificate list --expired

    `--valid` and `--expired` are mutually exclusive. `--expiring-in N`
    shows certificates that expire within N days.
    """
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.certificates.list(), _cert_to_dict, CERTIFICATE_COLUMNS
        )
        return
    vctx = get_context(ctx)

    if valid and expired:
        typer.echo("Error: --valid and --expired are mutually exclusive.", err=True)
        raise typer.Exit(2)

    # Determine which SDK method to call
    if expired:
        certs = vctx.client.certificates.list_expired()
    elif valid:
        certs = vctx.client.certificates.list_valid()
    elif expiring_in is not None:
        certs = vctx.client.certificates.list_expiring(days=expiring_in)
    elif cert_type is not None:
        sdk_type = _CLI_TYPE_TO_SDK.get(cert_type, cert_type)
        certs = vctx.client.certificates.list(cert_type=sdk_type, filter=filter)
    else:
        certs = vctx.client.certificates.list(filter=filter)

    output_result(
        [_cert_to_dict(c) for c in certs],
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CERTIFICATE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def cert_get(
    ctx: typer.Context,
    cert: Annotated[str, typer.Argument(help="Certificate key or domain name.")],
    show_keys: Annotated[
        bool,
        typer.Option("--show-keys", help="Include PEM certificate/key/chain in output."),
    ] = False,
) -> None:
    """Get certificate details.

    Examples:

        vrg certificate get verge.example.com
        vrg -o json certificate get 1
        vrg certificate get verge.example.com --show-keys

    Accepts a numeric `$key` or a domain. `--show-keys` includes the PEM
    public key, private key, and chain in the output — treat as sensitive.
    """
    vctx = get_context(ctx)

    if cert.isdigit():
        cert_obj = vctx.client.certificates.get(key=int(cert), include_keys=show_keys)
    else:
        cert_obj = vctx.client.certificates.get(domain=cert, include_keys=show_keys)

    output_result(
        _cert_to_dict(cert_obj, include_keys=show_keys),
        output_format=vctx.output_format,
        query=vctx.query,
        columns=CERTIFICATE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("create")
@handle_errors()
def cert_create(
    ctx: typer.Context,
    domain: Annotated[str, typer.Option("--domain", "-d", help="Primary domain name.")],
    cert_type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help="Certificate type (self-signed, letsencrypt, manual).",
        ),
    ] = "self-signed",
    domains: Annotated[
        str | None,
        typer.Option("--domains", help="Comma-separated Subject Alternative Names."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="Certificate description."),
    ] = None,
    key_type: Annotated[
        str | None,
        typer.Option("--key-type", help="Key type (ecdsa, rsa)."),
    ] = None,
    rsa_key_size: Annotated[
        int | None,
        typer.Option("--rsa-key-size", help="RSA key size (2048, 3072, 4096)."),
    ] = None,
    acme_server: Annotated[
        str | None,
        typer.Option("--acme-server", help="ACME server URL (Let's Encrypt)."),
    ] = None,
    contact_user: Annotated[
        int | None,
        typer.Option("--contact-user", help="Contact user key (Let's Encrypt)."),
    ] = None,
    agree_tos: Annotated[
        bool,
        typer.Option("--agree-tos", help="Agree to Let's Encrypt Terms of Service."),
    ] = False,
) -> None:
    """Create a new certificate (self-signed or Let's Encrypt).

    Examples:

        # Self-signed (default)
        vrg certificate create --domain verge.internal

        # Let's Encrypt — domain must be publicly resolvable
        vrg certificate create --type letsencrypt \\
            --domain verge.example.com --contact-user 3 --agree-tos

        # Custom ACME server
        vrg certificate create --type letsencrypt \\
            --domain verge.example.com --contact-user 3 --agree-tos \\
            --acme-server https://ca.internal/acme/acme/directory

    For manual (CA-issued) certificates, use `vrg certificate import` —
    `--type manual` is rejected here because PEM file flags only exist on
    `import`.
    """
    vctx = get_context(ctx)

    sdk_type = _CLI_TYPE_TO_SDK.get(cert_type, cert_type)

    if sdk_type == "Manual":
        typer.echo(
            "Error: Use 'vrg certificate import' for manual certificates with PEM files.",
            err=True,
        )
        raise typer.Exit(2)

    kwargs: dict[str, Any] = {
        "domain": domain,
        "cert_type": sdk_type,
    }
    if domains:
        kwargs["domain_list"] = [d.strip() for d in domains.split(",")]
    if description is not None:
        kwargs["description"] = description
    if key_type is not None:
        kwargs["key_type"] = key_type.upper()
    if rsa_key_size is not None:
        kwargs["rsa_key_size"] = rsa_key_size
    if acme_server is not None:
        kwargs["acme_server"] = acme_server
    if contact_user is not None:
        kwargs["contact_user_key"] = contact_user
    if agree_tos:
        kwargs["agree_tos"] = True

    cert_obj = vctx.client.certificates.create(**kwargs)

    output_success(
        f"Created certificate for '{domain}' (key: {cert_obj.key})",
        quiet=vctx.quiet,
    )

    output_result(
        _cert_to_dict(cert_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("import")
@handle_errors()
def cert_import(
    ctx: typer.Context,
    domain: Annotated[str, typer.Option("--domain", "-d", help="Primary domain name.")],
    public_key: Annotated[
        str,
        typer.Option("--public-key", help="Path to public certificate PEM file."),
    ],
    private_key: Annotated[
        str,
        typer.Option("--private-key", help="Path to private key PEM file."),
    ],
    chain: Annotated[
        str | None,
        typer.Option("--chain", help="Path to certificate chain PEM file."),
    ] = None,
    domains: Annotated[
        str | None,
        typer.Option("--domains", help="Comma-separated Subject Alternative Names."),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", help="Certificate description."),
    ] = None,
) -> None:
    """Import a manual certificate from PEM files.

    Examples:

        vrg certificate import --domain verge.example.com \\
            --public-key ./fullchain.pem \\
            --private-key ./privkey.pem

        # With separate chain file and SANs
        vrg certificate import --domain verge.example.com \\
            --public-key ./cert.pem --private-key ./privkey.pem \\
            --chain ./chain.pem \\
            --domains api.example.com,admin.example.com

    Use this when the certificate was issued by any CA other than a
    Let's Encrypt / ACME provider. `--public-key` may point at a single
    cert or a combined fullchain file; when the chain is in a separate
    file, pass it via `--chain`.
    """
    vctx = get_context(ctx)

    pub_content = _read_pem_file(public_key)
    key_content = _read_pem_file(private_key)
    chain_content = _read_pem_file(chain) if chain else None

    kwargs: dict[str, Any] = {
        "domain": domain,
        "cert_type": "Manual",
        "public_key": pub_content,
        "private_key": key_content,
    }
    if chain_content is not None:
        kwargs["chain"] = chain_content
    if domains:
        kwargs["domain_list"] = [d.strip() for d in domains.split(",")]
    if description is not None:
        kwargs["description"] = description

    cert_obj = vctx.client.certificates.create(**kwargs)

    output_success(
        f"Imported certificate for '{domain}' (key: {cert_obj.key})",
        quiet=vctx.quiet,
    )

    output_result(
        _cert_to_dict(cert_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def cert_update(
    ctx: typer.Context,
    cert: Annotated[str, typer.Argument(help="Certificate key or domain name.")],
    description: Annotated[
        str | None,
        typer.Option("--description", help="New description."),
    ] = None,
    domains: Annotated[
        str | None,
        typer.Option("--domains", help="Comma-separated Subject Alternative Names."),
    ] = None,
    public_key: Annotated[
        str | None,
        typer.Option("--public-key", help="Path to new public certificate PEM file."),
    ] = None,
    private_key: Annotated[
        str | None,
        typer.Option("--private-key", help="Path to new private key PEM file."),
    ] = None,
    chain_file: Annotated[
        str | None,
        typer.Option("--chain", help="Path to new certificate chain PEM file."),
    ] = None,
    key_type: Annotated[
        str | None,
        typer.Option("--key-type", help="Key type (ecdsa, rsa)."),
    ] = None,
    rsa_key_size: Annotated[
        int | None,
        typer.Option("--rsa-key-size", help="RSA key size (2048, 3072, 4096)."),
    ] = None,
    acme_server: Annotated[
        str | None,
        typer.Option("--acme-server", help="ACME server URL."),
    ] = None,
    contact_user: Annotated[
        int | None,
        typer.Option("--contact-user", help="Contact user key."),
    ] = None,
    agree_tos: Annotated[
        bool | None,
        typer.Option("--agree-tos/--no-agree-tos", help="Agree to TOS."),
    ] = None,
) -> None:
    """Update a certificate.

    Examples:

        # Edit metadata
        vrg certificate update verge.example.com \\
            --description 'Primary UI cert'

        # Replace keys on a manual certificate
        vrg certificate update verge.example.com \\
            --public-key ./new-fullchain.pem \\
            --private-key ./new-privkey.pem

        # Add Subject Alternative Names
        vrg certificate update verge.example.com \\
            --domains api.example.com,admin.example.com

    At least one update flag is required. Accepts a numeric `$key` or
    domain to identify the certificate.
    """
    vctx = get_context(ctx)

    key = _resolve_certificate(vctx.client, cert)

    kwargs: dict[str, Any] = {}
    if description is not None:
        kwargs["description"] = description
    if domains is not None:
        kwargs["domain_list"] = [d.strip() for d in domains.split(",")]
    if public_key is not None:
        kwargs["public_key"] = _read_pem_file(public_key)
    if private_key is not None:
        kwargs["private_key"] = _read_pem_file(private_key)
    if chain_file is not None:
        kwargs["chain"] = _read_pem_file(chain_file)
    if key_type is not None:
        kwargs["key_type"] = key_type.upper()
    if rsa_key_size is not None:
        kwargs["rsa_key_size"] = rsa_key_size
    if acme_server is not None:
        kwargs["acme_server"] = acme_server
    if contact_user is not None:
        kwargs["contact_user_key"] = contact_user
    if agree_tos is not None:
        kwargs["agree_tos"] = agree_tos

    if not kwargs:
        typer.echo("No updates specified.", err=True)
        raise typer.Exit(2)

    cert_obj = vctx.client.certificates.update(key, **kwargs)

    output_success(f"Updated certificate (key: {key})", quiet=vctx.quiet)

    output_result(
        _cert_to_dict(cert_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("delete")
@handle_errors()
def cert_delete(
    ctx: typer.Context,
    cert: Annotated[str, typer.Argument(help="Certificate key or domain name.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation.")] = False,
) -> None:
    """Delete a certificate.

    Examples:

        vrg certificate delete old.example.com
        vrg certificate delete 4 --yes

    Destructive. Prompts for confirmation unless `--yes` is passed. Do
    not delete the self-signed certificate bound to the `Verge-API`
    interface unless you have another certificate configured for local
    console access.
    """
    vctx = get_context(ctx)

    key = _resolve_certificate(vctx.client, cert)

    # Fetch for confirmation message
    cert_obj = vctx.client.certificates.get(key=key)
    domain = cert_obj.domain or str(key)

    if not confirm_action(f"Delete certificate '{domain}'?", yes=yes):
        typer.echo("Cancelled.")
        raise typer.Exit(0)

    vctx.client.certificates.delete(key)
    output_success(f"Deleted certificate '{domain}'", quiet=vctx.quiet)


@app.command("renew")
@handle_errors()
def cert_renew(
    ctx: typer.Context,
    cert: Annotated[str, typer.Argument(help="Certificate key or domain name.")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force renewal even if not near expiry."),
    ] = False,
) -> None:
    """Renew or regenerate a certificate.

    Examples:

        # Renew if the system considers it due (typically within 30 days
        # of expiry for Let's Encrypt)
        vrg certificate renew verge.example.com

        # Force immediate renewal regardless of expiry
        vrg certificate renew verge.example.com --force

    Behaviour by type:

    - **self-signed**: regenerates the certificate.
    - **letsencrypt**: triggers ACME renewal; without `--force` the
      request is queued for the next daily renewal cycle.
    - **manual**: not supported — upload replacement keys via
      `vrg certificate update`.
    """
    vctx = get_context(ctx)

    key = _resolve_certificate(vctx.client, cert)
    cert_obj = vctx.client.certificates.renew(key, force=force)

    output_success(f"Renewed certificate '{cert_obj.get('domain', '')}'", quiet=vctx.quiet)

    output_result(
        _cert_to_dict(cert_obj),
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
