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


def test_show_dialog_uses_mocked_showmodal_return_code(gui_window, monkeypatch) -> None:
    scope = "Dialog mock"
    win = gui_window(name="dialog_modal")
    win.add_dialog(Name="dlg_generic", Title="Generic", Modal=1)

    monkeypatch.setattr(wx.Dialog, "ShowModal", lambda self: wx.ID_CANCEL)

    result = win.show_dialog("dlg_generic")

    assert result == wx.ID_CANCEL
    _passed(scope, "Generic dialog returns mocked ShowModal code")


def test_show_msg_dialog_uses_mocked_showmodal_return_code(gui_window, monkeypatch) -> None:
    scope = "MessageDialog mock"
    win = gui_window(name="msg_modal")
    win.add_msg_dialog(Name="msg_yesno", Modal=1, DType="yesno", MType="question")

    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: wx.ID_YES)

    result = win.show_msg_dialog("msg_yesno", "Proceed?")

    assert result == wx.ID_YES
    _passed(scope, "Message dialog returns mocked ShowModal code")


def test_show_msg_dialog_callback_mode_keeps_parent_enabled(gui_window, monkeypatch) -> None:
    scope = "MessageDialog mock"
    callback_state: dict[str, int | None] = {"response": None}

    def on_response(_dialog, response_id) -> None:
        callback_state["response"] = int(response_id)

    class _FakeDestroyEvent:
        def Skip(self) -> None:
            return None

    class _FakeButtonEvent:
        def __init__(self, button_id: int):
            self._button_id = button_id

        def GetId(self) -> int:
            return self._button_id

    class _FakeMessageDialog:
        last_instance = None

        def __init__(self, parent, _message, _title, _style):
            self.parent = parent
            self._bindings: list[tuple[object, object, int | None]] = []
            self.destroyed = False
            self.extended_message = ""
            self.transient_parent = None
            type(self).last_instance = self

        def SetTransientFor(self, parent) -> None:
            self.transient_parent = parent

        def SetExtendedMessage(self, message: str) -> None:
            self.extended_message = message

        def Show(self) -> bool:
            return True

        def Bind(self, event, handler, id=None) -> None:
            self._bindings.append((event, handler, id))

        def Destroy(self) -> None:
            if self.destroyed:
                return None
            self.destroyed = True
            for event, handler, _bound_id in list(self._bindings):
                if event == wx.EVT_WINDOW_DESTROY:
                    handler(_FakeDestroyEvent())
            return None

        def click(self, button_id: int) -> None:
            for event, handler, bound_id in list(self._bindings):
                if event == wx.EVT_BUTTON and (bound_id is None or int(bound_id) == int(button_id)):
                    handler(_FakeButtonEvent(button_id))

    win = gui_window(name="msg_modeless_parent_lock")
    win.add_msg_dialog(Name="msg_async", Modal=0, DType="yesno", MType="question", RFunc=on_response)

    monkeypatch.setattr(wx, "MessageDialog", _FakeMessageDialog)

    assert win.ref is not None
    assert win.ref.IsEnabled()

    result = win.show_msg_dialog("msg_async", "Proceed?", "Parent should stay disabled.")

    assert result is None
    _passed(scope, "Callback-based message dialog returns None")
    assert win.ref.IsEnabled()
    _passed(scope, "Callback-based message dialog keeps the parent window enabled")

    dialog = _FakeMessageDialog.last_instance
    assert dialog is not None
    dialog.click(wx.ID_YES)

    assert callback_state["response"] == wx.ID_YES
    _passed(scope, "Callback-based message dialog forwards the response id")
    assert win.ref.IsEnabled()
    _passed(scope, "Parent window remains enabled after callback dialog closes")


def test_show_msg_dialog_one_shot_modal_override_keeps_parent_enabled(gui_window, monkeypatch) -> None:
    scope = "MessageDialog mock"

    class _FakeMessageDialog:
        show_modal_calls = 0

        def __init__(self, _parent, _message, _title, _style):
            return None

        def ShowModal(self) -> int:
            type(self).show_modal_calls += 1
            return wx.ID_YES

        def Show(self) -> bool:
            return True

        def Destroy(self) -> None:
            return None

        def Bind(self, _event, _handler, id=None) -> None:
            return None

    win = gui_window(name="msg_one_shot_non_modal")
    monkeypatch.setattr(wx, "MessageDialog", _FakeMessageDialog)

    assert win.ref is not None
    assert win.ref.IsEnabled()

    result = win.show_msg_dialog("yesno", "warning", "One-shot non-modal", Modal=0)

    assert result is None
    _passed(scope, "One-shot message dialog returns None when Modal=0")
    assert win.ref.IsEnabled()
    _passed(scope, "One-shot message dialog keeps parent enabled when Modal=0")


def test_show_msg_dialog_one_shot_defaults_to_non_modal(gui_window, monkeypatch) -> None:
    scope = "MessageDialog mock"

    class _FakeMessageDialog:
        show_modal_calls = 0

        def __init__(self, _parent, _message, _title, _style):
            return None

        def ShowModal(self) -> int:
            type(self).show_modal_calls += 1
            return wx.ID_YES

        def Show(self) -> bool:
            return True

        def Destroy(self) -> None:
            return None

        def Bind(self, _event, _handler, id=None) -> None:
            return None

    win = gui_window(name="msg_one_shot_default_non_modal")
    monkeypatch.setattr(wx, "MessageDialog", _FakeMessageDialog)

    assert win.ref is not None
    assert win.ref.IsEnabled()

    result = win.show_msg_dialog("yesno", "warning", "One-shot default non-modal")

    assert result is None
    _passed(scope, "One-shot message dialog defaults to non-modal return behavior")
    assert _FakeMessageDialog.show_modal_calls == 0
    _passed(scope, "One-shot message dialog default does not call ShowModal")


