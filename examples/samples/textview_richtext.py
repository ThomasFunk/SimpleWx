#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Plain and rich text modes in TextView, including formatting behavior.
from simplewx import SimpleWx as simplewx


# Build rich-text demo window.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="TextView RichText Demo",
    Size=[760, 480],
)

win.add_label(
    Name="infoLabel",
    Position=[20, 16],
    Title="TextView im RichText-Modus (Rich=1):",
)

win.add_text_view(
    Name="richTextView",
    Position=[20, 42],
    Size=[720, 390],
    Rich=1,
    Wrapped="word",
    Text="""Dies ist ein RichText-basierter TextView.\n\n"
         "Aktueller Modus (get_textview(..., 'Rich')): """,
)

is_rich = win.get_textview("richTextView", "Rich")
# Rewrite content to show detected rich-mode value.
win.set_textview(
    Name="richTextView",
    Text=f"Dies ist ein RichText-basierter TextView.\\n\\nAktueller Modus (get_textview(..., 'Rich')): {is_rich}",
)

win.show_and_run()
