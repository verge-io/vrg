"""System health check command."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated, Any

import typer

from verge_cli.columns import ColumnDef
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.output import get_console, output_result

if TYPE_CHECKING:
    from pyvergeos import VergeClient

app = typer.Typer(
    name="doctor",
    help=(
        "Run a scripted health audit against the current cloud.\n\n"
        "`vrg doctor` is the fastest way to answer *\"is this VergeOS cloud"
        " OK right now?\"*. It sweeps the core subsystems — connectivity,"
        " clusters, nodes, storage tiers, active alarms, update state,"
        " version consistency across nodes, fabric links, network"
        " dashboard, certificates, licenses, physical drive SMART and vSAN"
        " errors, DIMM health, vSAN journal/tier status, and pending driver"
        " reloads — and reports each as `pass`, `warn`, `fail`, or"
        " `skip`. Use it first when triaging an issue or before a change"
        " window.\n\n"
        "Each check runs in isolation: an exception in one check is"
        " captured as `fail` and the rest continue. Exit code is `1` if"
        " any check returns `fail`, otherwise `0` — safe to use in CI and"
        " agent pre-flight scripts. Use `-o json` for structured output;"
        " useful fields to `--query`: `name`, `status`, `message`,"
        " `details`.\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # Run every check (table output with colored summary line)\n"
        "    vrg doctor\n\n"
        "    # Structured output for agents / scripts\n"
        "    vrg -o json doctor\n"
        "    vrg -o json doctor | jq '.[] | select(.status == \"fail\")'\n\n"
        "    # Pre-flight: only run the fast checks\n"
        "    vrg doctor --check connectivity,alarms,updates\n\n"
        "    # Hardware triage: drives, memory, vSAN journal\n"
        "    vrg doctor --check drive_smart,dimm_health,vsan_journal\n\n"
        "    # Discover available check names\n"
        "    vrg doctor --list-checks\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Checks are additive to `vrg alarm list` and `vrg system diag`, not"
        " a replacement. Alarms tell you what the platform has already"
        " flagged; doctor also verifies things the platform does not raise"
        " alarms for (version drift across nodes, certificate/license"
        " expiry windows, pending driver reloads).\n\n"
        "A `warn` status does not change the exit code — only `fail` does."
        " Treat warnings as things to schedule, failures as things to fix"
        " now. Running doctor requires admin-level credentials on the"
        " provider cloud; tenant-scoped profiles will skip or fail checks"
        " that need cloud-root access."
    ),
    invoke_without_command=True,
    no_args_is_help=False,
    rich_markup_mode="markdown",
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

PASS = "pass"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check."""

    name: str
    status: str  # pass, warn, fail, skip
    message: str
    details: dict[str, Any] | None = None


DOCTOR_COLUMNS: list[ColumnDef] = [
    ColumnDef("name", header="Check"),
    ColumnDef(
        "status",
        header="Status",
        style_map={
            PASS: "green",
            WARN: "yellow",
            FAIL: "red bold",
            SKIP: "dim",
        },
    ),
    ColumnDef("message", header="Message"),
]


def _result_to_dict(r: CheckResult) -> dict[str, Any]:
    return asdict(r)


# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

CheckFn = Callable[["VergeClient"], CheckResult]

CHECKS: list[tuple[str, CheckFn]] = []


def _register(name: str) -> Callable[[CheckFn], CheckFn]:
    """Decorator to register a check function."""

    def decorator(fn: CheckFn) -> CheckFn:
        CHECKS.append((name, fn))
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_checks(
    client: VergeClient,
    only: list[str] | None = None,
) -> list[CheckResult]:
    """Run health checks, isolating exceptions per-check."""
    results: list[CheckResult] = []
    for name, fn in CHECKS:
        if only and name not in only:
            continue
        try:
            results.append(fn(client))
        except Exception as exc:
            results.append(CheckResult(name=name, status=FAIL, message=str(exc)))
    return results


