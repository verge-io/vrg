---
name: vrg
description: Manage VergeOS infrastructure using the vrg CLI. Use when asked to manage VMs, virtual machines, networks, firewall rules, DNS, tenants, NAS, snapshots, storage, certificates, or any VergeOS/Verge.io operations. Triggers on "vrg", "verge", "vergeos", "create a VM", "list VMs", "manage network", "firewall rule", "tenant", "NAS share", "snapshot", or any infrastructure management task targeting a VergeOS environment.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# VergeOS CLI (vrg)

Manage VergeOS infrastructure from the terminal. The `vrg` CLI covers 200+ commands across compute, networking, tenants, NAS, identity, automation, and monitoring.

## Command Pattern

```
vrg [global-options] <domain> [sub-domain] <action> [arguments] [options]
```

Most resources follow a consistent CRUD pattern:

```bash
vrg <domain> list                     # List all resources
vrg <domain> get <ID|NAME>            # Get by key or name
vrg <domain> create --name foo ...    # Create
vrg <domain> update <ID|NAME> ...     # Update
vrg <domain> delete <ID|NAME> --yes   # Delete (requires --yes)
```

Destructive operations (`delete`, `reset`) require `--yes` to skip confirmation.

## Global Options

| Option | Short | Purpose |
|--------|-------|---------|
| `--profile` | `-p` | Config profile |
| `--host` | `-H` | VergeOS host URL override |
| `--output` | `-o` | Format: `table`, `wide`, `json`, `csv` |
| `--query` | | Extract field via dot notation |
| `--verbose` | `-v` | Verbosity (`-v`, `-vv`, `-vvv`) |
| `--quiet` | `-q` | Suppress non-essential output |

Use `--output json` when you need to parse results programmatically. Use `--query` to extract specific fields (e.g., `--query status`).

## Domain Reference

### Compute

```bash
# VM lifecycle
vrg vm list [--status running|stopped] [--filter "name eq 'web'"]
vrg vm get <ID|NAME>
vrg vm create --name <name> --os linux --cpu 4 --ram 8192
vrg vm create -f template.vrg.yaml [--dry-run] [--set vm.ram="16 GB"]
vrg vm start|stop|restart|reset <ID|NAME>
vrg vm clone <ID|NAME> --name <new-name> [--preserve-macs]
vrg vm migrate <ID|NAME> [--node <target>]        # Live migrate (VM must be running)
vrg vm hibernate|console <ID|NAME>
vrg vm favorite|unfavorite <ID|NAME>
vrg vm tag|untag <ID|NAME> <TAG>
vrg vm delete <ID|NAME> --yes
vrg vm validate -f template.vrg.yaml

# Drives, NICs, devices, snapshots
vrg vm drive list|get|create|update|delete <VM> [options]
vrg vm nic list|get|create|update|delete <VM> [options]
vrg vm device list|get|create|delete <VM> [options]    # TPM (--model tis --version 2), GPU passthrough
vrg vm snapshot list|get|create|delete|restore <VM> [options]

# Import/Export
vrg vm export list|get|create|start|stop|delete|cleanup [options]
vrg vm import list|get|create|start|cancel|delete [options]
```

### Networking

```bash
# Networks (create requires --name, --type; add --cidr for internal)
vrg network list|get|create|update|delete|start|stop|restart|status [options]
vrg network apply-rules <ID|NAME>    # Apply pending firewall changes
vrg network apply-dns <ID|NAME>      # Apply pending DNS changes

# Firewall rules (--name required on create, --direction is incoming/outgoing, use --dest-ports/--source-ports)
vrg network rule list|get|create|update|delete|enable|disable <NETWORK> [options]

# DNS (views -> zones -> records) — NETWORK, VIEW, ZONE are positional args
vrg network dns view list|get|create|update|delete <NETWORK> [options]
vrg network dns zone list|get|create|update|delete <NETWORK> <VIEW> [options]
vrg network dns record list|get|create|update|delete <NETWORK> <VIEW> <ZONE> [options]

# DHCP & aliases
vrg network host list|get|create|update|delete <NETWORK> [options]
vrg network alias list|get|create|update|delete <NETWORK> [options]

# Diagnostics
vrg network diag leases|addresses|stats <NETWORK>
```

