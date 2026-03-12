#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Standalone message dialogs with modal return value vs non-modal callback.
import wx

from simplewx import SimpleWx as simplewx

# change this to "nonmodal" to see the difference in behavior and API usage
MODE = "modal"  # "modal" or "nonmodal"


def run_modal(window: simplewx) -> None:
    response = window.show_msg_dialog("yesno", "warning", "Standalone modal (returns a result)", Modal=1)

    if response == wx.ID_YES:
        print("Modal: Yes")
    elif response == wx.ID_NO:
        print("Modal: No")
    else:
        print(f"Modal: {response}")


def run_nonmodal(window: simplewx) -> None:
    def on_response(_dialog, response_id) -> None:
        if response_id == wx.ID_YES:
            print("Non-modal callback: Yes")
        elif response_id == wx.ID_NO:
            print("Non-modal callback: No")
        else:
            print(f"Non-modal callback: {response_id}")

        app = wx.GetApp()
        if isinstance(app, wx.App) and app.IsMainLoopRunning():
            app.ExitMainLoop()

    window.add_msg_dialog(
        Name="standalone_nonmodal",
        DType="yesno",
        MType="warning",
        Modal=0,
        RFunc=on_response,
    )
    immediate = window.show_msg_dialog(
        "standalone_nonmodal",
        "Standalone non-modal (returns immediately)",
        "Result comes via callback, not return value.",
    )
    print(f"Non-modal immediate return: {immediate!r}")

    app = wx.GetApp()
    if isinstance(app, wx.App):
        app.MainLoop()


win = simplewx()

if MODE == "nonmodal":
    run_nonmodal(win)
else:
    run_modal(win)
