"""Pytest configuration and fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer test runner for CLI testing."""
    return CliRunner()


@pytest.fixture
def mock_client(mocker: MockerFixture) -> MagicMock:
    """Mock the pyvergeos VergeClient for unit tests.

    This fixture patches get_client to return a mock client,
    preventing any actual API calls during tests.
    """
    mock = MagicMock()

    # Set up common properties
    mock.version = "6.0.0"
    mock.os_version = "1.0.0"
    mock.cloud_name = "Test Cloud"
    mock.host = "https://test.verge.io"

    # Mock system.statistics()
    mock_stats = MagicMock()
    mock_stats.vms_total = 10
    mock_stats.vms_online = 5
    mock_stats.tenants_total = 2
    mock_stats.tenants_online = 2
    mock_stats.networks_total = 3
    mock_stats.networks_online = 3
    mock_stats.nodes_total = 2
    mock_stats.nodes_online = 2
    mock_stats.alarms_total = 0
    mock.system.statistics.return_value = mock_stats

    mocker.patch("verge_cli.auth.get_client", return_value=mock)
    return mock


@pytest.fixture
def mock_vm() -> MagicMock:
    """Create a mock VM object."""
    vm = MagicMock()
    vm.key = 1
    vm.name = "test-vm"
    vm.status = "running"
    vm.is_running = True
    vm.is_snapshot = False
    vm.cluster_name = "Cluster1"
    vm.node_name = "Node1"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "description": "Test VM",
            "cpu_cores": 2,
            "ram": 2048,
            "os_family": "linux",
            "created": "2024-01-01T00:00:00Z",
            "modified": "2024-01-02T00:00:00Z",
            "need_restart": False,
        }
        return data.get(key, default)

    vm.get = mock_get
    return vm


@pytest.fixture
def mock_network() -> MagicMock:
    """Create a mock Network object."""
    net = MagicMock()
    net.key = 1
    net.name = "test-network"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "description": "Test Network",
            "type": "internal",
            "network": "10.0.0.0/24",
            "ipaddress": "10.0.0.1",
            "gateway": "10.0.0.1",
            "mtu": 1500,
            "status": "running",
            "running": True,
            "dhcp_enabled": True,
            "dhcp_start": "10.0.0.100",
            "dhcp_stop": "10.0.0.200",
            "dns": "10.0.0.1",
            "domain": "test.local",
            "need_restart": False,
            "need_fw_apply": False,
            "need_dns_apply": False,
        }
        return data.get(key, default)

    net.get = mock_get
    return net


@pytest.fixture
def mock_dns_view() -> MagicMock:
    """Create a mock DNS View object."""
    view = MagicMock()
    view.key = 10
    view.name = "internal"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 10,
            "name": "internal",
            "recursion": True,
            "match_clients": "10.0.0.0/8;192.168.0.0/16;",
            "match_destinations": None,
            "max_cache_size": 33554432,
            "vnet": 1,
        }
        return data.get(key, default)

    view.get = mock_get
    return view


@pytest.fixture
def mock_drive() -> MagicMock:
    """Create a mock Drive object."""
    drive = MagicMock()
    drive.key = 10
    drive.name = "OS Disk"
    drive.size_gb = 50.0
    drive.used_gb = 12.5
    drive.interface_display = "VirtIO SCSI"
    drive.media_display = "Disk"
    drive.is_enabled = True
    drive.is_readonly = False

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 10,
            "name": "OS Disk",
            "description": "Operating System Disk",
            "interface": "virtio-scsi",
            "media": "disk",
            "disksize": 53687091200,
            "preferred_tier": 3,
            "enabled": True,
            "readonly": False,
            "machine": 38,
        }
        return data.get(key, default)

    drive.get = mock_get
    return drive


@pytest.fixture
def mock_nic() -> MagicMock:
    """Create a mock NIC object."""
    nic = MagicMock()
    nic.key = 20
    nic.name = "Primary Network"
    nic.interface_display = "VirtIO"
    nic.is_enabled = True
    nic.mac_address = "52:54:00:12:34:56"
    nic.ip_address = "10.0.0.100"
    nic.network_name = "DMZ Internal"
    nic.network_key = 3

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 20,
            "name": "Primary Network",
            "description": "LAN connection",
            "interface": "virtio",
            "enabled": True,
            "mac": "52:54:00:12:34:56",
            "ipaddress": "10.0.0.100",
            "vnet": 3,
            "vnet_name": "DMZ Internal",
            "machine": 38,
        }
        return data.get(key, default)

    nic.get = mock_get
    return nic


@pytest.fixture
def mock_device() -> MagicMock:
    """Create a mock Device object (TPM)."""
    device = MagicMock()
    device.key = 30
    device.name = "TPM"
    device.device_type = "TPM"
    device.device_type_raw = "tpm"
    device.is_enabled = True
    device.is_optional = False
    device.is_tpm = True
    device.is_gpu = False
    device.is_usb = False

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 30,
            "name": "TPM",
            "type": "tpm",
            "enabled": True,
            "optional": False,
            "settings_args": {"model": "crb", "version": "2"},
            "machine": 38,
        }
        return data.get(key, default)

    device.get = mock_get
    return device


@pytest.fixture
def mock_tenant() -> MagicMock:
    """Create a mock Tenant object."""
    tenant = MagicMock()
    tenant.key = 5
    tenant.name = "acme-corp"
    tenant.status = "running"
    tenant.is_running = True

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "description": "ACME Corporation tenant",
            "state": "active",
            "is_isolated": False,
            "network_name": "Tenant Internal",
            "ui_address_ip": "10.10.0.100",
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "url": "acme.verge.local",
            "note": "Production tenant",
            "expose_cloud_snapshots": True,
            "allow_branding": False,
        }
        return data.get(key, default)

    tenant.get = mock_get

    # Sub-manager placeholders for tenant sub-resource tests
    tenant.nodes = MagicMock()
    tenant.storage = MagicMock()
    tenant.network_blocks = MagicMock()
    tenant.external_ips = MagicMock()
    tenant.l2_networks = MagicMock()
    tenant.snapshots = MagicMock()
    tenant.stats = MagicMock()
    tenant.logs = MagicMock()

    return tenant


