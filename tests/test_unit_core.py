#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/21"

import wx
import simplewx as simplewx_module

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


def test_enable_nsd_starts_thread_and_tracks_socket_path() -> None:
    original_thread_class = simplewx_module._NSDClientThread
    created: dict[str, object] = {}

    class FakeNSDThread:
        def __init__(self, socket_path: str, callback):
            created["socket_path"] = socket_path
            created["callback"] = callback
            created["started"] = False
            created["stopped"] = False

        def start(self) -> None:
            created["started"] = True

        def stop(self) -> None:
            created["stopped"] = True

        def send(self, _msg: dict) -> None:
            pass

    try:
        simplewx_module._NSDClientThread = FakeNSDThread  # type: ignore[assignment]
        sw = _new_simplewx_stub()
        sw._nsd_thread = None
        sw._nsd_socket_path = "/tmp/nsd.sock"

        callback = lambda _msg: None
        sw.enable_nsd(callback, socket_path="/tmp/custom_nsd.sock")

        assert created["socket_path"] == "/tmp/custom_nsd.sock"
        assert created["callback"] is callback
        assert created["started"] is True
        assert sw._nsd_socket_path == "/tmp/custom_nsd.sock"
        _unit_passed("enable_nsd starts thread and stores socket path")
    finally:
        simplewx_module._NSDClientThread = original_thread_class  # type: ignore[assignment]


def test_nsd_send_uses_running_nsd_thread_and_payload_shape() -> None:
    sw = _new_simplewx_stub()
    sent_messages: list[dict] = []

    class FakeThread:
        def send(self, msg: dict) -> None:
            sent_messages.append(msg)

    sw._nsd_thread = FakeThread()
    sw._nsd_socket_path = "/tmp/nsd.sock"
    sw.app_name = "demo_gui"

    sw.nsd_send("show_notification", {"title": "Hello", "message": "World"}, msg_type="command")

    assert len(sent_messages) == 1
    assert sent_messages[0] == {
        "src": "demo_gui",
        "type": "command",
        "action": "show_notification",
        "payload": {"title": "Hello", "message": "World"},
    }
    _unit_passed("nsd_send uses active thread and keeps nsd message schema")


def test_nsd_send_without_enable_uses_send_once_with_socket_path() -> None:
    original_send_once = simplewx_module._NSDClientThread.send_once
    calls: list[tuple[str, dict]] = []

    def fake_send_once(socket_path: str, msg_dict: dict) -> None:
        calls.append((socket_path, msg_dict))

    try:
        simplewx_module._NSDClientThread.send_once = staticmethod(fake_send_once)

        sw = _new_simplewx_stub()
        sw._nsd_thread = None
        sw._nsd_socket_path = "/tmp/nsd-custom.sock"

        sw.nsd_send("mounted", {"device": "/dev/sdb1"}, msg_type="event")

        assert len(calls) == 1
        socket_path, msg = calls[0]
        assert socket_path == "/tmp/nsd-custom.sock"
        assert msg["src"] == "simplewx_app"
        assert msg["type"] == "event"
        assert msg["action"] == "mounted"
        assert msg["payload"] == {"device": "/dev/sdb1"}
        _unit_passed("nsd_send works without enable_nsd via send_once")
    finally:
        simplewx_module._NSDClientThread.send_once = original_send_once
