#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/11"

import os
import sys
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
import wx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simplewx import SimpleWx


_TEST_FILE_ORDER: list[str] = [
    "test_smoke_gui.py",
    "test_unit_core.py",
    "test_widget_state_roundtrip.py",
    "test_notebook_regressions.py",
    "test_menu_toolbar_regressions.py",
    "test_data_widget_regressions.py",
    "test_dialog_mocking.py",
]

_TEST_SECTION_HEADERS: dict[str, str] = {
    "test_smoke_gui.py": "Smoke tests for core examples (startup + basic interactions).",
    "test_unit_core.py": "Unit test baseline for core helpers (alias normalization, filter building, art-id mapping, scale-factor calculation).",
    "test_widget_state_roundtrip.py": "Widget-state roundtrip tests (`set_value`/`get_value`) for CheckButton, RadioButton, ComboBox, Slider, SpinButton, ProgressBar.",
    "test_notebook_regressions.py": "Notebook regression tests: page add/remove, current page, icon assignment, event wiring.",
    "test_menu_toolbar_regressions.py": "Menu/toolbar regressions: radio groups, callback bindings.",
    "test_data_widget_regressions.py": "Data-widget tests: ListView/Grid/DataView data updates, cell access, sorting behavior.",
    "test_dialog_mocking.py": "Dialog tests with mocking (`ShowModal`/return codes) instead of native interaction.",
}

_PRINTED_SECTION_HEADERS: set[str] = set()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    order_map = {name: index for index, name in enumerate(_TEST_FILE_ORDER)}
    original_position = {id(item): index for index, item in enumerate(items)}

    def _sort_key(item: pytest.Item) -> tuple[int, str]:
        file_name = Path(str(item.fspath)).name
        order = order_map.get(file_name, len(_TEST_FILE_ORDER))
        return (order, original_position[id(item)])

    items.sort(key=_sort_key)


def pytest_runtest_setup(item: pytest.Item) -> None:
    file_name = Path(str(item.fspath)).name
    header = _TEST_SECTION_HEADERS.get(file_name)
    if header is None or file_name in _PRINTED_SECTION_HEADERS:
        return

    print("", flush=True)
    print(header, flush=True)
    print("-" * len(header), flush=True)
    _PRINTED_SECTION_HEADERS.add(file_name)


def _has_display() -> bool:
    return sys.platform in ("win32", "darwin") or bool(
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    )


def pump_events() -> None:
    app = wx.GetApp()
    if isinstance(app, wx.App):
        app.ProcessPendingEvents()
    wx.YieldIfNeeded()


@pytest.fixture(scope="session")
def gui_runtime() -> Generator[SimpleWx, None, None]:
    if not _has_display():
        pytest.skip("GUI tests require a display server (use xvfb-run on Linux).")

    runtime = SimpleWx()
    yield runtime

    frame = getattr(runtime, "main_window", None)
    if isinstance(frame, wx.Frame):
        frame.Destroy()
        pump_events()


@pytest.fixture()
def gui_window(gui_runtime: SimpleWx) -> Generator[Callable[..., SimpleWx], None, None]:
    def _create(
        name: str = "main",
        title: str = "SimpleWx Test",
        size: tuple[int, int] = (320, 240),
        fixed: int = 1,
    ) -> SimpleWx:
        existing_frame = getattr(gui_runtime, "main_window", None)
        if isinstance(existing_frame, wx.Frame):
            if existing_frame.IsShown():
                existing_frame.Hide()
            existing_frame.Destroy()
            gui_runtime.main_window = None
            gui_runtime.ref = None
            pump_events()

        gui_runtime.new_window(Name=name, Title=title, Size=list(size), Fixed=fixed)
        gui_runtime.show()
        pump_events()
        return gui_runtime

    yield _create

    frame = getattr(gui_runtime, "main_window", None)
    if isinstance(frame, wx.Frame):
        if frame.IsShown():
            frame.Hide()
        frame.Destroy()
        gui_runtime.main_window = None
        gui_runtime.ref = None
        pump_events()