@pytest.fixture
def mock_cluster() -> MagicMock:
    """Create a mock Cluster object."""
    cluster = MagicMock()
    cluster.key = 1
    cluster.name = "Cluster1"
    # SDK computed properties (not available via .get())
    cluster.status = "online"
    cluster.total_ram_gb = 256
    cluster.ram_used_percent = 45.2
    cluster.is_compute = True
    cluster.is_storage = True

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 1,
            "name": "Cluster1",
            "description": "Primary Cluster",
            "status": "online",
            "total_nodes": 4,
            "online_nodes": 4,
            "total_ram_gb": 256,
            "ram_used_percent": 45.2,
            "total_cores": 64,
            "running_machines": 20,
            "is_compute": True,
            "is_storage": True,
            "enabled": True,
        }
        return data.get(key, default)

    cluster.get = mock_get
    return cluster


@pytest.fixture
def mock_node() -> MagicMock:
    """Create a mock Node object."""
    node = MagicMock()
    node.key = 10
    node.name = "node1"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 10,
            "name": "node1",
            "status": "online",
            "cluster_name": "Cluster1",
            "ram_gb": 64,
            "cores": 16,
            "cpu_usage": 35.0,
            "is_physical": True,
            "model": "PowerEdge R740",
            "cpu": "Intel Xeon Gold 6248",
            "core_temp": 52,
            "vergeos_version": "6.0.1",
        }
        return data.get(key, default)

    node.get = mock_get
    return node


@pytest.fixture
def mock_storage_tier() -> MagicMock:
    """Create a mock Storage Tier object."""
    tier = MagicMock()
    tier.key = 1
    tier.name = "Tier 1 - SSD"
    # SDK computed properties accessed as attributes
    tier.tier = 1
    tier.description = "SSD Storage"
    tier.capacity_gb = 10240
    tier.used_gb = 6144
    tier.free_gb = 4096
    tier.used_percent = 60.0
    tier.dedupe_ratio = 1.5
    tier.dedupe_savings_percent = 33.3
    tier.read_ops = 15000
    tier.write_ops = 8000

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 1,
            "tier": 1,
            "description": "SSD Storage",
            "capacity_gb": 10240,
            "used_gb": 6144,
            "free_gb": 4096,
            "used_percent": 60.0,
            "dedupe_ratio": 1.5,
            "dedupe_savings_percent": 33.3,
            "read_ops": 15000,
            "write_ops": 8000,
        }
        return data.get(key, default)

    tier.get = mock_get
    return tier


@pytest.fixture
def mock_nas_service() -> MagicMock:
    """Create a mock NAS service object."""
    svc = MagicMock()
    svc.key = 1
    svc.name = "nas01"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 1,
            "name": "nas01",
            "vm_running": True,
            "volume_count": 3,
            "vm_cores": 4,
            "vm_ram": 8192,
            "max_imports": 2,
            "max_syncs": 2,
        }
        return data.get(key, default)

    svc.get = mock_get
    return svc


@pytest.fixture
def mock_nas_volume() -> MagicMock:
    """Create a mock NAS volume object."""
    vol = MagicMock()
    vol.key = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    vol.name = "data-vol"
    vol.max_size_gb = 50.0
    vol.used_gb = 12.5

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "name": "data-vol",
            "enabled": True,
            "maxsize": 53687091200,
            "fs_type": "ext4",
            "preferred_tier": "1",
            "description": "Data volume",
            "read_only": False,
            "owner_user": "root",
            "owner_group": "root",
            "automount_snapshots": False,
            "service": 1,
        }
        return data.get(key, default)

    vol.get = mock_get
    return vol


@pytest.fixture
def mock_nas_volume_snapshot() -> MagicMock:
    """Create a mock NAS volume snapshot object."""
    snap = MagicMock()
    snap.key = 42
    snap.name = "snap-001"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 42,
            "name": "snap-001",
            "created": 1707350400,
            "expires": 1707609600,
            "description": "Test snapshot",
            "volume": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        }
        return data.get(key, default)

    snap.get = mock_get
    return snap


@pytest.fixture
def mock_cifs_share() -> MagicMock:
    """Create a mock NAS CIFS share object."""
    share = MagicMock()
    share.key = "abc123def456abc123def456abc123def456abc1"
    share.name = "users"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "abc123def456abc123def456abc123def456abc1",
            "name": "users",
            "volume_name": "UserData",
            "enabled": True,
            "browseable": True,
            "read_only": False,
            "guest_ok": False,
            "guest_only": False,
            "shadow_copy_enabled": False,
            "share_path": "/",
            "description": "User home directories",
            "comment": "User shares",
            "force_user": None,
            "force_group": None,
            "valid_users": None,
            "valid_groups": None,
            "admin_users": None,
            "admin_groups": None,
            "allowed_hosts": None,
            "denied_hosts": None,
        }
        return data.get(key, default)

    share.get = mock_get
    return share


@pytest.fixture
def mock_nfs_share() -> MagicMock:
    """Create a mock NAS NFS share object."""
    share = MagicMock()
    share.key = "def456abc123def456abc123def456abc123def4"
    share.name = "linuxapps"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "def456abc123def456abc123def456abc123def4",
            "name": "linuxapps",
            "volume_name": "LinuxApps",
            "enabled": True,
            "data_access": "rw",
            "squash": "root_squash",
            "allowed_hosts": "10.0.0.0/24,192.168.1.0/24",
            "allow_all": False,
            "description": "Linux application data",
            "anonymous_uid": None,
            "anonymous_gid": None,
            "async_mode": False,
            "insecure": False,
            "no_acl": False,
            "filesystem_id": None,
        }
        return data.get(key, default)

    share.get = mock_get
    return share


