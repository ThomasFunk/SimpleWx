#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Numeric & Text Entries Basics",
    Size=[620, 340],
)

win.add_entry(
    Name="nameEntry",
    Position=[20, 24],
    Size=[260, 28],
    Title="Alice",
)

win.add_combo_box(
    Name="roleCombo",
    Position=[20, 70],
    Data=["Admin", "Editor", "Viewer"],
    Start=1,
    Size=[180, 28],
)

win.add_slider(
    Name="scoreSlider",
    Position=[20, 120],
    Orientation="horizontal",
    Size=[260, 50],
    Minimum=0,
    Maximum=100,
    Start=40,
    Step=5,
)

win.add_spin_button(
    Name="ageSpin",
    Position=[20, 192],
    Size=[120, 28],
    Minimum=0,
    Maximum=120,
    Start=30,
    Step=1,
)


def on_dump(_event):
    entry_value = win.get_object("nameEntry").ref.GetValue()
    combo_value = win.get_object("roleCombo").ref.GetStringSelection()
    slider_value = win.get_object("scoreSlider").ref.GetValue()
    spin_value = win.get_object("ageSpin").ref.GetValue()
    print(
        f"name={entry_value}, role={combo_value}, score={slider_value}, age={spin_value}"
    )


win.add_button(
    Name="dumpButton",
    Position=[20, 240],
    Title="Print Values",
    Function=on_dump,
)

win.show_and_run()
