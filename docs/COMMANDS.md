# Command Reference

Complete command reference for the Verge CLI (`vrg`).

## Command Pattern

```
vrg [global-options] <domain> [sub-domain] <action> [arguments] [options]
```

## Global Options

| Option | Short | Description |
|--------|-------|-------------|
| `--profile` | `-p` | Configuration profile to use |
| `--host` | `-H` | VergeOS host URL (override) |
| `--token` | | Bearer token for authentication |
| `--api-key` | | API key for authentication |
| `--username` | `-u` | Username for basic auth |
| `--password` | | Password for basic auth |
| `--output` | `-o` | Output format: `table`, `wide`, `json`, `csv` |
| `--query` | | Extract field using dot notation |
| `--verbose` | `-v` | Increase verbosity (`-v`, `-vv`, `-vvv`) |
| `--quiet` | `-q` | Suppress non-essential output |
| `--no-color` | | Disable colored output |
| `--version` | `-V` | Show version and exit |
| `--all-profiles` | | Run list commands across all configured profiles |

## Common Patterns

Most resource commands follow a consistent CRUD pattern:

```bash
vrg <domain> list                     # List all resources
vrg <domain> get <ID|NAME>            # Get a single resource by key or name
vrg <domain> create --name foo ...    # Create a new resource
vrg <domain> update <ID|NAME> ...     # Update a resource
vrg <domain> delete <ID|NAME> --yes   # Delete (requires --yes)
```

Destructive operations (`delete`, `reset`) require `--yes` to skip the confirmation prompt.

---

## Compute

### `vrg vm`

VM lifecycle management. Source: `commands/vm.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List all VMs |
| `get` | Get VM by ID or name |
| `create` | Create VM (flags or `-f template.vrg.yaml`) |
| `update` | Update VM attributes |
| `delete` | Delete a VM |
| `start` | Power on a VM |
| `stop` | Power off a VM |
| `restart` | Restart a VM |
| `reset` | Hard reset a VM |
| `validate` | Validate a `.vrg.yaml` template |
| `clone` | Clone a VM |
| `migrate` | Live-migrate a running VM to another node |
| `hibernate` | Hibernate a running VM |
| `console` | Show VM console connection info |
| `tag` | Assign a tag to a VM |
| `untag` | Remove a tag from a VM |
| `favorite` | Mark a VM as a favorite |
| `unfavorite` | Remove a VM from favorites |

### `vrg vm drive`

VM disk drive management. Source: `commands/vm_drive.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List drives on a VM |
| `get` | Get drive details |
| `create` | Add a drive to a VM |
| `update` | Update drive settings |
| `delete` | Remove a drive |
| `import` | Import a media file to a drive |

### `vrg vm nic`

VM network interface management. Source: `commands/vm_nic.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List NICs on a VM |
| `get` | Get NIC details |
| `create` | Add a NIC to a VM |
| `update` | Update NIC settings |
| `delete` | Remove a NIC |

### `vrg vm device`

VM device management (TPM, GPU passthrough). Source: `commands/vm_device.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List devices on a VM |
| `get` | Get device details |
| `create` | Add a device to a VM |
| `delete` | Remove a device |

### `vrg vm snapshot`

Per-VM snapshot management. Source: `commands/vm_snapshot.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List snapshots for a VM |
| `get` | Get snapshot details |
| `create` | Create a VM snapshot |
| `delete` | Delete a snapshot |
| `restore` | Restore VM from snapshot |

### `vrg vm export`

VM export management. Source: `commands/vm_export.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List VM exports |
| `get` | Get a VM export by name or key |
| `create` | Create a new VM export configuration |
| `start` | Start a VM export job |
| `stop` | Stop a running VM export job |
| `delete` | Delete a VM export configuration |
| `cleanup` | Clean up exported files for a VM export |

### `vrg vm export stats`

VM export statistics. Source: `commands/vm_export_stats.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List VM export statistics |
| `get` | Get a VM export stat entry by key |

### `vrg vm import`

VM import management. Source: `commands/vm_import.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List VM imports |
| `get` | Get a VM import by name or key |
| `create` | Create a new VM import job |
| `start` | Start a VM import job |
| `cancel` | Cancel a running VM import job |
| `delete` | Delete a VM import job |

### `vrg vm import log`

