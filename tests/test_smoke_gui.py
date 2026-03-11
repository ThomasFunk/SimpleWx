import wx


def test_new_window_and_button_smoke(gui_window):
    win = gui_window(name="smoke_button")

    win.add_button(
        Name="button_ok",
        Position=[10, 10],
        Title="_OK",
    )

    button = win.get_widget("button_ok")

    assert isinstance(button, wx.Button)
    assert win.exist_object("button_ok") == 1
    assert button.IsEnabled()
    assert win.main_window is not None and win.main_window.IsShown()


def test_button_click_callback_can_be_simulated(gui_window):
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

    button = win.get_widget("button_click_me")
    click_event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())

    handled = button.GetEventHandler().ProcessEvent(click_event)

    assert handled is True
    assert state["clicked"] == 1


def test_menu_item_callback_can_be_simulated(gui_window):
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

    menu_item_entry = win.get_object("menu_item_quit")
    menu_event = wx.CommandEvent(wx.EVT_MENU.typeId, int(menu_item_entry.data["id"]))

    handled = win.main_window.GetEventHandler().ProcessEvent(menu_event)

    assert handled is True
    assert state["triggered"] == 1
