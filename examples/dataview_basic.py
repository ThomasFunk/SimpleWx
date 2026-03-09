#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx
import wx.dataview as wxdataview


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="DataViewCtrl Demo",
    Size=[760, 430],
)

headers = ["ID", "Name", "Score"]
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
    item = event.GetItem()
    col = event.GetColumn()
    view = event.GetEventObject()
    row = view.ItemToRow(item) if item.IsOk() else -1
    value = win.get_value("scoreDataView", "Cell", [row, col]) if row >= 0 and col >= 0 else None
    print(f"Changed: row={row}, col={col}, value={value}")
    event.Skip()


win.add_signal_handler("scoreDataView", wxdataview.EVT_DATAVIEW_ITEM_VALUE_CHANGED, on_item_changed)

win.show_and_run()
