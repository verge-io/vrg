# Verge CLI Shakedown Test

> Full system integration test for vrg against a live VergeOS instance.
>
> **LAB/DEV ENVIRONMENT ONLY** — never run this against production.

## Safety Rules

- **NEVER** modify CORE, DMZ, or External networks — only test against resources we deploy
- All test resources use the `shakedown-` prefix for easy identification and cleanup
- Deploying resources IS part of the test — everything is built from scratch
- If a test fails, note it and continue — don't abandon the run

## Prerequisites

- A VergeOS lab/dev instance accessible via network
- Either an existing `~/.vrg/config.toml` (`vrg configure show`) or credentials for `vrg configure setup`
- At least one ISO or OVA in the media catalog (for drive import tests)
- An available network range that doesn't conflict with existing infrastructure

## Test Resource Names

| Resource | Name | Notes |
|----------|------|-------|
| Network | `shakedown-net` | Internal network, e.g. 10.99.99.0/24 |
| VM | `shakedown-vm` | Minimal: 1 CPU, 512MB RAM, Linux |
| VM Clone | `shakedown-vm-clone` | Clone of shakedown-vm (created & deleted in test) |
| Tenant | `shakedown-tenant` | Minimal tenant deployment |
| NAS Service | `shakedown-nas` | NAS service VM |
| NAS Volume | `shakedown-vol` | Small test volume |
| Snapshot Profile | `shakedown-profile` | With test period |
| NAS User | `shakedown-user` | Local NAS user |
| Cloud Snapshot | `shakedown-snap` | System-level snapshot |
| VM Snapshot | `shakedown-vm-snap` | Per-VM snapshot |
| Catalog | `shakedown-catalog` | Local catalog for recipe testing |
| Recipe | `shakedown-recipe` | Local recipe for testing |
| User | `shakedown-user-admin` | Test user account |
| Group | `shakedown-group` | Test group |
| API Key | `shakedown-apikey` | API key for test user |
| Auth Source | `shakedown-auth` | Test auth source (if SSO available) |
| Task | `shakedown-task` | Scheduled task |
| Task Schedule | `shakedown-schedule` | Task schedule |
| Certificate | `shakedown-cert` | Self-signed certificate |
| OIDC App | `shakedown-oidc` | OIDC application |
| Tag Category | `shakedown-category` | Tag category |
| Tag | `shakedown-tag` | Tag for resource tagging |
| Resource Group | `shakedown-rg` | PCI resource group |
| Shared Object | `shakedown-shared` | VM shared with tenant |
| Restored VM | `shakedown-restored-vm` | VM restored from cloud snapshot |
| Restore Snapshot | `shakedown-restore-snap` | Cloud snapshot for restore test |

---

## 1. Configure & System Info

Warmup / read-only tests. Use existing config or create one.

### Configuration

- [ ] `vrg configure setup` — complete interactive setup OR verify existing config works
- [ ] `vrg configure show` — displays host, profile, output format
- [ ] `vrg configure list` — lists all configured profiles

### System

- [ ] `vrg --version` — prints version string
- [ ] `vrg system info` — returns system name, version, uptime, cluster info
- [ ] `vrg system version` — returns VergeOS version string

### System Settings

- [ ] `vrg system settings list` — shows system settings
- [ ] `vrg system settings list --modified` — shows only modified settings
- [ ] `vrg system settings get <setting-key>` — shows specific setting value and default

### System License

- [ ] `vrg system license list` — lists licenses with validity status
- [ ] `vrg system license get <id>` — license details (is_valid, valid_from, valid_until, features, auto_renewal)
- [ ] `vrg system license generate-payload` — generates air-gap license request payload (read-only, safe to run)

> Do NOT run `vrg system license add` during shakedown — destructive to licensing.

### System Inventory

- [ ] `vrg system inventory` — full system inventory
- [ ] `vrg system inventory --vms --nodes` — filtered inventory (only VMs and nodes)

### Cluster

- [ ] `vrg cluster list` — lists clusters
- [ ] `vrg cluster get <name>` — shows cluster details
- [ ] `vrg cluster vsan-status --name <name>` — shows vSAN health

### Nodes

- [ ] `vrg node list` — lists all nodes with status
- [ ] `vrg node get <name>` — shows node details (CPU, RAM, role)
- [ ] `vrg node pci-list <name>` — lists PCI devices on a node
- [ ] `vrg node gpu-list <name>` — lists GPU devices on a node (may be empty if no GPUs)
- [ ] `vrg node stats <name>` — shows node statistics (CPU, RAM, temp)

### Node Query Commands

- [ ] `vrg node query ping node1 8.8.8.8` — ping from physical node
- [ ] `vrg node query dns node1 example.com` — DNS resolution from node
- [ ] `vrg node query traceroute node1 8.8.8.8` — traceroute from node
- [ ] `vrg node query arp node1` — ARP table for node
- [ ] `vrg node query lsblk node1` — list block devices
- [ ] `vrg node query dmidecode node1` — hardware info
- [ ] `vrg node query smartctl node1 /dev/sda` — SMART health data
- [ ] `vrg node query ipmi-sensor node1` — IPMI sensor readings
- [ ] `vrg node query ipmi-chassis node1` — IPMI chassis status
- [ ] `vrg node query run node1 whatsmyip` — generic query escape hatch
- [ ] `vrg -o json node query ping node1 8.8.8.8` — JSON output with metadata

### Node LLDP

- [ ] `vrg node lldp list node1` — list LLDP neighbors
- [ ] `vrg node lldp list node1 --nic 5` — filter by NIC key

### System Diagnostics

- [ ] `vrg system diag list` — list diagnostic bundles (may be empty)

### Storage

- [ ] `vrg storage list` — lists all storage tiers
- [ ] `vrg storage get <tier>` — shows tier details (capacity, used, available)
- [ ] `vrg storage summary` — shows aggregate storage across tiers

### Doctor (System Health Check)

- [ ] `vrg doctor` — runs all 15 checks, outputs summary table with pass/warn/fail/skip statuses
- [ ] `vrg doctor --check connectivity` — runs only the connectivity check (verifies auth + system version)
- [ ] `vrg doctor --check clusters,nodes,storage` — runs a subset of infrastructure checks
- [ ] `vrg doctor --check alarms` — alarm check (fail if critical, warn if error-level)
- [ ] `vrg doctor --check updates` — update state check (warn if reboot required)
- [ ] `vrg doctor --check versions` — version consistency across nodes
- [ ] `vrg doctor --check fabric` — NIC fabric health
- [ ] `vrg doctor --check networks` — network dashboard health
- [ ] `vrg doctor --check certificates` — certificate expiry (warn if <30 days)
- [ ] `vrg doctor --check licenses` — license validity
- [ ] `vrg doctor --check drive_smart` — physical drive SMART health (pass if no warnings)
- [ ] `vrg doctor --check dimm_health` — DIMM health across all nodes
- [ ] `vrg doctor --check vsan_journal` — vSAN journal and tier status
- [ ] `vrg doctor --check driver_reload` — node driver reload state
- [ ] `vrg doctor --list-checks` — prints all available check names
- [ ] `vrg -o json doctor` — JSON output with name, status, message, details for each check
- [ ] Verify exit code is 0 when all checks pass/warn/skip, 1 if any check fails

