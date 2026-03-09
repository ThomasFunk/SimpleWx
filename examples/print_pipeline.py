#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Print Pipeline Demo",
    Size=[560, 240],
)

sample_text = """SimpleWx Print Pipeline Demo

This output is sent through a predefined printout
to preview and printer output.

- PrintPreview
- Printer
- Printout
"""

win.add_printout(
    Name="doc1",
    Title="SimpleWx Demo Document",
    Text=sample_text,
    LinesPerPage=45,
)

win.add_printout(
    Name="docTemplate",
    Title="SimpleWx Demo Document",
    Text=sample_text,
    Header="{title} | {date}",
    Footer="Page {page}/{pages}",
    ShowDate=1,
    DateFormat="%d.%m.%Y",
    LinesPerPage=45,
)

win.add_print_dialog(
    Name="printCfg",
    Title="Print",
    MinPage=1,
    MaxPage=20,
    AllPages=1,
    Copies=1,
)

win.add_pagesetup_dialog(
    Name="pageCfg",
    Title="Page setup",
    Orientation="portrait",
)


def on_preview(_event):
    use_template = int(win.get_value("chkTemplate", "active")) == 1
    printout_name = "docTemplate" if use_template else "doc1"
    title = "Preview (Template)" if use_template else "Preview (Standard)"
    win.show_print_preview(printout_name, PrintDialog="printCfg", PageSetup="pageCfg", Title=title)


def on_print(_event):
    use_template = int(win.get_value("chkTemplate", "active")) == 1
    printout_name = "docTemplate" if use_template else "doc1"
    result = win.print_document(printout_name, PrintDialog="printCfg", PageSetup="pageCfg", Prompt=1)
    print(f"Print started: {result}")


def on_page_setup(_event):
    setup = win.show_pagesetup_dialog("pageCfg")
    print(f"PageSetup: {setup}")


def update_mode_label() -> None:
    use_template = int(win.get_value("chkTemplate", "active")) == 1
    mode_text = "Template" if use_template else "Standard"
    win.set_title("lblMode", f"Active print mode: {mode_text}")


def on_toggle_template(_event):
    update_mode_label()


win.add_button(
    Name="btnPageSetup",
    Position=[20, 40],
    Title="Page Setup",
    Function=on_page_setup,
)

win.add_button(
    Name="btnPreview",
    Position=[150, 40],
    Title="Print Preview",
    Function=on_preview,
)

win.add_button(
    Name="btnPrint",
    Position=[300, 40],
    Title="Print",
    Function=on_print,
)

win.add_check_button(
    Name="chkTemplate",
    Position=[20, 90],
    Title="Use template header/footer",
    Active=0,
    Function=on_toggle_template,
)

win.add_label(
    Name="lblMode",
    Position=[20, 125],
    Title="Active print mode: Standard",
)

update_mode_label()

win.show_and_run()
