#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Advanced notebook features like close tabs, icons, and page events.
from simplewx import SimpleWx as simplewx


# Receive page-change events from the notebook.
def on_notebook_page_changed(event):
    notebook = event.GetEventObject()
    page_index = notebook.GetSelection()
    page_title = notebook.GetPageText(page_index) if page_index >= 0 else ""
    print(f"Notebook event: page changed -> index={page_index}, title='{page_title}'")
    event.Skip()


# Create notebook demo with closeable tabs and icons.
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

# Page 1: home tab.
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

# Page 2: search tab.
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

# Page 3: settings tab.
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
