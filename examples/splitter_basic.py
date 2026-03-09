#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="SplitterWindow Demo",
    Size=[820, 480],
)

win.add_splitter_window(
    Name="mainSplit",
    Position=[20, 20],
    Size=[780, 420],
    Orient="vertical",
    Split=260,
    MinSize=120,
)

win.add_splitter_pane(
    Name="leftPane",
    Splitter="mainSplit",
    Side="first",
)

win.add_splitter_pane(
    Name="rightPane",
    Splitter="mainSplit",
    Side="second",
)

win.add_label(
    Name="leftLabel",
    Position=[12, 12],
    Title="Left pane",
    Frame="leftPane",
)

win.add_label(
    Name="rightLabel",
    Position=[12, 12],
    Title="Right pane",
    Frame="rightPane",
)


def update_splitter_status() -> None:
    is_unsplit = int(win.get_value("mainSplit", "Unsplit")) == 1
    if not is_unsplit:
        state = "expanded"
    else:
        collapse_side = str(win.get_value("mainSplit", "Collapse") or "second")
        state = f"collapsed {collapse_side}"
    win.set_title("statusLabel", f"Splitter status: {state}")


def on_expand(_event):
    win.expand_splitter("mainSplit")
    update_splitter_status()


def on_collapse_right(_event):
    win.collapse_splitter("mainSplit", "second")
    update_splitter_status()


def on_collapse_left(_event):
    win.collapse_splitter("mainSplit", "first")
    update_splitter_status()

win.add_button(
    Name="btnToggle",
    Position=[12, 44],
    Title="Expand",
    Frame="leftPane",
    Function=on_expand,
)

win.add_button(
    Name="btnCollapseRight",
    Position=[12, 80],
    Title="Collapse Right",
    Frame="leftPane",
    Function=on_collapse_right,
)

win.add_button(
    Name="btnCollapseLeft",
    Position=[12, 116],
    Title="Collapse Left",
    Frame="leftPane",
    Function=on_collapse_left,
)

win.add_label(
    Name="statusLabel",
    Position=[12, 154],
    Title="Splitter status: expanded",
    Frame="leftPane",
)

update_splitter_status()

win.show_and_run()
