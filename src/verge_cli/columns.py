"""Column definitions and styling for CLI output."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class FormatFn(Protocol):
    """Canonical signature for format functions. Must return str, never Text."""

    def __call__(self, value: Any, *, for_csv: bool = False) -> str: ...


@dataclass(frozen=True)
class ColumnDef:
    """Column definition with display and styling hints."""

    key: str
    header: str | None = None
    style_map: Mapping[Any, str] | None = None
    style_fn: Callable[[Any, dict[str, Any]], str | None] | None = None
    default_style: str | None = None
    format_fn: FormatFn | None = None
    normalize_fn: Callable[[Any], Any] | None = None
    wide_only: bool = False

    @property
    def resolved_header(self) -> str:
        """Return the display header, using default if not set."""
        if self.header is not None:
            return self.header
        return self.key.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Shared style maps
# ---------------------------------------------------------------------------

STATUS_STYLES: Mapping[Any, str] = {
    "running": "green",
    "online": "green",
    "healthy": "green",
    "stopped": "dim",
    "offline": "dim",
    "starting": "yellow",
    "stopping": "yellow",
    "paused": "yellow",
    "suspended": "yellow",
    "degraded": "yellow",
    "pending": "yellow",
    "provisioning": "yellow",
    "maintenance": "yellow",
    "error": "red bold",
    "failed": "red bold",
    "unreachable": "red bold",
    "unknown": "dim",
}

FLAG_STYLES: Mapping[Any, str] = {
    True: "yellow bold",
    False: "dim",
}

BOOL_STYLES: Mapping[Any, str] = {
    True: "green",
    False: "red",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def normalize_lower(value: Any) -> Any:
    """Normalize string values to lowercase for style lookups."""
    return str(value).strip().lower() if isinstance(value, str) else value


def format_bool_yn(value: Any, *, for_csv: bool = False) -> str:
    """Format bool as Y/- for flag columns."""
    if isinstance(value, bool):
        if for_csv:
            return "true" if value else "false"
        return "Y" if value else "-"
    if value is None:
        return "" if for_csv else "-"
    return str(value)


def json_serializer(obj: Any) -> str:
    """JSON serializer for datetime and other types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def default_format(value: Any, *, for_csv: bool = False) -> str:
    """Default formatter for cell values."""
    if value is None:
        return "" if for_csv else "-"
    if isinstance(value, bool):
        if for_csv:
            return "true" if value else "false"
        return "yes" if value else "no"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=json_serializer)
    return str(value)


def format_epoch(value: Any, *, for_csv: bool = False) -> str:
    """Format an epoch timestamp as a datetime string."""
    if value is None:
        return "" if for_csv else "-"
    if isinstance(value, (int, float)) and value > 0:
        dt = datetime.fromtimestamp(value)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def format_microseconds(value: Any, *, for_csv: bool = False) -> str:
    """Format microsecond timestamp as datetime string."""
    if value is None:
        return "" if for_csv else "-"
    if isinstance(value, (int, float)) and value > 0:
        dt = datetime.fromtimestamp(value / 1_000_000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def format_epoch_or_never(value: Any, *, for_csv: bool = False) -> str:
    """Format an epoch timestamp, treating 0/None as 'Never'."""
    if value is None or value == 0:
        return "" if for_csv else "Never"
    return format_epoch(value, for_csv=for_csv)


def style_percent_threshold(value: Any, row: dict[str, Any]) -> str | None:
    """Style function for percentage values — red >80, yellow >60."""
    if isinstance(value, (int, float)):
        if value > 80:
            return "red bold"
        if value > 60:
            return "yellow"
    return None


# ---------------------------------------------------------------------------
# Resource column definitions
# ---------------------------------------------------------------------------

VM_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("cpu_cores", header="CPU"),
    ColumnDef("ram", header="RAM (MB)"),
    ColumnDef("cluster_name", header="Cluster"),
    ColumnDef("node_name", header="Node"),
    ColumnDef(
        "needs_restart",
        header="Restart",
        style_map=FLAG_STYLES,
        format_fn=format_bool_yn,
    ),
    # wide-only
    ColumnDef("description", wide_only=True),
    ColumnDef("os_family", header="OS", wide_only=True),
]

