#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Modal and non-modal message dialogs with response callbacks.
from simplewx import SimpleWx as simplewx


# Callback for non-modal dialog response
def non_modal(_dialog, response_id):
    if response_id == 5103:  # wx.ID_YES
        print("Yes")
    else:
        print("No")


# Open predefined modal dialog and print result
def modal(window):
    response = window.show_msg_dialog("diag1", "Message Type", "Warning")
    if response == 5100:  # wx.ID_OK
        print("Ok")
    else:
        print("Cancel")


# Open one-shot dialog and print Yes/No result
def simple(window):
    response = window.show_msg_dialog("yesno", "warning", "This is a simple one")
    if response == 5103:  # wx.ID_YES
        print("Yes")
    else:
        print("No")


# Create top-level window
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Message Test",
    Size=[220, 190],
)

# Button + predefined modal message dialog
win.add_button(
    Name="Button1",
    Position=[60, 10],
    Size=[90, 40],
    Title="_Modal",
    Function=lambda _event: modal(win),
)

win.add_msg_dialog(
    Name="diag1",
    DType="okcancel",
    MType="warning",
    Icon="gtk-quit",
)

# Message text used for non-modal example
first_msg = "Message Type"
second_msg = "Info box."

# Button + predefined non-modal message dialog
win.add_button(
    Name="Button2",
    Position=[60, 60],
    Size=[90, 40],
    Title="_NonModal",
    Function=lambda _event: win.show_msg_dialog("diag2", first_msg, second_msg),
)

win.add_msg_dialog(
    Name="diag2",
    DType="yesno",
    MType="info",
    RFunc=non_modal,
    Modal=0,
)

# Button + one-shot message dialog helper
win.add_button(
    Name="Button3",
    Position=[60, 110],
    Size=[90, 40],
    Title="_Simple",
    Function=lambda _event: simple(win),
)

# Show window and start event loop
win.show_and_run()
