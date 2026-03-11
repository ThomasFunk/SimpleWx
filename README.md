SimpleWx version 0.2.0
=======================

SimpleWx is a Python wrapper around wxPython (the Python binding for wxWidgets)
to support RAD (Rapid Application Development).

It is a direct port of the original Perl module SimpleGtk2: functionality
and formatting conventions are preserved where practical, implemented on
top of Python and the wx toolkit (wxPython).

Most commonly used widgets are already implemented with convenience functions.
At the same time, you can still use native wxPython functionality directly.

<center><span style="color:red"><strong>This is a work in progress!</strong></span></center>

<center><span style="color:red"><strong>Currently not usable because all is untested.</strong></span></center>

<center><span style="color:red"><strong>The complete functionality of SimpleGtk2 is integrated plus missing WxWidget widgets with the help of GitHub Copilot (Auto).</strong></span></center>

<center><span style="color:red"><strong>If all is tested this note will disappear ^^</strong></span></center>

Implemented widgets (current status)
------------------------------------

**Windows**
- Window
- MessageDialog (normal + simple/one-shot)
- Dialog (normal)
- AboutDialog (normal)

**Display Widgets**
- Image
- Label
- Statusbar
- DrawingArea
- ProgressBar
- StatusIcon (perhaps)

**Buttons and Toggles**
- Button
- CheckButton
- RadioButton
- LinkButton
- FontButton
- FileChooserButton

**Numeric/Text Data Entry**
- TextEntry
- ComboBox
- Slider
- SpinButton

**Multiline Text Editor**
- TextView (Plain + RichTextCtrl via Rich=1)

**Tree, List and Icon Grid Widgets**
- TreeView
- ListView
- Grid (Sorting + Editing)
- DataViewCtrl (Sorting + Editing)

**Menus and Toolbar**
- MenuBar
- Menu
- MenuItem
- Toolbar

**Selectors (File/Font/Color)**
- FileChooserDialog (normal + simple/one-shot)
- DirPickerCtrl
- DatePickerCtrl
- TimePickerCtrl
- FontSelectionDialog (normal + simple/one-shot)
- ColorSelectionDialog (normal + simple/one-shot)

**ayout Containers**
- Notebook (Close-Tabs, Images, Events)
- NotebookPage
- SplitterWindow
- Frame
- Separator

**Scrolling**
- Scrollbar

**Printing**
- PrintDialog (normal + simple/one-shot)
- PageSetupDialog (normal + simple/one-shot)
- PrintPreview + Printer + Printout

**Miscellaneous**
- Tooltip


EXAMPLES
--------

Minimal Hello-World example with SimpleWx (Python):

    from simplewx import SimpleWx as simplewx

    def on_click(_event):
        print("Hello SimpleWx (Python)")

    win = simplewx()
    win.new_window(
        Name="main",
        Title="Hello World",
        Size=[300, 200],
    )

    win.add_button(
        Name="button",
        Pos=[20, 40],
        Title="Action",
        Func=on_click,
    )

    win.show_and_run()

Basic examples for a quick start:
- **Windows:**
  - examples/windows_basic.py
- **Buttons & Toggles:**
  - examples/buttons_toggles_basic.py
- **Numeric/Text Entries:**
  - examples/numeric_text_entries_basic.py
- **TreeView:**
  - examples/treeview_basic.py
- **ListView:**
  - examples/listview_basic.py
- **TextView with RichTextCtrl:**
  - examples/textview_richtext.py
- **SplitterWindow (2 panes, draggable split, collapse/expand):**
  - examples/splitter_basic.py
- **Notebook + extensions  (close tabs, images, events):**
  - examples/notebook_extensions.py
- **DirPickerCtrl (directory selection):**
  - examples/dirpicker_ctrl.py
- **print pipeline  (PrintPreview + Printer + Printout):**
  - examples/print_pipeline.py
- **print pipeline with header/footer templates:**
  - examples/print_pipeline_template.py
- **Localization (gettext):**
  - examples/i18n_basic.py.
  - German translation:
    - locale/de/LC_MESSAGES/simplewx_demo.po.
  - Compiled runtime file: 
    - locale/de/LC_MESSAGES/simplewx_demo.mo.

You can rebuild it with:

    msgfmt locale/de/LC_MESSAGES/simplewx_demo.po -o locale/de/LC_MESSAGES/simplewx_demo.mo

Run the example in German:

    LANGUAGE=de_DE ./venv/bin/python examples/i18n_basic.py

Or with an activated venv:

    source venv/bin/activate
    LANGUAGE=de_DE python examples/i18n_basic.py

Short alias-style form:

    from simplewx import SimpleWx as simplewx

    win = simplewx()
    win.new_window(Name="main", Title="Demo", Size=[400, 300])
    win.show_and_run()


INSTALLATION
------------

Create and activate a Python virtual environment, then install dependencies:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install wxPython


DEPENDENCIES
------------

Runtime dependencies:

  - Python 3
  - wxPython (wxWidgets binding)


COPYRIGHT AND LICENCE
---------------------

See LICENSE for licensing information.


BUGS
----

Please send bug reports or suggestions for improvements to <t.funk@web.de>.
