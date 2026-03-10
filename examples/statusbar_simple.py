#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Working with statusbar text fields and status message updates.
from simplewx import SimpleWx as simplewx


# Create top-level window with default statusbar support
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Statusbar Example",
    Statusbar=1,
    Size=[170, 300],
)

# Add custom statusbar object used by helper APIs
win.add_statusbar(
    Name="sbar1",
    Position=[0, 0],
    Timeout=2,
)

# Runtime state for generated item labels and tracked ids
counter = {"value": 1}
message_ids = []


# Push message via explicit statusbar name
def push_above(_event):
    text = f"Item {counter['value']}"
    msg_id = win.set_sb_text("sbar1", text)
    message_ids.append(msg_id)
    counter["value"] += 1


# Push message via compatibility shorthand (text only)
def push_below(_event):
    text = f"Item {counter['value']}"
    msg_id = win.set_sb_text(text)
    message_ids.append(msg_id)
    counter["value"] += 1


# Remove last statusbar message
def pop_last(_event):
    win.remove_sb_text("sbar1")
    if message_ids:
        message_ids.pop()


# Remove tracked third message
def remove_3rd(_event):
    if len(message_ids) >= 3:
        win.remove_sb_text("sbar1", MsgId=message_ids[2])


# Remove tracked message "Item 4" by id
def del_item4(_event):
    # remove by tracked id if available
    if len(message_ids) >= 4:
        win.remove_sb_text("sbar1", MsgId=message_ids[3])


# Control buttons
win.add_button(
    Name="button_push1",
    Position=[30, 30],
    Size=[90, 25],
    Title="push above",
    Function=push_above,
)

win.add_button(
    Name="button_push2",
    Position=[30, 70],
    Size=[90, 25],
    Title="push below",
    Function=push_below,
)

win.add_button(
    Name="button_pop1",
    Position=[30, 110],
    Size=[90, 25],
    Title="pop last",
    Function=pop_last,
)

win.add_button(
    Name="button_remove1",
    Position=[30, 150],
    Size=[90, 25],
    Title="remove 3rd",
    Function=remove_3rd,
)

win.add_button(
    Name="button_item1",
    Position=[30, 190],
    Size=[90, 25],
    Title="del 'item 4'",
    Function=del_item4,
)

# Show window and start event loop
win.show_and_run()
