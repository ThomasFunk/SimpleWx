#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Buttons & Toggles Basics",
    Size=[560, 320],
)

win.add_label(
    Name="hint",
    Position=[20, 16],
    Title="Button, CheckButton, RadioButton and LinkButton in one window.",
)

win.add_check_button(
    Name="checkEnabled",
    Position=[20, 52],
    Title="Feature enabled",
    Active=1,
)

win.add_radio_button(
    Name="radioLow",
    Position=[20, 84],
    Title="Low",
    Group="priority",
    Active=1,
)

win.add_radio_button(
    Name="radioHigh",
    Position=[120, 84],
    Title="High",
    Group="priority",
)

win.add_link_button(
    Name="projectLink",
    Position=[20, 118],
    Title="Open SimpleWx repository",
    Uri="https://github.com/ThomasFunk/SimpleWx",
)


def on_submit(_event):
    checked = win.get_object("checkEnabled").ref.GetValue()
    low = win.get_object("radioLow").ref.GetValue()
    high = win.get_object("radioHigh").ref.GetValue()
    print(f"checkEnabled={checked}, radioLow={low}, radioHigh={high}")


win.add_button(
    Name="submitButton",
    Position=[20, 160],
    Title="Read States",
    Function=on_submit,
)

win.show_and_run()
