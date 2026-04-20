"""Site sync management — registers outgoing and incoming sub-typers."""

from __future__ import annotations

import typer

from verge_cli.commands import site_sync_incoming, site_sync_outgoing, site_sync_schedule

app = typer.Typer(
    name="sync",
    help=(
        "Manage site-to-site replication jobs (**site syncs**).\n\n"
        "Site syncs move cloud snapshots between paired VergeOS systems over"
        " the vSAN data plane (default port 14201). Replication is"
        " **directional**: an **outgoing sync** on the source pushes snapshots"
        " to a remote site; an **incoming sync** on the destination receives"
        " them. Outgoing and incoming are paired via a registration code"
        " generated on the destination during pairing.\n\n"
        "Transfers are block-level deduplicated and compressed — only blocks"
        " that differ from the destination are sent. A **schedule** attaches a"
        " snapshot profile period to a sync so snapshots created by that"
        " period are automatically queued for replication with a specific"
        " retention and priority.\n\n"
        "Subcommands: `vrg site sync outgoing` (outbound replication jobs),"
        " `vrg site sync incoming` (inbound receivers), and `vrg site sync"
        " schedule` (per-sync profile-period bindings that control what gets"
        " replicated and how long the remote copy is kept).\n\n"
        "---\n\n"
        "**Examples:**\n\n"
        "    # List outgoing syncs (source side)\n"
        "    vrg site sync outgoing list\n\n"
        "    # List incoming syncs (destination side)\n"
        "    vrg site sync incoming list\n\n"
        "    # List schedules that drive which snapshots replicate\n"
        "    vrg site sync schedule list\n\n"
        "    # JSON output for scripting / agents\n"
        "    vrg -o json site sync outgoing list\n\n"
        "---\n\n"
        "**Notes:**\n\n"
        "Set up flow: create the incoming sync on the destination first to"
        " generate a registration code, then create the outgoing sync on the"
        " source using that code. Once paired, snapshots created by the"
        " scheduled profile period are queued, transferred, and stored"
        " remotely with the configured retention.\n\n"
        "System limit: **100,000 syncs per type** per system. Syncs and"
        " schedules are referenced by numeric key (`$key`); when a name"
        " matches multiple records, vrg exits with code 7 — use the key to"
        " disambiguate. Use `-o json` for machine-readable output."
    ),
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

app.add_typer(site_sync_outgoing.app, name="outgoing")
app.add_typer(site_sync_incoming.app, name="incoming")
app.add_typer(site_sync_schedule.app, name="schedule")
