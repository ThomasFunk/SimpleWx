#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Showing a standalone message dialog without creating a full main window.
from simplewx import SimpleWx as simplewx


# Standalone one-shot message dialog (no window setup)
win = simplewx()
response = win.show_msg_dialog("yesno", "warning", "This is a simple standalone")

# Print interpreted result
if response == 5103:  # wx.ID_YES
    print("Yes")
else:
    print("No")