VM import logs. Source: `commands/vm_import_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List VM import logs |
| `get` | Get a VM import log entry by key |

---

## Network

### `vrg network`

Network lifecycle and operations. Source: `commands/network.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List all networks |
| `get` | Get network details |
| `create` | Create a network |
| `update` | Update network settings |
| `delete` | Delete a network |
| `start` | Start a network |
| `stop` | Stop a network |
| `restart` | Restart a network |
| `status` | Show network status |
| `apply-rules` | Apply pending firewall rule changes |
| `apply-dns` | Apply pending DNS changes |

### `vrg network rule`

Firewall rule management. Source: `commands/network_rule.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List rules on a network (includes packets, bytes, trace columns) |
| `get` | Get rule details |
| `create` | Create a firewall rule |
| `update` | Update a rule |
| `delete` | Delete a rule |
| `enable` | Enable a rule |
| `disable` | Disable a rule |

### `vrg network dns view`

DNS view management. Source: `commands/network_dns.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List DNS views |
| `get` | Get view details |
| `create` | Create a DNS view |
| `update` | Update a view |
| `delete` | Delete a view |

### `vrg network dns zone`

DNS zone management. Source: `commands/network_dns.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List zones in a view |
| `get` | Get zone details |
| `create` | Create a DNS zone |
| `update` | Update a zone |
| `delete` | Delete a zone |

### `vrg network dns record`

DNS record management. Source: `commands/network_dns.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List records in a zone |
| `get` | Get record details |
| `create` | Create a DNS record |
| `update` | Update a record |
| `delete` | Delete a record |

### `vrg network host`

DHCP host override management. Source: `commands/network_host.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List host overrides |
| `get` | Get host override details |
| `create` | Create a host override |
| `update` | Update a host override |
| `delete` | Delete a host override |

### `vrg network alias`

IP alias management. Source: `commands/network_alias.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List IP aliases |
| `get` | Get alias details |
| `create` | Create an IP alias |
| `update` | Update an alias |
| `delete` | Delete an alias |

### `vrg network diag`

Network diagnostics and monitoring. Source: `commands/network_diag.py`

| Subcommand | Description |
|------------|-------------|
| `leases` | Show DHCP leases |
| `addresses` | Show address table |
| `stats` | Show traffic statistics |
| `quality` | Show current quality metrics (latency, packet loss) |
| `history` | Show monitoring history (`--long` for aggregated data) |

### `vrg network diag dashboard`

Network dashboard views. Source: `commands/network_dashboard.py`

| Subcommand | Description |
|------------|-------------|
| `overview` | Show network dashboard summary |
| `ipsec-status` | Show IPSec active connections for a network |
| `wireguard-status` | Show WireGuard peer status for a network |

### `vrg network query`

Run diagnostic queries on a network's virtual router. Source: `commands/network_query.py`

All commands take a network name/key as the first argument. Results are returned asynchronously via the query API.

| Subcommand | Description |
|------------|-------------|
| `ping` | Ping a host from the network router |
| `dns` | DNS resolution from the network |
| `traceroute` | Traceroute from the network |
| `tcpdump` | Packet capture on the network |
| `arp` | Show ARP table |
| `arp-scan` | Scan for hosts via ARP |
| `firewall` | Show nftables rules |
| `trace` | Trace packet flow through firewall |
| `nmap` | Port scan a target |
| `tcp-connect` | Test TCP connectivity to host:port |
| `run` | Run an arbitrary query type |

---

## Tenants

### `vrg tenant`

Tenant lifecycle management. Source: `commands/tenant.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List all tenants |
| `get` | Get tenant details |
| `create` | Create a tenant |
| `update` | Update tenant settings |
| `delete` | Delete a tenant |
| `start` | Power on a tenant |
| `stop` | Power off a tenant |
| `restart` | Restart a tenant |
| `reset` | Hard reset a tenant |
| `clone` | Clone a tenant |
| `isolate` | Toggle tenant isolation |

### `vrg tenant node`

Tenant node allocation. Source: `commands/tenant_node.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant nodes |
| `get` | Get node details |
| `create` | Allocate a node |
| `update` | Update node allocation |
| `delete` | Remove a node |

### `vrg tenant storage`