---

## 2. Network Provisioning

### Create & Start

- [ ] `vrg network create --name shakedown-net --type internal --cidr 10.99.99.0/24` — created successfully (IP auto-derived as .1)
- [ ] `vrg network get shakedown-net` — verify CIDR is 10.99.99.0/24 and IP is 10.99.99.1
- [ ] `vrg network update shakedown-net --name shakedown-net2` — rename to free up name
- [ ] `vrg network create --name shakedown-net --type internal --cidr 10.99.99.0/24 --ip 10.99.99.254` — created with explicit IP
- [ ] `vrg network get shakedown-net` — verify IP is 10.99.99.254 (not auto-derived .1)
- [ ] `vrg network delete shakedown-net --yes` — delete explicit-IP network
- [ ] `vrg network update shakedown-net2 --name shakedown-net` — rename back for remaining tests
- [ ] `vrg network start shakedown-net` — network starts
- [ ] `vrg network status shakedown-net` — shows running status

### Firewall Rules

- [ ] `vrg network rule create shakedown-net --name "Allow SSH" --action accept --protocol tcp --direction incoming --dest-ports 22` — rule created
- [ ] `vrg network rule create shakedown-net --name "Allow HTTP" --action accept --protocol tcp --direction incoming --dest-ports 80,443` — rule created
- [ ] `vrg network rule list shakedown-net` — shows both rules
- [ ] `vrg network rule get shakedown-net <rule-id>` — shows rule details
- [ ] `vrg network rule update shakedown-net <rule-id> --dest-ports 8080` — updated
- [ ] `vrg network rule disable shakedown-net <rule-id>` — rule disabled
- [ ] `vrg network rule enable shakedown-net <rule-id>` — rule re-enabled
- [ ] `vrg network apply-rules shakedown-net` — rules applied

### DNS

- [ ] `vrg network dns view list shakedown-net` — lists views
- [ ] `vrg network dns view create shakedown-net --name shakedown-view` — view created
- [ ] `vrg network dns zone create shakedown-net shakedown-view --domain shakedown.local` — zone created
- [ ] `vrg network dns zone list shakedown-net shakedown-view` — shows zone
- [ ] `vrg network dns zone get shakedown-net shakedown-view <zone-id>` — zone details
- [ ] `vrg network dns record create shakedown-net shakedown-view shakedown.local --name www --type A --value 10.99.99.10` — record created
- [ ] `vrg network dns record list shakedown-net shakedown-view shakedown.local` — shows record
- [ ] `vrg network dns record get shakedown-net shakedown-view shakedown.local <record-id>` — record details
- [ ] `vrg network dns record update shakedown-net shakedown-view shakedown.local <record-id> --value 10.99.99.20` — updated
- [ ] `vrg network dns record delete shakedown-net shakedown-view shakedown.local <record-id> --yes` — deleted
- [ ] `vrg network dns zone delete shakedown-net shakedown-view <zone-id> --yes` — deleted
- [ ] `vrg network dns view delete shakedown-net <view-id> --yes` — deleted
- [ ] `vrg network apply-dns shakedown-net` — DNS applied

### Host Overrides

- [ ] `vrg network host create shakedown-net --hostname testhost --ip 10.99.99.50` — host created
- [ ] `vrg network host list shakedown-net` — shows host
- [ ] `vrg network host get shakedown-net <host-id>` — host details
- [ ] `vrg network host update shakedown-net <host-id> --ip 10.99.99.51` — updated
- [ ] `vrg network host delete shakedown-net <host-id> --yes` — deleted

### IP Aliases

- [ ] `vrg network alias create shakedown-net --ip 10.99.99.200 --name shakedown-alias` — alias created
- [ ] `vrg network alias list shakedown-net` — shows alias
- [ ] `vrg network alias get shakedown-net <alias-id>` — alias details
- [ ] `vrg network alias update shakedown-net <alias-id> --description "test alias"` — updated
- [ ] `vrg network alias delete shakedown-net <alias-id> --yes` — deleted

### Network Diagnostics

- [ ] `vrg network diag leases shakedown-net` — shows DHCP leases (may be empty)
- [ ] `vrg network diag addresses shakedown-net` — shows IP addresses in use
- [ ] `vrg network diag stats shakedown-net` — shows network statistics

### Network Monitor Quality

- [ ] `vrg network diag quality External` — shows quality %, latency, packet loss
- [ ] `vrg network diag history External --limit 5` — shows recent monitoring history
- [ ] `vrg network diag history External --long --limit 5` — shows long-term history

### Network Query Commands

- [ ] `vrg network query ping External 8.8.8.8` — ping from network router
- [ ] `vrg network query dns External example.com` — DNS resolution from network
- [ ] `vrg network query traceroute External 8.8.8.8` — traceroute from network
- [ ] `vrg network query arp External` — ARP table for network
- [ ] `vrg network query firewall External` — nftables rules for network
- [ ] `vrg network query tcp-connect External 8.8.8.8 443` — TCP connectivity test
- [ ] `vrg network query run External whatsmyip` — generic query escape hatch
- [ ] `vrg -o json network query ping External 8.8.8.8` — JSON output with metadata

### Network Dashboard

- [ ] `vrg network diag dashboard overview` — shows network dashboard summary
- [ ] `vrg network diag dashboard ipsec-status shakedown-net` — IPSec active connections (may be empty)
- [ ] `vrg network diag dashboard wireguard-status shakedown-net` — WireGuard peer status (may be empty)

---

## 3. VM Provisioning

### Create & Lifecycle

- [ ] `vrg vm create --name shakedown-vm --cpu 1 --ram 512 --os linux` — VM created
- [ ] `vrg vm list` — shows shakedown-vm
- [ ] `vrg vm get shakedown-vm` — shows name, CPU, RAM, OS, status
- [ ] `vrg vm update shakedown-vm --description "Shakedown test VM"` — updated
- [ ] `vrg vm start shakedown-vm` — VM starts
- [ ] `vrg vm stop shakedown-vm` — VM stops (graceful)
- [ ] `vrg vm start shakedown-vm` — restart for further tests
- [ ] `vrg vm restart shakedown-vm` — graceful restart
- [ ] `vrg vm reset shakedown-vm --yes` — hard reset

### Clone

- [ ] `vrg vm clone shakedown-vm --name shakedown-vm-clone` — VM cloned
- [ ] `vrg vm get shakedown-vm-clone` — verify clone exists (stopped, same CPU/RAM)
- [ ] `vrg vm clone shakedown-vm --name shakedown-vm-clone2 --preserve-macs` — clone with MAC preservation
- [ ] `vrg vm delete shakedown-vm-clone2 --yes` — cleanup second clone
- [ ] `vrg vm delete shakedown-vm-clone --yes` — cleanup first clone

### Console

- [ ] `vrg vm console shakedown-vm` — shows console info (type, host, port, url)
- [ ] `vrg -o json vm console shakedown-vm` — JSON output includes console_type, host, port, web_url, is_available

### Migrate

- [ ] `vrg vm migrate shakedown-vm` — auto node selection (succeeds on multi-node cluster)
- [ ] `vrg vm migrate shakedown-vm --node <target-node>` — explicit target node
- [ ] `vrg vm stop shakedown-vm --wait` — stop for migrate error test
- [ ] `vrg vm migrate shakedown-vm` — fails with "not running" (exit 1)
- [ ] `vrg vm start shakedown-vm --wait` — restart for further tests

