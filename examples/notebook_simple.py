#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/11"
# What this example demonstrates:
# Basic notebook creation with multiple pages and simple navigation.
from simplewx import SimpleWx as simplewx


# Create top-level window
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Notebook simple",
    Size=[450, 400],
    Fixed=0,
    ThemeIcon="emblem-dropbox-syncing",
)

# Create notebook
win.add_notebook(
    Name="NB1",
    Position=[10, 10],
    Size=[400, 300],
    Tabs="top",
    Scrollable=1,
    Popup=1,
)

# Add pages in defined order
win.add_nb_page(
    Name="NB_page1",
    PositionNumber=0,
    Title="One",
    Notebook="NB1",
    Tooltip="Page 1",
)

# Deactivate first page
#win.set_sensitive("NB_page1", 0)

win.add_nb_page(
    Name="NB_page2",
    PositionNumber=1,
    Title="Two",
    Notebook="NB1",
    Tooltip="Page 2",
)

# Change title of second page
win.set_title("NB_page2", "Two2One")

win.add_nb_page(Name="NB_page3", PositionNumber=3, Title="Three", Notebook="NB1", Tooltip="Page 3 on 3")
win.add_nb_page(Name="NB_page4", PositionNumber=2, Title="Four", Notebook="NB1", Tooltip="Page 4 on 2")
win.add_nb_page(Name="NB_page5", PositionNumber=4, Title="Five", Notebook="NB1", Tooltip="Page 5 on 4")
win.add_nb_page(Name="NB_page6", PositionNumber=5, Title="Six", Notebook="NB1", Tooltip="Page 6 on 5")
win.add_nb_page(Name="NB_page7", PositionNumber=6, Title="Seven", Notebook="NB1", Tooltip="Page 7 on 6")

win.add_button(
    Name="Button",
    Position=[10, 30],
    Size=[80, 40],
    Title="_Jup",
    Tooltip="button to jump to page 4",
    Frame="NB_page1",
)

# Button to remove a notebook page
def remove_current_page(_event):
    notebook_obj = win.get_object("NB1")
    notebook_ref = notebook_obj.ref
    if notebook_ref is None:
        return

    current_index = int(notebook_ref.GetSelection())
    if current_index < 0:
        return

    win.remove_nb_page("NB1", current_index)


win.add_button(
    Name="removeButton",
    Position=[310, 345],
    Title="_Remove",
    Tooltip="Click removes current page",
    Function=remove_current_page,
)

# Show window and start event loop
win.show_and_run()