NETWORK_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("type"),
    ColumnDef("network", header="CIDR"),
    ColumnDef("ipaddress", header="IP Address"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("running", style_map=BOOL_STYLES, format_fn=format_bool_yn),
    ColumnDef(
        "needs_restart",
        header="Restart",
        style_map=FLAG_STYLES,
        format_fn=format_bool_yn,
    ),
    ColumnDef(
        "needs_rule_apply",
        header="Rules",
        style_map=FLAG_STYLES,
        format_fn=format_bool_yn,
    ),
    ColumnDef(
        "needs_dns_apply",
        header="DNS",
        style_map=FLAG_STYLES,
        format_fn=format_bool_yn,
    ),
    # wide-only
    ColumnDef("description", wide_only=True),
    ColumnDef("gateway", wide_only=True),
    ColumnDef("mtu", wide_only=True),
]

RULE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("direction"),
    ColumnDef("action"),
    ColumnDef("protocol"),
    ColumnDef("source_ip", header="Source"),
    ColumnDef("dest_ports", header="Dest Ports"),
    ColumnDef("enabled", style_map=BOOL_STYLES, format_fn=format_bool_yn),
    ColumnDef("order"),
    # wide-only
    ColumnDef("description", wide_only=True),
    ColumnDef("dest_ip", header="Dest IP", wide_only=True),
    ColumnDef("statistics", header="Stats", style_map=BOOL_STYLES, format_fn=format_bool_yn, wide_only=True),
    ColumnDef("trace", header="Trace", style_map=BOOL_STYLES, format_fn=format_bool_yn, wide_only=True),
    ColumnDef("packets", header="Packets", wide_only=True),
    ColumnDef("bytes", header="Bytes", wide_only=True),
]

ZONE_COLUMNS = [
    ColumnDef("id"),
    ColumnDef("domain"),
    ColumnDef("type"),
    ColumnDef("view_name", header="View"),
    ColumnDef("serial"),
]

RECORD_COLUMNS = [
    ColumnDef("id"),
    ColumnDef("host"),
    ColumnDef("type"),
    ColumnDef("value"),
    ColumnDef("ttl", header="TTL"),
    ColumnDef("priority"),
]

VIEW_COLUMNS = [
    ColumnDef("id"),
    ColumnDef("name"),
    ColumnDef("recursion", style_map=BOOL_STYLES, format_fn=format_bool_yn),
    ColumnDef("match_clients", header="Match Clients"),
]

HOST_COLUMNS = [
    ColumnDef("host"),
    ColumnDef("ip", header="IP"),
    ColumnDef("type"),
]

ALIAS_COLUMNS = [
    ColumnDef("hostname"),
    ColumnDef("ip", header="IP"),
    ColumnDef("description"),
]

LEASE_COLUMNS = [
    ColumnDef("mac", header="MAC"),
    ColumnDef("ip", header="IP"),
    ColumnDef("hostname"),
    ColumnDef("expires"),
    ColumnDef("state"),
]

ADDRESS_COLUMNS = [
    ColumnDef("ip", header="IP"),
    ColumnDef("mac", header="MAC"),
    ColumnDef("interface"),
    ColumnDef("type"),
]

DRIVE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("media"),
    ColumnDef("interface"),
    ColumnDef("size_gb", header="Size (GB)"),
    ColumnDef("tier"),
    ColumnDef("enabled", style_map=BOOL_STYLES, format_fn=format_bool_yn),
]

NIC_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("interface"),
    ColumnDef("network_name", header="Network"),
    ColumnDef("mac_address", header="MAC"),
    ColumnDef("ip_address", header="IP"),
    ColumnDef("enabled", style_map=BOOL_STYLES, format_fn=format_bool_yn),
]

