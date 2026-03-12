#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Creating a basic main window and placing simple widgets in it.
from simplewx import SimpleWx as simplewx


# Create a basic top-level window with statusbar.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Windows Basics",
    Version="v1",
    Size=[480, 260],
    Statusbar=1,
)

win.add_label(
    Name="titleLabel",
    Position=[20, 20],
    Title="Basic window setup with title, size and statusbar.",
)


def on_click(_event):
    # Write feedback into the statusbar instead of stdout.
    win.set_sb_text("Window is running.")


win.add_button(
    Name="infoButton",
    Position=[20, 60],
    Title="Show Status",
    Function=on_click,
)

win.show_and_run()
