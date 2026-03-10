#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Creating menus, menu items, and handling menu-driven actions.
from pathlib import Path
from simplewx import SimpleWx as simplewx


# Create top-level window
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Menubar Simple",
    Size=[400, 200],
)

# Create menu bar
win.add_menu_bar(
    Name="menubar1",
    Position=[0, 0],
)

# Edit menu
win.add_menu(
    Name="menu_edit",
    Title="_Edit",
    Menubar="menubar1",
)

# Tearoff-like separator entry (compatibility)
win.add_menu_item(
    Name="menu_item_toff",
    Type="tearoff",
    Menu="menu_edit",
    Tooltip="This is a tearoff",
)

# Save item with stock icon
win.add_menu_item(
    Name="menu_item_save",
    Icon="gtk-save",
    Menu="menu_edit",
    Tooltip="This is the Save entry",
)

# Separator
win.add_menu_item(
    Name="menu_item_sep1",
    Type="separator",
    Menu="menu_edit",
)

# Item with custom image icon
icon_path = str((Path(__file__).resolve().parent / "1.png"))
win.add_menu_item(
    Name="menu_item_icon",
    Title="Burger",
    Icon=icon_path,
    Menu="menu_edit",
    Tooltip="This is the Burger",
)

# Check item
win.add_menu_item(
    Name="menu_item_check",
    Type="check",
    Title="Check em",
    Menu="menu_edit",
    Tooltip="This is a check menu",
    Active=1,
)

# Radio group items
win.add_menu_item(
    Name="menu_item_radio1",
    Type="radio",
    Title="First",
    Menu="menu_edit",
    Tooltip="First radio",
    Group="Yeah",
    Active=1,
)
win.add_menu_item(
    Name="menu_item_radio2",
    Type="radio",
    Title="Second",
    Menu="menu_edit",
    Tooltip="Second radio",
    Group="Yeah",
)
win.add_menu_item(
    Name="menu_item_radio3",
    Type="radio",
    Title="_Third",
    Menu="menu_edit",
    Tooltip="Third radio",
    Group="Yeah",
)

# Help menu aligned right
win.add_menu(
    Name="menu_help",
    Title="_Help",
    Justify="right",
    Menubar="menubar1",
)

# Disabled About item
win.add_menu_item(
    Name="menu_item_about",
    Icon="gtk-help",
    Menu="menu_help",
    Tooltip="This is the About dialog",
    Sensitive=0,
)

# Show window and start event loop
win.show_and_run()