DEVICE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("device_type", header="Type"),
    ColumnDef("enabled", style_map=BOOL_STYLES, format_fn=format_bool_yn),
    ColumnDef("optional", style_map=BOOL_STYLES, format_fn=format_bool_yn),
]

TENANT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("state"),
    ColumnDef(
        "is_isolated",
        header="Isolated",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
    ),
    # wide-only
    ColumnDef("description", wide_only=True),
    ColumnDef("network_name", header="Network", wide_only=True),
    ColumnDef("ui_address_ip", header="UI IP", wide_only=True),
    ColumnDef("uuid", wide_only=True),
]

CLUSTER_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("total_nodes", header="Nodes"),
    ColumnDef("online_nodes", header="Online"),
    ColumnDef("total_ram_gb", header="RAM GB"),
    ColumnDef("ram_used_percent", header="RAM %", style_fn=style_percent_threshold),
    ColumnDef("total_cores", header="Cores"),
    # wide-only
    ColumnDef("running_machines", header="Running VMs", wide_only=True),
    ColumnDef(
        "is_compute",
        header="Compute",
        wide_only=True,
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
    ),
    ColumnDef(
        "is_storage",
        header="Storage",
        wide_only=True,
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
    ),
]

NODE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("cluster_name", header="Cluster"),
    ColumnDef("ram_gb", header="RAM GB"),
    ColumnDef("cores"),
    ColumnDef("cpu_usage", header="CPU %", style_fn=style_percent_threshold),
    # wide-only
    ColumnDef(
        "is_physical",
        header="Physical",
        wide_only=True,
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
    ),
    ColumnDef("model", wide_only=True),
    ColumnDef("cpu", header="CPU", wide_only=True),
    ColumnDef("core_temp", header="Temp °C", wide_only=True, style_fn=style_percent_threshold),
    ColumnDef("vergeos_version", header="Version", wide_only=True),
]

NODE_PCI_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("slot"),
    ColumnDef("vendor"),
    ColumnDef("device", header="Device"),
    ColumnDef("driver"),
    ColumnDef("class_display", header="Class"),
]

NODE_GPU_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("slot"),
    ColumnDef("vendor"),
    ColumnDef("device", header="Device"),
    ColumnDef("driver"),
    ColumnDef("max_instances", header="Max Instances"),
]

STORAGE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("tier", header="Tier #"),
    ColumnDef("description"),
    ColumnDef("capacity_gb", header="Capacity GB"),
    ColumnDef("used_gb", header="Used GB"),
    ColumnDef("free_gb", header="Free GB"),
    ColumnDef("used_percent", header="Used %", style_fn=style_percent_threshold),
    # wide-only
    ColumnDef("dedupe_ratio", header="Dedupe", wide_only=True),
    ColumnDef("dedupe_savings_percent", header="Savings %", wide_only=True),
    ColumnDef("read_ops", header="Read IOPS", wide_only=True),
    ColumnDef("write_ops", header="Write IOPS", wide_only=True),
]

VSAN_STATUS_COLUMNS = [
    ColumnDef("cluster_name", header="Cluster"),
    ColumnDef(
        "health_status",
        header="Health",
        style_map={
            "Healthy": "green",
            "Degraded": "yellow",
            "Critical": "red bold",
            "Offline": "red",
        },
    ),
    ColumnDef("total_nodes", header="Nodes"),
    ColumnDef("online_nodes", header="Online"),
    ColumnDef("used_ram_gb", header="RAM Used GB"),
    ColumnDef("online_ram_gb", header="RAM Total GB"),
    ColumnDef("ram_used_percent", header="RAM %", style_fn=style_percent_threshold),
    # wide-only
    ColumnDef("total_cores", header="Cores", wide_only=True),
    ColumnDef("online_cores", header="Online Cores", wide_only=True),
    ColumnDef("used_cores", header="Used Cores", wide_only=True),
    ColumnDef(
        "core_used_percent", header="Core %", wide_only=True, style_fn=style_percent_threshold
    ),
    ColumnDef("running_machines", header="Running VMs", wide_only=True),
]