### Hibernate

- [ ] `vrg vm hibernate shakedown-vm` — VM enters hibernating/hibernated state
- [ ] `vrg vm get shakedown-vm` — verify status is hibernated (wait ~15s if still hibernating)
- [ ] `vrg vm start shakedown-vm --wait` — resume from hibernate, VM running again

### Favorite / Unfavorite

- [ ] `vrg vm favorite shakedown-vm` — VM marked as favorite
- [ ] `vrg vm unfavorite shakedown-vm` — VM removed from favorites

### Tag / Untag

> Requires shakedown-tag to exist (created in Section 15). If running out of order, create a tag first.

- [ ] `vrg vm tag shakedown-vm shakedown-tag` — tag assigned to VM
- [ ] `vrg vm untag shakedown-vm shakedown-tag` — tag removed from VM
- [ ] `vrg vm tag shakedown-vm 1` — tag by numeric key works
- [ ] `vrg vm untag shakedown-vm 1` — untag by numeric key works

### Drives

- [ ] `vrg vm drive list shakedown-vm` — empty or default drive
- [ ] `vrg vm drive create shakedown-vm --size 10GB --name "Boot Disk"` — drive created
- [ ] `vrg vm drive create shakedown-vm --size 5GB --name "Data Disk" --interface ide --tier 2` — second drive
- [ ] `vrg vm drive list shakedown-vm` — shows both drives
- [ ] `vrg vm drive get shakedown-vm "Boot Disk"` — shows size, interface, tier
- [ ] `vrg vm drive update shakedown-vm "Boot Disk" --name "OS Disk"` — renamed
- [ ] `vrg vm drive update shakedown-vm "OS Disk" --disabled` — disabled
- [ ] `vrg vm drive update shakedown-vm "OS Disk" --enabled` — re-enabled
- [ ] `vrg vm drive import shakedown-vm --file-name <ova-or-iso> --name "Imported"` — imported from catalog
- [ ] `vrg vm drive delete shakedown-vm "Imported" --yes` — deleted
- [ ] `vrg vm drive delete shakedown-vm "Data Disk" --yes` — deleted

### NICs

- [ ] `vrg vm nic create shakedown-vm --network shakedown-net --name "Primary NIC"` — NIC created
- [ ] `vrg vm nic create shakedown-vm --network shakedown-net --name "Static NIC" --ip 10.99.99.50` — static IP
- [ ] `vrg vm nic list shakedown-vm` — shows both NICs
- [ ] `vrg vm nic get shakedown-vm "Primary NIC"` — shows MAC, network, IP
- [ ] `vrg vm nic update shakedown-vm "Primary NIC" --name "mgmt0"` — renamed
- [ ] `vrg vm nic update shakedown-vm "mgmt0" --disabled` — disabled
- [ ] `vrg vm nic update shakedown-vm "mgmt0" --enabled` — re-enabled
- [ ] `vrg vm nic delete shakedown-vm "Static NIC" --yes` — deleted
- [ ] `vrg vm nic delete shakedown-vm "mgmt0" --yes` — deleted

### Devices (TPM)

- [ ] `vrg vm device create shakedown-vm --name "Test TPM" --model tis --version 2` — TPM created
- [ ] `vrg vm device list shakedown-vm` — shows TPM
- [ ] `vrg vm device get shakedown-vm "Test TPM"` — shows device type
- [ ] `vrg vm device delete shakedown-vm "Test TPM" --yes` — deleted

### VM Snapshots

- [ ] `vrg vm snapshot create shakedown-vm --name shakedown-vm-snap` — snapshot created
- [ ] `vrg vm snapshot list shakedown-vm` — shows snapshot
- [ ] `vrg vm snapshot get shakedown-vm <snap-id>` — snapshot details
- [ ] `vrg vm snapshot delete shakedown-vm <snap-id> --yes` — deleted

### Templates

> Uses `.claude/reference/shakedown.vrg.yaml` — defines a minimal Linux VM with 1 CPU, 512 MB RAM,
> two drives (OS + Data), a NIC on `shakedown-net`, and a TPM device. Uses `${VM_NAME}` and
> `${NETWORK}` variables for override testing.

- [ ] `vrg vm validate -f .claude/reference/shakedown.vrg.yaml` — validates template (exit 0)
- [ ] `vrg vm create -f .claude/reference/shakedown.vrg.yaml --dry-run` — preview without creating
- [ ] `vrg vm create -f .claude/reference/shakedown.vrg.yaml` — creates VM from template
- [ ] `vrg vm get shakedown-template-vm` — verify VM exists with 1 CPU, 512 MB RAM
- [ ] `vrg vm drive list shakedown-template-vm` — verify 2 drives (OS Disk 10 GB, Data Disk 5 GB)
- [ ] `vrg vm nic list shakedown-template-vm` — verify NIC on shakedown-net
- [ ] `vrg vm device list shakedown-template-vm` — verify TPM device
- [ ] `vrg vm delete shakedown-template-vm --yes` — cleanup template VM

#### Template --set overrides

- [ ] `vrg vm create -f .claude/reference/shakedown.vrg.yaml --set vm.name=shakedown-override-vm --set vm.cpu_cores=2 --set vm.ram="1 GB"` — create with overrides
- [ ] `vrg vm get shakedown-override-vm` — verify name override, 2 CPU, 1 GB RAM
- [ ] `vrg vm delete shakedown-override-vm --yes` — cleanup override VM

---

## 4. Tenant Provisioning

### Create & Lifecycle

- [ ] `vrg tenant create --name shakedown-tenant --password <admin-pass>` — tenant created
- [ ] `vrg tenant list` — shows shakedown-tenant
- [ ] `vrg tenant get shakedown-tenant` — shows name, status, is_isolated
- [ ] `vrg tenant update shakedown-tenant --description "Shakedown test tenant"` — updated

### Resource Allocation

- [ ] `vrg tenant node list shakedown-tenant` — list node allocations (may be empty)
- [ ] `vrg tenant node create shakedown-tenant --cpu-cores 2 --ram-gb 4` — allocate compute
- [ ] `vrg tenant node get shakedown-tenant <alloc-id>` — allocation details (cpu_cores, ram_gb)
- [ ] `vrg tenant node update shakedown-tenant <alloc-id> --cpu-cores 4` — update allocation
- [ ] `vrg tenant node update shakedown-tenant <alloc-id> --enabled` — enable via update flag
- [ ] `vrg tenant node update shakedown-tenant <alloc-id> --disabled` — disable via update flag
- [ ] `vrg tenant storage list shakedown-tenant` — list storage allocations
- [ ] `vrg tenant storage create shakedown-tenant --tier 1 --provisioned-gb 50` — allocate storage
- [ ] `vrg tenant storage get shakedown-tenant <alloc-id>` — allocation details (tier, provisioned_gb)
- [ ] `vrg tenant storage update shakedown-tenant <alloc-id> --provisioned-gb 100` — update size

### Networking