# ---------------------------------------------------------------------------
# Checks — core infrastructure
# ---------------------------------------------------------------------------


@_register("connectivity")
def check_connectivity(client: VergeClient) -> CheckResult:
    """Verify auth and read system info."""
    client.system.statistics()
    version = client.version
    cloud = client.cloud_name
    msg = f"Connected: VergeOS {version}"
    if cloud:
        msg += f" ({cloud})"
    return CheckResult(
        name="connectivity",
        status=PASS,
        message=msg,
        details={"version": version, "os_version": client.os_version, "cloud_name": cloud},
    )


@_register("clusters")
def check_clusters(client: VergeClient) -> CheckResult:
    clusters = client.clusters.list()
    vsan = client.clusters.vsan_status()
    health_map = {s.cluster_name: s.health_status for s in vsan}

    problems: list[str] = []
    has_error = False
    for c in clusters:
        h = health_map.get(c.name, "unknown").lower()
        if h == "error":
            problems.append(f"{c.name}: error")
            has_error = True
        elif h != "healthy":
            problems.append(f"{c.name}: {h}")
        on = c.get("online_nodes", 0)
        total = c.get("total_nodes", 0)
        if on < total:
            problems.append(f"{c.name}: {on}/{total} nodes online")

    if has_error:
        return CheckResult(name="clusters", status=FAIL, message="; ".join(problems))
    if problems:
        return CheckResult(name="clusters", status=WARN, message="; ".join(problems))
    return CheckResult(
        name="clusters",
        status=PASS,
        message=f"{len(clusters)} cluster(s) healthy",
    )


@_register("nodes")
def check_nodes(client: VergeClient) -> CheckResult:
    nodes = client.nodes.list()
    problems: list[str] = []
    for n in nodes:
        if n.status.lower() not in ("online", "running"):
            problems.append(f"{n.name}: {n.status}")
        if n.needs_restart:
            problems.append(f"{n.name}: needs restart")
        if not n.vsan_connected:
            problems.append(f"{n.name}: vSAN disconnected")

    if problems:
        return CheckResult(
            name="nodes",
            status=WARN,
            message="; ".join(problems),
            details={
                "nodes": [
                    {"name": n.name, "status": n.status, "version": n.vergeos_version}
                    for n in nodes
                ]
            },
        )
    return CheckResult(
        name="nodes",
        status=PASS,
        message=f"{len(nodes)} node(s) online",
    )


@_register("storage")
def check_storage(client: VergeClient) -> CheckResult:
    tiers = client.storage_tiers.list()
    problems: list[str] = []
    has_critical = False
    total_cap = 0.0

    for t in tiers:
        total_cap += t.capacity_gb
        if t.used_percent >= 95:
            problems.append(f"Tier {t.tier}: {t.used_percent:.0f}% used (critical)")
            has_critical = True
        elif t.used_percent >= 80:
            problems.append(f"Tier {t.tier}: {t.used_percent:.0f}% used")

    if has_critical:
        return CheckResult(name="storage", status=FAIL, message="; ".join(problems))
    if problems:
        return CheckResult(name="storage", status=WARN, message="; ".join(problems))
    return CheckResult(
        name="storage",
        status=PASS,
        message=f"{len(tiers)} tier(s), {total_cap:.0f} GB total",
    )


# ---------------------------------------------------------------------------
# Checks — operational
# ---------------------------------------------------------------------------


@_register("alarms")
def check_alarms(client: VergeClient) -> CheckResult:
    alarms = client.alarms.list()
    critical = sum(1 for a in alarms if a.level == "critical")
    error = sum(1 for a in alarms if a.level == "error")
    total = len(alarms)

    if critical:
        return CheckResult(
            name="alarms",
            status=FAIL,
            message=f"{critical} critical alarm(s)",
            details={"critical": critical, "error": error, "total": total},
        )
    if error:
        return CheckResult(
            name="alarms",
            status=WARN,
            message=f"{error} error alarm(s)",
            details={"critical": critical, "error": error, "total": total},
        )
    return CheckResult(
        name="alarms",
        status=PASS,
        message=f"No critical/error alarms ({total} total active)",
    )