### Tenants

```bash
vrg tenant list|get|create|update|delete|start|stop|restart|reset|clone|isolate [options]
vrg tenant node list|get|create|update|delete <TENANT> [options]
vrg tenant storage list|get|create|update|delete <TENANT> [options]
vrg tenant net-block list|get|create|delete <TENANT> [options]
vrg tenant ext-ip list|get|create|delete <TENANT> [options]
vrg tenant l2 list|get|create|delete <TENANT> [options]
vrg tenant snapshot list|get|create|delete|restore <TENANT> [options]
vrg tenant stats current|history <TENANT>
vrg tenant logs list <TENANT>
vrg tenant share list|get|import|accept|reject|delete <TENANT> [options]
```

### Storage & NAS

```bash
# Storage tiers
vrg storage list|get|summary

# NAS services
vrg nas service list|get|create|update|delete|power-on|power-off|restart [options]

# Volumes & snapshots
vrg nas volume list|get|create|update|delete|enable|disable|reset [options]
vrg nas volume snapshot list|get|create|delete [options]

# Shares
vrg nas cifs list|get|create|update|delete|enable|disable [options]
vrg nas nfs list|get|create|update|delete|enable|disable [options]

# Users, sync, file browsing
vrg nas user list|get|create|update|delete|enable|disable [options]
vrg nas sync list|get|create|update|delete|enable|disable|start|stop [options]
vrg nas files list|get [options]

# Media catalog (ISO, disk images, OVA/OVF)
vrg file list|get|upload|download|update|delete|types [options]
```

### Infrastructure

```bash
vrg cluster list|get
vrg node list|get|maintenance --enable|--disable|restart [options]
vrg gpu list|get|update|stats|instances [options]
vrg gpu profile list|get    # vGPU profiles
vrg gpu device list|get     # Physical GPU inventory
vrg snapshot list|get|create|delete|vms|tenants [options]   # Cloud-level
vrg snapshot profile list|get|create|update|delete [options]
vrg snapshot profile period list|get|create|update|delete [options]
vrg site list|get|create|update|delete|enable|disable|reauth|refresh [options]
vrg site sync outgoing|incoming list|get|enable|disable [options]
```

### Identity & Access

```bash
vrg user list|get|create|update|delete|enable|disable [options]
vrg group list|get|create|update|delete|enable|disable [options]
vrg group member list|add|remove [options]
vrg permission list|get|grant|revoke|revoke-all [options]
vrg api-key list|get|create|delete [options]
vrg auth-source list|get|create|update|delete|debug-on|debug-off [options]
```

### Security

```bash
vrg certificate list|get|create|import|update|delete|renew [options]
vrg oidc list|get|create|update|delete|enable|disable [options]
vrg oidc user list|add|remove [options]
vrg oidc group list|add|remove [options]
vrg oidc log list|get [options]
```

### Automation

```bash
vrg task list|get|create|update|delete|enable|disable|run|cancel [options]
vrg task schedule list|get|create|update|delete|enable|disable|show [options]
vrg task trigger list|create|delete|run [options]
vrg task event list|get|create|update|delete|trigger [options]
vrg task script list|get|create|update|delete|run [options]
vrg recipe list|get|create|update|delete|deploy [options]
vrg tenant-recipe list|get|update|delete|download|deploy [options]
vrg tag list|get|create|update|delete|assign|unassign [options]
vrg tag category list|get|create|update|delete [options]
vrg resource-group list|get|create|update|delete|enable|disable [options]
```

### Monitoring & System

