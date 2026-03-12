#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Creating and populating a DataViewCtrl with editable tabular data.
from simplewx import SimpleWx as simplewx
import wx.dataview as wxdataview


# Build the host window for the DataView demo.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="DataViewCtrl Demo",
    Size=[760, 430],
)

headers = ["ID", "Name", "Score"]
# Initial table data displayed in the control.
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

win.add_dataview(
    Name="scoreDataView",
    Position=[20, 40],
    Size=[720, 320],
    Headers=headers,
    Data=rows,
    Editable=1,
    Sortable=1,
)


def on_item_changed(event):
    # Read edited cell coordinates and print current value.
    item = event.GetItem()
    col = event.GetColumn()
    view = event.GetEventObject()
    row = view.ItemToRow(item) if item.IsOk() else -1
    value = win.get_value("scoreDataView", "Cell", [row, col]) if row >= 0 and col >= 0 else None
    print(f"Changed: row={row}, col={col}, value={value}")
    event.Skip()


# Bind native wx event to track inline edits.
win.add_signal_handler("scoreDataView", wxdataview.EVT_DATAVIEW_ITEM_VALUE_CHANGED, on_item_changed)

win.show_and_run()
