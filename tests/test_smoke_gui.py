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


def test_new_window_and_button_smoke(gui_window):
    scope = "Main window"
    win = gui_window(name="smoke_button")
    _passed(scope, "Creation")

    win.add_button(
        Name="button_ok",
        Position=[10, 10],
        Title="_OK",
    )
    _passed(scope, "Button creation")

    button = win.get_widget("button_ok")

    assert isinstance(button, wx.Button)
    _passed(scope, "Button type is wx.Button")
    assert win.exist_object("button_ok") == 1
    _passed(scope, "Button registered in widget map")
    assert button.IsEnabled()
    _passed(scope, "Button starts enabled")
    assert win.main_window is not None and win.main_window.IsShown()
    _passed(scope, "Main window is shown")


def test_button_click_callback_can_be_simulated(gui_window):
    scope = "Button event"
    state = {"clicked": 0}

    def on_click(_event: wx.CommandEvent) -> None:
        state["clicked"] += 1

    win = gui_window(name="button_click")
    win.add_button(
        Name="button_click_me",
        Position=[10, 10],
        Title="Click",
        Function=on_click,
    )
    _passed(scope, "Button with callback created")

    button = win.get_widget("button_click_me")
    click_event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())

    handled = button.GetEventHandler().ProcessEvent(click_event)

    assert handled is True
    _passed(scope, "Synthetic click event was handled")
    assert state["clicked"] == 1
    _passed(scope, "Callback was invoked exactly once")


def test_menu_item_callback_can_be_simulated(gui_window):
    scope = "Menu event"
    state = {"triggered": 0}

    def on_menu(_event: wx.CommandEvent) -> None:
        state["triggered"] += 1

    win = gui_window(name="menu_click")
    win.add_menu_bar(Name="menubar_main")
    win.add_menu(Name="menu_file", Menubar="menubar_main", Title="_File")
    win.add_menu_item(
        Name="menu_item_quit",
        Menu="menu_file",
        Title="_Quit",
        Function=on_menu,
    )
    _passed(scope, "MenuBar/Menu/MenuItem creation")

    menu_item_entry = win.get_object("menu_item_quit")
    menu_event = wx.CommandEvent(wx.EVT_MENU.typeId, int(menu_item_entry.data["id"]))

    handled = win.main_window.GetEventHandler().ProcessEvent(menu_event)

    assert handled is True
    _passed(scope, "Synthetic menu event was handled")
    assert state["triggered"] == 1
    _passed(scope, "Menu callback was invoked exactly once")
