"""GPU management commands."""

from __future__ import annotations

from typing import Annotated, Any

import click
import typer

from verge_cli.columns import (
    GPU_COLUMNS,
    GPU_DEVICE_COLUMNS,
    GPU_INSTANCE_COLUMNS,
    GPU_PROFILE_COLUMNS,
)
from verge_cli.context import get_context
from verge_cli.errors import handle_errors
from verge_cli.multi import list_all_profiles
from verge_cli.output import output_result, output_success
from verge_cli.utils import confirm_action, resolve_resource_id

app = typer.Typer(
    name="gpu",
    help="Manage GPUs and vGPU profiles.",
    no_args_is_help=True,
)

profile_app = typer.Typer(
    name="profile",
    help="Manage vGPU profiles.",
    no_args_is_help=True,
)
app.add_typer(profile_app)

device_app = typer.Typer(
    name="device",
    help="Manage physical GPU devices.",
    no_args_is_help=True,
)
app.add_typer(device_app)


# ---------------------------------------------------------------------------
# Converter functions
# ---------------------------------------------------------------------------


def _profile_to_dict(profile: Any) -> dict[str, Any]:
    return {
        "$key": profile.key,
        "name": profile.name,
        "type": getattr(profile, "type", profile.get("type", "")),
        "framebuffer": getattr(profile, "framebuffer", profile.get("framebuffer", "")),
        "max_resolution": getattr(profile, "max_resolution", profile.get("max_resolution", "")),
        "max_instance": getattr(profile, "max_instance", profile.get("max_instance", "")),
        "grid_license": getattr(profile, "grid_license", profile.get("grid_license", "")),
    }


def _gpu_to_dict(gpu: Any) -> dict[str, Any]:
    return {
        "$key": gpu.key,
        "name": gpu.name,
        "node_name": getattr(gpu, "node_name", gpu.get("node_name", "")),
        "mode_display": getattr(gpu, "mode_display", gpu.get("mode_display", gpu.get("mode", ""))),
        "nvidia_vgpu_profile_display": getattr(
            gpu,
            "nvidia_vgpu_profile_display",
            gpu.get("nvidia_vgpu_profile_display", gpu.get("nvidia_vgpu_profile", "")),
        ),
        "instances_count": getattr(gpu, "instances_count", gpu.get("instances_count", 0)),
        "max_instances": getattr(gpu, "max_instances", gpu.get("max_instances", 0)),
    }


def _gpu_stats_to_dict(stats: Any) -> dict[str, Any]:
    return {
        "gpus_total": getattr(stats, "gpus_total", stats.get("gpus_total", 0)),
        "gpus": getattr(stats, "gpus", stats.get("gpus", 0)),
        "gpus_idle": getattr(stats, "gpus_idle", stats.get("gpus_idle", 0)),
        "vgpus_total": getattr(stats, "vgpus_total", stats.get("vgpus_total", 0)),
        "vgpus": getattr(stats, "vgpus", stats.get("vgpus", 0)),
        "vgpus_idle": getattr(stats, "vgpus_idle", stats.get("vgpus_idle", 0)),
    }


def _gpu_instance_to_dict(instance: Any) -> dict[str, Any]:
    key = (
        instance.key if hasattr(instance, "key") else instance.get("$key", instance.get("key", ""))
    )
    return {
        "$key": key,
        "machine_name": getattr(instance, "machine_name", instance.get("machine_name", "")),
        "machine_type_display": getattr(
            instance,
            "machine_type_display",
            instance.get("machine_type_display", instance.get("machine_type", "")),
        ),
        "mode_display": getattr(
            instance,
            "mode_display",
            instance.get("mode_display", instance.get("mode", "")),
        ),
        "machine_device_status": getattr(
            instance,
            "machine_device_status",
            instance.get("machine_device_status", ""),
        ),
    }


