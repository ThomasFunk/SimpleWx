#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Building a tree view, selecting nodes, and reading selected values.
from simplewx import SimpleWx as simplewx


# Create a minimal tree view demo window.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="TreeView Basics",
    Size=[560, 360],
)

headers = ["Project"]
# Nested format: [label, [children...]].
data = [
    ["src", [["core", []], ["widgets", [["buttons.py", []], ["listview.py", []]]]]],
    ["tests", [["test_core.py", []], ["test_widgets.py", []]]],
    ["README.md", []],
]

win.add_treeview(
    Name="projectTree",
    Type="Tree",
    Position=[20, 20],
    Size=[500, 280],
    Headers=headers,
    Data=data,
)

win.show_and_run()