Tenant storage allocation. Source: `commands/tenant_storage.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant storage |
| `get` | Get storage details |
| `create` | Allocate storage |
| `update` | Update storage allocation |
| `delete` | Remove storage |

### `vrg tenant net-block`

Tenant network block management. Source: `commands/tenant_net.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List network blocks |
| `get` | Get block details |
| `create` | Assign a network block |
| `delete` | Remove a network block |

### `vrg tenant ext-ip`

Tenant external IP management. Source: `commands/tenant_net.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List external IPs |
| `get` | Get external IP details |
| `create` | Assign an external IP |
| `delete` | Remove an external IP |

### `vrg tenant l2`

Tenant Layer 2 network management. Source: `commands/tenant_net.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List L2 networks |
| `get` | Get L2 network details |
| `create` | Assign an L2 network |
| `delete` | Remove an L2 network |

### `vrg tenant snapshot`

Tenant snapshot management. Source: `commands/tenant_snapshot.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant snapshots |
| `get` | Get snapshot details |
| `create` | Create a tenant snapshot |
| `delete` | Delete a snapshot |
| `restore` | Restore tenant from snapshot |

### `vrg tenant stats`

Tenant resource statistics. Source: `commands/tenant_stats.py`

| Subcommand | Description |
|------------|-------------|
| `current` | Show current resource usage |
| `history` | Show historical usage |

### `vrg tenant logs`

Tenant log viewing. Source: `commands/tenant.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant log entries |

### `vrg tenant share`

Tenant object sharing. Source: `commands/tenant_share.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List shared objects |
| `get` | Get shared object details |
| `import` | Import a shared object |
| `accept` | Accept a shared object |
| `reject` | Reject a shared object |
| `delete` | Remove a shared object |

### `vrg tenant-recipe`

Tenant recipe management. Source: `commands/tenant_recipe.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant recipes |
| `get` | Get a tenant recipe by name or key |
| `update` | Update a tenant recipe |
| `delete` | Delete a tenant recipe |
| `download` | Download a tenant recipe from the catalog repository |
| `deploy` | Deploy a tenant recipe to create a new tenant |

### `vrg tenant-recipe instance`

Tenant recipe instance management. Source: `commands/tenant_recipe_instance.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant recipe instances |
| `get` | Get a tenant recipe instance by name or key |
| `delete` | Delete a tenant recipe instance |

### `vrg tenant-recipe log`

Tenant recipe logs. Source: `commands/tenant_recipe_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tenant recipe logs |
| `get` | Get a tenant recipe log entry by key |

---

## Storage & NAS

### `vrg storage`

Storage tier information. Source: `commands/storage.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List storage tiers |
| `get` | Get tier details |
| `summary` | Show aggregate storage across all tiers |

### `vrg nas service`

NAS service management. Source: `commands/nas_service.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List NAS services |
| `get` | Get service details |
| `create` | Create a NAS service |
| `update` | Update service settings |
| `delete` | Delete a service |
| `power-on` | Power on NAS VM |
| `power-off` | Power off NAS VM |
| `restart` | Restart NAS VM |

### `vrg nas volume`

NAS volume management. Source: `commands/nas_volume.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List volumes |
| `get` | Get volume details |
| `create` | Create a volume |
| `update` | Update volume settings |
| `delete` | Delete a volume |
| `enable` | Enable a volume |
| `disable` | Disable a volume |
| `reset` | Reset a volume |

### `vrg nas volume snapshot`

NAS volume snapshot management. Source: `commands/nas_volume_snapshot.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List volume snapshots |
| `get` | Get snapshot details |
| `create` | Create a snapshot |
| `delete` | Delete a snapshot |

### `vrg nas cifs`

CIFS/SMB share management. Source: `commands/nas_cifs.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List CIFS shares |
| `get` | Get share details |
| `create` | Create a share |
| `update` | Update share settings |
| `delete` | Delete a share |
| `enable` | Enable a share |
| `disable` | Disable a share |

### `vrg nas nfs`

NFS export management. Source: `commands/nas_nfs.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List NFS exports |
| `get` | Get export details |
| `create` | Create an export |
| `update` | Update export settings |
| `delete` | Delete an export |
| `enable` | Enable an export |
| `disable` | Disable an export |

### `vrg nas user`

