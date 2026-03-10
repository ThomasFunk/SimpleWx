#!/usr/bin/env python3
author = 'Thomas Funk'
coauthors = 'Github Copilot'
date = "2026/03/10"
# What this example demonstrates:
# Print headers and footers using template placeholders in the print pipeline.
from simplewx import SimpleWx as simplewx


# Create a focused demo for template-based print output.
win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Print Pipeline Template Demo",
    Size=[620, 250],
)

body_text = """Simple document for the template variant.

Header and footer are generated using placeholders:
- {title}
- {date}
- {page}
- {pages}
"""

# Define printout with dynamic header/footer placeholders.
win.add_printout(
    Name="docTemplate",
    Title="SimpleWx Report",
    Text=body_text,
    Header="{title}  |  {date}",
    Footer="Page {page}/{pages}",
    ShowDate=1,
    DateFormat="%d.%m.%Y",
    LinesPerPage=40,
)

win.add_print_dialog(Name="printCfg", Title="Print", MinPage=1, MaxPage=20)
win.add_pagesetup_dialog(Name="pageCfg", Title="Page setup", Orientation="portrait")


def on_preview(_event):
    # Open preview for the template printout.
    win.show_print_preview("docTemplate", PrintDialog="printCfg", PageSetup="pageCfg", Title="Template Preview")


def on_print(_event):
    # Send template printout to printer with prompt dialog.
    result = win.print_document("docTemplate", PrintDialog="printCfg", PageSetup="pageCfg", Prompt=1)
    print(f"Print started: {result}")


win.add_button(Name="btnPreview", Position=[20, 40], Title="Template Preview", Function=on_preview)
win.add_button(Name="btnPrint", Position=[200, 40], Title="Template Print", Function=on_print)

win.show_and_run()