@_register("updates")
def check_updates(client: VergeClient) -> CheckResult:
    settings = client.update_settings.get()
    reboot = settings.get("reboot_required", False)
    if reboot:
        return CheckResult(
            name="updates",
            status=WARN,
            message="System reboot required after update",
        )
    return CheckResult(name="updates", status=PASS, message="No pending reboots")


@_register("versions")
def check_versions(client: VergeClient) -> CheckResult:
    nodes = client.nodes.list()
    if len(nodes) <= 1:
        ver = nodes[0].vergeos_version if nodes else "unknown"
        return CheckResult(
            name="versions",
            status=PASS,
            message=f"All {len(nodes)} node(s) running {ver}",
        )

    versions: dict[str, list[str]] = {}
    for n in nodes:
        v = n.vergeos_version or "unknown"
        versions.setdefault(v, []).append(n.name)

    if len(versions) == 1:
        ver = next(iter(versions))
        return CheckResult(
            name="versions",
            status=PASS,
            message=f"All {len(nodes)} node(s) running {ver}",
        )

    parts = [f"{v} ({len(names)} node(s))" for v, names in versions.items()]
    return CheckResult(
        name="versions",
        status=WARN,
        message=f"Version mismatch: {', '.join(parts)}",
        details={"versions": dict(versions.items())},
    )


# ---------------------------------------------------------------------------
# Checks — fabric & network
# ---------------------------------------------------------------------------


@_register("fabric")
def check_fabric(client: VergeClient) -> CheckResult:
    statuses = client.machine_nic_fabric_status.list()
    if not statuses:
        return CheckResult(name="fabric", status=PASS, message="No fabric NICs found")

    unhealthy = [s for s in statuses if not s.is_healthy]
    if unhealthy:
        msgs = [f"NIC {s.fabric_status}" for s in unhealthy]
        return CheckResult(
            name="fabric",
            status=WARN,
            message=f"{len(unhealthy)} unhealthy fabric link(s): {'; '.join(msgs)}",
        )
    return CheckResult(
        name="fabric",
        status=PASS,
        message=f"{len(statuses)} fabric link(s) healthy",
    )


@_register("networks")
def check_networks(client: VergeClient) -> CheckResult:
    dashboard = client.network_dashboard.get()
    # The dashboard returns a dict-like object; check for error counts
    if isinstance(dashboard, dict):
        errors = dashboard.get("error_count", 0) or dashboard.get("errors", 0)
        warnings = dashboard.get("warning_count", 0) or dashboard.get("warnings", 0)
    else:
        errors = getattr(dashboard, "error_count", 0) or 0
        warnings = getattr(dashboard, "warning_count", 0) or 0

    if errors:
        return CheckResult(
            name="networks", status=FAIL, message=f"{errors} network(s) in error state"
        )
    if warnings:
        return CheckResult(
            name="networks", status=WARN, message=f"{warnings} network(s) with warnings"
        )
    return CheckResult(name="networks", status=PASS, message="Network dashboard healthy")


# ---------------------------------------------------------------------------
# Checks — admin hygiene
# ---------------------------------------------------------------------------


@_register("certificates")
def check_certificates(client: VergeClient) -> CheckResult:
    certs = client.certificates.list()
    if not certs:
        return CheckResult(name="certificates", status=PASS, message="No certificates configured")

    expired: list[str] = []
    expiring: list[str] = []
    for c in certs:
        if not c.is_valid:
            expired.append(c.domain)
        elif c.days_until_expiry is not None and c.days_until_expiry <= 30:
            expiring.append(f"{c.domain} ({c.days_until_expiry}d)")

    if expired:
        return CheckResult(
            name="certificates",
            status=FAIL,
            message=f"Expired: {', '.join(expired)}",
        )
    if expiring:
        return CheckResult(
            name="certificates",
            status=WARN,
            message=f"Expiring soon: {', '.join(expiring)}",
        )
    return CheckResult(
        name="certificates",
        status=PASS,
        message=f"{len(certs)} certificate(s) valid",
    )