```bash
vrg alarm list|get|snooze|unsnooze|resolve|summary [options]
vrg alarm history list|get [options]
vrg log list|get|search [options]       # list --errors, --level, --type, --since; search <term>
vrg system info|version
vrg theme list|get|create|update|enable|disable|delete|export|import [options]
vrg billing list|get|generate|latest|summary [options]
vrg webhook list|get|create|update|delete|send|history [options]
vrg update settings|source|branch|package|available|log [subcommands]
```

## VM Templates

Create VMs from declarative `.vrg.yaml` files instead of long command lines:

```yaml
apiVersion: v4
kind: VirtualMachine

vars:
  VM_NAME: web-server
  NETWORK: prod-net

vm:
  name: "${VM_NAME}"
  description: "Production web server"
  os_family: linux
  cpu_cores: 4
  ram: 8 GB
  machine_type: q35
  boot_order: cd

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 50 GB

  nics:
    - name: "Primary"
      network: "${NETWORK}"
      interface: virtio

  devices:
    - type: tpm
      model: tis
      version: 2
```

```bash
vrg vm validate -f web-server.vrg.yaml           # Validate
vrg vm create -f web-server.vrg.yaml --dry-run    # Preview
vrg vm create -f web-server.vrg.yaml              # Create
vrg vm create -f web-server.vrg.yaml --set vm.ram="16 GB"  # Override
```

**Batch provisioning:** Use `kind: VirtualMachineSet` with `defaults:` and `vms:` array. Each VM inherits defaults; list fields (drives, nics, devices) replace entirely, not merge.

See `references/templates.md` for the full field reference.

## Common Workflows

**Create a VM with network access:**
```bash
vrg vm create --name web-01 --os linux --cpu 2 --ram 4096
vrg vm drive create web-01 --name "OS Disk" --media disk --interface virtio-scsi --size 50GB
vrg vm nic create web-01 --network "Production" --interface virtio
vrg vm start web-01
```

**Set up a network with firewall:**
```bash
vrg network create --name lab-net --type internal --cidr 10.0.0.0/24 [--ip 10.0.0.254]
vrg network rule create lab-net --name "Allow HTTPS" --action accept --protocol tcp --dest-ports 443 --direction incoming
vrg network apply-rules lab-net
vrg network start lab-net
```

**Configure DNS:**
```bash
vrg network dns view create my-net --name "Internal"
vrg network dns zone create my-net Internal --domain "lab.local" --type master
vrg network dns record create my-net Internal lab.local --name "app" --type A --value "10.0.0.10"
vrg network apply-dns my-net
```

**Snapshot and restore:**
```bash
vrg vm snapshot create my-vm --name "pre-upgrade"
# ... do work ...
vrg vm snapshot restore my-vm --name "pre-upgrade"
```

**Check what's running:**
```bash
vrg -o wide vm list --status running
vrg -o wide node list
vrg alarm summary
vrg system info
```

## Output Tips

**`-o` is a global option — place it BEFORE the command:**
- `vrg -o json vm list` for scripting and piping to `jq`
- `vrg -o csv vm list` for spreadsheet export
- `vrg -o wide vm list` for all columns in table format
- `vrg --query name vm get web-01` to extract a single field as plain text
- Chain with `jq`: `vrg -o json vm get web-01 | jq '.status'`

## Edge Cases

- **Name vs ID:** Most commands accept either. If a name matches multiple resources, use the numeric ID instead.
- **Firewall/DNS changes are staged.** After creating/updating rules or records, run `apply-rules` or `apply-dns` on the network to activate them.
- **Destructive commands** require `--yes` — don't add it unless explicitly confirmed by the user.
- **Template variables** use `${VAR}` syntax and can be overridden by environment variables or `--set`.

## Configuration

Config lives in `~/.vrg/config.toml`. Precedence: CLI args > env vars > config profile > defaults.

```bash
vrg configure setup          # Interactive wizard
vrg configure show           # Show current profile
vrg configure list           # List all profiles
vrg system info              # Verify connection
```

Multiple profiles supported — switch with `vrg -p <profile> <command>`.