- [ ] `vrg tenant net-block list shakedown-tenant` — list network blocks
- [ ] `vrg tenant net-block create shakedown-tenant --cidr 10.99.99.0/24 --network <network-key>` — create block
- [ ] `vrg tenant net-block delete shakedown-tenant <block-id> --yes` — delete block
- [ ] `vrg tenant ext-ip list shakedown-tenant` — list external IPs
- [ ] `vrg tenant ext-ip create shakedown-tenant --ip <ip> --network <network-key>` — allocate IP
- [ ] `vrg tenant ext-ip delete shakedown-tenant <ip-id> --yes` — delete IP
- [ ] `vrg tenant l2 list shakedown-tenant` — list L2 networks
- [ ] `vrg tenant l2 create shakedown-tenant --network-name <network>` — create L2 pass-through
- [ ] `vrg tenant l2 delete shakedown-tenant <l2-id> --yes` — delete L2

### Tenant Start & Operations

- [ ] `vrg tenant start shakedown-tenant` — tenant starts
- [ ] `vrg tenant stop shakedown-tenant` — tenant stops
- [ ] `vrg tenant restart shakedown-tenant` — tenant restarts
- [ ] `vrg tenant reset shakedown-tenant --yes` — hard reset
- [ ] `vrg tenant isolate shakedown-tenant --enable` — network isolation enabled
- [ ] `vrg tenant isolate shakedown-tenant --disable` — network isolation disabled

### Tenant Snapshots

- [ ] `vrg tenant snapshot create shakedown-tenant --name "shakedown-tenant-snap"` — snapshot created
- [ ] `vrg tenant snapshot list shakedown-tenant` — shows snapshot
- [ ] `vrg tenant snapshot get shakedown-tenant <snap-id>` — snapshot details
- [ ] `vrg tenant snapshot delete shakedown-tenant <snap-id> --yes` — deleted

### Clone

- [ ] `vrg tenant clone shakedown-tenant --name shakedown-tenant-clone` — tenant cloned
- [ ] `vrg tenant get shakedown-tenant-clone` — verify clone exists
- [ ] `vrg tenant stop shakedown-tenant-clone` — stop clone before delete
- [ ] `vrg tenant delete shakedown-tenant-clone --yes` — delete clone

### Tenant Stats & Logs

- [ ] `vrg tenant stats current shakedown-tenant` — shows current resource usage (ram_used_mb)
- [ ] `vrg tenant stats history shakedown-tenant --limit 5` — shows usage history
- [ ] `vrg tenant logs list shakedown-tenant` — shows activity logs
- [ ] `vrg tenant logs list shakedown-tenant --errors-only` — filters to errors only

---

## 5. Snapshot System

### Cloud Snapshots

- [ ] `vrg snapshot create --name shakedown-snap` — cloud snapshot created
- [ ] `vrg snapshot list` — shows shakedown-snap
- [ ] `vrg snapshot get shakedown-snap` — snapshot details (status, created, expires)
- [ ] `vrg snapshot vms shakedown-snap` — lists VMs in snapshot
- [ ] `vrg snapshot tenants shakedown-snap` — lists tenants in snapshot
- [ ] `vrg snapshot delete shakedown-snap --yes` — deleted

### Cloud Snapshot Restore

> Requires a cloud snapshot with at least one VM. Create a snapshot first, then restore.

- [ ] `vrg snapshot create --name shakedown-restore-snap` — create snapshot for restore test
- [ ] `vrg snapshot restore-vm shakedown-restore-snap --vm shakedown-vm --new-name shakedown-restored-vm` — restore VM from snapshot
- [ ] `vrg vm get shakedown-restored-vm` — verify restored VM exists
- [ ] `vrg vm delete shakedown-restored-vm --yes` — cleanup restored VM
- [ ] `vrg snapshot delete shakedown-restore-snap --yes` — cleanup restore snapshot

### Snapshot Profiles

- [ ] `vrg snapshot profile create --name shakedown-profile --description "Test profile"` — created
- [ ] `vrg snapshot profile list` — shows profile
- [ ] `vrg snapshot profile get shakedown-profile` — profile details
- [ ] `vrg snapshot profile update shakedown-profile --description "Updated"` — updated

### Profile Periods

- [ ] `vrg snapshot profile period create shakedown-profile --name "Hourly Test" --frequency hourly --retention 3600` — period created
- [ ] `vrg snapshot profile period list shakedown-profile` — shows period
- [ ] `vrg snapshot profile period get shakedown-profile <period-id>` — period details
- [ ] `vrg snapshot profile period update shakedown-profile <period-id> --retention 7200` — updated
- [ ] `vrg snapshot profile period delete shakedown-profile <period-id> --yes` — deleted
- [ ] `vrg snapshot profile delete shakedown-profile --yes` — profile deleted

---

## 6. NAS Provisioning

### NAS Service

- [ ] `vrg nas service create --name shakedown-nas` — NAS service created
- [ ] `vrg nas service list` — shows shakedown-nas
- [ ] `vrg nas service get shakedown-nas` — service details
- [ ] `vrg nas service update shakedown-nas --description "Shakedown NAS"` — updated
- [ ] `vrg nas service power-on shakedown-nas` — service powered on
- [ ] Wait 10 seconds, then `vrg nas service get shakedown-nas` — verify NAS VM is running (check status field)
- [ ] `vrg nas service cifs-settings shakedown-nas` — shows CIFS settings
- [ ] `vrg nas service nfs-settings shakedown-nas` — shows NFS settings
- [ ] `vrg nas service set-cifs-settings shakedown-nas --workgroup SHAKEDOWN` — CIFS updated
- [ ] `vrg nas service set-nfs-settings shakedown-nas --enable-nfsv4` — NFS updated

### Volumes

- [ ] `vrg nas volume create --service shakedown-nas --name shakedown-vol --size-gb 10` — volume created
- [ ] `vrg nas volume list --service shakedown-nas` — shows volume
- [ ] `vrg nas volume get shakedown-vol` — volume details (size, fs_type)
- [ ] `vrg nas volume update shakedown-vol --description "Test volume"` — updated
- [ ] `vrg nas volume disable shakedown-vol` — disabled
- [ ] `vrg nas volume enable shakedown-vol` — re-enabled

### Volume Snapshots

- [ ] `vrg nas volume snapshot create shakedown-vol --name shakedown-vol-snap` — created
- [ ] `vrg nas volume snapshot list shakedown-vol` — shows snapshot
- [ ] `vrg nas volume snapshot get shakedown-vol <snap-id>` — details
- [ ] `vrg nas volume snapshot delete shakedown-vol <snap-id> --yes` — deleted

### Shares

- [ ] `vrg nas cifs create --name shakedown-cifs --volume shakedown-vol` — CIFS share created
- [ ] `vrg nas cifs list` — shows share (use `--volume` to filter)
- [ ] `vrg nas cifs get shakedown-cifs` — share details
- [ ] `vrg nas cifs update shakedown-cifs --description "Test CIFS"` — updated
- [ ] `vrg nas cifs disable shakedown-cifs` — disabled
- [ ] `vrg nas cifs enable shakedown-cifs` — re-enabled
- [ ] `vrg nas nfs create --name shakedown-nfs --volume shakedown-vol --allow-all` — NFS share created
- [ ] `vrg nas nfs list` — shows share
- [ ] `vrg nas nfs get shakedown-nfs` — share details
- [ ] `vrg nas nfs update shakedown-nfs --description "Test NFS"` — updated
- [ ] `vrg nas nfs disable shakedown-nfs` — disabled
- [ ] `vrg nas nfs enable shakedown-nfs` — re-enabled