def test_show_msg_dialog_one_shot_modal_override_still_supports_modal(gui_window, monkeypatch) -> None:
    scope = "MessageDialog mock"

    class _FakeMessageDialog:
        show_modal_calls = 0

        def __init__(self, _parent, _message, _title, _style):
            return None

        def ShowModal(self) -> int:
            type(self).show_modal_calls += 1
            return wx.ID_YES

        def Show(self) -> bool:
            return True

        def Destroy(self) -> None:
            return None

        def Bind(self, _event, _handler, id=None) -> None:
            return None

    win = gui_window(name="msg_one_shot_force_modal")
    monkeypatch.setattr(wx, "MessageDialog", _FakeMessageDialog)

    result = win.show_msg_dialog("yesno", "warning", "One-shot forced modal", Modal=1)

    assert result == wx.ID_YES
    _passed(scope, "One-shot message dialog returns modal code when Modal=1")
    assert _FakeMessageDialog.show_modal_calls == 1
    _passed(scope, "One-shot message dialog calls ShowModal when Modal=1")


def test_show_filechooser_dialog_with_mocked_showmodal_and_path(gui_window, monkeypatch) -> None:
    scope = "FileDialog mock"
    callback_state: dict[str, str | None] = {"path": None}

    def on_file_selected(_dialog, selected_path) -> None:
        callback_state["path"] = selected_path

    win = gui_window(name="file_dialog")
    win.add_filechooser_dialog(
        Name="file_open",
        Action="open",
        Title="Open file",
        RFunc=on_file_selected,
    )

    monkeypatch.setattr(wx.FileDialog, "ShowModal", lambda self: wx.ID_OK)
    monkeypatch.setattr(wx.FileDialog, "GetPath", lambda self: "/tmp/mock-selected.txt")

    result = win.show_filechooser_dialog("file_open")

    assert result is None
    _passed(scope, "File chooser uses callback mode for predefined dialog")
    assert callback_state["path"] == "/tmp/mock-selected.txt"
    _passed(scope, "Callback receives mocked selected path")


def test_show_print_dialog_with_mocked_dialog_payload(gui_window, monkeypatch) -> None:
    scope = "PrintDialog mock"
    win = gui_window(name="print_dialog")
    win.add_print_dialog(
        Name="print_cfg",
        MinPage=1,
        MaxPage=12,
        FromPage=2,
        ToPage=5,
        Copies=3,
        Modal=1,
    )

    class _FakePrintDialogData:
        def GetMinPage(self):
            return 1

        def GetMaxPage(self):
            return 12

        def GetFromPage(self):
            return 2

        def GetToPage(self):
            return 5

        def GetAllPages(self):
            return False

        def GetSelection(self):
            return False

        def GetPrintToFile(self):
            return False

        def GetNoCopies(self):
            return 3

    class _FakePrintDialog:
        def __init__(self, _parent, _print_data):
            self._title = ""

        def SetTitle(self, title):
            self._title = title

        def ShowModal(self):
            return wx.ID_OK

        def GetPrintDialogData(self):
            return _FakePrintDialogData()

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "PrintDialog", _FakePrintDialog)

    result = win.show_print_dialog("print_cfg")

    assert isinstance(result, dict)
    assert result["frompage"] == 2
    _passed(scope, "Print dialog returns mocked payload")
    assert result["topage"] == 5
    _passed(scope, "Print dialog payload preserves page range")
    assert result["copies"] == 3
    _passed(scope, "Print dialog payload preserves copies")


def test_show_pagesetup_dialog_with_mocked_dialog_payload(gui_window, monkeypatch) -> None:
    scope = "PageSetupDialog mock"
    win = gui_window(name="pagesetup_dialog")
    win.add_pagesetup_dialog(
        Name="pset_cfg",
        Orientation="portrait",
        MarginTopLeft=[10, 10],
        MarginBottomRight=[20, 20],
        Modal=1,
    )

    class _FakePrintData:
        def GetPaperId(self):
            return int(wx.PAPER_A4)

        def GetOrientation(self):
            return wx.LANDSCAPE

    class _FakePageSetupData:
        def GetPrintData(self):
            return _FakePrintData()

        def GetMarginTopLeft(self):
            return wx.Point(15, 25)

        def GetMarginBottomRight(self):
            return wx.Point(35, 45)

    class _FakePageSetupDialog:
        def __init__(self, _parent, _page_setup_data):
            self._title = ""

        def SetTitle(self, title):
            self._title = title

        def ShowModal(self):
            return wx.ID_OK

        def GetPageSetupData(self):
            return _FakePageSetupData()

        def Destroy(self):
            return None

    monkeypatch.setattr(wx, "PageSetupDialog", _FakePageSetupDialog)

    result = win.show_pagesetup_dialog("pset_cfg")

    assert isinstance(result, dict)
    assert result["orientation"] == "landscape"
    _passed(scope, "Page setup dialog returns mocked orientation")
    assert result["margintopleft"] == [15, 25]
    _passed(scope, "Page setup dialog returns mocked top-left margin")
    assert result["marginbottomright"] == [35, 45]
    _passed(scope, "Page setup dialog returns mocked bottom-right margin")