TENANT_NODE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("cpu_cores", header="CPU"),
    ColumnDef("ram_gb", header="RAM GB"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("is_enabled", header="Enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    # wide-only
    ColumnDef("cluster_name", header="Cluster", wide_only=True),
    ColumnDef("host_node", header="Host Node", wide_only=True),
]

TENANT_STORAGE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("tier_name", header="Tier"),
    ColumnDef("provisioned_gb", header="Provisioned GB"),
    # wide-only
    ColumnDef("used_gb", header="Used GB", wide_only=True),
    ColumnDef(
        "used_percent",
        header="Used %",
        wide_only=True,
        style_fn=style_percent_threshold,
    ),
]

TENANT_NET_BLOCK_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("cidr", header="CIDR"),
    ColumnDef("network_name", header="Network"),
    # wide-only
    ColumnDef("description", wide_only=True),
]

TENANT_EXT_IP_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("ip_address", header="IP"),
    ColumnDef("network_name", header="Network"),
    # wide-only
    ColumnDef("hostname", wide_only=True),
]

TENANT_L2_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("network_name", header="Network"),
    ColumnDef("network_type", header="Type"),
    ColumnDef("is_enabled", header="Enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
]

VM_SNAPSHOT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("created", format_fn=format_epoch),
    ColumnDef("expires", format_fn=format_epoch_or_never),
    # wide-only
    ColumnDef("quiesced", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("description", wide_only=True),
]

TENANT_SNAPSHOT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("created", format_fn=format_epoch),
    ColumnDef("expires", format_fn=format_epoch_or_never),
    # wide-only
    ColumnDef("profile", wide_only=True),
]

TENANT_STATS_COLUMNS = [
    ColumnDef("timestamp", format_fn=format_epoch),
    ColumnDef("cpu_percent", header="CPU %", style_fn=style_percent_threshold),
    ColumnDef("ram_used_mb", header="RAM Used MB"),
    ColumnDef("ram_total_mb", header="RAM Total MB"),
    ColumnDef("disk_read_ops", header="Disk Read IOPS"),
    ColumnDef("disk_write_ops", header="Disk Write IOPS"),
]

TENANT_LOG_COLUMNS = [
    ColumnDef("timestamp", header="Time"),
    ColumnDef("type", header="Type"),
    ColumnDef("message", header="Message"),
]

CLOUD_SNAPSHOT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("created", format_fn=format_epoch),
    ColumnDef("expires", format_fn=format_epoch_or_never),
    # wide-only
    ColumnDef("immutable", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("private", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("description", wide_only=True),
]

CLOUD_SNAPSHOT_VM_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
]

CLOUD_SNAPSHOT_TENANT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
]

SNAPSHOT_PROFILE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description", wide_only=True),
]

SITE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("url", header="URL"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("authentication_status", header="Auth Status"),
    # wide-only
    ColumnDef("config_cloud_snapshots", header="Cloud Snapshots", wide_only=True),
    ColumnDef("description", wide_only=True),
    ColumnDef("domain", wide_only=True),
    ColumnDef("city", wide_only=True),
    ColumnDef("country", wide_only=True),
]