@pytest.fixture
def mock_nas_user() -> MagicMock:
    """Create a mock NAS user object."""
    user = MagicMock()
    user.key = "aabbccdd11223344556677889900aabbccdd1122"
    user.name = "nasadmin"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "aabbccdd11223344556677889900aabbccdd1122",
            "name": "nasadmin",
            "displayname": "NAS Admin",
            "enabled": True,
            "service_name": "nas01",
            "status": "online",
            "home_share_name": "AdminDocs",
            "home_drive": "H",
            "description": "NAS administrator account",
        }
        return data.get(key, default)

    user.get = mock_get
    return user


@pytest.fixture
def mock_nas_sync() -> MagicMock:
    """Create a mock NAS volume sync object."""
    sync = MagicMock()
    sync.key = "aabb001122334455667788990011223344556677"
    sync.name = "daily-backup"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "aabb001122334455667788990011223344556677",
            "name": "daily-backup",
            "enabled": True,
            "status": "idle",
            "sync_method": "ysync",
            "workers": 4,
            "source_volume": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "destination_volume": "f6e5d4c3b2a1f6e5d4c3b2a1f6e5d4c3b2a1f6e5",
            "destination_delete": "never",
            "description": "Daily backup sync",
        }
        return data.get(key, default)

    sync.get = mock_get
    return sync


@pytest.fixture
def mock_nas_file() -> dict[str, Any]:
    """Create a mock NAS file entry (dict-based)."""
    return {
        "name": "report.txt",
        "type": "file",
        "size": 1024,
        "date": 1700000000,
        "n_name": "report.txt",
    }


@pytest.fixture
def mock_nas_dir() -> dict[str, Any]:
    """Create a mock NAS directory entry (dict-based)."""
    return {
        "name": "documents",
        "type": "directory",
        "size": 0,
        "date": 1700000000,
        "n_name": "documents",
    }


@pytest.fixture
def mock_recipe() -> MagicMock:
    """Create a mock VmRecipe object."""
    recipe = MagicMock()
    recipe.key = "8f73f8bcc9c9f1aaba32f733bfc295acaf548554"
    recipe.name = "Ubuntu Server 22.04"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "8f73f8bcc9c9f1aaba32f733bfc295acaf548554",
            "name": "Ubuntu Server 22.04",
            "description": "Ubuntu Server LTS recipe",
            "enabled": True,
            "notes": "Standard server template",
        }
        return data.get(key, default)

    recipe.get = mock_get
    return recipe


@pytest.fixture
def mock_recipe_section() -> MagicMock:
    """Create a mock RecipeSection object."""
    section = MagicMock()
    section.key = 100
    section.name = "Virtual Machine"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 100,
            "name": "Virtual Machine",
            "description": "Core VM settings",
            "orderid": 1,
        }
        return data.get(key, default)

    section.get = mock_get
    return section


@pytest.fixture
def mock_recipe_question() -> MagicMock:
    """Create a mock RecipeQuestion object."""
    question = MagicMock()
    question.key = 200
    question.name = "YB_CPU_CORES"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 200,
            "name": "YB_CPU_CORES",
            "display": "CPU Cores",
            "type": "num",
            "required": True,
            "default": "2",
            "hint": "Number of CPU cores",
        }
        return data.get(key, default)

    question.get = mock_get
    return question


@pytest.fixture
def mock_recipe_instance() -> MagicMock:
    """Create a mock VmRecipeInstance object."""
    inst = MagicMock()
    inst.key = 50
    inst.name = "my-ubuntu"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 50,
            "name": "my-ubuntu",
            "recipe_name": "Ubuntu Server 22.04",
            "auto_update": False,
        }
        return data.get(key, default)

    inst.get = mock_get
    return inst


@pytest.fixture
def mock_recipe_log() -> MagicMock:
    """Create a mock VmRecipeLog object."""
    log = MagicMock()
    log.key = 300

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 300,
            "level": "message",
            "text": "Recipe deployed successfully",
            "timestamp": 1707350400000000,
            "user": "admin",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.key = 10
    user.name = "admin"
    user.is_enabled = True

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "displayname": "Administrator",
            "email": "admin@example.com",
            "user_type": "normal",
            "user_type_display": "Normal",
            "two_factor_enabled": False,
            "is_locked": False,
            "auth_source_name": "",
            "last_login": 1707100000,
            "created": 1707000000,
            "ssh_keys": "",
        }
        return data.get(key, default)

    user.get = mock_get
    return user


@pytest.fixture
def mock_group() -> MagicMock:
    """Create a mock Group object."""
    group = MagicMock()
    group.key = 20
    group.name = "admins"
    group.is_enabled = True

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Admin group",
            "email": "admins@example.com",
            "member_count": 3,
            "created": 1707000000,
        }
        return data.get(key, default)

    group.get = mock_get
    return group


@pytest.fixture
def mock_group_member() -> MagicMock:
    """Create a mock GroupMember object."""
    member = MagicMock()
    member.key = 30
    member.member_name = "admin"
    member.member_type = "User"
    member.member_key = 10
    return member


@pytest.fixture
def mock_permission() -> MagicMock:
    """Create a mock Permission object."""
    perm = MagicMock()
    perm.key = 50
    perm.identity_name = "admin"
    perm.table = "vms"
    perm.row_key = 0
    perm.row_display = ""
    perm.is_table_level = True
    perm.can_list = True
    perm.can_read = True
    perm.can_create = False
    perm.can_modify = False
    perm.can_delete = False
    perm.has_full_control = False
    return perm


