#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Building and updating a wx.grid-based table with headers and rows.
from simplewx import SimpleWx as simplewx
import wx.grid as wxgrid


# Build the host window for the grid demo.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Grid Demo",
    Size=[760, 430],
)

headers = ["ID", "Name", "Score"]
# Initial row set shown by the grid.
rows = [
    [1, "Alice", 92],
    [2, "Bob", 78],
    [3, "Carla", 85],
    [4, "David", 90],
]

win.add_label(
    Name="hint",
    Position=[20, 16],
    Title="Click a column header to sort; cells are editable.",
)

win.add_grid(
    Name="scoreGrid",
    Position=[20, 40],
    Size=[720, 310],
    Headers=headers,
    Data=rows,
    Editable=1,
    Sortable=1,
)


def on_cell_changed(event):
    # Report changed cell and its new value.
    row = event.GetRow()
    col = event.GetCol()
    value = win.get_value("scoreGrid", "Cell", [row, col])
    print(f"Changed: row={row}, col={col}, value={value}")
    event.Skip()


# Bind grid cell-change event.
win.add_signal_handler("scoreGrid", wxgrid.EVT_GRID_CELL_CHANGED, on_cell_changed)

win.show_and_run()
