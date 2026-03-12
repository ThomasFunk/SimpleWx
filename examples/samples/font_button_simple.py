#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Picking fonts with a font button and applying the selected font.
from simplewx import SimpleWx as simplewx


# Create top-level window
win = simplewx()

win.new_window(
    Name="main",
    Title="Font Button",
    Size=[400, 200],
)

# Add font button with initial font
win.add_font_button(
    Name="font_button",
    Position=[20, 40],
    Font=["Arial", 12],
)

# Show window and start event loop
win.show_and_run()