SNAPSHOT_PROFILE_PERIOD_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("frequency"),
    ColumnDef("retention", header="Retention (s)"),
    ColumnDef("min_snapshots", header="Min Snaps"),
    ColumnDef("max_tier", header="Max Tier"),
    # wide-only
    ColumnDef("minute", wide_only=True),
    ColumnDef("hour", wide_only=True),
    ColumnDef("day_of_week", header="Day of Week", wide_only=True),
    ColumnDef("quiesce", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("immutable", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef(
        "skip_missed",
        header="Skip Missed",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
        wide_only=True,
    ),
]

SITE_SYNC_OUTGOING_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("site"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("state"),
    # wide-only
    ColumnDef("encryption", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("compression", format_fn=format_bool_yn, style_map=BOOL_STYLES, wide_only=True),
    ColumnDef("threads", wide_only=True),
    ColumnDef("last_run", format_fn=format_epoch, wide_only=True),
    ColumnDef("destination_tier", header="Dest Tier", wide_only=True),
    ColumnDef("description", wide_only=True),
]

SHARED_OBJECT_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("tenant_name", header="Tenant"),
    ColumnDef("object_type", header="Type"),
    ColumnDef("is_inbox", header="Inbox", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    # wide-only
    ColumnDef("description", wide_only=True),
    ColumnDef("object_id", header="Object ID", wide_only=True),
]

SYSTEM_SETTING_COLUMNS = [
    ColumnDef("key"),
    ColumnDef("value"),
    ColumnDef("default_value", header="Default"),
    ColumnDef("modified", format_fn=format_bool_yn, style_map=FLAG_STYLES),
    # wide-only
    ColumnDef("description", wide_only=True),
]

SYSTEM_LICENSE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("is_valid", header="Valid", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("valid_from", header="Valid From"),
    ColumnDef("valid_until", header="Valid Until"),
    ColumnDef("features"),
    # wide-only
    ColumnDef(
        "auto_renewal",
        header="Auto Renew",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
        wide_only=True,
    ),
    ColumnDef(
        "allow_branding",
        header="Branding",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
        wide_only=True,
    ),
    ColumnDef("note", wide_only=True),
]

SITE_SYNC_SCHEDULE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("sync_name", header="Sync"),
    ColumnDef("profile_period_name", header="Profile Period"),
    ColumnDef("retention", header="Retention (s)"),
    ColumnDef("priority"),
    # wide-only
    ColumnDef(
        "do_not_expire",
        header="No Expire",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
        wide_only=True,
    ),
    ColumnDef("destination_prefix", header="Dest Prefix", wide_only=True),
]

NAS_SERVICE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef(
        "vm_running",
        header="Running",
        format_fn=format_bool_yn,
        style_map={"Yes": "green", "No": "red"},
    ),
    ColumnDef("volume_count", header="Volumes"),
    ColumnDef("vm_cores", header="Cores", wide_only=True),
    ColumnDef("vm_ram", header="RAM (MB)", wide_only=True),
    ColumnDef("max_imports", header="Max Imports", wide_only=True),
    ColumnDef("max_syncs", header="Max Syncs", wide_only=True),
]

CIFS_SETTINGS_COLUMNS = [
    ColumnDef("workgroup"),
    ColumnDef("server_type", header="Server Type"),
    ColumnDef("server_min_protocol", header="Min Protocol"),
    ColumnDef("map_to_guest", header="Guest Mapping"),
    ColumnDef("extended_acl_support", header="Extended ACL", format_fn=format_bool_yn),
    ColumnDef("ad_status", header="AD Status", wide_only=True),
]

NFS_SETTINGS_COLUMNS = [
    ColumnDef("enable_nfsv4", header="NFSv4", format_fn=format_bool_yn),
    ColumnDef("allow_all", header="Allow All", format_fn=format_bool_yn),
    ColumnDef("allowed_hosts", header="Allowed Hosts"),
    ColumnDef("squash"),
    ColumnDef("data_access", header="Access"),
    ColumnDef("anonuid", header="Anon UID", wide_only=True),
    ColumnDef("anongid", header="Anon GID", wide_only=True),
]

USER_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("displayname", header="Display Name"),
    ColumnDef("email"),
    ColumnDef("user_type", header="Type"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    # wide-only
    ColumnDef("last_login", format_fn=format_epoch, wide_only=True),
    ColumnDef(
        "two_factor_enabled",
        header="2FA",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
        wide_only=True,
    ),
    ColumnDef(
        "is_locked",
        header="Locked",
        format_fn=format_bool_yn,
        style_map=FLAG_STYLES,
        wide_only=True,
    ),
    ColumnDef("auth_source_name", header="Auth Source", wide_only=True),
]