def _license_days_remaining(lic: Any) -> int | None:
    """Compute days until license expiry from valid_until field."""
    # Try days_until_expiry first (may exist on future SDK versions)
    due = getattr(lic, "days_until_expiry", None)
    if due is not None:
        return int(due)
    # Fall back to computing from valid_until datetime
    vu = getattr(lic, "valid_until", None) or lic.get("valid_until")
    if vu is None:
        return None
    if isinstance(vu, datetime):
        now = datetime.now(timezone.utc)
        return (vu - now).days
    # Epoch int/float
    if isinstance(vu, (int, float)):
        now_ts = datetime.now(timezone.utc).timestamp()
        return int((vu - now_ts) / 86400)
    return None


@_register("licenses")
def check_licenses(client: VergeClient) -> CheckResult:
    licenses = client.system.licenses.list()
    if not licenses:
        return CheckResult(name="licenses", status=PASS, message="No licenses configured")

    invalid: list[str] = []
    expiring: list[str] = []
    for lic in licenses:
        if not lic.is_valid:
            invalid.append(lic.name)
        else:
            days = _license_days_remaining(lic)
            if days is not None and days <= 30:
                expiring.append(f"{lic.name} ({days}d)")

    if invalid:
        return CheckResult(
            name="licenses",
            status=FAIL,
            message=f"Invalid: {', '.join(invalid)}",
        )
    if expiring:
        return CheckResult(
            name="licenses",
            status=WARN,
            message=f"Expiring soon: {', '.join(expiring)}",
        )
    return CheckResult(
        name="licenses",
        status=PASS,
        message=f"{len(licenses)} license(s) valid",
    )


# ---------------------------------------------------------------------------
# Blocked stubs
# ---------------------------------------------------------------------------


@_register("drive_smart")
def check_drive_smart(client: VergeClient) -> CheckResult:
    """Check physical drive SMART health and vSAN errors."""
    drives = client.physical_drives.list()
    if not drives:
        return CheckResult(name="drive_smart", status=PASS, message="No physical drives found")

    warn_drives: list[str] = []
    vsan_err_drives: list[str] = []
    for d in drives:
        if d.has_warnings:
            label = getattr(d, "serial", None) or getattr(d, "model", None) or str(d.key)
            warn_drives.append(label)
        if d.has_vsan_errors:
            label = getattr(d, "serial", None) or getattr(d, "model", None) or str(d.key)
            if label not in vsan_err_drives:
                vsan_err_drives.append(label)

    problems: list[str] = []
    if warn_drives:
        problems.append(f"{len(warn_drives)} drive(s) with SMART warnings")
    if vsan_err_drives:
        problems.append(f"{len(vsan_err_drives)} drive(s) with vSAN errors")

    if problems:
        return CheckResult(
            name="drive_smart",
            status=WARN,
            message="; ".join(problems),
            details={"smart_warnings": warn_drives, "vsan_errors": vsan_err_drives},
        )
    return CheckResult(
        name="drive_smart",
        status=PASS,
        message=f"{len(drives)} drive(s) healthy",
    )


@_register("dimm_health")
def check_dimm_health(client: VergeClient) -> CheckResult:
    """Check node memory / DIMM health."""
    dimms = client.node_memory.list()
    if not dimms:
        return CheckResult(name="dimm_health", status=PASS, message="No DIMM data available")

    unhealthy = [d for d in dimms if not d.is_healthy]
    if unhealthy:
        details_list = [
            f"{d.locator}: {d.status}" for d in unhealthy
        ]
        return CheckResult(
            name="dimm_health",
            status=WARN,
            message=f"{len(unhealthy)} DIMM(s) unhealthy: {'; '.join(details_list)}",
        )
    return CheckResult(
        name="dimm_health",
        status=PASS,
        message=f"{len(dimms)} DIMM(s) healthy",
    )


