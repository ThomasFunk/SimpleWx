#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Creating a list view and filling it with rows of text data.
from simplewx import SimpleWx as simplewx


# Build a simple list view demo window.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="ListView Basics",
    Size=[640, 360],
)

headers = ["ID", "Name", "Role"]
# Seed rows for the initial list content.
rows = [
    [1, "Alice", "Admin"],
    [2, "Bob", "Editor"],
    [3, "Carla", "Viewer"],
]

win.add_listview(
    Name="usersList",
    Position=[20, 20],
    Size=[590, 250],
    Headers=headers,
    Data=rows,
)

next_id = {"value": 4}


def on_add(_event):
    # Append a generated user row.
    user_id = next_id["value"]
    win.modify_list_data("usersList", push=[user_id, f"User {user_id}", "Viewer"])
    next_id["value"] += 1


def on_remove_last(_event):
    # Remove the last row from the list.
    win.modify_list_data("usersList", pop=1)


win.add_button(
    Name="addRow",
    Position=[20, 290],
    Title="Add Row",
    Function=on_add,
)

win.add_button(
    Name="removeRow",
    Position=[120, 290],
    Title="Remove Last",
    Function=on_remove_last,
)

win.show_and_run()
