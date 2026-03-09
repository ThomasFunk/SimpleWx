#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


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
    print("Window is running.")


win.add_button(
    Name="infoButton",
    Position=[20, 60],
    Title="Print Info",
    Function=on_click,
)

win.show_and_run()