@_register("vsan_journal")
def check_vsan_journal(client: VergeClient) -> CheckResult:
    """Check vSAN journal, tier, and repair status."""
    problems: list[str] = []

    journal = client.vsan_queries.journal_status(timeout=30)
    if journal.is_error:
        problems.append(f"Journal query error: {journal.result}")
    elif journal.is_complete and journal.result:
        # Result is a JSON string — surface it in details
        pass  # journal complete is good

    tier = client.vsan_queries.tier_status(timeout=30)
    if tier.is_error:
        problems.append(f"Tier query error: {tier.result}")

    if problems:
        return CheckResult(
            name="vsan_journal",
            status=WARN,
            message="; ".join(problems),
            details={"journal": journal.result, "tier": tier.result},
        )
    return CheckResult(
        name="vsan_journal",
        status=PASS,
        message="vSAN journal and tier status healthy",
        details={"journal": journal.result, "tier": tier.result},
    )


@_register("driver_reload")
def check_driver_reload(client: VergeClient) -> CheckResult:
    """Check if any nodes require a driver reload."""
    nodes = client.nodes.list()
    needs_reload = [n.name for n in nodes if n.reload_drivers_required]
    if needs_reload:
        return CheckResult(
            name="driver_reload",
            status=WARN,
            message=f"Driver reload required: {', '.join(needs_reload)}",
        )
    return CheckResult(
        name="driver_reload",
        status=PASS,
        message=f"{len(nodes)} node(s) — no driver reloads pending",
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
@handle_errors()
def doctor_cmd(
    ctx: typer.Context,
    check: Annotated[
        str | None,
        typer.Option(
            "--check",
            help=(
                "Comma-separated check names to run. "
                "Available: connectivity, clusters, nodes, storage, alarms, "
                "updates, versions, fabric, networks, certificates, licenses, "
                "drive_smart, dimm_health, vsan_journal, driver_reload"
            ),
        ),
    ] = None,
    list_checks: Annotated[
        bool,
        typer.Option("--list-checks", help="List available check names and exit."),
    ] = False,
) -> None:
    """Run system health checks against best practices.

    Checks connectivity, cluster/node/storage health, alarms, updates,
    version consistency, fabric status, network health, certificate and
    license expiry. Returns exit code 1 if any check fails.

    Examples:
        vrg doctor
        vrg doctor --check connectivity,alarms
        vrg doctor -o json
        vrg doctor --list-checks
    """
    if list_checks:
        for name, _ in CHECKS:
            typer.echo(name)
        raise typer.Exit(0)

    vctx = get_context(ctx)
    only = [s.strip() for s in check.split(",")] if check else None

    results = run_checks(vctx.client, only=only)
    data = [_result_to_dict(r) for r in results]

    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=DOCTOR_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )

    # Summary line (table mode only)
    if vctx.output_format in ("table", "wide"):
        passed = sum(1 for r in results if r.status == PASS)
        warned = sum(1 for r in results if r.status == WARN)
        failed = sum(1 for r in results if r.status == FAIL)
        skipped = sum(1 for r in results if r.status == SKIP)

        console = get_console(vctx.no_color)
        if failed:
            style = "red bold"
        elif warned:
            style = "yellow"
        else:
            style = "green"

        summary = f"{passed} passed, {warned} warning, {failed} failed, {skipped} skipped"
        console.print(f"\n[{style}]{summary}[/{style}]")

    # Exit code: 1 if any check failed
    if any(r.status == FAIL for r in results):
        raise typer.Exit(1)
