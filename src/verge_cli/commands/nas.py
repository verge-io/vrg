"""NAS management commands (parent group)."""

from __future__ import annotations

import typer

from verge_cli.commands import (
    nas_cifs,
    nas_files,
    nas_nfs,
    nas_service,
    nas_sync,
    nas_user,
    nas_volume,
    nas_volume_snapshot,
)

app = typer.Typer(
    name="nas",
    help=(
        "Manage VergeOS NAS (Network Attached Storage) services, volumes, and"
        " shares.\n\n"
        "VergeOS NAS provides file-level storage on top of vSAN. A **NAS"
        " service** is a dedicated VM (deployed from the standard NAS VM"
        " recipe) that hosts **volumes** (filesystems — `ext4`, `ybfsv2`, or"
        " remote CIFS/NFS mounts). Volumes can be exported as **NFS** and/or"
        " **CIFS/SMB shares** and support point-in-time snapshots for backup"
        " and restore.\n\n"
        "The resource hierarchy is: **NAS Service → Volume → Share**. Most"
        " subcommands take the NAS service name or key as their first"
        " positional argument, because volumes, shares, and users are scoped"
        " to a single service.\n\n"
        "Subresources have their own groups: `vrg nas service` (service VMs),"
        " `vrg nas volume` (filesystems), `vrg nas volume snapshot` (volume"
        " snapshots), `vrg nas cifs` (SMB shares), `vrg nas nfs` (NFS"
        " exports), `vrg nas user` (CIFS users), `vrg nas sync` (remote"
        " volume sync), and `vrg nas files` (filesystem browser).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List NAS services\n"
        "    vrg nas service list\n\n"
        "    # Start / stop a NAS service VM\n"
        "    vrg nas service start my-nas\n"
        "    vrg nas service stop my-nas\n\n"
        "    # List volumes on a NAS service\n"
        "    vrg nas volume list my-nas\n\n"
        "    # Create a 100 GB volume on tier 2\n"
        "    vrg nas volume create my-nas --name shared-data --maxsize 100GB --preferred-tier 2\n\n"
        "    # Create a CIFS/SMB and an NFS share on that volume\n"
        "    vrg nas cifs create my-nas --volume shared-data --name smb-share\n"
        "    vrg nas nfs create my-nas --volume shared-data --name nfs-export\n\n"
        "    # List and create volume snapshots\n"
        "    vrg nas volume snapshot list my-nas --volume shared-data\n"
        "    vrg nas volume snapshot create my-nas --volume shared-data --name nightly\n\n"
        "    # Browse files inside a volume\n"
        "    vrg nas files list my-nas --volume shared-data --path /\n\n"
        "    # JSON output for scripting / agents\n"
        "    vrg -o json nas volume list my-nas\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "A NAS service is a VM. It **must be powered on and online** before"
        " its volumes will mount or its shares serve traffic. Use"
        " `vrg nas service start` / `stop` to control the service VM.\n\n"
        "Volumes are scoped to a single NAS service and cannot be moved"
        " between services after creation. `fs_type` and `encrypt` are set at"
        " creation and are immutable.\n\n"
        "NAS services, volumes, shares, and users are referenced by name or"
        " numeric key (`$key`). When a name matches multiple resources, vrg"
        " prints all matches and exits with code 7 — use the numeric key to"
        " disambiguate. Use `-o json` for machine-readable output suitable for"
        " automation and agents."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(nas_service.app, name="service")

# Volume commands with snapshot sub-typer
nas_volume.app.add_typer(nas_volume_snapshot.app, name="snapshot")
app.add_typer(nas_volume.app, name="volume")

app.add_typer(nas_cifs.app, name="cifs")
app.add_typer(nas_nfs.app, name="nfs")
app.add_typer(nas_user.app, name="user")
app.add_typer(nas_sync.app, name="sync")
app.add_typer(nas_files.app, name="files")
