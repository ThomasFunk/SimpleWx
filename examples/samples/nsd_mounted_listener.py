#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/21"

"""SimpleWx + nsd IPC example.

This example listens for nsd broadcast events and reacts to:
- action='mounted'          (automount plugin)
- action='show_notification' (notifications plugin)
"""

import datetime
from simplewx import SimpleWx as simplewx


win = simplewx()
win.new_window(
    Name="mainWindow",
    Title="NSD mounted listener",
    Size=[760, 360],
    Statusbar=1,
)

win.add_statusbar(
    Name="sbar1",
    Position=[0, 0],
    Timeout=4,
)

win.add_listview(
    Name="mountEvents",
    Position=[10, 10],
    Size=[740, 290],
    Headers=["Time", "Action", "Device", "Mount point", "Label"],
    Data=[],
)


def _append_row(action: str, payload: dict) -> None:
    list_view = win.get_widget("mountEvents")
    if list_view is None:
        return

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    row = [
        timestamp,
        action,
        str(payload.get("device", "")),
        str(payload.get("mount_point", "")),
        str(payload.get("label", "")),
    ]
    list_view.Append(row)


def on_nsd_message(message: dict) -> None:
    action = str(message.get("action") or "")
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}

    if action == "mounted":
        _append_row("mounted", payload)
        device = str(payload.get("device", "?"))
        mount_point = str(payload.get("mount_point", "?"))
        win.set_sb_text("sbar1", f"mounted: {device} -> {mount_point}")

    elif action == "show_notification":
        title = str(payload.get("title", "notification"))
        body = str(payload.get("message", ""))
        win.set_sb_text("sbar1", f"notification: {title} {body}")


# Start background IPC listener thread (default socket: /tmp/nsd.sock)
win.enable_nsd(on_nsd_message)

win.show_and_run()