def _device_to_dict(device: Any) -> dict[str, Any]:
    return {
        "$key": device.key,
        "name": device.name,
        "node_name": getattr(device, "node_name", device.get("node_name", "")),
        "slot": getattr(device, "slot", device.get("slot", "")),
        "vendor": getattr(device, "vendor", device.get("vendor", "")),
        "device": getattr(device, "device", device.get("device", "")),
        "driver": getattr(device, "driver", device.get("driver", "")),
        "max_instances": getattr(device, "max_instances", device.get("max_instances", 0)),
    }


# ---------------------------------------------------------------------------
# Profile commands
# ---------------------------------------------------------------------------


@profile_app.command("list")
@handle_errors()
def profile_list(
    ctx: typer.Context,
    profile_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by profile type.",
            click_type=click.Choice(["A", "B", "C", "Q"]),
        ),
    ] = None,
) -> None:
    """List vGPU profiles."""
    vctx = get_context(ctx)
    kwargs: dict[str, Any] = {}
    if profile_type is not None:
        kwargs["profile_type"] = profile_type
    profiles = vctx.client.vgpu_profiles.list(**kwargs)
    data = [_profile_to_dict(p) for p in profiles]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GPU_PROFILE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@profile_app.command("get")
@handle_errors()
def profile_get(
    ctx: typer.Context,
    profile: Annotated[str, typer.Argument(help="Profile ID or name.")],
) -> None:
    """Get vGPU profile details."""
    vctx = get_context(ctx)
    key = int(resolve_resource_id(vctx.client.vgpu_profiles, profile, "vGPU profile"))
    result = vctx.client.vgpu_profiles.get(key)
    data = _profile_to_dict(result)
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


# ---------------------------------------------------------------------------
# GPU commands
# ---------------------------------------------------------------------------


@app.command("list")
@handle_errors()
def gpu_list(
    ctx: typer.Context,
    node: Annotated[
        str | None,
        typer.Option("--node", help="Filter by node name or ID."),
    ] = None,
    mode: Annotated[
        str | None,
        typer.Option(
            "--mode",
            help="Filter by GPU mode.",
            click_type=click.Choice(["gpu", "nvidia_vgpu", "none"]),
        ),
    ] = None,
) -> None:
    """List GPU configurations."""
    if ctx.obj.get("all_profiles"):
        list_all_profiles(
            ctx, lambda c: c.nodes.all_gpus.list(), _gpu_to_dict, GPU_COLUMNS
        )
        return
    vctx = get_context(ctx)
    if node is not None:
        node_key = int(resolve_resource_id(vctx.client.nodes, node, "node"))
        gpus = vctx.client.nodes.gpus(node_key).list()
    else:
        kwargs: dict[str, Any] = {}
        if mode is not None:
            kwargs["mode"] = mode
        gpus = vctx.client.nodes.all_gpus.list(**kwargs)
    data = [_gpu_to_dict(g) for g in gpus]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GPU_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("get")
