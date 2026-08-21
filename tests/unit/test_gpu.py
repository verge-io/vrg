"""Tests for GPU commands."""

from verge_cli.cli import app

# ---------------------------------------------------------------------------
# Profile commands
# ---------------------------------------------------------------------------


def test_profile_list(cli_runner, mock_client, mock_vgpu_profile):
    """vrg gpu profile list should list vGPU profiles."""
    mock_client.vgpu_profiles.list.return_value = [mock_vgpu_profile]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "profile", "list"])

    assert result.exit_code == 0
    assert "nvidia-256c" in result.output
    mock_client.vgpu_profiles.list.assert_called_once()


def test_profile_list_empty(cli_runner, mock_client):
    """vrg gpu profile list should handle empty results."""
    mock_client.vgpu_profiles.list.return_value = []

    result = cli_runner.invoke(app, ["gpu", "profile", "list"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_profile_list_with_type(cli_runner, mock_client, mock_vgpu_profile):
    """vrg gpu profile list --type C should filter by type."""
    mock_client.vgpu_profiles.list.return_value = [mock_vgpu_profile]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "profile", "list", "--type", "C"])

    assert result.exit_code == 0
    assert "nvidia-256c" in result.output
    call_kwargs = mock_client.vgpu_profiles.list.call_args[1]
    assert call_kwargs["profile_type"] == "C"


def test_profile_list_json(cli_runner, mock_client, mock_vgpu_profile):
    """vrg gpu profile list --output json should output JSON."""
    mock_client.vgpu_profiles.list.return_value = [mock_vgpu_profile]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "profile", "list"])

    assert result.exit_code == 0
    assert '"name": "nvidia-256c"' in result.output


def test_profile_get(cli_runner, mock_client, mock_vgpu_profile):
    """vrg gpu profile get should show profile details."""
    mock_client.vgpu_profiles.list.return_value = [mock_vgpu_profile]
    mock_client.vgpu_profiles.get.return_value = mock_vgpu_profile

    result = cli_runner.invoke(app, ["gpu", "profile", "get", "nvidia-256c"])

    assert result.exit_code == 0
    assert "nvidia-256c" in result.output


def test_profile_get_by_key(cli_runner, mock_client, mock_vgpu_profile):
    """vrg gpu profile get by numeric key should work."""
    mock_client.vgpu_profiles.get.return_value = mock_vgpu_profile

    result = cli_runner.invoke(app, ["gpu", "profile", "get", "1"])

    assert result.exit_code == 0
    assert "nvidia-256c" in result.output


# ---------------------------------------------------------------------------
# GPU commands
# ---------------------------------------------------------------------------


