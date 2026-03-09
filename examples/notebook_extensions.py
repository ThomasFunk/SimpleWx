#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


def on_notebook_page_changed(event):
    notebook = event.GetEventObject()
    page_index = notebook.GetSelection()
    page_title = notebook.GetPageText(page_index) if page_index >= 0 else ""
    print(f"Notebook event: page changed -> index={page_index}, title='{page_title}'")
    event.Skip()


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Notebook Extensions Demo",
    Size=[860, 560],
)

win.add_label(
    Name="hintLabel",
    Position=[20, 16],
    Title="Middle-click on a tab closes the page (CloseTabs=1).",
)

win.add_notebook(
    Name="mainNotebook",
    Position=[20, 45],
    Size=[820, 490],
    Tabs="top",
    Scrollable=1,
    CloseTabs=1,
    Function=on_notebook_page_changed,
)

win.add_nb_page(
    Name="pageHome",
    Notebook="mainNotebook",
    Title="Home",
    Image="gtk-home",
)
win.add_label(
    Name="labelHome",
    Position=[16, 16],
    Title="This is the home page with a tab image.",
    Frame="pageHome",
)

win.add_nb_page(
    Name="pageSearch",
    Notebook="mainNotebook",
    Title="Search",
    Image="gtk-find",
)
win.add_label(
    Name="labelSearch",
    Position=[16, 16],
    Title="This page also has a tab image.",
    Frame="pageSearch",
)

win.add_nb_page(
    Name="pageSettings",
    Notebook="mainNotebook",
    Title="Settings",
    Image="gtk-new",
)
win.add_label(
    Name="labelSettings",
    Position=[16, 16],
    Title="Changing tabs triggers the notebook event.",
    Frame="pageSettings",
)

win.show_and_run()