### Users

- [ ] `vrg nas user create --service shakedown-nas --name shakedown-user --password TestPass123` — user created
- [ ] `vrg nas user list --service shakedown-nas` — shows user
- [ ] `vrg nas user get shakedown-user` — user details
- [ ] `vrg nas user update shakedown-user --description "Test user"` — updated
- [ ] `vrg nas user disable shakedown-user` — disabled
- [ ] `vrg nas user enable shakedown-user` — re-enabled

### NAS Files

- [ ] `vrg nas files list shakedown-vol` — lists files (may show .snapshots, lost+found)
- [ ] `vrg nas files get shakedown-vol <filename>` — file details

### NAS Sync

> Requires a remote NAS target. Skip if not available.

- [ ] `vrg nas sync list --service shakedown-nas` — list sync jobs (may be empty)
- [ ] `vrg nas sync create --service shakedown-nas ...` — create sync job (if remote target available)

---

## 7. Sites & Syncs

> Site create/delete require a remote VergeOS instance. Test read operations
> and enable/disable on existing sites if available.

- [ ] `vrg site list` — lists registered sites
- [ ] `vrg site get <site>` — site details (URL, status, auth_status)
- [ ] `vrg site update <site> --description "test"` — updated (revert after)
- [ ] `vrg site disable <site>` — disabled
- [ ] `vrg site enable <site>` — re-enabled
- [ ] `vrg site sync outgoing list` — lists outgoing syncs
- [ ] `vrg site sync outgoing get <sync-id>` — sync details
- [ ] `vrg site sync outgoing disable <sync-id>` — disabled
- [ ] `vrg site sync outgoing enable <sync-id>` — re-enabled
- [ ] `vrg site sync outgoing start <sync-id>` — trigger sync now
- [ ] `vrg site sync outgoing stop <sync-id>` — stop running sync
- [ ] `vrg site sync outgoing set-throttle <sync-id> --mbps 100` — set bandwidth throttle
- [ ] `vrg site sync outgoing disable-throttle <sync-id>` — remove bandwidth throttle
- [ ] `vrg site sync outgoing refresh-remote <sync-id>` — refresh remote snapshots

### Sync Schedules

- [ ] `vrg site sync schedule list` — lists sync schedules
- [ ] `vrg site sync schedule list --sync <sync-id>` — lists schedules for specific sync
- [ ] `vrg site sync schedule get <schedule-id>` — schedule details

> Create/delete schedules only if a sync exists:

- [ ] `vrg site sync schedule create --sync-key <sync-key> --profile-period-key <period-key> --retention 3600` — schedule created
- [ ] `vrg site sync schedule delete <schedule-id> --yes` — schedule deleted

### Incoming Syncs

- [ ] `vrg site sync incoming list` — lists incoming syncs
- [ ] `vrg site sync incoming get <sync-id>` — sync details
- [ ] `vrg site sync incoming disable <sync-id>` — disabled
- [ ] `vrg site sync incoming enable <sync-id>` — re-enabled

---

## 8. Recipes

> Recipes are templates built from existing VMs (golden images). Sections and questions
> are auto-created when a recipe is based on a VM. The Marketplace repository provides
> pre-built recipes that can be used without setup.

### Read Operations (Marketplace recipes)

- [ ] `vrg recipe list` — lists available recipes (includes Marketplace)
- [ ] `vrg recipe get <recipe>` — recipe details (pick any Marketplace recipe)
- [ ] `vrg recipe download <recipe>` — download a Marketplace recipe (pick one not yet downloaded)

### Sections & Questions (read-only on existing recipe)

- [ ] `vrg recipe section list <recipe>` — shows auto-created sections
- [ ] `vrg recipe section get <recipe> <section-id>` — section details
- [ ] `vrg recipe question list <recipe>` — shows auto-created questions (drive sizes, etc.)
- [ ] `vrg recipe question get <recipe> <question-id>` — question details

### Instances (read-only)

- [ ] `vrg recipe instance list` — lists deployed recipe instances
- [ ] `vrg recipe instance get <instance-id>` — instance details

### Recipe Logs

- [ ] `vrg recipe log list` — lists recipe operation logs
- [ ] `vrg recipe log get <log-id>` — log entry details

### Recipe Create & Deploy

- [ ] `vrg catalog repo list` — identify a repository to use (note its name or key)
- [ ] `vrg catalog create --name shakedown-catalog --repo <repo> --publishing-scope private` — create local catalog for recipe testing
- [ ] `vrg catalog get shakedown-catalog` — verify catalog created
- [ ] `vrg recipe create --name shakedown-recipe --catalog shakedown-catalog --vm shakedown-vm --version 1.0.0` — recipe from shakedown-vm (tests catalog name resolution)
- [ ] `vrg recipe get shakedown-recipe` — verify recipe details
- [ ] `vrg recipe section list shakedown-recipe` — verify auto-created sections
- [ ] `vrg recipe question list shakedown-recipe` — verify auto-created questions (drive/NIC questions)
- [ ] `vrg recipe deploy shakedown-recipe --name shakedown-deployed` — deploy recipe as new VM
- [ ] `vrg recipe instance list` — shows shakedown-deployed as instance
- [ ] `vrg vm get shakedown-deployed` — verify deployed VM exists
- [ ] `vrg vm stop shakedown-deployed` — stop before delete
- [ ] `vrg vm delete shakedown-deployed --yes` — cleanup deployed VM
- [ ] `vrg recipe delete shakedown-recipe --yes` — cleanup recipe
- [ ] `vrg catalog delete shakedown-catalog --yes` — cleanup catalog

---

## 9. Media Catalog

- [ ] `vrg file list` — lists media catalog files
- [ ] `vrg file get <filename>` — file details (name, type, size, tier)
- [ ] `vrg file types` — lists supported file types
- [ ] `vrg file update <filename> --description "test"` — updated (revert after)

> Upload/download tests require local files. Skip if not practical.

- [ ] `vrg file upload <local-file>` — file uploaded to catalog
- [ ] `vrg file download <filename>` — file downloaded
- [ ] `vrg file delete <filename> --yes` — uploaded file deleted

---

## 10. Identity & Access Management

### Users

- [ ] `vrg user list` — lists existing users
- [ ] `vrg user create --name shakedown-user-admin --password TempPass123!` — user created
- [ ] `vrg user list` — shows shakedown-user-admin
- [ ] `vrg user get shakedown-user-admin` — shows user details (name, type, enabled)
- [ ] `vrg user update shakedown-user-admin --displayname "Shakedown Admin"` — updated
- [ ] `vrg user disable shakedown-user-admin` — user disabled
- [ ] `vrg user enable shakedown-user-admin` — user re-enabled
- [ ] `vrg user list --enabled` — shows only enabled users
- [ ] `vrg user list --disabled` — shows only disabled users

### Groups

