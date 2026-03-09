#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="TreeView Basics",
    Size=[560, 360],
)

headers = ["Project"]
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