def test_gpu_list(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu list should list GPU configs."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "list"])

    assert result.exit_code == 0
    assert "NVIDIA A100" in result.output
    mock_client.nodes.all_gpus.list.assert_called_once()


def test_gpu_list_empty(cli_runner, mock_client):
    """vrg gpu list should handle empty results."""
    mock_client.nodes.all_gpus.list.return_value = []

    result = cli_runner.invoke(app, ["gpu", "list"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_gpu_list_with_mode(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu list --mode nvidia_vgpu should filter by mode."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]

    result = cli_runner.invoke(app, ["gpu", "list", "--mode", "nvidia_vgpu"])

    assert result.exit_code == 0
    call_kwargs = mock_client.nodes.all_gpus.list.call_args[1]
    assert call_kwargs["mode"] == "nvidia_vgpu"


def test_gpu_list_with_node(cli_runner, mock_client, mock_node, mock_node_gpu):
    """vrg gpu list --node should use scoped manager."""
    mock_client.nodes.list.return_value = [mock_node]
    mock_client.nodes.gpus.return_value.list.return_value = [mock_node_gpu]

    result = cli_runner.invoke(app, ["gpu", "list", "--node", "node1"])

    assert result.exit_code == 0
    mock_client.nodes.gpus.assert_called_once_with(10)


def test_gpu_list_json(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu list --output json should output JSON."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "list"])

    assert result.exit_code == 0
    assert '"name": "NVIDIA A100"' in result.output


def test_gpu_get(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu get should show GPU details."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "get", "NVIDIA A100"])

    assert result.exit_code == 0
    assert "NVIDIA A100" in result.output


def test_gpu_get_by_key(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu get by numeric key should work."""
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "get", "1"])

    assert result.exit_code == 0
    assert "NVIDIA A100" in result.output


def test_gpu_update(cli_runner, mock_client, mock_node_gpu, mock_vgpu_profile):
    """vrg gpu update should change GPU mode."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "update", "NVIDIA A100", "--mode", "gpu", "--yes"])

    assert result.exit_code == 0
    mock_client.nodes.gpus.assert_called_with(10)
    mock_client.nodes.gpus.return_value.update.assert_called_once_with(1, mode="gpu")


def test_gpu_update_rejects_invalid_mode(cli_runner, mock_client):
    """GPU update should reject mode typos before calling the API."""
    result = cli_runner.invoke(app, ["gpu", "update", "1", "--mode", "nvidia-vgpu", "--yes"])

    assert result.exit_code == 2
    assert "nvidia_vgpu" in result.output


def test_gpu_update_with_profile(cli_runner, mock_client, mock_node_gpu, mock_vgpu_profile):
    """vrg gpu update with --profile should include profile key."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu
    mock_client.vgpu_profiles.list.return_value = [mock_vgpu_profile]

    result = cli_runner.invoke(
        app,
        [
            "gpu",
            "update",
            "NVIDIA A100",
            "--mode",
            "nvidia_vgpu",
            "--profile",
            "nvidia-256c",
            "--yes",
        ],
    )

    assert result.exit_code == 0
    mock_client.nodes.gpus.return_value.update.assert_called_once_with(
        1, mode="nvidia_vgpu", nvidia_vgpu_profile=1
    )


def test_gpu_update_no_yes(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu update without --yes should prompt and abort on 'n'."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "update", "NVIDIA A100", "--mode", "gpu"], input="n\n")

    assert result.exit_code == 0
    mock_client.nodes.gpus.return_value.update.assert_not_called()


def test_gpu_stats(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu stats should show GPU utilization."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "stats", "NVIDIA A100"])

    assert result.exit_code == 0
    gpu_obj = mock_client.nodes.all_gpus.get.return_value
    gpu_obj.stats.get.assert_called_once()


def test_gpu_stats_json(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu stats --output json should output JSON."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "stats", "NVIDIA A100"])

    assert result.exit_code == 0
    assert "gpus_total" in result.output


def test_gpu_instances(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu instances should list VMs using the GPU."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "instances", "NVIDIA A100"])

    assert result.exit_code == 0
    assert "test-vm" in result.output


def test_gpu_instances_empty(cli_runner, mock_client, mock_node_gpu):
    """vrg gpu instances should handle no VMs."""
    mock_client.nodes.all_gpus.list.return_value = [mock_node_gpu]
    mock_node_gpu.instances.list.return_value = []
    mock_client.nodes.all_gpus.get.return_value = mock_node_gpu

    result = cli_runner.invoke(app, ["gpu", "instances", "NVIDIA A100"])

    assert result.exit_code == 0
    assert "No results" in result.output


# ---------------------------------------------------------------------------
# Device commands
# ---------------------------------------------------------------------------


def test_device_list(cli_runner, mock_client, mock_vgpu_device, mock_host_gpu_device):
    """vrg gpu device list should list all GPU devices."""
    mock_client.nodes.all_vgpu_devices.list.return_value = [mock_vgpu_device]
    mock_client.nodes.all_host_gpu_devices.list.return_value = [mock_host_gpu_device]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "device", "list"])

    assert result.exit_code == 0
    assert "A100" in result.output
    assert "T400" in result.output


def test_device_list_vgpu_only(cli_runner, mock_client, mock_vgpu_device):
    """vrg gpu device list --type vgpu should list only vGPU devices."""
    mock_client.nodes.all_vgpu_devices.list.return_value = [mock_vgpu_device]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "device", "list", "--type", "vgpu"])

    assert result.exit_code == 0
    assert "A100" in result.output
    mock_client.nodes.all_host_gpu_devices.list.assert_not_called()


def test_device_list_host_only(cli_runner, mock_client, mock_host_gpu_device):
    """vrg gpu device list --type host should list only host GPU devices."""
    mock_client.nodes.all_host_gpu_devices.list.return_value = [mock_host_gpu_device]

    result = cli_runner.invoke(app, ["--output", "json", "gpu", "device", "list", "--type", "host"])

    assert result.exit_code == 0
    assert "T400" in result.output
    mock_client.nodes.all_vgpu_devices.list.assert_not_called()


def test_device_list_with_node(
    cli_runner, mock_client, mock_node, mock_vgpu_device, mock_host_gpu_device
):
    """vrg gpu device list --node should use scoped managers."""
    mock_client.nodes.list.return_value = [mock_node]
    mock_client.nodes.vgpu_devices.return_value.list.return_value = [mock_vgpu_device]
    mock_client.nodes.host_gpu_devices.return_value.list.return_value = [mock_host_gpu_device]

    result = cli_runner.invoke(app, ["gpu", "device", "list", "--node", "node1"])

    assert result.exit_code == 0
    mock_client.nodes.vgpu_devices.assert_called_once_with(10)
    mock_client.nodes.host_gpu_devices.assert_called_once_with(10)


def test_device_list_empty(cli_runner, mock_client):
    """vrg gpu device list should handle empty results."""
    mock_client.nodes.all_vgpu_devices.list.return_value = []
    mock_client.nodes.all_host_gpu_devices.list.return_value = []

    result = cli_runner.invoke(app, ["gpu", "device", "list"])

    assert result.exit_code == 0
    assert "No results" in result.output


def test_device_get(cli_runner, mock_client, mock_vgpu_device):
    """vrg gpu device get should show device details."""
    mock_client.nodes.all_vgpu_devices.get.return_value = mock_vgpu_device

    result = cli_runner.invoke(app, ["gpu", "device", "get", "5"])

    assert result.exit_code == 0
    assert "NVIDIA A100" in result.output


def test_device_get_host_fallback(cli_runner, mock_client, mock_host_gpu_device):
    """vrg gpu device get should fall back to host GPU devices."""
    mock_client.nodes.all_vgpu_devices.get.side_effect = Exception("Not found")
    mock_client.nodes.all_host_gpu_devices.get.return_value = mock_host_gpu_device

    result = cli_runner.invoke(app, ["gpu", "device", "get", "6"])

    assert result.exit_code == 0
    assert "NVIDIA T400" in result.output


def test_device_get_non_numeric(cli_runner, mock_client):
    """vrg gpu device get with non-numeric ID should fail."""
    result = cli_runner.invoke(app, ["gpu", "device", "get", "abc"])

    assert result.exit_code == 1
    assert "numeric" in result.output.lower()
