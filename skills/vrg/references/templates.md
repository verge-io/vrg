# VM Templates

Verge CLI supports declarative YAML templates for creating virtual machines. Instead of passing dozens of flags to `vrg vm create`, you define the desired state in a `.vrg.yaml` file and provision it with a single command.

Templates support variables, dry-run previews, runtime overrides, cloud-init, and batch provisioning of multiple VMs from shared defaults.

---

## Quick Start

Create a file called `web-server.vrg.yaml`:

```yaml
apiVersion: v4
kind: VirtualMachine

vm:
  name: web-server-01
  os_family: linux
  cpu_cores: 2
  ram: 4GB

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 50GB

  nics:
    - network: External
```

Then:

```bash
# Validate the template
vrg vm validate -f web-server.vrg.yaml

# Preview what will be created
vrg vm create -f web-server.vrg.yaml --dry-run

# Create the VM
vrg vm create -f web-server.vrg.yaml
```

---

## CLI Usage

### Create from template

```bash
vrg vm create -f <template.vrg.yaml> [--set key.path=value ...] [--dry-run]
```

| Flag | Short | Description |
|------|-------|-------------|
| `--file` | `-f` | Path to `.vrg.yaml` template file |
| `--set` | | Override a template value (repeatable) |
| `--dry-run` | | Show what would be created without making API calls |

### Validate a template

```bash
vrg vm validate -f <template.vrg.yaml> [--set key.path=value ...]
```

Validates the template against the JSON schema, checks required fields, enum values, and unit formats. Exits with code 0 on success or 8 on validation failure.

### Runtime overrides with --set

Override any value in the template at create time using dot-path notation:

```bash
vrg vm create -f template.vrg.yaml \
  --set vm.name=web-server-02 \
  --set vm.ram=16GB \
  --set vm.cpu_cores=8
```

Overrides are applied after variable substitution and before validation. Intermediate objects are created automatically — you don't need to pre-define the full path.

---

## Template Structure

Every template has three required top-level fields:

```yaml
apiVersion: v4                    # Must be "v4"
kind: VirtualMachine              # "VirtualMachine" or "VirtualMachineSet"
vm:                               # VM configuration (for VirtualMachine kind)
  name: my-vm
  os_family: linux
```

Optional top-level fields:

```yaml
vars:                             # Variable definitions (see Variables section)
  env: staging
```

---

## VM Configuration Reference

The `vm:` block (or each entry in `vms:` for sets) accepts the following fields.

### Identification

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | | VM name |
| `description` | string | no | | VM description |
| `enabled` | boolean | no | `true` | Whether the VM is enabled |
| `os_family` | string | yes | | `linux`, `windows`, `freebsd`, or `other` |
| `os_description` | string | no | | Free-text OS description (e.g., "Ubuntu 24.04 LTS") |

### Compute

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cpu_cores` | integer | no | `1` | Number of CPU cores (minimum 1) |
| `cpu_type` | string | no | `"auto"` | CPU emulation type |
| `ram` | sizeValue | no | `1GB` | RAM amount (e.g., `512MB`, `4GB`, `1TB`, or integer MB) |

### Machine

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `machine_type` | string | no | `"q35"` | `q35` or `pc` |
| `boot_order` | string | no | `"cd"` | Boot device order (see below) |
| `allow_hotplug` | boolean | no | `true` | Allow hot-plugging devices |
| `uefi` | boolean | no | `false` | Enable UEFI firmware |
| `secure_boot` | boolean | no | `false` | Enable Secure Boot (requires `uefi: true`) |

**Boot order values:** `d` (disk), `cd` (cdrom then disk), `cdn` (cdrom, disk, network), `c` (cdrom), `dc` (disk then cdrom), `n` (network), `nd` (network then disk), `do` (disk only)

### Display and Console

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `console` | string | no | `"vnc"` | `vnc` or `spice` |
| `video` | string | no | `"std"` | `std`, `cirrus`, `vmware`, `qxl`, `virtio`, or `none` |
| `guest_agent` | boolean | no | `false` | Enable QEMU guest agent |
| `rtc_base` | string | no | `"utc"` | `utc` or `localtime` (use `localtime` for Windows) |

### Scheduling and HA

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cluster` | nameOrId | no | | Target cluster (name or numeric ID) |
| `failover_cluster` | nameOrId | no | | Failover cluster |
| `preferred_node` | nameOrId | no | | Preferred node for placement |
| `ha_group` | string | no | | HA group name |
| `snapshot_profile` | nameOrId | no | | Snapshot profile |

### Power and Advanced

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `power_on_after_create` | boolean | no | `false` | Start the VM after provisioning |
| `advanced_options` | string | no | | Multiline QEMU options (one per line) |

---

## Drives

Each entry in `drives:` defines a virtual disk or optical drive.