- [ ] `vrg group list` — lists existing groups
- [ ] `vrg group create --name shakedown-group --description "Shakedown test group"` — group created
- [ ] `vrg group get shakedown-group` — shows group details
- [ ] `vrg group update shakedown-group --description "Updated test group"` — updated
- [ ] `vrg group member add shakedown-group --user shakedown-user-admin` — user added to group
- [ ] `vrg group member list shakedown-group` — shows shakedown-user-admin as member
- [ ] `vrg group member remove shakedown-group --user shakedown-user-admin` — user removed
- [ ] `vrg group disable shakedown-group` — group disabled
- [ ] `vrg group enable shakedown-group` — group re-enabled

### Permissions

- [ ] `vrg permission list` — lists existing permissions
- [ ] `vrg permission grant --table vms --user shakedown-user-admin --list --read` — list+read on VMs granted
- [ ] `vrg permission list --user shakedown-user-admin` — shows granted permission
- [ ] `vrg permission get <perm-id>` — shows permission details (table, user, access levels)
- [ ] `vrg permission revoke <perm-id> --yes` — permission revoked
- [ ] `vrg permission grant --table vms --group shakedown-group --full-control` — full control to group
- [ ] `vrg permission revoke-all --group shakedown-group --yes` — all group permissions revoked

### API Keys

- [ ] `vrg api-key list` — lists existing API keys
- [ ] `vrg api-key create --user shakedown-user-admin --name shakedown-apikey --expires-in 1d` — key created, secret shown once
- [ ] `vrg api-key list --user shakedown-user-admin` — shows shakedown-apikey
- [ ] `vrg api-key get <key-id>` — shows key details (name, user, expires)
- [ ] `vrg api-key delete <key-id> --yes` — key deleted

### Authentication Sources

> Requires SSO/OAuth provider. Test read operations; create/delete only if test IdP available.

- [ ] `vrg auth-source list` — lists auth sources (may be empty)
- [ ] `vrg auth-source list --driver azure` — filters by driver type

> If test IdP available:

- [ ] `vrg auth-source create --name shakedown-auth --driver openid --client-id test-client --client-secret test-secret` — created
- [ ] `vrg auth-source get shakedown-auth` — shows auth source details
- [ ] `vrg auth-source get shakedown-auth --show-settings` — shows configuration settings
- [ ] `vrg auth-source update shakedown-auth --auto-create-users` — updated
- [ ] `vrg auth-source debug-on shakedown-auth` — debug logging enabled
- [ ] `vrg auth-source debug-off shakedown-auth` — debug logging disabled
- [ ] `vrg auth-source delete shakedown-auth --yes` — deleted

---

## 11. Task Automation

> Tasks define an action on a specific object (VM, tenant, network, etc.) and are
> triggered by events or schedules. The `--owner` is the target object's key, `--table`
> is the object type, and `--action` is the operation to perform.

### Tasks

> Use shakedown-vm as the target object. Get its key first with `vrg vm get shakedown-vm`.

- [ ] `vrg task list` — lists existing tasks
- [ ] `vrg task create --name shakedown-task --owner <shakedown-vm-key> --table vms --action poweron --description "Shakedown power-on task" --disabled` — task created in disabled state
- [ ] `vrg task get shakedown-task` — shows task details (name, action, owner, status)
- [ ] `vrg task update shakedown-task --description "Updated test task"` — updated
- [ ] `vrg task enable shakedown-task` — task enabled
- [ ] `vrg task disable shakedown-task` — task disabled
- [ ] `vrg task list --enabled` — shows only enabled tasks
- [ ] `vrg task list --disabled` — shows only disabled tasks

### Task Schedules

- [ ] `vrg task schedule list` — lists existing schedules (includes system defaults)
- [ ] `vrg task schedule create --name shakedown-schedule --repeat-every hour` — schedule created
- [ ] `vrg task schedule get shakedown-schedule` — shows schedule details
- [ ] `vrg task schedule update shakedown-schedule --repeat-every day` — updated
- [ ] `vrg task schedule show shakedown-schedule` — shows upcoming execution times
- [ ] `vrg task schedule disable shakedown-schedule` — disabled
- [ ] `vrg task schedule enable shakedown-schedule` — re-enabled

### Task Triggers (link task to schedule)

- [ ] `vrg task trigger list shakedown-task` — lists triggers for task (empty)
- [ ] `vrg task trigger create shakedown-task --schedule shakedown-schedule` — schedule trigger linked
- [ ] `vrg task trigger list shakedown-task` — shows trigger
- [ ] `vrg task trigger delete <trigger-id> --yes` — trigger deleted

### Task Events (event-based triggers)

- [ ] `vrg task event list` — lists task events
- [ ] `vrg task event get <event-id>` — event details (read-only on existing events)

### Task Scripts

> Scripts use GCS (a C/JS-like language internal to VergeOS). A test script
> is provided at `tests/shakedown/shakedown-script.gcs`.

- [ ] `vrg task script list` — lists task scripts
- [ ] `vrg task script create --name shakedown-script --script @tests/shakedown/shakedown-script.gcs --description "Shakedown test script"` — script created
- [ ] `vrg task script get shakedown-script` — shows script details (name, code)
- [ ] `vrg task script update shakedown-script --description "Updated shakedown script"` — updated
- [ ] `vrg task script run shakedown-script` — script executed (check logs for output)
- [ ] `vrg task script delete shakedown-script --yes` — script deleted

---

## 12. Security & Certificates

### Certificates

- [ ] `vrg certificate list` — lists existing certificates
- [ ] `vrg certificate create --domain shakedown.local --type self-signed` — self-signed cert created
- [ ] `vrg certificate list --type self-signed` — filters by type
- [ ] `vrg certificate get shakedown.local` — shows cert details (domain, type, expiry)
- [ ] `vrg certificate get shakedown.local --show-keys` — includes PEM content
- [ ] ~~`vrg certificate show`~~ — command does not exist; use `vrg certificate get <id> --show-keys` instead
- [ ] `vrg certificate update shakedown.local --description "Shakedown test cert"` — updated
- [ ] `vrg certificate delete shakedown.local --yes` — deleted

### OIDC Applications

- [ ] `vrg oidc list` — lists OIDC applications (may be empty)
- [ ] `vrg oidc create --name shakedown-oidc --redirect-uri https://localhost/callback` — app created, client_secret shown
- [ ] `vrg oidc get shakedown-oidc` — shows app details (client_id, redirect_uris)
- [ ] `vrg oidc get shakedown-oidc --show-secret` — includes client_secret
- [ ] `vrg oidc get shakedown-oidc --show-well-known` — shows OIDC discovery endpoints
- [ ] `vrg oidc update shakedown-oidc --description "Shakedown OIDC app"` — updated
- [ ] `vrg oidc disable shakedown-oidc` — disabled
- [ ] `vrg oidc enable shakedown-oidc` — re-enabled

### OIDC User/Group Access

- [ ] `vrg oidc user list shakedown-oidc` — lists allowed users (empty)
- [ ] `vrg oidc user grant shakedown-oidc --user shakedown-user-admin` — user granted access
- [ ] `vrg oidc user list shakedown-oidc` — shows shakedown-user-admin
- [ ] `vrg oidc user revoke shakedown-oidc shakedown-user-admin` — access revoked
- [ ] `vrg oidc group list shakedown-oidc` — lists allowed groups (empty)
- [ ] `vrg oidc group grant shakedown-oidc --group shakedown-group` — group granted access
- [ ] `vrg oidc group list shakedown-oidc` — shows shakedown-group
- [ ] `vrg oidc group revoke shakedown-oidc shakedown-group` — access revoked