@handle_errors()
def gpu_get(
    ctx: typer.Context,
    gpu: Annotated[str, typer.Argument(help="GPU ID or name.")],
) -> None:
    """Get GPU configuration details."""
    vctx = get_context(ctx)
    key = int(resolve_resource_id(vctx.client.nodes.all_gpus, gpu, "GPU"))
    result = vctx.client.nodes.all_gpus.get(key)
    data = _gpu_to_dict(result)
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("update")
@handle_errors()
def gpu_update(
    ctx: typer.Context,
    gpu: Annotated[str, typer.Argument(help="GPU ID or name.")],
    mode: Annotated[
        str,
        typer.Option("--mode", help="GPU mode to set."),
    ],
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="vGPU profile name or ID."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Change GPU mode and optionally assign a vGPU profile."""
    vctx = get_context(ctx)
    gpu_key = int(resolve_resource_id(vctx.client.nodes.all_gpus, gpu, "GPU"))
    gpu_obj = vctx.client.nodes.all_gpus.get(gpu_key)
    node_key = int(getattr(gpu_obj, "node_key", gpu_obj.get("node_key", gpu_obj.get("node", 0))))

    if not confirm_action(f"Update GPU '{gpu}' mode to '{mode}'?", yes=yes):
        return

    update_kwargs: dict[str, Any] = {"mode": mode}
    if profile is not None:
        profile_key = int(resolve_resource_id(vctx.client.vgpu_profiles, profile, "vGPU profile"))
        update_kwargs["nvidia_vgpu_profile"] = profile_key

    vctx.client.nodes.gpus(node_key).update(gpu_key, **update_kwargs)
    output_success(f"GPU '{gpu}' updated successfully.", quiet=vctx.quiet)


@app.command("stats")
@handle_errors()
def gpu_stats(
    ctx: typer.Context,
    gpu: Annotated[str, typer.Argument(help="GPU ID or name.")],
) -> None:
    """Show GPU utilization statistics."""
    vctx = get_context(ctx)
    key = int(resolve_resource_id(vctx.client.nodes.all_gpus, gpu, "GPU"))
    gpu_obj = vctx.client.nodes.all_gpus.get(key)
    stats = gpu_obj.stats.get()
    data = _gpu_stats_to_dict(stats)
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@app.command("instances")
@handle_errors()
def gpu_instances(
    ctx: typer.Context,
    gpu: Annotated[str, typer.Argument(help="GPU ID or name.")],
) -> None:
    """List VMs using this GPU."""
    vctx = get_context(ctx)
    key = int(resolve_resource_id(vctx.client.nodes.all_gpus, gpu, "GPU"))
    gpu_obj = vctx.client.nodes.all_gpus.get(key)
    instances = gpu_obj.instances.list()
    data = [_gpu_instance_to_dict(i) for i in instances]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GPU_INSTANCE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


# ---------------------------------------------------------------------------
# Device commands
# ---------------------------------------------------------------------------


@device_app.command("list")
@handle_errors()
def device_list(
    ctx: typer.Context,
    node: Annotated[
        str | None,
        typer.Option("--node", help="Filter by node name or ID."),
    ] = None,
    device_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Filter by device type.",
            click_type=click.Choice(["vgpu", "host"]),
        ),
    ] = None,
) -> None:
    """List physical GPU devices."""
    vctx = get_context(ctx)
    devices: list[Any] = []

    if node is not None:
        node_key = int(resolve_resource_id(vctx.client.nodes, node, "node"))
        if device_type is None or device_type == "vgpu":
            devices.extend(vctx.client.nodes.vgpu_devices(node_key).list())
        if device_type is None or device_type == "host":
            devices.extend(vctx.client.nodes.host_gpu_devices(node_key).list())
    else:
        if device_type is None or device_type == "vgpu":
            devices.extend(vctx.client.nodes.all_vgpu_devices.list())
        if device_type is None or device_type == "host":
            devices.extend(vctx.client.nodes.all_host_gpu_devices.list())

    data = [_device_to_dict(d) for d in devices]
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        columns=GPU_DEVICE_COLUMNS,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )


@device_app.command("get")
@handle_errors()
def device_get(
    ctx: typer.Context,
    device_id: Annotated[str, typer.Argument(help="Device ID (numeric key).")],
) -> None:
    """Get physical GPU device details."""
    vctx = get_context(ctx)

    if not device_id.isdigit():
        typer.echo("Error: Device ID must be a numeric key.", err=True)
        raise typer.Exit(code=1)

    key = int(device_id)

    # Try vgpu devices first, then host GPU devices.
    device: Any
    try:
        device = vctx.client.nodes.all_vgpu_devices.get(key=key)
    except Exception:
        device = vctx.client.nodes.all_host_gpu_devices.get(key=key)

    data = _device_to_dict(device)
    output_result(
        data,
        output_format=vctx.output_format,
        query=vctx.query,
        quiet=vctx.quiet,
        no_color=vctx.no_color,
    )
