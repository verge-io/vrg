"""Certificate management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from verge_cli.columns import CERTIFICATE_COLUMNS
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action

app = typer.Typer(
    name="certificate",
    help="Manage TLS/SSL certificates.",
    no_args_is_help=True,
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
    """List certificates."""
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
    """Get certificate details."""
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
    """Create a new certificate.

    For manual certificates (uploading PEM files), use 'vrg certificate import' instead.
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
    """Import a manual certificate from PEM files."""
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
    """Update a certificate."""
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
    """Delete a certificate."""
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

    Self-signed: regenerates the certificate.
    Let's Encrypt: triggers ACME renewal.
    Manual: not supported (upload new keys via update instead).
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