NAS local user management. Source: `commands/nas_user.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List NAS users |
| `get` | Get user details |
| `create` | Create a user |
| `update` | Update user settings |
| `delete` | Delete a user |
| `enable` | Enable a user |
| `disable` | Disable a user |

### `vrg nas sync`

NAS volume sync job management. Source: `commands/nas_sync.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List sync jobs |
| `get` | Get sync job details |
| `create` | Create a sync job |
| `update` | Update sync settings |
| `delete` | Delete a sync job |
| `enable` | Enable a sync job |
| `disable` | Disable a sync job |
| `start` | Start a sync run |
| `stop` | Stop a running sync |

### `vrg nas files`

NAS file browsing. Source: `commands/nas_files.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List files in a volume |
| `get` | Get file details |

### `vrg file`

Media catalog (ISO, disk, OVA/OVF) management. Source: `commands/file.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List media files |
| `get` | Get file details |
| `upload` | Upload a file |
| `download` | Download a file |
| `update` | Update file metadata |
| `delete` | Delete a file |
| `types` | List available file types |

---

## Infrastructure

### `vrg cluster`

Cluster management and health. Source: `commands/cluster.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List clusters |
| `get` | Get cluster details |
| `create` | Create a cluster |
| `update` | Update cluster settings |
| `delete` | Delete a cluster |
| `vsan-status` | Show vSAN health status (`--name` to filter by cluster) |

### `vrg node`

Node management. Source: `commands/node.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List nodes |
| `get` | Get node details |
| `maintenance` | Enable or disable maintenance mode (`--enable`/`--disable`) |
| `restart` | Restart a node |
| `pci-list` | List PCI devices on a node |
| `gpu-list` | List GPU devices on a node |
| `stats` | Show node statistics (CPU, RAM, temperature) |

### `vrg node nic`

Node NIC monitoring and statistics. Source: `commands/node_nic.py`

| Subcommand | Description |
|------------|-------------|
| `stats` | Show NIC traffic statistics (rx/tx bytes, packets, errors) |
| `status` | Show NIC link status (speed, duplex, carrier) |
| `fabric` | Show NIC fabric membership and role |

All commands take a node name/key. Use `--nic <key>` to filter to a single NIC.

### `vrg node lldp`

LLDP neighbor discovery. Source: `commands/node_lldp.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List LLDP neighbors on a node (`--nic` to filter by NIC) |

### `vrg node query`

Run diagnostic queries on a physical node. Source: `commands/node_query.py`

All commands take a node name/key as the first argument. Results are returned asynchronously via the query API.

**Network diagnostics:**

| Subcommand | Description |
|------------|-------------|
| `ping` | Ping a host from the node |
| `dns` | DNS resolution from the node |
| `traceroute` | Traceroute from the node |
| `tcpdump` | Packet capture on the node |
| `arp` | Show ARP table |
| `arp-scan` | Scan for hosts via ARP |

**Storage & hardware:**

| Subcommand | Description |
|------------|-------------|
| `smartctl` | SMART health data for a drive |
| `smartctl-test` | Run a SMART self-test |
| `lsblk` | List block devices |
| `dmidecode` | Hardware/BIOS information |

**IPMI:**

| Subcommand | Description |
|------------|-------------|
| `ipmi-sensor` | IPMI sensor readings |
| `ipmi-sel` | IPMI system event log |
| `ipmi-fru` | IPMI FRU (field-replaceable unit) data |
| `ipmi-lan` | IPMI LAN configuration |
| `ipmi-chassis` | IPMI chassis status |

**Generic:**

| Subcommand | Description |
|------------|-------------|
| `run` | Run an arbitrary query type |

### `vrg gpu`

GPU configuration management. Source: `commands/gpu.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List GPU configurations |
| `get` | Get GPU configuration details |
| `update` | Change GPU mode and optionally assign a vGPU profile |
| `stats` | Show GPU utilization statistics |
| `instances` | List VMs using a GPU |

### `vrg gpu profile`

NVIDIA vGPU profile catalog. Source: `commands/gpu.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List vGPU profiles |
| `get` | Get vGPU profile details |

### `vrg gpu device`

Physical GPU device inventory. Source: `commands/gpu.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List physical GPU devices |
| `get` | Get physical GPU device details |

### `vrg snapshot`

