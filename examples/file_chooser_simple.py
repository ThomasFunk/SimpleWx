#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# File chooser button and dialog usage for opening and saving files.
from simplewx import SimpleWx as simplewx


# Create top-level window
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="File Choosers",
    Size=[200, 180],
)

# File chooser button: generic file open dialog
win.add_filechooser_button(
    Name="FButton1",
    Position=[40, 20],
    Size=[120, 40],
    Title="Select a file",
    Action="open",
)

# File chooser button: image-only filter, start in ~/Pictures
win.add_filechooser_button(
    Name="FButton2",
    Position=[40, 70],
    Size=[120, 40],
    Title="Select an image",
    Action="open",
    Folder="~/Pictures",
    Filter=["Images", "*.png"],
)

# File chooser button: folder selection mode
win.add_filechooser_button(
    Name="FButton3",
    Position=[40, 120],
    Size=[120, 40],
    Title="Select a folder",
    Action="select-folder",
    Folder="/home",
    Filter="*.txt",
)

# Show window and start event loop
win.show_and_run()