@pytest.fixture
def mock_api_key() -> MagicMock:
    """Create a mock API Key object."""
    key = MagicMock()
    key.key = 60
    key.name = "automation"
    key.user_name = "admin"
    key.is_expired = False
    key.ip_allow_list = []
    key.ip_deny_list = []

    def mock_get(attr: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Automation key",
            "created": 1707100000,
            "expires": 0,
            "last_login": 1707200000,
            "last_login_ip": "192.168.1.100",
        }
        return data.get(attr, default)

    key.get = mock_get
    return key


@pytest.fixture
def mock_api_key_created() -> MagicMock:
    """Create a mock APIKeyCreated response object."""
    result = MagicMock()
    result.key = 61
    result.name = "new-key"
    result.user_name = "admin"
    result.secret = "vrg_sk_abc123def456ghi789"
    return result


@pytest.fixture
def mock_auth_source() -> MagicMock:
    """Create a mock AuthSource object."""
    source = MagicMock()
    source.key = 40
    source.name = "azure-sso"
    source.driver = "azure"
    source.is_menu = True
    source.is_debug_enabled = False
    source.is_azure = True
    source.is_google = False
    source.is_gitlab = False
    source.is_okta = False
    source.is_openid = False
    source.is_oauth2 = False
    source.is_vergeos = False
    source.button_style = {
        "background_color": "#0078d4",
        "text_color": "#ffffff",
        "icon": "bi-microsoft",
        "icon_color": "#ffffff",
    }
    source.settings = {
        "client_id": "abc-123",
        "tenant_id": "tenant-456",
        "scope": "openid profile email",
    }
    return source


@pytest.fixture
def mock_task() -> MagicMock:
    """Create a mock Task object."""
    task = MagicMock()
    task.key = 100
    task.name = "nightly-backup"
    task.status = "idle"
    task.is_enabled = True
    task.is_running = False
    task.is_complete = True
    task.has_error = False
    task.action_display_name = "Snapshot"
    task.owner_display = "web-server"
    task.creator_display = "admin"
    task.is_delete_after_run = False
    task.is_system_created = False
    task.progress = 0
    task.trigger_count = 1
    task.event_count = 0

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Nightly backup task",
            "action": "snapshot",
            "action_display": "Snapshot",
            "table": "vms",
            "owner": 1,
            "last_run": 1707200000,
            "error": "",
        }
        return data.get(key, default)

    task.get = mock_get
    return task


@pytest.fixture
def mock_task_schedule() -> MagicMock:
    """Create a mock TaskSchedule object."""
    schedule = MagicMock()
    schedule.key = 200
    schedule.name = "nightly-window"
    schedule.is_enabled = True
    schedule.repeat_every_display = "Day(s)"
    schedule.repeat_count = 1
    schedule.active_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Nightly maintenance window",
            "repeat_every": "day",
            "start_date": "2026-01-01",
            "end_date": "",
            "start_time_of_day": 7200,
            "end_time_of_day": 14400,
            "day_of_month": "start_date",
        }
        return data.get(key, default)

    schedule.get = mock_get
    return schedule


@pytest.fixture
def mock_task_trigger() -> MagicMock:
    """Create a mock TaskScheduleTrigger object."""
    trigger = MagicMock()
    trigger.key = 300
    trigger.task_key = 100
    trigger.task_display = "nightly-backup"
    trigger.schedule_key = 200
    trigger.schedule_display = "nightly-window"
    trigger.is_schedule_enabled = True
    trigger.schedule_repeat_every = "day"
    return trigger


@pytest.fixture
def mock_task_event() -> MagicMock:
    """Create a mock TaskEvent object."""
    event = MagicMock()
    event.key = 400
    event.event_type = "poweron"
    event.event_name_display = "Power On"
    event.owner_key = 1
    event.owner_display = "web-server"
    event.owner_table = "vms"
    event.task_key = 100
    event.task_display = "nightly-backup"
    event.event_filters = None
    event.event_context = None
    return event


@pytest.fixture
def mock_task_script() -> MagicMock:
    """Create a mock TaskScript object."""
    script = MagicMock()
    script.key = 500
    script.name = "cleanup-logs"
    script.script_code = 'log("Cleaning up old logs")\ndelete_old_files("/var/log", 30)'
    script.task_count = 2
    script.settings = None

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Cleans up log files older than 30 days",
        }
        return data.get(key, default)

    script.get = mock_get
    return script


@pytest.fixture
def mock_certificate() -> MagicMock:
    """Create a mock Certificate object."""
    cert = MagicMock()
    cert.key = 70
    cert.domain = "example.com"
    cert.is_valid = True
    cert.cert_type_display = "Self-Signed"
    cert.key_type_display = "ECDSA"
    cert.days_until_expiry = 350

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "domain": "example.com",
            "domainname": "example.com",
            "domainlist": "*.example.com,api.example.com",
            "description": "Main wildcard cert",
            "type": "self_signed",
            "key_type": "ecdsa",
            "valid": True,
            "expires": 1738000000,
            "created": 1707000000,
            "autocreated": False,
            "public": "-----BEGIN CERTIFICATE-----\nMIIB...",
            "private": "-----BEGIN PRIVATE KEY-----\nMIIE...",
            "chain": "",
        }
        return data.get(key, default)

    cert.get = mock_get
    return cert