Cloud-level snapshot management. Source: `commands/snapshot.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List cloud snapshots |
| `get` | Get snapshot details |
| `create` | Create a cloud snapshot |
| `delete` | Delete a snapshot |
| `vms` | List VMs in a snapshot |
| `tenants` | List tenants in a snapshot |

### `vrg snapshot profile`

Snapshot profile management. Source: `commands/snapshot_profile.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List profiles |
| `get` | Get profile details |
| `create` | Create a profile |
| `update` | Update a profile |
| `delete` | Delete a profile |

### `vrg snapshot profile period`

Snapshot profile period management. Source: `commands/snapshot_profile_period.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List periods in a profile |
| `get` | Get period details |
| `create` | Create a period |
| `update` | Update a period |
| `delete` | Delete a period |

### `vrg site`

Remote site management. Source: `commands/site.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List sites |
| `get` | Get site details |
| `create` | Create a site |
| `update` | Update site settings |
| `delete` | Delete a site |
| `enable` | Enable a site |
| `disable` | Disable a site |
| `reauth` | Re-authenticate with a site |
| `refresh` | Refresh site status |

### `vrg site sync outgoing`

Outgoing site sync management. Source: `commands/site_sync_outgoing.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List outgoing syncs |
| `get` | Get sync details |
| `enable` | Enable an outgoing sync |
| `disable` | Disable an outgoing sync |

### `vrg site sync incoming`

Incoming site sync management. Source: `commands/site_sync_incoming.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List incoming syncs |
| `get` | Get sync details |
| `enable` | Enable an incoming sync |
| `disable` | Disable an incoming sync |

---

## Identity & Access

### `vrg user`

User management. Source: `commands/user.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List users |
| `get` | Get user details |
| `create` | Create a user |
| `update` | Update user settings |
| `delete` | Delete a user |
| `enable` | Enable a user |
| `disable` | Disable a user |

### `vrg group`

Group management. Source: `commands/group.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List groups |
| `get` | Get group details |
| `create` | Create a group |
| `update` | Update group settings |
| `delete` | Delete a group |
| `enable` | Enable a group |
| `disable` | Disable a group |

#### `vrg group member`

| Subcommand | Description |
|------------|-------------|
| `list` | List group members |
| `add` | Add a member to a group |
| `remove` | Remove a member from a group |

### `vrg permission`

Permission management. Source: `commands/permission.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List permissions |
| `get` | Get permission details |
| `grant` | Grant a permission |
| `revoke` | Revoke a permission |
| `revoke-all` | Revoke all permissions for an identity |

### `vrg api-key`

API key management. Source: `commands/api_key.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List API keys |
| `get` | Get key details |
| `create` | Create an API key |
| `delete` | Delete an API key |

### `vrg auth-source`

Authentication source management. Source: `commands/auth_source.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List auth sources |
| `get` | Get source details |
| `create` | Create an auth source |
| `update` | Update source settings |
| `delete` | Delete an auth source |
| `debug-on` | Enable debug logging |
| `debug-off` | Disable debug logging |

---

## Automation

### `vrg task`

Task management. Source: `commands/task.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tasks |
| `get` | Get task details |
| `create` | Create a task |
| `update` | Update task settings |
| `delete` | Delete a task |
| `enable` | Enable a task |
| `disable` | Disable a task |
| `run` | Execute a task immediately |
| `cancel` | Cancel a running task |

### `vrg task schedule`

Task schedule management. Source: `commands/task_schedule.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List schedules |
| `get` | Get schedule details |
| `create` | Create a schedule |
| `update` | Update schedule settings |
| `delete` | Delete a schedule |
| `enable` | Enable a schedule |
| `disable` | Disable a schedule |
| `show` | Show schedule summary |

### `vrg task trigger`

Task trigger management. Source: `commands/task_trigger.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List triggers |
| `create` | Create a trigger |
| `delete` | Delete a trigger |
| `run` | Fire a trigger |

### `vrg task event`

Task event management. Source: `commands/task_event.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List events |
| `get` | Get event details |
| `create` | Create an event binding |
| `update` | Update an event binding |
| `delete` | Delete an event binding |
| `trigger` | Manually trigger an event |

### `vrg task script`

Task script management. Source: `commands/task_script.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List scripts |
| `get` | Get script details |
| `create` | Create a script |
| `update` | Update a script |
| `delete` | Delete a script |
| `run` | Execute a script |

