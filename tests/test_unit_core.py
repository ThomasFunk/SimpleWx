#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/11"

import wx

from simplewx import SimpleWx


def _unit_passed(check: str) -> None:
    print("", flush=True)
    left = f"Unit core: {check}"
    print(f"{left:<72} [PASSED]", flush=True)


def _new_simplewx_stub() -> SimpleWx:
    return SimpleWx.__new__(SimpleWx)


def test_extend_maps_known_aliases() -> None:
    sw = _new_simplewx_stub()

    assert sw._extend("pos") == "position"
    assert sw._extend("func") == "function"
    assert sw._extend("dtype") == "dialogtype"
    assert sw._extend("gname") == "groupname"
    _unit_passed("_extend maps known aliases")


def test_extend_keeps_unknown_key() -> None:
    sw = _new_simplewx_stub()

    assert sw._extend("customkey") == "customkey"
    _unit_passed("_extend keeps unknown keys")


def test_normalize_lowercases_and_expands_aliases() -> None:
    sw = _new_simplewx_stub()

    normalized = sw._normalize(Name="btn1", Pos=[10, 20], Func="cb", Tip="hint")

    assert normalized["name"] == "btn1"
    assert normalized["position"] == [10, 20]
    assert normalized["function"] == "cb"
    assert normalized["tooltip"] == "hint"
    _unit_passed("_normalize lowercases and expands")


def test_calc_scalefactor_handles_zero_or_negative() -> None:
    sw = _new_simplewx_stub()

    assert sw._calc_scalefactor(0, 12) == 1.0
    assert sw._calc_scalefactor(10, 0) == 1.0
    assert sw._calc_scalefactor(-1, 12) == 1.0
    _unit_passed("_calc_scalefactor handles invalid input")


def test_calc_scalefactor_regular_case() -> None:
    sw = _new_simplewx_stub()

    assert sw._calc_scalefactor(10, 15) == 1.5
    _unit_passed("_calc_scalefactor computes regular case")


def test_build_wx_filter_none_and_string_cases() -> None:
    sw = _new_simplewx_stub()

    assert sw._build_wx_filter(None) == "*.*"
    assert sw._build_wx_filter("*.py") == "*.py"
    assert sw._build_wx_filter("   ") == "*.*"
    _unit_passed("_build_wx_filter handles None/string")


def test_build_wx_filter_list_tuple_cases() -> None:
    sw = _new_simplewx_stub()

    assert sw._build_wx_filter(["Python", "*.py"]) == "Python|*.py"
    assert sw._build_wx_filter([None, "*.txt"]) == "Files (*.txt)|*.txt"
    assert sw._build_wx_filter(["*.md"]) == "*.md"
    assert sw._build_wx_filter([None, None]) == "*.*"
    _unit_passed("_build_wx_filter handles list/tuple")


def test_resolve_art_id_known_and_unknown() -> None:
    sw = _new_simplewx_stub()

    assert sw._resolve_art_id("gtk-open") == wx.ART_FILE_OPEN
    assert sw._resolve_art_id(" GTK-SAVE ") == wx.ART_FILE_SAVE
    assert sw._resolve_art_id("not-existing-icon") == wx.ART_MISSING_IMAGE
    _unit_passed("_resolve_art_id maps known/unknown")