@pytest.fixture
def mock_oidc_app() -> MagicMock:
    """Create a mock OIDC Application object."""
    oidc_app = MagicMock()
    oidc_app.key = 80
    oidc_app.name = "grafana"
    oidc_app.is_enabled = True
    oidc_app.is_access_restricted = False
    oidc_app.redirect_uris = ["https://grafana.example.com/callback"]
    oidc_app.scopes = ["openid", "profile", "email", "groups"]
    oidc_app.force_auth_source_key = None
    oidc_app.map_user_key = None
    oidc_app.client_id = "oidc_abc123"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Grafana SSO",
            "client_id": "oidc_abc123",
            "client_secret": "oidc_secret_xyz789",
            "enabled": True,
            "redirect_uri": "https://grafana.example.com/callback",
            "restrict_access": False,
            "scope_profile": True,
            "scope_email": True,
            "scope_groups": True,
            "force_auth_source": "",
            "map_user": "",
            "created": 1707000000,
            "well_known_configuration": "https://verge.example.com/.well-known/openid-configuration",
        }
        return data.get(key, default)

    oidc_app.get = mock_get
    return oidc_app


@pytest.fixture
def mock_oidc_user_entry() -> MagicMock:
    """Create a mock OIDC application user ACL entry."""
    entry = MagicMock()
    entry.key = 90

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "user": 10,
            "user_display": "admin",
            "oidc_application": 80,
        }
        return data.get(key, default)

    entry.get = mock_get
    return entry


@pytest.fixture
def mock_oidc_group_entry() -> MagicMock:
    """Create a mock OIDC application group ACL entry."""
    entry = MagicMock()
    entry.key = 91

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "group": 20,
            "group_display": "admins",
            "oidc_application": 80,
        }
        return data.get(key, default)

    entry.get = mock_get
    return entry


@pytest.fixture
def mock_oidc_log() -> MagicMock:
    """Create a mock OIDC application log entry."""
    log = MagicMock()
    log.key = 1000
    log.application_key = 80
    log.is_error = False
    log.is_warning = False

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "timestamp": 1707100000000000,  # microseconds
            "level": "audit",
            "text": "User admin authenticated successfully",
            "user": 10,
            "user_display": "admin",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_catalog() -> MagicMock:
    """Create a mock Catalog object."""
    catalog = MagicMock()
    catalog.key = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    catalog.name = "test-catalog"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "repository": 1,
            "description": "Test catalog",
            "publishing_scope": "private",
            "enabled": True,
            "created": "2026-02-10T00:00:00",
        }
        return data.get(key, default)

    catalog.get = mock_get
    return catalog


@pytest.fixture
def mock_catalog_log() -> MagicMock:
    """Create a mock CatalogLog object."""
    log = MagicMock()
    log.key = 200

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "catalog": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "level": "message",
            "text": "Catalog synced successfully",
            "timestamp": 1707000000000000,
            "user": "admin",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_catalog_repo() -> MagicMock:
    """Create a mock CatalogRepository object."""
    repo = MagicMock()
    repo.key = 1
    repo.name = "test-repo"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "type": "local",
            "description": "Test repository",
            "url": "",
            "enabled": True,
            "auto_refresh": True,
            "max_tier": "1",
            "override_default_scope": "none",
            "last_refreshed": "2026-02-10T00:00:00",
        }
        return data.get(key, default)

    repo.get = mock_get
    return repo


@pytest.fixture
def mock_catalog_repo_status() -> MagicMock:
    """Create a mock CatalogRepositoryStatus object."""
    status = MagicMock()
    status.key = 1

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "status": "online",
            "state": "online",
            "info": "",
            "last_update": "2026-02-10T00:00:00",
        }
        return data.get(key, default)

    status.get = mock_get
    return status


@pytest.fixture
def mock_catalog_repo_log() -> MagicMock:
    """Create a mock CatalogRepositoryLog object."""
    log = MagicMock()
    log.key = 100

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "catalog_repository": 1,
            "level": "message",
            "text": "Repository refreshed successfully",
            "timestamp": 1707000000000000,
            "user": "admin",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_update_settings() -> MagicMock:
    """Create a mock UpdateSettings object."""
    settings = MagicMock()
    settings.key = 1

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "source": 1,
            "branch": 1,
            "auto_refresh": True,
            "auto_update": False,
            "auto_reboot": False,
            "update_time": "02:00",
            "max_vsan_usage": 80,
            "warm_reboot": True,
            "multi_cluster_update": False,
            "snapshot_cloud_on_update": True,
            "snapshot_cloud_expire_seconds": 86400,
            "installed": False,
            "reboot_required": False,
            "applying_updates": False,
            "anonymize_statistics": False,
        }
        return data.get(key, default)

    settings.get = mock_get
    return settings


@pytest.fixture
def mock_update_source() -> MagicMock:
    """Create a mock UpdateSource object."""
    source = MagicMock()
    source.key = 1
    source.name = "test-source"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Default update source",
            "url": "https://updates.verge.io",
            "enabled": True,
            "last_updated": "2026-02-10T00:00:00",
            "last_refreshed": "2026-02-10T00:00:00",
        }
        return data.get(key, default)

    source.get = mock_get
    return source


@pytest.fixture
def mock_update_source_status() -> MagicMock:
    """Create a mock UpdateSourceStatus object."""
    status = MagicMock()
    status.key = 1

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "source": 1,
            "status": "idle",
            "info": "",
            "nodes_updated": 2,
            "last_update": "2026-02-10T00:00:00",
        }
        return data.get(key, default)

    status.get = mock_get
    return status


@pytest.fixture
def mock_update_branch() -> MagicMock:
    """Create a mock UpdateBranch object."""
    branch = MagicMock()
    branch.key = 1
    branch.name = "stable-4.13"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "description": "Stable 4.13 release branch",
            "created": "2026-01-15T00:00:00",
        }
        return data.get(key, default)

    branch.get = mock_get
    return branch


