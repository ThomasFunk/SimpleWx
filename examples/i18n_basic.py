#!/usr/bin/env python3
from pathlib import Path
from simplewx import SimpleWx as simplewx


win = simplewx()

project_root = Path(__file__).resolve().parents[1]
locale_paths = f"{project_root}/locale:+"
win.use_gettext("simplewx_demo", locale_paths)

win.new_window(
    Name="mainWindow",
    Title=win.translate("Localization Demo"),
    Size=[520, 280],
)

win.add_label(
    Name="helloLabel",
    Position=[20, 20],
    Title=win.translate("Hello World"),
)

win.add_label(
    Name="hintLabel",
    Position=[20, 55],
    Title=win.translate("Click the button to print a translated message."),
)


def on_click(_event):
    print(win.translate("Button clicked"))


win.add_button(
    Name="actionButton",
    Position=[20, 95],
    Title=win.translate("Action"),
    Function=on_click,
)

win.add_label(
    Name="footerLabel",
    Position=[20, 145],
    Title=win.translate("Tip: set LANGUAGE=de_DE to test German translations."),
)

win.show_and_run()