GROUP_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description"),
    ColumnDef("email"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("member_count", header="Members"),
    # wide-only
    ColumnDef("created", format_fn=format_epoch, wide_only=True),
]

GROUP_MEMBER_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("member_name", header="Name"),
    ColumnDef("member_type", header="Type"),
    ColumnDef("member_key", header="Member Key"),
]

SITE_SYNC_INCOMING_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("site"),
    ColumnDef("status", style_map=STATUS_STYLES, normalize_fn=normalize_lower),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("state"),
    # wide-only
    ColumnDef("last_sync", format_fn=format_epoch, wide_only=True),
    ColumnDef("min_snapshots", header="Min Snapshots", wide_only=True),
    ColumnDef("description", wide_only=True),
]

PERMISSION_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("identity_name", header="Identity"),
    ColumnDef("table"),
    ColumnDef("row_display", header="Resource"),
    ColumnDef("can_list", header="List", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("can_read", header="Read", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("can_create", header="Create", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("can_modify", header="Modify", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("can_delete", header="Delete", format_fn=format_bool_yn, style_map=BOOL_STYLES),
]

API_KEY_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("user_name", header="User"),
    ColumnDef("created", format_fn=format_epoch),
    ColumnDef("expires", format_fn=format_epoch_or_never),
    ColumnDef("is_expired", header="Expired", format_fn=format_bool_yn, style_map=FLAG_STYLES),
    # wide-only
    ColumnDef("last_login", format_fn=format_epoch, wide_only=True),
    ColumnDef("last_login_ip", header="Last IP", wide_only=True),
    ColumnDef("description", wide_only=True),
]

API_KEY_CREATED_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("user_name", header="User"),
    ColumnDef("secret"),
]

AUTH_SOURCE_COLUMNS = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("driver"),
    ColumnDef(
        "show_on_login", header="Login Menu", format_fn=format_bool_yn, style_map=BOOL_STYLES
    ),
    ColumnDef("debug", header="Debug", format_fn=format_bool_yn, style_map=FLAG_STYLES),
    # wide-only
    ColumnDef("button_icon", header="Icon", wide_only=True),
    ColumnDef("button_bg_color", header="BG Color", wide_only=True),
]

TASK_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("action_display", header="Action"),
    ColumnDef("owner_display", header="Owner"),
    ColumnDef("status", style_map={"running": "green", "idle": "dim", "error": "red bold"}),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    # wide-only
    ColumnDef("last_run", format_fn=format_epoch, wide_only=True),
    ColumnDef("progress", wide_only=True),
    ColumnDef("triggers_count", header="Triggers", wide_only=True),
    ColumnDef("events_count", header="Events", wide_only=True),
    ColumnDef("description", wide_only=True),
    ColumnDef(
        "delete_after_run",
        header="Auto-Delete",
        format_fn=format_bool_yn,
        style_map=FLAG_STYLES,
        wide_only=True,
    ),
]

TASK_SCHEDULE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("repeat_display", header="Repeat"),
    ColumnDef("repeat_iteration", header="Every N"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("active_days", header="Days"),
    # wide-only
    ColumnDef("start_date", wide_only=True),
    ColumnDef("end_date", wide_only=True),
    ColumnDef("start_time_display", header="Start Time", wide_only=True),
    ColumnDef("end_time_display", header="End Time", wide_only=True),
    ColumnDef("day_of_month", header="Day of Month", wide_only=True),
    ColumnDef("description", wide_only=True),
]

TASK_TRIGGER_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("task_display", header="Task"),
    ColumnDef("schedule_display", header="Schedule"),
    ColumnDef(
        "schedule_enabled",
        header="Sch Enabled",
        format_fn=format_bool_yn,
        style_map=BOOL_STYLES,
    ),
    ColumnDef("schedule_repeat", header="Repeat"),
]

SCHEDULE_UPCOMING_COLUMNS: list[ColumnDef] = [
    ColumnDef("execution_time", header="Scheduled Time"),
]