@pytest.fixture
def mock_update_package() -> MagicMock:
    """Create a mock UpdatePackage object."""
    pkg = MagicMock()
    pkg.key = "yb-core"
    pkg.name = "yb-core"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "version": "4.13.1-12345",
            "type": "ybpkg",
            "optional": False,
            "description": "VergeOS Core Package",
            "branch": 1,
            "modified": "2026-02-08T00:00:00",
        }
        return data.get(key, default)

    pkg.get = mock_get
    return pkg


@pytest.fixture
def mock_update_source_package() -> MagicMock:
    """Create a mock UpdateSourcePackage object."""
    pkg = MagicMock()
    pkg.key = 10
    pkg.name = "yb-core"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "version": "4.13.2-12400",
            "downloaded": False,
            "optional": False,
            "description": "VergeOS Core Package",
            "branch": 1,
            "source": 1,
            "require_license_feature": "",
        }
        return data.get(key, default)

    pkg.get = mock_get
    return pkg


@pytest.fixture
def mock_update_log() -> MagicMock:
    """Create a mock UpdateLog object."""
    log = MagicMock()
    log.key = 500

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "level": "audit",
            "text": "Update check completed",
            "timestamp": 1707000000000000,
            "user": "admin",
            "object_name": "system",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_update_dashboard() -> MagicMock:
    """Create a mock UpdateDashboard object."""
    dashboard = MagicMock()

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "node_count": 3,
            "counts": {"event_count": 12, "task_count": 5},
            "logs": [],
            "packages": [],
            "branches": [],
            "settings": {},
        }
        return data.get(key, default)

    dashboard.get = mock_get
    return dashboard


@pytest.fixture
def mock_alarm() -> MagicMock:
    """Create a mock Alarm object."""
    from datetime import datetime

    alarm = MagicMock()
    alarm.key = 42
    alarm.level = "warning"
    alarm.level_display = "Warning"
    alarm.alarm_type = "High CPU Usage"
    alarm.alarm_id = "a1b2c3d4"
    alarm.status = "CPU usage above 90% for 15 minutes"
    alarm.description = "Triggered when CPU usage exceeds threshold"
    alarm.owner_type = "vms"
    alarm.owner_type_display = "VM"
    alarm.owner_name = "web-server-01"
    alarm.owner_key = 10
    alarm.is_resolvable = True
    alarm.resolve_text = "Reduce CPU load or add resources"
    alarm.is_snoozed = False
    alarm.snoozed_by = ""
    alarm.snooze_until = None
    alarm.created_at = datetime(2026, 2, 10, 12, 0, 0)
    alarm.modified_at = datetime(2026, 2, 10, 12, 0, 0)
    return alarm


@pytest.fixture
def mock_alarm_history() -> MagicMock:
    """Create a mock AlarmHistory object."""
    from datetime import datetime

    entry = MagicMock()
    entry.key = 100
    entry.level = "error"
    entry.level_display = "Error"
    entry.alarm_type = "Disk Failure"
    entry.alarm_id = "e5f6g7h8"
    entry.status = "Disk /dev/sdb failed"
    entry.owner = "node-01"
    entry.archived_by = "auto"
    entry.raised_at = datetime(2026, 2, 8, 10, 0, 0)
    entry.lowered_at = datetime(2026, 2, 8, 14, 0, 0)
    return entry


@pytest.fixture
def mock_log_entry() -> MagicMock:
    """Create a mock Log entry object."""
    from datetime import datetime

    log = MagicMock()
    log.key = 1000
    log.level = "audit"
    log.level_display = "Audit"
    log.text = "VM 'web-server-01' started by admin"
    log.user = "admin"
    log.object_type = "vm"
    log.object_type_display = "VM"
    log.object_name = "web-server-01"
    log.timestamp_us = 1707000000000000  # microseconds
    log.created_at = datetime(2026, 2, 4, 0, 0, 0)
    return log


@pytest.fixture
def mock_tag() -> MagicMock:
    """Create a mock Tag object."""
    tag = MagicMock()
    tag.key = 5
    tag.name = "production"
    tag.description = "Production environment"
    tag.category_name = "Environment"
    tag.category_key = 1
    tag.created = 1707000000
    tag.modified = 1707000000
    tag.members = MagicMock()  # TagMemberManager
    return tag


@pytest.fixture
def mock_tag_category() -> MagicMock:
    """Create a mock TagCategory object."""
    cat = MagicMock()
    cat.key = 1
    cat.name = "Environment"
    cat.description = "Environment classification"
    cat.is_single_tag_selection = True
    cat.taggable_vms = True
    cat.taggable_networks = True
    cat.taggable_volumes = False
    cat.taggable_nodes = True
    cat.taggable_tenants = True
    cat.taggable_users = False
    cat.taggable_clusters = False
    cat.taggable_sites = False
    cat.taggable_groups = False
    cat.taggable_network_rules = False
    cat.taggable_vmware_containers = False
    cat.taggable_tenant_nodes = False
    cat.created = 1707000000
    cat.modified = 1707000000
    return cat


@pytest.fixture
def mock_tag_member() -> MagicMock:
    """Create a mock TagMember object."""
    member = MagicMock()
    member.key = 10
    member.resource_type = "vms"
    member.resource_key = 42
    member.resource_name = "web-server-01"
    member.resource_ref = "vms/42"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "resource_type": "vms",
            "resource_key": 42,
            "resource_name": "web-server-01",
        }
        return data.get(key, default)

    member.get = mock_get
    return member


@pytest.fixture
def mock_resource_group() -> MagicMock:
    """Create a mock ResourceGroup object."""
    from datetime import datetime

    group = MagicMock()
    group.key = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    group.uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    group.name = "gpu-passthrough"
    group.device_type = "node_pci_devices"
    group.device_type_display = "PCI"
    group.device_class = "gpu"
    group.device_class_display = "GPU"
    group.is_enabled = True
    group.resource_count = 2
    group.description = "GPU passthrough group"
    group.created_at = datetime(2026, 2, 10, 0, 0, 0)
    group.modified_at = datetime(2026, 2, 10, 0, 0, 0)
    return group


