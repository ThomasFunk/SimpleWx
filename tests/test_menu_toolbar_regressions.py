#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/11"

import wx


_LAST_SCOPE: str | None = None
_STATUS_COLUMN = 72


def _passed(scope: str, check: str) -> None:
    global _LAST_SCOPE
    if _LAST_SCOPE is None:
        print("", flush=True)
    elif _LAST_SCOPE != scope:
        print("", flush=True)
    _LAST_SCOPE = scope
    left = f"{scope}: {check}"
    print(f"{left:<{_STATUS_COLUMN}} [PASSED]", flush=True)


def test_menu_radio_group_regression(gui_window) -> None:
    scope = "Menu radio groups"
    win = gui_window(name="menu_radio_groups")
    win.add_menu_bar(Name="menubar_main")
    win.add_menu(Name="menu_view", Menubar="menubar_main", Title="_View")
    win.add_menu_item(
        Name="menu_mode_basic",
        Menu="menu_view",
        Type="radio",
        Title="_Basic",
        Group="view_mode",
        Active=1,
    )
    win.add_menu_item(
        Name="menu_mode_advanced",
        Menu="menu_view",
        Type="radio",
        Title="_Advanced",
        Group="view_mode",
        Active=0,
    )

    assert win.is_active("menu_mode_basic") == 1
    _passed(scope, "Initial radio item starts active")
    assert win.is_active("menu_mode_advanced") == 0
    _passed(scope, "Sibling radio item starts inactive")
    assert win.is_sensitive("view_mode") == 1
    _passed(scope, "Radio group is registered")

    win.set_value("menu_mode_advanced", "Active", 1)

    assert win.is_active("menu_mode_advanced") == 1
    _passed(scope, "Activating second radio item works")
    assert win.is_active("menu_mode_basic") == 0
    _passed(scope, "Activating second item clears previous one")


def test_menu_callback_binding_regression(gui_window) -> None:
    scope = "Menu callbacks"
    state = {"count": 0}

    def on_menu(_event: wx.CommandEvent) -> None:
        state["count"] += 1

    win = gui_window(name="menu_callbacks")
    win.add_menu_bar(Name="menubar_callbacks")
    win.add_menu(Name="menu_file", Menubar="menubar_callbacks", Title="_File")
    win.add_menu_item(
        Name="menu_item_open",
        Menu="menu_file",
        Title="_Open",
        Function=on_menu,
    )

    menu_item_entry = win.get_object("menu_item_open")
    menu_event = wx.CommandEvent(wx.EVT_MENU.typeId, int(menu_item_entry.data["id"]))
    win.main_window.GetEventHandler().ProcessEvent(menu_event)

    assert state["count"] == 1
    _passed(scope, "Menu callback binding is invoked via EVT_MENU")
    assert wx.EVT_MENU in menu_item_entry.handler
    _passed(scope, "Menu handler metadata is stored")


def test_toolbar_radio_group_regression(gui_window) -> None:
    scope = "Toolbar radio groups"
    win = gui_window(name="toolbar_radio_groups")
    win.add_toolbar(
        Name="toolbar_modes",
        Position=[0, 0],
        Data=[
            {"label": "Select", "icon": "gtk-open", "kind": "radio", "active": 1},
            {"label": "Move", "icon": "gtk-save", "kind": "radio", "active": 0},
        ],
    )

    toolbar_entry = win.get_object("toolbar_modes")
    tools = toolbar_entry.data["tools"]
    first_tool_id = int(tools[0]["id"])
    second_tool_id = int(tools[1]["id"])
    toolbar = win.get_widget("toolbar_modes")

    assert toolbar.GetToolState(first_tool_id) is True
    _passed(scope, "Initial toolbar radio tool starts active")
    assert toolbar.GetToolState(second_tool_id) is False
    _passed(scope, "Sibling toolbar radio tool starts inactive")

    win.set_value("toolbar_modes", "Active", 1)

    assert toolbar_entry.data["lasttool"] == second_tool_id
    _passed(scope, "set_value targets tool by index")
    assert toolbar.GetToolState(second_tool_id) is True
    _passed(scope, "Selected toolbar radio tool becomes active")
    assert tools[1]["active"] == 1
    _passed(scope, "Toolbar metadata tracks active radio tool")


def test_toolbar_callback_binding_regression(gui_window) -> None:
    scope = "Toolbar callbacks"
    state = {"count": 0, "tool_id": None}

    def on_tool(event: wx.CommandEvent) -> None:
        state["count"] += 1
        state["tool_id"] = int(event.GetId())

    win = gui_window(name="toolbar_callbacks")
    win.add_toolbar(
        Name="toolbar_actions",
        Position=[0, 0],
        Data=[
            {"label": "Open", "icon": "gtk-open", "kind": "normal", "tooltip": "Open file"},
            {"label": "Save", "icon": "gtk-save", "kind": "check", "active": 0, "tooltip": "Save file"},
        ],
        Function=on_tool,
    )

    toolbar_entry = win.get_object("toolbar_actions")
    first_tool_id = int(toolbar_entry.data["tools"][0]["id"])
    toolbar = win.get_widget("toolbar_actions")
    tool_event = wx.CommandEvent(wx.EVT_TOOL.typeId, first_tool_id)
    tool_event.SetEventObject(toolbar)

    toolbar.GetEventHandler().ProcessEvent(tool_event)

    assert state["count"] == 1
    _passed(scope, "Toolbar callback binding is invoked via EVT_TOOL")
    assert state["tool_id"] == first_tool_id
    _passed(scope, "Toolbar callback receives the triggering tool id")
    assert toolbar_entry.data["lasttool"] == first_tool_id
    _passed(scope, "Toolbar metadata stores last triggered tool")