### `vrg recipe`

VM recipe management. Source: `commands/recipe.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List recipes |
| `get` | Get recipe details |
| `create` | Create a recipe |
| `update` | Update a recipe |
| `delete` | Delete a recipe |
| `deploy` | Deploy a recipe |

### `vrg recipe instance`

Recipe instance management. Source: `commands/recipe_instance.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List deployed instances |
| `get` | Get instance details |
| `delete` | Delete an instance |

### `vrg recipe section`

Recipe section management. Source: `commands/recipe_section.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List sections |
| `get` | Get section details |
| `create` | Create a section |
| `update` | Update a section |
| `delete` | Delete a section |

### `vrg recipe question`

Recipe question management. Source: `commands/recipe_question.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List questions |
| `get` | Get question details |
| `create` | Create a question |
| `update` | Update a question |
| `delete` | Delete a question |

### `vrg recipe log`

Recipe deployment logs. Source: `commands/recipe_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List log entries |
| `get` | Get log entry details |

### `vrg tag`

Tag management. Source: `commands/tag.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List tags |
| `get` | Get tag details |
| `create` | Create a tag |
| `update` | Update a tag |
| `delete` | Delete a tag |
| `assign` | Assign a tag to a resource |
| `unassign` | Remove a tag from a resource |

### `vrg tag category`

Tag category management. Source: `commands/tag_category.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List categories |
| `get` | Get category details |
| `create` | Create a category |
| `update` | Update a category |
| `delete` | Delete a category |

### `vrg resource-group`

Resource group management. Source: `commands/resource_group.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List resource groups |
| `get` | Get group details |
| `create` | Create a resource group |
| `update` | Update group settings |
| `delete` | Delete a resource group |
| `enable` | Enable a group |
| `disable` | Disable a group |

---

## Security

### `vrg certificate`

TLS certificate management. Source: `commands/certificate.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List certificates |
| `get` | Get certificate details |
| `create` | Create a self-signed certificate |
| `import` | Import a certificate + key |
| `update` | Update certificate metadata |
| `delete` | Delete a certificate |
| `renew` | Renew a certificate |

### `vrg oidc`

OIDC provider application management. Source: `commands/oidc.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List OIDC applications |
| `get` | Get application details |
| `create` | Create an application |
| `update` | Update application settings |
| `delete` | Delete an application |
| `enable` | Enable an application |
| `disable` | Disable an application |

### `vrg oidc user`

OIDC application user ACL. Source: `commands/oidc_user.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List allowed users |
| `add` | Grant user access |
| `remove` | Revoke user access |

### `vrg oidc group`

OIDC application group ACL. Source: `commands/oidc_group.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List allowed groups |
| `add` | Grant group access |
| `remove` | Revoke group access |

### `vrg oidc log`

OIDC application audit logs. Source: `commands/oidc_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List log entries |
| `get` | Get log entry details |

---

## Catalog & Updates

### `vrg catalog`

Catalog management. Source: `commands/catalog.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List catalogs |
| `get` | Get catalog details |
| `create` | Create a catalog |
| `update` | Update catalog settings |
| `delete` | Delete a catalog |
| `enable` | Enable a catalog |
| `disable` | Disable a catalog |

### `vrg catalog repo`

Catalog repository management. Source: `commands/catalog_repo.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List repositories |
| `get` | Get repository details |
| `create` | Create a repository |
| `update` | Update repository settings |
| `delete` | Delete a repository |
| `refresh` | Refresh repository |
| `status` | Show repository status |

### `vrg catalog repo log`

Catalog repository logs. Source: `commands/catalog_repo_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List log entries |
| `get` | Get log entry details |

### `vrg catalog log`

Catalog logs. Source: `commands/catalog_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List log entries |
| `get` | Get log entry details |

### `vrg update`

System update management. Source: `commands/update.py`

| Subcommand | Description |
|------------|-------------|
| `settings` | View or modify update settings |

### `vrg update source`

Update source management. Source: `commands/update_source.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List update sources |
| `get` | Get source details |
| `create` | Create an update source |
| `update` | Update source settings |
| `delete` | Delete a source |
| `enable` | Enable a source |
| `disable` | Disable a source |
| `refresh` | Refresh a source |
| `status` | Show source status |