@pytest.fixture
def mock_shared_object() -> MagicMock:
    """Create a mock SharedObject."""
    from datetime import datetime

    obj = MagicMock()
    obj.key = 15
    obj.name = "shared-web-server"
    obj.description = "Web server VM shared to dev tenant"
    obj.tenant_key = 3
    obj.tenant_name = "dev-tenant"
    obj.object_type = "vm"
    obj.object_id = "vms/42"
    obj.snapshot_path = None
    obj.snapshot_key = None
    obj.is_inbox = True
    obj.created_at = datetime(2026, 2, 10, 0, 0, 0)
    return obj


@pytest.fixture
def mock_billing_record() -> MagicMock:
    """Create a mock BillingRecord object."""
    record = MagicMock()
    record.key = 1
    record.created_epoch = 1707000000
    record.from_epoch = 1706900000
    record.to_epoch = 1707000000
    record.used_cores = 8
    record.total_cores = 16
    record.online_cores = 16
    record.total_nodes = 2
    record.online_nodes = 2
    record.running_machines = 5
    record.used_ram = 16384
    record.used_ram_gb = 16.0
    record.total_ram = 32768
    record.total_ram_gb = 32.0
    record.total_storage_used_gb = 500.0
    record.total_storage_total_gb = 2000.0
    record.description = "Billing record"
    record.sent_epoch = 1707000000
    record.cpu_utilization_pct = 50.0
    record.ram_utilization_pct = 50.0
    return record


@pytest.fixture
def mock_webhook() -> MagicMock:
    """Create a mock Webhook object."""
    wh = MagicMock()
    wh.key = 10
    wh.name = "my-webhook"
    wh.webhook_type = "custom"
    wh.url = "https://example.com/hook"
    wh.authorization_type_display = "None"
    wh.is_insecure = False
    wh.timeout = 5
    wh.retries = 3
    wh.headers = {}
    return wh


@pytest.fixture
def mock_webhook_history() -> MagicMock:
    """Create a mock WebhookHistory object."""
    from datetime import datetime

    entry = MagicMock()
    entry.key = 100
    entry.webhook_key = 10
    entry.status_display = "Sent"
    entry.status_info = "200 OK"
    entry.message_raw = '{"test": true}'
    entry.last_attempt_at = datetime(2026, 2, 10, 12, 0, 0)
    entry.created_at = datetime(2026, 2, 10, 11, 59, 0)
    entry.is_pending = False
    entry.is_sent = True
    entry.has_error = False
    return entry


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory."""
    config_dir = tmp_path / ".vrg"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config_file(temp_config_dir: Path) -> Path:
    """Create a sample config file for testing."""
    config_file = temp_config_dir / "config.toml"
    config_file.write_text(
        """
[default]
host = "https://verge.example.com"
token = "test-token-12345"
verify_ssl = true
output = "table"
timeout = 30

