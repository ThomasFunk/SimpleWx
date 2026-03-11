#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/11"

import pytest
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


def test_check_button_active_roundtrip(gui_window) -> None:
    scope = "CheckButton"
    win = gui_window(name="roundtrip_check")
    win.add_check_button(Name="check_enabled", Position=[10, 10], Title="Enabled", Active=0)

    assert win.get_value("check_enabled", "Active") == 0
    _passed(scope, "Initial active state read")

    win.set_value("check_enabled", "Active", 1)

    assert win.get_value("check_enabled", "Active") == 1
    _passed(scope, "set_value updates active state")
    assert win.get_widget("check_enabled").GetValue() is True
    _passed(scope, "Native widget reflects active state")


def test_radio_button_active_roundtrip(gui_window) -> None:
    scope = "RadioButton"
    win = gui_window(name="roundtrip_radio")
    win.add_radio_button(Name="radio_low", Position=[10, 10], Title="Low", Group="prio", Active=1)
    win.add_radio_button(Name="radio_high", Position=[10, 35], Title="High", Group="prio", Active=0)

    assert win.get_value("radio_low", "Active") == 1
    _passed(scope, "Initial active state read")

    win.set_value("radio_high", "Active", 1)

    assert win.get_value("radio_high", "Active") == 1
    _passed(scope, "set_value activates target radio")
    assert win.get_value("radio_low", "Active") == 0
    _passed(scope, "Group state updates previous radio")


def test_combo_box_active_roundtrip(gui_window) -> None:
    scope = "ComboBox"
    win = gui_window(name="roundtrip_combo")
    win.add_combo_box(
        Name="combo_resolution",
        Position=[10, 10],
        Data=["800x600", "1280x720", "1920x1080"],
        Start=0,
    )

    assert win.get_value("combo_resolution", "Active") == 0
    _passed(scope, "Initial selection index read")

    win.set_value("combo_resolution", "Active", 2)

    assert win.get_value("combo_resolution", "Active") == 2
    _passed(scope, "set_value updates selection index")
    assert win.get_widget("combo_resolution").GetStringSelection() == "1920x1080"
    _passed(scope, "Native widget reflects selected item")


def test_slider_state_roundtrip(gui_window) -> None:
    scope = "Slider"
    win = gui_window(name="roundtrip_slider")
    win.add_slider(
        Name="slider_volume",
        Position=[10, 10],
        Orientation="horizontal",
        Start=10,
        Minimum=0,
        Maximum=100,
        Step=5,
    )

    assert win.get_value("slider_volume", "Active") == 10
    _passed(scope, "Initial value read")

    win.set_values("slider_volume", {"Minimum": 10, "Maximum": 90, "Step": 10, "Active": 40})

    assert win.get_value("slider_volume", "Minimum") == 10
    _passed(scope, "Minimum roundtrip")
    assert win.get_value("slider_volume", "Maximum") == 90
    _passed(scope, "Maximum roundtrip")
    assert win.get_value("slider_volume", "Step") == 10
    _passed(scope, "Step roundtrip")
    assert win.get_value("slider_volume", "Active") == 40
    _passed(scope, "Active value roundtrip")
    assert win.get_widget("slider_volume").GetValue() == 40
    _passed(scope, "Native widget reflects slider value")


def test_spin_button_state_roundtrip(gui_window) -> None:
    scope = "SpinButton"
    win = gui_window(name="roundtrip_spin")
    win.add_spin_button(
        Name="spin_zoom",
        Position=[10, 10],
        Start=1.5,
        Minimum=0.5,
        Maximum=5.0,
        Step=0.5,
        Digits=1,
        Align="right",
    )

    assert win.get_value("spin_zoom", "Active") == pytest.approx(1.5)
    _passed(scope, "Initial value read")

    win.set_values("spin_zoom", {"Minimum": 1.0, "Maximum": 4.0, "Step": 0.25, "Active": 3.5})

    assert win.get_value("spin_zoom", "Minimum") == pytest.approx(1.0)
    _passed(scope, "Minimum roundtrip")
    assert win.get_value("spin_zoom", "Maximum") == pytest.approx(4.0)
    _passed(scope, "Maximum roundtrip")
    assert win.get_value("spin_zoom", "Step") == pytest.approx(0.25)
    _passed(scope, "Step roundtrip")
    assert win.get_value("spin_zoom", "Active") == pytest.approx(3.5)
    _passed(scope, "Active value roundtrip")
    assert win.get_value("spin_zoom", "Align") == "right"
    _passed(scope, "Alignment metadata preserved")
    assert win.get_widget("spin_zoom").GetValue() == pytest.approx(3.5)
    _passed(scope, "Native widget reflects spin value")


def test_progress_bar_state_roundtrip(gui_window) -> None:
    scope = "ProgressBar"
    win = gui_window(name="roundtrip_progress")
    win.add_progress_bar(
        Name="progress_upload",
        Position=[10, 10],
        Size=[180, 18],
        Mode="percent",
        Steps=10,
    )

    assert win.get_value("progress_upload", "Value") == 0
    _passed(scope, "Initial progress value read")

    win.set_values("progress_upload", {"Steps": 8, "Value": 5})

    assert win.get_value("progress_upload", "Steps") == 8
    _passed(scope, "Steps roundtrip")
    assert win.get_value("progress_upload", "Value") == 5
    _passed(scope, "Value roundtrip")
    assert win.get_value("progress_upload", "Fraction") == pytest.approx(0.625)
    _passed(scope, "Fraction derived from value/steps")

    win.set_value("progress_upload", "Fraction", 0.25)

    assert win.get_value("progress_upload", "Value") == 2
    _passed(scope, "Fraction updates stored value")
    assert win.get_widget("progress_upload").GetValue() == 2
    _passed(scope, "Native widget reflects gauge value")