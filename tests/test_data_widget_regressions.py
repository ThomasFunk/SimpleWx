#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/11"


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


def test_listview_data_update_and_cell_access(gui_window) -> None:
    scope = "ListView"
    win = gui_window(name="data_listview")
    win.add_listview(
        Name="lv_users",
        Position=[10, 10],
        Size=[300, 160],
        Headers=["Name", "Age"],
        Data=[["Anna", "31"], ["Ben", "27"]],
    )

    assert win.get_value("lv_users", "Path", 0) == ["Anna", "31"]
    _passed(scope, "Initial row path access works")
    assert win.get_value("lv_users", "Cell", [1, 1]) == "27"
    _passed(scope, "Initial cell access works")

    win.set_value("lv_users", "Data", [["Clara", "29"], ["Dylan", "34"]])

    assert win.get_value("lv_users", "Path", 0) == ["Clara", "29"]
    _passed(scope, "Data update replaces rows")
    assert win.get_value("lv_users", "Cell", [1, 0]) == "Dylan"
    _passed(scope, "Cell access reflects updated data")


def test_grid_data_update_cell_access_and_sorting(gui_window) -> None:
    scope = "Grid"
    win = gui_window(name="data_grid")
    win.add_grid(
        Name="grid_scores",
        Position=[10, 10],
        Size=[340, 180],
        Headers=["Name", "Score"],
        Data=[["Eve", "42"], ["Bob", "7"], ["Cara", "15"]],
        Sortable=1,
    )

    assert win.get_value("grid_scores", "Cell", [0, 1]) == "42"
    _passed(scope, "Initial cell access works")

    win.set_value("grid_scores", "Cell", [1, 1, "9"])

    assert win.get_value("grid_scores", "Cell", [1, 1]) == "9"
    _passed(scope, "Cell update is persisted")

    win.set_values("grid_scores", {"SortColumn": 1, "SortAscending": 1})

    assert win.get_value("grid_scores", "SortColumn") == 1
    _passed(scope, "Sort column metadata stored")
    assert win.get_value("grid_scores", "SortAscending") == 1
    _passed(scope, "Sort direction metadata stored")
    assert win.get_value("grid_scores", "Cell", [0, 0]) == "Bob"
    _passed(scope, "Ascending numeric sort applied")

    win.set_values("grid_scores", {"SortColumn": 1, "SortAscending": 0})

    assert win.get_value("grid_scores", "SortAscending") == 0
    _passed(scope, "Sort direction toggles to descending")
    assert win.get_value("grid_scores", "Cell", [0, 0]) == "Eve"
    _passed(scope, "Descending numeric sort applied")


def test_dataview_data_update_cell_access_and_sortable_metadata(gui_window) -> None:
    scope = "DataView"
    win = gui_window(name="data_dataview")
    win.add_dataview(
        Name="dv_items",
        Position=[10, 10],
        Size=[340, 180],
        Headers=["Item", "Qty"],
        Data=[["Pencil", "12"], ["Paper", "50"]],
        Sortable=1,
    )

    assert win.get_value("dv_items", "Cell", [0, 0]) == "Pencil"
    _passed(scope, "Initial cell access works")
    assert win.get_value("dv_items", "Sortable") == 1
    _passed(scope, "Initial sortable flag is set")

    win.set_values(
        "dv_items",
        {
            "Data": [["Marker", "8"], ["Folder", "3"]],
            "Cell": [1, 1, "4"],
            "Sortable": 0,
        },
    )

    assert win.get_value("dv_items", "Cell", [0, 0]) == "Marker"
    _passed(scope, "Data update replaces rows")
    assert win.get_value("dv_items", "Cell", [1, 1]) == "4"
    _passed(scope, "Cell update is persisted")
    assert win.get_value("dv_items", "Sortable") == 0
    _passed(scope, "Sortable metadata can be updated")