[profile.dev]
host = "https://192.168.1.100"
username = "admin"
password = "secret"
verify_ssl = false
"""
    )
    return config_file


@pytest.fixture
def mock_vm_import() -> MagicMock:
    """Create a mock VmImport object (hex key)."""
    imp = MagicMock()
    imp.key = "ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12"
    imp.name = "ubuntu-import"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12",
            "name": "ubuntu-import",
            "status": "ready",
            "file": 5,
            "volume": "",
            "volume_path": "",
            "preserve_macs": True,
            "preserve_drive_format": False,
            "preferred_tier": "",
            "no_optical_drives": False,
            "override_drive_interface": "",
            "override_nic_interface": "",
            "cleanup_on_delete": True,
            "shared_object": 0,
        }
        return data.get(key, default)

    imp.get = mock_get
    return imp


@pytest.fixture
def mock_vm_import_log() -> MagicMock:
    """Create a mock VmImportLog object (int key)."""
    log = MagicMock()
    log.key = 500

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 500,
            "level": "message",
            "text": "Import started",
            "timestamp": 1707350400000000,
            "user": "admin",
            "vm_import": "ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_vm_export() -> MagicMock:
    """Create a mock VolumeVmExport object (int key).

    Note: VolumeVmExport has no ``name`` attribute — uses ``volume_name``
    from the SDK's default fields.
    """
    exp = MagicMock(spec=[])  # spec=[] prevents auto-creating .name
    exp.key = 10

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 10,
            "volume_name": "vm-exports",
            "volume_display": "vm-exports",
            "status": "idle",
            "volume": "ca094f47c075bca00ffc76c2cdfc5aafc7138308",
            "quiesced": True,
            "create_current": True,
            "max_exports": 3,
        }
        return data.get(key, default)

    exp.get = mock_get
    return exp


@pytest.fixture
def mock_vm_export_stat() -> MagicMock:
    """Create a mock VolumeVmExportStat object (int key).

    Note: VolumeVmExportStat has no ``name`` attribute — uses ``file_name``.
    """
    stat = MagicMock(spec=[])  # spec=[] prevents auto-creating .name
    stat.key = 100

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 100,
            "file_name": "backup-2026-02-18",
            "virtual_machines": 3,
            "export_success": 3,
            "errors": 0,
            "size_bytes": 53687091200,
            "duration": 120,
            "timestamp": 1707350400,
            "volume_vm_exports": 10,
            "quiesced": True,
        }
        return data.get(key, default)

    stat.get = mock_get
    return stat


@pytest.fixture
def mock_tenant_recipe() -> MagicMock:
    """Create a mock TenantRecipe object (hex key)."""
    recipe = MagicMock()
    recipe.key = "cc11dd22ee33ff44cc11dd22ee33ff44cc11dd22"
    recipe.name = "Standard Tenant"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": "cc11dd22ee33ff44cc11dd22ee33ff44cc11dd22",
            "name": "Standard Tenant",
            "description": "Standard tenant recipe",
            "enabled": True,
            "version": "1.0",
            "icon": "",
            "preserve_certs": False,
        }
        return data.get(key, default)

    recipe.get = mock_get
    return recipe


@pytest.fixture
def mock_tenant_recipe_instance() -> MagicMock:
    """Create a mock TenantRecipeInstance object (int key)."""
    inst = MagicMock()
    inst.key = 60
    inst.name = "acme-tenant"

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 60,
            "name": "acme-tenant",
            "recipe_name": "Standard Tenant",
            "recipe": "cc11dd22ee33ff44cc11dd22ee33ff44cc11dd22",
        }
        return data.get(key, default)

    inst.get = mock_get
    return inst


@pytest.fixture
def mock_tenant_recipe_log() -> MagicMock:
    """Create a mock TenantRecipeLog object (int key)."""
    log = MagicMock()
    log.key = 600

    def mock_get(key: str, default: Any = None) -> Any:
        data: dict[str, Any] = {
            "$key": 600,
            "level": "message",
            "text": "Tenant recipe deployed successfully",
            "timestamp": 1707350400000000,
            "user": "admin",
            "tenant_recipe": "cc11dd22ee33ff44cc11dd22ee33ff44cc11dd22",
        }
        return data.get(key, default)

    log.get = mock_get
    return log


@pytest.fixture
def mock_vgpu_profile() -> MagicMock:
    """Create a mock NVIDIA vGPU profile object."""
    profile = MagicMock()
    profile.key = 1
    profile.name = "nvidia-256c"

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 1,
            "name": "nvidia-256c",
            "type": "C",
            "framebuffer": "256M",
            "max_resolution": "1920x1200",
            "max_instance": 24,
            "grid_license": "vCS",
        }
        return data.get(key, default)

    profile.get = mock_get
    return profile


@pytest.fixture
def mock_node_gpu() -> MagicMock:
    """Create a mock node GPU object."""
    gpu = MagicMock()
    gpu.key = 1
    gpu.name = "NVIDIA A100"
    gpu.node_name = "node1"
    gpu.node_key = 10
    gpu.mode_display = "nvidia_vgpu"
    gpu.nvidia_vgpu_profile_display = "nvidia-256c"
    gpu.instances_count = 3
    gpu.max_instances = 24

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 1,
            "name": "NVIDIA A100",
            "node_name": "node1",
            "node_key": 10,
            "mode": "nvidia_vgpu",
            "mode_display": "nvidia_vgpu",
            "nvidia_vgpu_profile": 1,
            "nvidia_vgpu_profile_display": "nvidia-256c",
            "instances_count": 3,
            "max_instances": 24,
        }
        return data.get(key, default)

    gpu.get = mock_get

    # Sub-managers for stats and instances
    mock_stats = MagicMock()
    mock_stats.gpus_total = 1
    mock_stats.gpus = 1
    mock_stats.gpus_idle = 0
    mock_stats.vgpus_total = 24
    mock_stats.vgpus = 3
    mock_stats.vgpus_idle = 21

    def stats_get(key: str, default: Any = None) -> Any:
        data = {
            "gpus_total": 1,
            "gpus": 1,
            "gpus_idle": 0,
            "vgpus_total": 24,
            "vgpus": 3,
            "vgpus_idle": 21,
        }
        return data.get(key, default)

    mock_stats.get = stats_get
    gpu.stats.get.return_value = mock_stats

    mock_instance = MagicMock()
    mock_instance.key = 100
    mock_instance.machine_name = "test-vm"
    mock_instance.machine_type_display = "VM"
    mock_instance.mode_display = "nvidia_vgpu"
    mock_instance.machine_device_status = "running"

    def instance_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 100,
            "machine_name": "test-vm",
            "machine_type_display": "VM",
            "mode_display": "nvidia_vgpu",
            "machine_device_status": "running",
        }
        return data.get(key, default)

    mock_instance.get = instance_get
    gpu.instances.list.return_value = [mock_instance]

    return gpu


@pytest.fixture
def mock_vgpu_device() -> MagicMock:
    """Create a mock vGPU device object."""
    device = MagicMock()
    device.key = 5
    device.name = "NVIDIA A100 [0000:3b:00.0]"
    device.node_name = "node1"
    device.slot = "3b:00.0"
    device.vendor = "NVIDIA Corporation"
    device.device = "A100 PCIe 40GB"
    device.driver = "nvidia"
    device.max_instances = 24

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 5,
            "name": "NVIDIA A100 [0000:3b:00.0]",
            "node_name": "node1",
            "slot": "3b:00.0",
            "vendor": "NVIDIA Corporation",
            "device": "A100 PCIe 40GB",
            "driver": "nvidia",
            "max_instances": 24,
        }
        return data.get(key, default)

    device.get = mock_get
    return device


@pytest.fixture
def mock_host_gpu_device() -> MagicMock:
    """Create a mock host GPU device object."""
    device = MagicMock()
    device.key = 6
    device.name = "NVIDIA T400 [0000:86:00.0]"
    device.node_name = "node1"
    device.slot = "86:00.0"
    device.vendor = "NVIDIA Corporation"
    device.device = "T400 4GB"
    device.driver = "nvidia"
    device.max_instances = 1

    def mock_get(key: str, default: Any = None) -> Any:
        data = {
            "$key": 6,
            "name": "NVIDIA T400 [0000:86:00.0]",
            "node_name": "node1",
            "slot": "86:00.0",
            "vendor": "NVIDIA Corporation",
            "device": "T400 4GB",
            "driver": "nvidia",
            "max_instances": 1,
        }
        return data.get(key, default)

    device.get = mock_get
    return device