### OIDC Logs

- [ ] `vrg oidc log list shakedown-oidc` — shows OIDC login logs (may be empty)

---

## 13. Catalogs & Updates

### Catalog Repositories

- [ ] `vrg catalog repo list` — lists catalog repositories
- [ ] `vrg catalog repo get <repo>` — shows repository details

> If a test repository is available:

- [ ] `vrg catalog repo sync <repo>` — triggers sync
- [ ] `vrg catalog repo log list <repo>` — shows sync logs

### Catalogs

- [ ] `vrg catalog list` — lists catalogs
- [ ] `vrg catalog get <catalog>` — shows catalog details (name, repo, scope, enabled)
- [ ] `vrg catalog log list` — shows catalog operation logs

- [ ] `vrg catalog create --name shakedown-catalog-crud --repo <repo> --publishing-scope private` — catalog created
- [ ] `vrg catalog get shakedown-catalog-crud` — shows catalog details
- [ ] `vrg catalog update shakedown-catalog-crud --description "Shakedown catalog"` — updated
- [ ] `vrg catalog disable shakedown-catalog-crud` — disabled
- [ ] `vrg catalog enable shakedown-catalog-crud` — re-enabled
- [ ] `vrg catalog delete shakedown-catalog-crud --yes` — deleted

### System Updates

> Read-only tests — do NOT install updates during shakedown.

- [ ] `vrg update status` — shows current update status/configuration
- [ ] `vrg update settings` — shows update settings
- [ ] `vrg update source list` — lists update sources
- [ ] `vrg update source get <source>` — shows source details
- [ ] `vrg update source status <source>` — shows source connection status
- [ ] `vrg update branch list` — lists available update branches
- [ ] `vrg update branch get <branch>` — shows branch details
- [ ] `vrg update package list` — lists installed packages
- [ ] `vrg update package get <package>` — shows package details
- [ ] `vrg update log list` — shows update history
- [ ] `vrg update check` — checks for available updates (read-only)

---

## 14. Monitoring & Observability

### Alarms

- [ ] `vrg alarm list` — lists active alarms
- [ ] `vrg alarm summary` — shows alarm counts by level (critical, error, warning, message)
- [ ] `vrg alarm list --level warning` — filters by level
- [ ] `vrg alarm list --level error` — filters errors
- [ ] `vrg alarm get <alarm-id>` — shows alarm details (level, message, owner, snoozed)

> If alarms exist:

- [ ] `vrg alarm snooze <alarm-id>` — snoozes alarm (default 24 hours)
- [ ] `vrg alarm snooze <alarm-id> --hours 2` — snoozes for 2 hours
- [ ] `vrg alarm unsnooze <alarm-id>` — unsnoozes alarm
- [ ] `vrg alarm resolve <alarm-id>` — resolves alarm (if resolvable)

### Alarm History

- [ ] `vrg alarm history list` — shows alarm history
- [ ] `vrg alarm history list --level critical` — filters by level
- [ ] `vrg alarm history get <alarm-id>` — shows history for specific alarm

### System Logs

- [ ] `vrg log list` — lists recent log entries
- [ ] `vrg log list --limit 10` — limits results
- [ ] `vrg log list --level error` — filters by level
- [ ] `vrg log list --errors` — shows only error and critical logs
- [ ] `vrg log list --type vm` — filters by object type
- [ ] `vrg log list --since 2026-02-01` — filters by date
- [ ] `vrg log search "shakedown"` — searches log content
- [ ] `vrg log search "shakedown" --level error` — search with level filter

---

## 15. Tags & Resource Organization

### Tag Categories

- [ ] `vrg tag category list` — lists tag categories (may be empty)
- [ ] `vrg tag category create --name shakedown-category --description "Shakedown test category" --taggable-vms --taggable-networks` — created (must enable taggable types for assign to work)
- [ ] `vrg tag category get shakedown-category` — shows category details
- [ ] `vrg tag category update shakedown-category --description "Updated category"` — updated

### Tags

- [ ] `vrg tag list` — lists tags
- [ ] `vrg tag create --name shakedown-tag --category shakedown-category --description "Shakedown test tag"` — tag created
- [ ] `vrg tag get shakedown-tag` — shows tag details (name, category, description)
- [ ] `vrg tag update shakedown-tag --description "Updated tag"` — updated

### Tag Assignment

- [ ] `vrg tag assign shakedown-tag vm shakedown-vm` — tag assigned to VM
- [ ] `vrg tag members shakedown-tag` — lists tagged resources, shows shakedown-vm
- [ ] `vrg tag members shakedown-tag --type vm` — filters by resource type
- [ ] `vrg tag unassign shakedown-tag vm shakedown-vm` — tag removed from VM

### Resource Groups

> Requires PCI/USB devices. Test CRUD if hardware available, otherwise read-only.

- [ ] `vrg resource-group list` — lists resource groups (may be empty)

> If PCI devices available:

- [ ] `vrg resource-group create --name shakedown-rg --type pci --description "Shakedown test"` — created
- [ ] `vrg resource-group get shakedown-rg` — shows group details (name, type, device_class)
- [ ] `vrg resource-group update shakedown-rg --description "Updated"` — updated
- [ ] `vrg resource-group delete shakedown-rg --yes` — deleted

### Tenant Shared Objects

> Requires shakedown-tenant and shakedown-vm to be deployed.

- [ ] `vrg tenant share list shakedown-tenant` — lists shared objects (empty)
- [ ] `vrg tenant share create shakedown-tenant --vm shakedown-vm --name "Shared VM"` — VM shared with tenant
- [ ] `vrg tenant share list shakedown-tenant` — shows shared object
- [ ] `vrg tenant share get shakedown-tenant <share-id>` — shows share details
- [ ] `vrg tenant share refresh shakedown-tenant <share-id>` — refreshes shared data
- [ ] `vrg tenant share delete shakedown-tenant <share-id> --yes` — deleted

---

## 16. Shared Objects

> Shared objects allow sharing VMs between tenants. Requires shakedown-tenant and shakedown-vm.

- [ ] `vrg shared-object list` — lists shared objects (may be empty)
- [ ] `vrg shared-object create --tenant-key <tenant-key> --vm-name shakedown-vm --name "shakedown-shared"` — share VM with tenant
- [ ] `vrg shared-object get shakedown-shared` — shows shared object details
- [ ] `vrg shared-object list --tenant <tenant-key>` — filters by tenant
- [ ] `vrg shared-object list --inbox` — shows only inbox (received) objects
- [ ] `vrg shared-object refresh shakedown-shared` — refresh shared object state
- [ ] `vrg shared-object delete shakedown-shared --yes` — delete shared object

---

## 17. Update Configure Licensing

> Non-airgap systems set licensing credentials via update server configuration.

- [ ] `vrg update configure --user <user> --password <pass>` — set update server credentials (verify no error)

---

## 18. Cross-Cutting Tests

Run these against any representative commands (e.g., `vm list`, `network get`).

### Output Formats