```yaml
drives:
  - name: "OS Disk"
    media: disk
    interface: virtio-scsi
    size: 50GB
    preferred_tier: 2

  - name: "Install ISO"
    media: cdrom
    interface: ahci
    media_source: ubuntu-24.04-server    # Resolved by name
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | no | | Drive name |
| `description` | string | no | | Drive description |
| `media` | string | no | `"disk"` | `disk`, `cdrom`, `import`, `clone`, or `efidisk` |
| `interface` | string | no | `"virtio-scsi"` | `virtio-scsi`, `virtio`, `ide`, `ahci`, `lsi53c895a`, or `nvme` |
| `size` | sizeValue | no | | Disk size (e.g., `50GB`, `1TB`) — not needed for cdrom |
| `preferred_tier` | integer | no | `3` | Storage tier 1-5 (1 = fastest) |
| `media_source` | nameOrId | no | | Source file for cdrom/import (name or numeric ID) |
| `enabled` | boolean | no | `true` | Whether the drive is enabled |
| `order` | integer | no | | Boot/display order |

---

## NICs

Each entry in `nics:` defines a network interface. The `network` field is required.

```yaml
nics:
  - name: "Primary"
    interface: virtio
    network: External

  - name: "Management"
    network: internal-mgmt
    mac: "52:54:00:12:34:56"
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `network` | nameOrId | **yes** | | Network to connect to (name or numeric ID) |
| `name` | string | no | | NIC name |
| `description` | string | no | | NIC description |
| `interface` | string | no | `"virtio"` | `virtio`, `e1000`, `e1000e`, `rtl8139`, `pcnet`, `igb`, or `vmxnet3` |
| `enabled` | boolean | no | `true` | Whether the NIC is enabled |
| `mac` | string | no | | MAC address (`XX:XX:XX:XX:XX:XX` format, auto-assigned if omitted) |

---

## Devices

Currently supports TPM devices. The `type` field is required.

```yaml
devices:
  - type: tpm
    model: crb
    version: "2.0"
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | **yes** | | Device type (`tpm`) |
| `name` | string | no | | Device name |
| `model` | string | no | `"crb"` | TPM model: `tis` or `crb` |
| `version` | string | no | `"2.0"` | TPM version: `"1.2"` or `"2.0"` |

---

## Cloud-Init

Configure cloud-init to run first-boot provisioning. When a `cloudinit` block is present, the API auto-creates the data files; the template populates them with your content.

```yaml
cloudinit:
  datasource: nocloud
  files:
    - name: user-data
      content: |
        #cloud-config
        hostname: web-server-01
        users:
          - name: deploy
            groups: sudo
            shell: /bin/bash
            sudo: ALL=(ALL) NOPASSWD:ALL
            ssh_authorized_keys:
              - ssh-ed25519 AAAAC3...
        packages:
          - nginx
          - qemu-guest-agent
        runcmd:
          - systemctl enable --now nginx
          - systemctl enable --now qemu-guest-agent
    - name: meta-data
      content: |
        instance-id: web-server-01
        local-hostname: web-server-01
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `datasource` | string | no | | `nocloud` or `config_drive_v2` |
| `files` | array | no | | Cloud-init data files |
| `files[].name` | string | yes | | `user-data`, `meta-data`, `vendor-data`, or `network-data` |
| `files[].content` | string | yes | | File contents (typically cloud-config YAML) |

---

## Variables

Templates support `${VAR}` substitution for values that change between environments or deployments.

### Defining variables

Variables can be defined in a `vars:` block at the top of the template:

```yaml
vars:
  env: staging
  cluster_id: "1"

vm:
  name: "${env}-web-01"
  cluster: ${cluster_id}
```

### Environment variable overrides

Environment variables take precedence over `vars:` definitions:

```bash
env=production vrg vm create -f template.vrg.yaml
```

This creates a VM named `production-web-01` even though the template defines `env: staging`.

### Default values

Use `${VAR:-default}` to provide a fallback when a variable is not set:

```yaml
vm:
  name: "${VM_NAME:-my-vm}"
  ram: "${VM_RAM:-4GB}"
  cpu_cores: ${VM_CORES:-2}
```

### Required variables

Variables without a default raise an error if not set:

```yaml
vm:
  name: "${VM_NAME}"     # Error if VM_NAME is not set
```

```
Error: Unresolved template variables: VM_NAME
```

### Processing order

1. `vars:` block is extracted from the template
2. Environment variables are merged (env wins over `vars:`)
3. `${VAR}` references are substituted in the raw YAML text
4. YAML is parsed
5. `--set` overrides are applied
6. Schema validation runs

---

## Batch Provisioning with VirtualMachineSet

Use `kind: VirtualMachineSet` to create multiple VMs from shared defaults.

