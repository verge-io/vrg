# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for vrg CLI."""

import importlib
import os

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Rich dynamically imports hyphenated modules in _unicode_data (e.g. unicode17-0-0.py)
# that PyInstaller's module discovery can't find. include_py_files=True is required
# because collect_data_files excludes .py by default.
rich_unicode_datas = collect_data_files("rich._unicode_data", include_py_files=True)

# Collect certifi CA bundle for HTTPS connections
certifi_path = os.path.join(
    os.path.dirname(importlib.import_module("certifi").__file__),
    "cacert.pem",
)

a = Analysis(
    ["src/verge_cli/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("src/verge_cli/schemas/vrg-vm-template.schema.json", "verge_cli/schemas"),
        (certifi_path, "certifi"),
        *rich_unicode_datas,
    ],
    hiddenimports=[
        # pyvergeos lazy-loads resources via @property on the client
        "pyvergeos.resources.alarms",
        "pyvergeos.resources.aliases",
        "pyvergeos.resources.api_keys",
        "pyvergeos.resources.auth_sources",
        "pyvergeos.resources.base",
        "pyvergeos.resources.billing",
        "pyvergeos.resources.catalogs",
        "pyvergeos.resources.certificates",
        "pyvergeos.resources.cloud_snapshots",
        "pyvergeos.resources.cloudinit_files",
        "pyvergeos.resources.cluster_tiers",
        "pyvergeos.resources.clusters",
        "pyvergeos.resources.devices",
        "pyvergeos.resources.dns",
        "pyvergeos.resources.dns_views",
        "pyvergeos.resources.drives",
        "pyvergeos.resources.files",
        "pyvergeos.resources.gpu",
        "pyvergeos.resources.groups",
        "pyvergeos.resources.hosts",
        "pyvergeos.resources.ipsec",
        "pyvergeos.resources.logs",
        "pyvergeos.resources.machine_stats",
        "pyvergeos.resources.nas_antivirus",
        "pyvergeos.resources.nas_cifs",
        "pyvergeos.resources.nas_nfs",
        "pyvergeos.resources.nas_services",
        "pyvergeos.resources.nas_users",
        "pyvergeos.resources.nas_volume_browser",
        "pyvergeos.resources.nas_volume_syncs",
        "pyvergeos.resources.nas_volumes",
        "pyvergeos.resources.network_stats",
        "pyvergeos.resources.networks",
        "pyvergeos.resources.nics",
        "pyvergeos.resources.nodes",
        "pyvergeos.resources.oidc_applications",
        "pyvergeos.resources.permissions",
        "pyvergeos.resources.recipe_common",
        "pyvergeos.resources.resource_groups",
        "pyvergeos.resources.routing",
        "pyvergeos.resources.rules",
        "pyvergeos.resources.shared_objects",
        "pyvergeos.resources.site_syncs",
        "pyvergeos.resources.sites",
        "pyvergeos.resources.snapshot_profiles",
        "pyvergeos.resources.snapshots",
        "pyvergeos.resources.storage_tiers",
        "pyvergeos.resources.system",
        "pyvergeos.resources.tags",
        "pyvergeos.resources.task_events",
        "pyvergeos.resources.task_schedule_triggers",
        "pyvergeos.resources.task_schedules",
        "pyvergeos.resources.task_scripts",
        "pyvergeos.resources.tasks",
        "pyvergeos.resources.tenant_external_ips",
        "pyvergeos.resources.tenant_layer2",
        "pyvergeos.resources.tenant_manager",
        "pyvergeos.resources.tenant_network_blocks",
        "pyvergeos.resources.tenant_nodes",
        "pyvergeos.resources.tenant_recipes",
        "pyvergeos.resources.tenant_snapshots",
        "pyvergeos.resources.tenant_stats",
        "pyvergeos.resources.tenant_storage",
        "pyvergeos.resources.updates",
        "pyvergeos.resources.users",
        "pyvergeos.resources.vm_imports",
        "pyvergeos.resources.vm_recipes",
        "pyvergeos.resources.vms",
        "pyvergeos.resources.vnet_proxy",
        "pyvergeos.resources.volume_vm_exports",
        "pyvergeos.resources.webhooks",
        "pyvergeos.resources.wireguard",
        # Typer completion internals
        "typer._completion_shared",
        "typer._completion_classes",
        # JSON Schema validation
        "jsonschema",
        "jsonschema_specifications",
        "referencing",
        "referencing.jsonschema",
        # TOML reader (conditional import for Python <3.11)
        "tomli",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="vrg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