> Note: `-o` is a **global** option placed before the command: `vrg -o json vm list`, not `vrg vm list -o json`

- [ ] `vrg -o table vm list` — formatted table output
- [ ] `vrg -o wide vm list` — wide table with extra columns
- [ ] `vrg -o json vm list` — valid JSON array
- [ ] `vrg -o csv vm list` — proper CSV with headers
- [ ] `vrg -o json vm get shakedown-vm` — valid JSON object
- [ ] `vrg --query name vm get shakedown-vm` — returns plain value "shakedown-vm"
- [ ] `vrg -q vm list` — quiet mode, minimal output

### Error Handling

- [ ] `vrg vm get nonexistent-vm` — exit code 6, "not found" message
- [ ] `vrg network get nonexistent-net` — exit code 6
- [ ] `vrg vm drive get shakedown-vm "No Such Drive"` — exit code 6
- [ ] `vrg vm update shakedown-vm` (no flags) — exit code 2, "no updates specified"

### Global Options

> Use credentials from `.claude/TESTENV.md` for inline credential tests.

- [ ] `vrg --profile <name> vm list` — uses specified profile
- [ ] `vrg --no-color vm list` — output without ANSI colors
- [ ] `vrg -H <host> --username admin --password <password> vm list` — inline credentials work (set `VERGE_VERIFY_SSL=false` for self-signed cert environments)

---

## 19. Cleanup

Delete all test resources in reverse order. Verify each deletion.

### Tag & Resource Group Cleanup

- [ ] Delete tag assignment (if assigned): `vrg tag unassign shakedown-tag vm shakedown-vm`
- [ ] Delete tag: `vrg tag delete shakedown-tag --yes`
- [ ] Delete tag category: `vrg tag category delete shakedown-category --yes`
- [ ] Delete resource group (if created): `vrg resource-group delete shakedown-rg --yes`
- [ ] Delete tenant share (if created): `vrg tenant share delete shakedown-tenant <share-id> --yes`
- [ ] Delete shared object (if created): `vrg shared-object delete shakedown-shared --yes`

### Sync Schedule Cleanup

- [ ] Delete sync schedule (if created): `vrg site sync schedule delete <schedule-id> --yes`

### OIDC & Certificate Cleanup

- [ ] Revoke OIDC user access: `vrg oidc user revoke shakedown-oidc shakedown-user-admin` (if granted)
- [ ] Revoke OIDC group access: `vrg oidc group revoke shakedown-oidc shakedown-group` (if granted)
- [ ] Delete OIDC app: `vrg oidc delete shakedown-oidc --yes`
- [ ] Delete certificate: `vrg certificate delete shakedown.local --yes` (if created)

### Task Cleanup

- [ ] Delete task script (if created): `vrg task script delete shakedown-script --yes`
- [ ] Delete task triggers (if created): `vrg task trigger delete <trigger-id> --yes`
- [ ] Delete task schedule: `vrg task schedule delete shakedown-schedule --yes`
- [ ] Delete task: `vrg task delete shakedown-task --yes`

### IAM Cleanup

- [ ] Delete API key: `vrg api-key delete <key-id> --yes` (if created)
- [ ] Revoke all permissions: `vrg permission revoke-all --user shakedown-user-admin --yes`
- [ ] Revoke all permissions: `vrg permission revoke-all --group shakedown-group --yes`
- [ ] Delete auth source: `vrg auth-source delete shakedown-auth --yes` (if created)
- [ ] Delete group: `vrg group delete shakedown-group --yes`
- [ ] Delete user: `vrg user delete shakedown-user-admin --yes`

### NAS Cleanup

- [ ] Delete NAS user: `vrg nas user delete shakedown-user --yes`
- [ ] Delete NFS share: `vrg nas nfs delete shakedown-nfs --yes`
- [ ] Delete CIFS share: `vrg nas cifs delete shakedown-cifs --yes`
- [ ] Delete NAS volume: `vrg nas volume delete shakedown-vol --yes`
- [ ] Power off NAS: `vrg nas service power-off shakedown-nas`
- [ ] Delete NAS service: `vrg nas service delete shakedown-nas --yes`

### Tenant Cleanup

- [ ] Delete tenant net-blocks: `vrg tenant net-block delete shakedown-tenant <block-id> --yes`
- [ ] Delete tenant ext-ips: `vrg tenant ext-ip delete shakedown-tenant <ip-id> --yes`
- [ ] Delete tenant L2s: `vrg tenant l2 delete shakedown-tenant <l2-id> --yes`
- [ ] Delete tenant storage: `vrg tenant storage delete shakedown-tenant <alloc-id> --yes`
- [ ] Delete tenant nodes: `vrg tenant node delete shakedown-tenant <alloc-id> --yes`
- [ ] Stop tenant: `vrg tenant stop shakedown-tenant`
- [ ] Delete tenant: `vrg tenant delete shakedown-tenant --yes --force`

### VM Cleanup

- [ ] Delete remaining drives: `vrg vm drive delete shakedown-vm "OS Disk" --yes`
- [ ] Stop VM: `vrg vm stop shakedown-vm --force`
- [ ] Delete VM: `vrg vm delete shakedown-vm --yes`

### Network Cleanup

- [ ] Stop network: `vrg network stop shakedown-net`
- [ ] Delete network: `vrg network delete shakedown-net --yes`

### Verification

- [ ] `vrg vm list` — shakedown-vm not present
- [ ] `vrg network list` — shakedown-net not present
- [ ] `vrg tenant list` — shakedown-tenant not present
- [ ] `vrg nas service list` — shakedown-nas not present
- [ ] `vrg snapshot profile list` — shakedown-profile not present
- [ ] `vrg user list` — shakedown-user-admin not present
- [ ] `vrg group list` — shakedown-group not present
- [ ] `vrg tag list` — shakedown-tag not present
- [ ] `vrg tag category list` — shakedown-category not present
- [ ] `vrg oidc list` — shakedown-oidc not present
- [ ] `vrg task list` — shakedown-task not present
- [ ] `vrg task schedule list` — shakedown-schedule not present

---

## 20. Results

### Summary

| Section | Tests | Passed | Failed | Notes |
|---------|-------|--------|--------|-------|
| 1. Configure & System | | | | |
| 2. Network Provisioning | | | | |
| 3. VM Provisioning | | | | |
| 4. Tenant Provisioning | | | | |
| 5. Snapshot System | | | | |
| 6. NAS Provisioning | | | | |
| 7. Sites & Syncs | | | | |
| 8. Recipes | | | | |
| 9. Media Catalog | | | | |
| 10. Identity & Access Mgmt | | | | |
| 11. Task Automation | | | | |
| 12. Security & Certificates | | | | |
| 13. Catalogs & Updates | | | | |
| 14. Monitoring & Observability | | | | |
| 15. Tags & Organization | | | | |
| 16. Shared Objects | | | | |
| 17. Update Configure Licensing | | | | |
| 18. Cross-Cutting | | | | |
| 19. Cleanup | | | | |
| **Total** | | | | |

### Issues Found

| # | Severity | Command | Description |
|---|----------|---------|-------------|
| | | | |

### Environment

- **Date:** YYYY-MM-DD
- **VergeOS Version:**
- **CLI Version:** `vrg --version`
- **Tester:**
