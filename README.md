SimpleWx version 0.4.1
=======================

SimpleWx is a Python wrapper around wxPython (the Python binding for wxWidgets)
to support RAD (Rapid Application Development).

It is a direct port of the original Perl module SimpleGtk2: functionality
and formatting conventions are preserved where practical, implemented on
top of Python and the wx toolkit (wxPython).

Most commonly used widgets are already implemented with convenience functions.
At the same time, you can still use native wxPython functionality directly.

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

**Layout Containers**
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
  - examples/samples/windows_basic.py
- **Buttons & Toggles:**
  - examples/samples/buttons_toggles_basic.py
- **Numeric/Text Entries:**
  - examples/samples/numeric_text_entries_basic.py
- **TreeView:**
  - examples/samples/treeview_basic.py
- **ListView:**
  - examples/samples/listview_basic.py
- **TextView with RichTextCtrl:**
  - examples/samples/textview_richtext.py
- **SplitterWindow (2 panes, draggable split, collapse/expand):**
  - examples/samples/splitter_basic.py
- **Notebook + extensions  (close tabs, images, events):**
  - examples/samples/notebook_extensions.py
- **DirPickerCtrl (directory selection):**
  - examples/samples/dirpicker_ctrl.py
- **print pipeline  (PrintPreview + Printer + Printout):**
  - examples/samples/print_pipeline.py
- **print pipeline with header/footer templates:**
  - examples/samples/print_pipeline_template.py
- **Localization (gettext):**
  - examples/samples/i18n_basic.py.
  - German translation:
    - locale/de/LC_MESSAGES/simplewx_demo.po.
  - Compiled runtime file: 
    - locale/de/LC_MESSAGES/simplewx_demo.mo.

You can rebuild it with:

    msgfmt locale/de/LC_MESSAGES/simplewx_demo.po -o locale/de/LC_MESSAGES/simplewx_demo.mo

Run the example in German:

  LANGUAGE=de_DE ./venv/bin/python examples/samples/i18n_basic.py

Or with an activated venv:

    source venv/bin/activate
  LANGUAGE=de_DE python examples/samples/i18n_basic.py

Short alias-style form:

    from simplewx import SimpleWx as simplewx

    win = simplewx()
    win.new_window(Name="main", Title="Demo", Size=[400, 300])
    win.show_and_run()


QT DESIGNER IMPORT (STATIC ONLY)
--------------------------------

`swx-builder.py` converts a Qt Designer `.ui` (XML) file into a SimpleWx
starter script.

Important: only pure static layouts are supported.
If the `.ui` contains `QLayout`/Sizer-style layout elements, the converter
aborts with an error message.

Supported widget mapping (current subset):

- `QPushButton` -> `add_button`
- `QLabel` -> `add_label`
- `QLineEdit` -> `add_entry`
- `QCheckBox` -> `add_check_button`
- `QMenuBar` / `QMenu` / `QAction` -> `add_menu_bar` / `add_menu` / `add_menu_item`

Convert a form:

  ./venv/bin/python swx-builder.py -i path/to/form.ui

This creates `path/to/form_swx.py` by default (same directory as input).

Or set an explicit output file or directory:

  ./venv/bin/python swx-builder.py -i path/to/form.ui -o path/to/generated_form.py
  ./venv/bin/python swx-builder.py -i path/to/form.ui -o path/to/output_dir

Dev mode (pixel-accurate geometry debugging):

  ./venv/bin/python swx-builder.py -d -i path/to/form.ui

With `-d` / `--dev`, the generated `new_window(...)` call includes `Base=0`.
Without the flag, no `Base` argument is written and the SimpleWx default is used.

Quick workflow:

1. Start with default mode (no `-d`) for regular app behavior.
2. If measured sizes/positions differ from Qt Designer, regenerate with `--dev`.
3. Compare both outputs and keep the mode that matches your target runtime behavior.

Geometry / scaling notes:

- `--dev` (`Base=0`) disables geometry scaling from SimpleWx base-font logic.
- Default mode uses SimpleWx defaults and can scale geometry depending on theme/font metrics.
- This means the same `.ui` can look slightly different between environments unless `--dev` is used.

Known pitfalls:

- Menu bar and status bar heights are theme-dependent. Visible content area can differ across desktops.
- With default scaling, fixed-position widgets may shift slightly if runtime font metrics differ.
- If your measured runtime geometry does not match Qt Designer values, regenerate with `--dev` and compare.
- `Statusbar=0` means no statusbar should be created; if one still appears, verify the generated script and rerun.


INSTALLATION
------------

Create and activate a Python virtual environment, then install dependencies:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -U pip
  pip install -r requirements.txt

For development and tests, install:

  pip install -r requirements-dev.txt


TESTING
-------

Basic smoke tests now live in `tests/` and cover:

- window creation,
- button creation,
- simulated button clicks,
- menubar/menu/menu item creation,
- simulated menu-item activation.

Install development/test dependencies (if not already installed):

  pip install -r requirements-dev.txt

Run the test suite:

    pytest -q

The smoke tests print readable step output (for example `Main window: Creation [PASSED]`) so you can see what was executed.

For headless Linux environments (for example CI), run the GUI tests under Xvfb:

    xvfb-run -a pytest -q

Note for Linux/GTK test runs: you may occasionally see non-fatal renderer log messages such as
`Gtk-Message` (missing `appmenu-gtk-module`) or pixman warnings like
`In pixman_region32_init_rect: Invalid rectangle passed`.
If pytest still reports all tests as passed, these messages are environment/rendering noise and not test assertion failures.
In current Data-Widget regression runs this pixman message can appear during sequential multi-widget teardown,
while isolated single-widget runs may stay quiet; this further indicates backend-level rendering noise.


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
