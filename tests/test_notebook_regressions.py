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


def test_notebook_page_add_remove_regression(gui_window) -> None:
    scope = "Notebook pages"
    win = gui_window(name="nb_pages")
    win.add_notebook(Name="book_pages", Position=[10, 10], Size=[280, 180], CloseTabs=1)

    win.add_nb_page(Name="page_home", Notebook="book_pages", Title="Home")
    win.add_nb_page(Name="page_settings", Notebook="book_pages", Title="Settings")
    win.add_nb_page(Name="page_search", Notebook="book_pages", Title="Search", PositionNumber=1)

    assert win.get_value("book_pages", "Pages") == 3
    _passed(scope, "Page count after inserts")
    assert win.get_value("book_pages", "Number2Name", 0) == "Home"
    _passed(scope, "First page title preserved")
    assert win.get_value("book_pages", "Number2Name", 1) == "Search"
    _passed(scope, "Inserted page lands at requested index")

    assert win.remove_nb_page("page_search") == 1

    assert win.get_value("book_pages", "Pages") == 2
    _passed(scope, "Removing page by name updates count")
    assert win.exist_object("page_search") == 0
    _passed(scope, "Removed page is deleted from widget map")

    assert win.remove_nb_page("book_pages", 0) == 1

    assert win.get_value("book_pages", "Pages") == 1
    _passed(scope, "Removing page by index updates count")
    assert win.get_value("book_pages", "Number2Name", 0) == "Settings"
    _passed(scope, "Remaining page order stays consistent")


def test_notebook_currentpage_roundtrip(gui_window) -> None:
    scope = "Notebook CurrentPage"
    win = gui_window(name="nb_current")
    win.add_notebook(Name="book_current", Position=[10, 10], Size=[280, 180])
    win.add_nb_page(Name="page_one", Notebook="book_current", Title="One")
    win.add_nb_page(Name="page_two", Notebook="book_current", Title="Two")
    win.add_nb_page(Name="page_three", Notebook="book_current", Title="Three")

    assert win.get_value("book_current", "CurrentPage") == 2
    _passed(scope, "Latest added page starts selected")

    win.set_value("book_current", "CurrentPage", 0)

    assert win.get_value("book_current", "CurrentPage") == 0
    _passed(scope, "set_value updates current page")
    assert win.get_widget("book_current").GetSelection() == 0
    _passed(scope, "Native notebook selection matches")
    assert win.get_value("book_current", "Name2Number", "Three") == 2
    _passed(scope, "Title-to-index lookup stays valid")


def test_notebook_icon_assignment_regression(gui_window) -> None:
    scope = "Notebook icons"
    win = gui_window(name="nb_icons")
    win.add_notebook(Name="book_icons", Position=[10, 10], Size=[280, 180])
    win.add_nb_page(Name="page_icon", Notebook="book_icons", Title="Icon", Image="gtk-home")

    assert win.get_value("page_icon", "Image") == "gtk-home"
    _passed(scope, "Initial page image metadata stored")

    notebook = win.get_widget("book_icons")
    assert notebook.GetImageList() is not None
    _passed(scope, "Notebook image list created on demand")
    assert notebook.GetPageImage(0) >= 0
    _passed(scope, "Native tab image index assigned")

    win.set_value("page_icon", "Icon", "gtk-find")

    assert win.get_value("page_icon", "Icon") == "gtk-find"
    _passed(scope, "set_value updates page icon metadata")
    assert notebook.GetPageImage(0) >= 0
    _passed(scope, "Native tab image remains assigned after update")


def test_notebook_event_wiring_regression(gui_window) -> None:
    scope = "Notebook events"
    state = {"count": 0, "selection": None}

    def on_page_changed(event: wx.BookCtrlEvent) -> None:
        notebook = event.GetEventObject()
        state["count"] += 1
        state["selection"] = notebook.GetSelection()
        event.Skip()

    win = gui_window(name="nb_events")
    win.add_notebook(
        Name="book_events",
        Position=[10, 10],
        Size=[280, 180],
        Function=on_page_changed,
    )
    win.add_nb_page(Name="page_alpha", Notebook="book_events", Title="Alpha")
    win.add_nb_page(Name="page_beta", Notebook="book_events", Title="Beta")

    state["count"] = 0
    state["selection"] = None

    notebook = win.get_widget("book_events")
    notebook.SetSelection(1)

    event = wx.BookCtrlEvent(wx.wxEVT_NOTEBOOK_PAGE_CHANGED, notebook.GetId())
    event.SetEventObject(notebook)
    event.SetSelection(1)
    event.SetOldSelection(0)
    notebook.GetEventHandler().ProcessEvent(event)

    assert state["count"] == 1
    _passed(scope, "Synthetic page-changed event reached callback")
    assert state["selection"] == 1
    _passed(scope, "Callback observed the selected page")
    assert win.get_object("book_events").data.get("currentpage") == 1
    _passed(scope, "Internal notebook metadata syncs current page")


def test_notebook_progressbar_page_does_not_shift_geometry(gui_window) -> None:
    scope = "Notebook progressbar"
    win = gui_window(name="nb_progress")
    win.add_notebook(Name="book_progress", Position=[20, 70], Size=[520, 270], Scrollable=0)
    win.add_nb_page(Name="tab_sound", Notebook="book_progress", Title="Sound")
    win.add_progress_bar(
        Name="progress_sound",
        Position=[140, 70],
        Size=[341, 41],
        Steps=100,
        Frame="tab_sound",
    )
    win.set_value("progress_sound", "Value", 24)

    win.add_nb_page(Name="tab_other", Notebook="book_progress", Title="Other")
    win.add_label(Name="label_other", Position=[10, 10], Title="Other", Frame="tab_other")

    notebook = win.get_widget("book_progress")
    initial_pos = tuple(notebook.GetPosition())
    initial_size = tuple(notebook.GetSize())

    notebook.SetSelection(0)
    wx.YieldIfNeeded()
    notebook.SetSelection(1)
    wx.YieldIfNeeded()
    notebook.SetSelection(0)
    wx.YieldIfNeeded()

    assert tuple(notebook.GetPosition()) == initial_pos
    _passed(scope, "Notebook position stays stable on tab switches")
    assert tuple(notebook.GetSize()) == initial_size
    _passed(scope, "Notebook size stays stable on progressbar page")