```yaml
apiVersion: v4
kind: VirtualMachineSet

defaults:
  os_family: linux
  cpu_cores: 2
  ram: 4GB
  machine_type: q35
  uefi: true
  guest_agent: true

  cloudinit:
    datasource: nocloud
    files:
      - name: user-data
        content: |
          #cloud-config
          users:
            - name: deploy
              groups: sudo
              sudo: ALL=(ALL) NOPASSWD:ALL
              ssh_authorized_keys:
                - ssh-ed25519 AAAAC3...
          packages:
            - qemu-guest-agent
          runcmd:
            - systemctl enable --now qemu-guest-agent

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 30GB

  nics:
    - name: "Primary"
      interface: virtio
      network: Internal

vms:
  - name: k8s-control-01
    description: "Kubernetes control plane node 1"
    cpu_cores: 4
    ram: 8GB
    ha_group: "k8s-control"
    drives:
      - name: "OS Disk"
        media: disk
        interface: virtio-scsi
        size: 50GB
        preferred_tier: 2
      - name: "etcd Data"
        media: disk
        interface: virtio-scsi
        size: 20GB
        preferred_tier: 1

  - name: k8s-worker-01
    description: "Kubernetes worker node 1"
    cpu_cores: 8
    ram: 32GB

  - name: monitoring-01
    description: "Prometheus + Grafana stack"
    # Inherits all defaults — 2 cores, 4GB, 30GB disk
```

### How merging works

- Each VM in `vms:` inherits all fields from `defaults:`
- VM-level values override defaults
- **List fields (`drives`, `nics`, `devices`) are replaced entirely, not merged** — if a VM defines its own `drives:`, the default drives are not included
- Each VM in `vms:` requires at least `name`; `os_family` can come from `defaults:`

### Preview and create

```bash
# Preview all VMs that would be created
vrg vm create -f k8s-cluster.vrg.yaml --dry-run

# Create all VMs
vrg vm create -f k8s-cluster.vrg.yaml
```

---

## Size Values

RAM and disk sizes accept human-friendly strings or plain integers.

| Format | RAM meaning | Disk meaning |
|--------|-------------|--------------|
| `512MB` | 512 MB | 0 GB (rounded) |
| `4GB` | 4096 MB | 4 GB |
| `1TB` | 1048576 MB | 1024 GB |
| `4096` (integer) | 4096 MB | 4096 GB |

Units are case-insensitive (`gb`, `GB`, `Gb` all work).

---

## Name Resolution

Fields marked as `nameOrId` accept either a numeric ID or a resource name. The CLI resolves names to IDs at create time by querying the API.

```yaml
# By numeric ID
cluster: 1
network: 3

# By name (resolved via API lookup)
cluster: production-cluster
network: External
media_source: ubuntu-24.04-server
```

If a name matches multiple resources, the CLI reports an error and asks you to use a numeric ID instead.

---

## Provisioning Order

When a template is applied, resources are created in this order:

1. **VM** — created with compute, machine, display, and scheduling settings
2. **Cloud-init files** — auto-created files are populated with template content
3. **Drives** — created in array order
4. **NICs** — created in array order
5. **Devices** — created in array order
6. **Power on** — if `power_on_after_create: true`

If a sub-resource fails to create (e.g., a NIC references a non-existent network), the VM still exists with any previously-created resources. The error is reported and the CLI exits with code 1.

---

## Examples

### Linux Web Server

```yaml
apiVersion: v4
kind: VirtualMachine

vm:
  name: web-server-01
  description: "Nginx web server"
  os_family: linux
  cpu_cores: 4
  ram: 8GB
  machine_type: q35
  uefi: true
  guest_agent: true

  cloudinit:
    datasource: nocloud
    files:
      - name: user-data
        content: |
          #cloud-config
          hostname: web-server-01
          packages:
            - nginx
            - qemu-guest-agent
          runcmd:
            - systemctl enable --now nginx
            - systemctl enable --now qemu-guest-agent

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 50GB

  nics:
    - name: "External"
      interface: virtio
      network: External
```

### Windows Server with ISO

```yaml
apiVersion: v4
kind: VirtualMachine

vm:
  name: dc-01
  description: "Primary Domain Controller"
  os_family: windows
  cpu_cores: 4
  ram: 16GB
  machine_type: q35
  uefi: true
  secure_boot: true
  rtc_base: localtime
  guest_agent: true

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 100GB
      preferred_tier: 2

    - name: "Windows ISO"
      media: cdrom
      interface: ahci
      media_source: windows-2025-eval

    - name: "VirtIO Drivers"
      media: cdrom
      interface: ahci
      media_source: virtio-win

  nics:
    - name: "Corporate LAN"
      interface: virtio
      network: internal-lan

  devices:
    - type: tpm
      model: crb
      version: "2.0"
```

### Parameterized Template

```yaml
apiVersion: v4
kind: VirtualMachine

vars:
  env: dev
  role: web

vm:
  name: "${env}-${role}-01"
  os_family: linux
  cpu_cores: ${VM_CORES:-2}
  ram: "${VM_RAM:-4GB}"
  machine_type: q35

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: "${DISK_SIZE:-30GB}"

  nics:
    - network: "${NETWORK:-Internal}"
```

```bash
# Use defaults (dev-web-01, 2 cores, 4GB, 30GB, Internal)
vrg vm create -f template.vrg.yaml

# Override for production
env=prod VM_CORES=8 VM_RAM=32GB DISK_SIZE=100GB NETWORK=External \
  vrg vm create -f template.vrg.yaml
```