TASK_EVENT_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("event", header="Event"),
    ColumnDef("event_name", header="Event Name"),
    ColumnDef("owner_display", header="Owner"),
    ColumnDef("table", header="Table"),
    ColumnDef("task_display", header="Task"),
    # wide-only
    ColumnDef("owner_key", header="Owner Key", wide_only=True),
    ColumnDef("task_key", header="Task Key", wide_only=True),
]

TASK_SCRIPT_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("description"),
    ColumnDef("task_count", header="Tasks"),
    # wide-only — script code is too long for table, show in get/json only
]

OIDC_APP_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("client_id", header="Client ID"),
    ColumnDef("enabled", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("scopes", header="Scopes"),
    ColumnDef(
        "restrict_access",
        header="Restricted",
        format_fn=format_bool_yn,
        style_map=FLAG_STYLES,
    ),
    # wide-only
    ColumnDef("redirect_uris_display", header="Redirect URIs", wide_only=True),
    ColumnDef("force_auth_source_display", header="Auth Source", wide_only=True),
    ColumnDef("description", wide_only=True),
]

OIDC_USER_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Entry Key"),
    ColumnDef("user_display", header="User"),
    ColumnDef("user_key", header="User Key"),
]

OIDC_GROUP_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Entry Key"),
    ColumnDef("group_display", header="Group"),
    ColumnDef("group_key", header="Group Key"),
]

OIDC_LOG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("timestamp", format_fn=format_microseconds),
    ColumnDef(
        "level",
        style_map={
            "audit": "cyan",
            "message": "dim",
            "warning": "yellow",
            "error": "red bold",
            "critical": "red bold",
        },
    ),
    ColumnDef("text", header="Message"),
    # wide-only
    ColumnDef("user_display", header="User", wide_only=True),
]

CERTIFICATE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("domain"),
    ColumnDef("type_display", header="Type"),
    ColumnDef("key_type_display", header="Key Type"),
    ColumnDef("valid", header="Valid", format_fn=format_bool_yn, style_map=BOOL_STYLES),
    ColumnDef("days_until_expiry", header="Expires In"),
    # wide-only
    ColumnDef("domain_list", header="SANs", wide_only=True),
    ColumnDef("expires", format_fn=format_epoch, wide_only=True),
    ColumnDef("description", wide_only=True),
    ColumnDef(
        "autocreated",
        header="Auto",
        format_fn=format_bool_yn,
        style_map=FLAG_STYLES,
        wide_only=True,
    ),
]

GPU_PROFILE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("type"),
    ColumnDef("framebuffer"),
    ColumnDef("max_resolution", header="Max Resolution"),
    ColumnDef("max_instance", header="Max Instances"),
    ColumnDef("grid_license", header="Grid License"),
]

GPU_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("node_name", header="Node"),
    ColumnDef("mode_display", header="Mode"),
    ColumnDef("nvidia_vgpu_profile_display", header="vGPU Profile"),
    ColumnDef("instances_count", header="Instances"),
    ColumnDef("max_instances", header="Max Instances"),
]

GPU_STATS_COLUMNS: list[ColumnDef] = [
    ColumnDef("gpus_total", header="GPUs Total"),
    ColumnDef("gpus", header="GPUs Used"),
    ColumnDef("gpus_idle", header="GPUs Idle"),
    ColumnDef("vgpus_total", header="vGPUs Total"),
    ColumnDef("vgpus", header="vGPUs Used"),
    ColumnDef("vgpus_idle", header="vGPUs Idle"),
]

GPU_INSTANCE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("machine_name", header="Machine"),
    ColumnDef("machine_type_display", header="Type"),
    ColumnDef("mode_display", header="Mode"),
    ColumnDef("machine_device_status", header="Device Status"),
]

GPU_DEVICE_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef("node_name", header="Node"),
    ColumnDef("slot"),
    ColumnDef("vendor"),
    ColumnDef("device", header="Device"),
    ColumnDef("driver"),
    ColumnDef("max_instances", header="Max Instances"),
]