### `vrg update branch`

Update branch information. Source: `commands/update_branch.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List branches |
| `get` | Get branch details |

### `vrg update package`

Installed package information. Source: `commands/update_package.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List installed packages |
| `get` | Get package details |

### `vrg update available`

Available update packages. Source: `commands/update_available.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List available packages |
| `get` | Get package details |

### `vrg update log`

Update logs. Source: `commands/update_log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List update log entries |
| `get` | Get log entry details |

---

## Billing & Integrations

### `vrg billing`

Billing and usage reports. Source: `commands/billing.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List billing records |
| `get` | Get a billing record by key |
| `generate` | Generate a new billing record |
| `latest` | Get the most recent billing record |
| `summary` | Show billing usage summary |

### `vrg webhook`

Webhook integration management. Source: `commands/webhook.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List webhooks |
| `get` | Get webhook details |
| `create` | Create a new webhook |
| `update` | Update an existing webhook |
| `delete` | Delete a webhook |
| `send` | Send a test message to a webhook |
| `history` | Show webhook delivery history |

---

## Monitoring

### `vrg alarm`

Active alarm management. Source: `commands/alarm.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List active alarms |
| `get` | Get alarm details |
| `snooze` | Snooze an alarm |
| `unsnooze` | Unsnooze an alarm |
| `resolve` | Resolve an alarm |
| `summary` | Show alarm summary |

### `vrg alarm history`

Historical alarm records. Source: `commands/alarm_history.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List historical alarms |
| `get` | Get historical alarm details |

### `vrg log`

System log viewing. Source: `commands/log.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List system log entries |
| `get` | Get log entry details |

---

## System

### `vrg system`

System information and management. Source: `commands/system.py`

| Subcommand | Description |
|------------|-------------|
| `info` | Show system info and statistics |
| `version` | Show VergeOS version |
| `inventory` | Full system inventory (`--vms`, `--nodes` to filter) |

### `vrg system settings`

System settings management. Source: `commands/system.py`

| Subcommand | Description |
|------------|-------------|
| `list` | Show system settings (`--modified` for changed only) |
| `get` | Get a specific setting value and default |
| `set` | Change a system setting |
| `reset` | Reset a setting to its default |

### `vrg system license`

License management. Source: `commands/system.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List licenses with validity status |
| `get` | Get license details (validity, features, auto-renewal) |
| `add` | Add a license key |
| `generate-payload` | Generate air-gap license request payload |

### `vrg system diag`

System diagnostic bundle management. Source: `commands/system_diag.py`

| Subcommand | Description |
|------------|-------------|
| `list` | List diagnostic bundles |
| `create` | Create a new diagnostic bundle |
| `get` | Get bundle details |
| `send` | Send a bundle to support |
| `delete` | Delete a diagnostic bundle |

### `vrg doctor`

System health checks against best practices. Source: `commands/doctor.py`

Runs 15 automated checks covering connectivity, clusters, nodes, storage, alarms, updates, version consistency, NIC fabric, networks, certificates, licenses, drive SMART health, DIMM health, vSAN journal, and driver reload state.

| Option | Description |
|--------|-------------|
| `--check <names>` | Comma-separated check names to run (e.g. `--check connectivity,alarms`) |
| `--list-checks` | Print all available check names and exit |

**Available checks:** `connectivity`, `clusters`, `nodes`, `storage`, `alarms`, `updates`, `versions`, `fabric`, `networks`, `certificates`, `licenses`, `drive_smart`, `dimm_health`, `vsan_journal`, `driver_reload`

**Exit codes:** 0 if all checks pass/warn/skip, 1 if any check fails.

```bash
vrg doctor                                    # Run all checks
vrg doctor --check connectivity,alarms        # Run specific checks
vrg doctor --list-checks                      # List check names
vrg -o json doctor                            # JSON output with details
```

### `vrg configure`

CLI configuration management. Source: `commands/configure.py`

| Subcommand | Description |
|------------|-------------|
| `setup` | Interactive configuration wizard |
| `show` | Show current profile settings |
| `list` | List all profiles |

### `vrg completion`

Shell completion scripts. Source: `commands/completion.py`

| Subcommand | Description |
|------------|-------------|
| `show` | Print completion script for a shell |
