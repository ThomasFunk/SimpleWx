#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


def on_dir_changed(event):
    picker = event.GetEventObject()
    print(f"Selected folder: {picker.GetPath()}")
    event.Skip()


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="DirPickerCtrl Demo",
    Size=[700, 180],
)

win.add_label(
    Name="hintLabel",
    Position=[20, 20],
    Title="Please select a folder:",
)

win.add_dirpicker_ctrl(
    Name="projectDir",
    Position=[20, 50],
    Size=[650, 30],
    Title="Select project folder",
    Function=on_dir_changed,
)

win.show_and_run()