# ---------------------------------------------------------------------------
# Network Monitor Stats
# ---------------------------------------------------------------------------

MONITOR_QUALITY_COLUMNS: list[ColumnDef] = [
    ColumnDef("quality", header="Quality %"),
    ColumnDef("latency_avg_ms", header="Latency Avg (ms)"),
    ColumnDef("latency_peak_ms", header="Latency Peak (ms)"),
    ColumnDef("sent", header="Sent"),
    ColumnDef("dropped", header="Dropped"),
    ColumnDef("dropped_pct", header="Drop %", wide_only=True),
    ColumnDef("duplicates", header="Duplicates", wide_only=True),
    ColumnDef("bad_checksums", header="Bad Checksums", wide_only=True),
    ColumnDef("bad_data", header="Bad Data", wide_only=True),
]

MONITOR_HISTORY_COLUMNS: list[ColumnDef] = [
    ColumnDef("timestamp", header="Timestamp"),
    ColumnDef("quality", header="Quality %"),
    ColumnDef("latency_avg_ms", header="Latency Avg (ms)"),
    ColumnDef("latency_peak_ms", header="Latency Peak (ms)", wide_only=True),
    ColumnDef("dropped", header="Dropped"),
    ColumnDef("sent", header="Sent", wide_only=True),
]


# ---------------------------------------------------------------------------
# LLDP Neighbors
# ---------------------------------------------------------------------------

LLDP_NEIGHBOR_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("nic", header="NIC"),
    ColumnDef("chassis_name", header="Chassis"),
    ColumnDef("port_id", header="Port"),
    ColumnDef("via", header="Via"),
    ColumnDef("age", header="Age"),
    ColumnDef("rid", header="Remote ID", wide_only=True),
]


# ---------------------------------------------------------------------------
# NIC Stats / Status / Fabric
# ---------------------------------------------------------------------------

NIC_STATS_COLUMNS: list[ColumnDef] = [
    ColumnDef("parent_nic", header="NIC"),
    ColumnDef("txpps", header="TX pps"),
    ColumnDef("rxpps", header="RX pps"),
    ColumnDef("txbps", header="TX bps"),
    ColumnDef("rxbps", header="RX bps"),
    ColumnDef("totalxbps", header="Total bps"),
    ColumnDef("tx_pckts", header="TX Packets", wide_only=True),
    ColumnDef("rx_pckts", header="RX Packets", wide_only=True),
    ColumnDef("tx_bytes", header="TX Bytes", wide_only=True),
    ColumnDef("rx_bytes", header="RX Bytes", wide_only=True),
]

NIC_STATUS_COLUMNS: list[ColumnDef] = [
    ColumnDef("parent_nic", header="NIC"),
    ColumnDef(
        "status",
        header="Link",
        style_map={"up": "green", "down": "red", "unknown": "yellow"},
    ),
    ColumnDef("state", header="State"),
    ColumnDef("speed", header="Speed"),
]

NIC_FABRIC_COLUMNS: list[ColumnDef] = [
    ColumnDef("parent_nic", header="NIC"),
    ColumnDef(
        "status",
        header="Fabric",
        style_map={"confirmed": "green", "degraded": "yellow", "no_path": "red"},
    ),
    ColumnDef("state", header="State"),
    ColumnDef("max_score", header="Max Score"),
    ColumnDef("min_score", header="Min Score"),
]


# ---------------------------------------------------------------------------
# System Diagnostics
# ---------------------------------------------------------------------------

SYSTEM_DIAG_COLUMNS: list[ColumnDef] = [
    ColumnDef("$key", header="Key"),
    ColumnDef("name"),
    ColumnDef(
        "status",
        style_map={
            "complete": "green",
            "error": "red",
            "building": "yellow",
            "uploading": "yellow",
            "initializing": "dim",
        },
    ),
    ColumnDef("timestamp", header="Created"),
    ColumnDef("description", wide_only=True),
    ColumnDef("status_info", header="Status Info", wide_only=True),
]
