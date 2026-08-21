# Verge CLI Cookbook

Practical recipes for common vrg tasks. Each recipe includes a goal, steps, verification, and optional cleanup.

---

## Recipe 1: Getting Started

**Goal:** Install vrg and connect to your VergeOS instance.

### Steps

1. Install the CLI:

```bash
# Using uv (recommended)
uv tool install vrg

# Or using pip
pip install vrg
```

2. Run interactive setup to create a configuration profile:

```bash
vrg configure setup
```

This prompts for your VergeOS host URL, authentication method (token, API key, or username/password), and default output format. Config is saved to `~/.vrg/config.toml`.

3. Alternatively, use environment variables instead of a config file:

```bash
export VERGE_HOST=https://verge.example.com
export VERGE_TOKEN=your-api-token
```

### Verify

```bash
vrg system info
```

You should see your VergeOS cluster name, version, and node count.

### Check Your Config

```bash
vrg configure show
```

Displays the active profile and its settings (credentials are masked).

---

## Recipe 2: Creating a VM with Drive, NIC, and TPM

**Goal:** Create a VM, attach a disk drive, connect it to the External network, and add a TPM 2.0 device.

### Steps

1. Create a VM with 4 GB RAM and 2 vCPUs:

```bash
vrg vm create --name web-server --ram 4096 --cpu 2
```

2. Add a 50 GB disk drive:

```bash
vrg vm drive create web-server --size 50GB --name os-disk
```

3. Attach a NIC to the External network:

```bash
vrg vm nic create web-server --network External
```

4. Add a TPM 2.0 device:

```bash
vrg vm device create web-server --model crb --version 2
```

5. Start the VM:

```bash
vrg vm start web-server --wait
```

### Verify

```bash
vrg vm get web-server
vrg vm drive list web-server
vrg vm nic list web-server
vrg vm device list web-server
```

### Cleanup

```bash
vrg vm delete web-server --force --yes
```

---

## Recipe 3: Setting Up a Network

**Goal:** Create an internal network with DHCP, firewall rules, and a static host entry.

### Steps

1. Create a network with a CIDR range, gateway IP, and DHCP enabled:

```bash
vrg network create --name dev-net --cidr 10.0.0.0/24 --ip 10.0.0.1 --dhcp
```

2. Start the network:

```bash
vrg network start dev-net
```

3. Add a firewall rule to allow incoming SSH:

```bash
vrg network rule create dev-net \
  --name allow-ssh --action accept --direction incoming \
  --protocol tcp --dest-ports 22
```

4. Apply the firewall rules so they take effect:

```bash
vrg network apply-rules dev-net
```

5. Add a DHCP host override to assign a static lease:

```bash
vrg network host create dev-net \
  --hostname db-server --ip 10.0.0.50
```

### Verify

Confirm the host override was created:

```bash
vrg network host list dev-net
```

Check active DHCP leases on the network:

```bash
vrg network diag leases dev-net
```

---

## Recipe 4: Configuring DNS

**Goal:** Set up DNS resolution with zones and records on an internal network.

### Steps

1. Create a DNS view to group your zones:

```bash
vrg network dns view create dev-net --name internal
```

2. Create a master zone under that view (use the view key returned in step 1 as the second positional argument):

```bash
vrg network dns zone create dev-net 1 \
  --domain example.local --type master
```

3. Add an A record pointing `www` to a server IP. DNS record commands take three positional arguments: network, view, and zone:

```bash
vrg network dns record create dev-net 1 1 \
  --name www --type A --value 10.0.0.10 --ttl 3600
```

4. Add a CNAME record pointing `mail` to the `www` host:

```bash
vrg network dns record create dev-net 1 1 \
  --name mail --type CNAME --value www.example.local --ttl 3600
```

5. Apply DNS configuration so the changes take effect:

```bash
vrg network apply-dns dev-net
```

### Verify

List records in the zone to confirm they were created:

```bash
vrg network dns record list dev-net 1 1
```

You should see the `www` A record and `mail` CNAME record in the output.

---

## Recipe 5: Creating VMs from a Template

**Goal:** Define a VM as a `.vrg.yaml` file and provision it with a single command.

### Template File

Save this as `web-server.vrg.yaml`:

```yaml
apiVersion: v4
kind: VirtualMachine

vm:
  name: web-server-01
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

  drives:
    - name: "OS Disk"
      media: disk
      interface: virtio-scsi
      size: 50GB

  nics:
    - name: "Primary"
      interface: virtio
      network: External

  devices:
    - type: tpm
      model: crb
      version: "2.0"
```

### Steps

1. Validate the template before creating:

```bash
vrg vm validate -f web-server.vrg.yaml
```

2. Preview what will be created with `--dry-run`:

```bash
vrg vm create -f web-server.vrg.yaml --dry-run
```

3. Create the VM:

```bash
vrg vm create -f web-server.vrg.yaml
```

4. Override values at create time with `--set`:

```bash
vrg vm create -f web-server.vrg.yaml \
  --set vm.name=web-server-02 --set vm.ram=16GB
```

### Batch Provisioning

Use `VirtualMachineSet` to create multiple VMs from shared defaults:

```yaml
apiVersion: v4
kind: VirtualMachineSet

defaults:
  os_family: linux
  cpu_cores: 2
  ram: 4GB
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
  - name: app-01
    cpu_cores: 4
    ram: 8GB
  - name: app-02
    cpu_cores: 4
    ram: 8GB
  - name: monitoring-01
    # Inherits all defaults
```

### Variables

Templates support `${VAR}` substitution from environment variables or a `vars:` block:

```yaml
apiVersion: v4
kind: VirtualMachine
vars:
  env: staging
vm:
  name: "${env}-web-01"
  ram: "${VM_RAM:-4GB}"
```

```bash
VM_RAM=16GB vrg vm create -f template.vrg.yaml
```

---

## Recipe 6: Using Output Formats

**Goal:** Get data in different formats for scripting, analysis, or wider views.

### Table (default)

```bash
vrg vm list
```

### Wide

Show all columns, including those hidden in the default table view:

```bash
vrg -o wide vm list
```

### JSON

Pipe to `jq` for further processing:

```bash
vrg -o json vm list | jq '.[].name'
```

### CSV

Export to a file for spreadsheet analysis:

```bash
vrg -o csv vm list > vms.csv
```

### Field Extraction

Pull a single field with `--query`:

```bash
vrg --query status vm get web-server
```
