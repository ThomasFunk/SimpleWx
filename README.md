SimpleWx version 0.6.0
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
- **NSD IPC mounted listener:**
  - examples/samples/nsd_mounted_listener.py

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

After extensive evaluation and testing of several GUI builders for SimpleWx (wxFormBuilder, Glade, wxSmith in Code::Blocks, and Qt Designer), only one remained suitable: Qt Designer. Why? Because only Qt Designer supports static layouts in the required way. The other tools rely on dynamic layouts and sizers. The goal was a GUI builder with straightforward WYSIWYG support that does not require additional layout planning first.

The Qt Designer converter lives in `tools/swx-builder/`.

Use:

  ./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui

Currently supported Qt static import includes top-level `QMainWindow` and `QDialog`. Supported widget classes include `QPushButton`, `QLabel`, `QLineEdit`, `QCheckBox`, `QRadioButton`, `QFrame`, `QTabWidget`, `QTextEdit`, `QSpinBox`, `QComboBox`, `QSlider`, `QProgressBar`, `QDialogButtonBox` (expanded to SimpleWx buttons), `QListWidget`/`QListView`, `QTableWidget`/`QTableView`, `QTreeWidget`/`QTreeView`, `QSplitter`, `QToolBar`, `QFontComboBox`, and `QGraphicsView` plus `QMenuBar` / `QMenu` / `QAction`.

`QDateTimeEdit` is intentionally not supported by the static importer; use separate `QDateEdit` and `QTimeEdit` widgets in Designer.

On Linux/GTK, use at least `135px` width for `QTimeEdit` in Designer; narrower controls can cause truncated time text in the generated SimpleWx time picker.

`QFileDialog` and `QMessageBox` are runtime dialog calls and are intentionally handled in application code, not as static Designer top-level windows.

For full usage, options, examples, and troubleshooting, see:

  `tools/swx-builder/README.md`


NSD IPC JSON PAYLOADS
---------------------

SimpleWx apps can connect to nsd daemon via:

    win.enable_nsd(on_nsd_message, socket_path="/tmp/nsd.sock")

Messages follow the common envelope:

```json
{
  "src": "nsd.notifications | nsd.automount | your_client",
  "type": "broadcast | command | event",
  "action": "show_notification | mounted | ...",
  "payload": { }
}
```

Expected payload for `action: show_notification` (broadcast from nsd notifications plugin):

```json
{
  "src": "nsd.notifications",
  "type": "broadcast",
  "action": "show_notification",
  "payload": {
    "app": "string",
    "title": "string",
    "message": "string",
    "icon": "string",
    "timeout": 5000
  }
}
```

Expected payload for `action: mounted` (broadcast from nsd automount plugin):

```json
{
  "src": "nsd.automount",
  "type": "broadcast",
  "action": "mounted",
  "payload": {
    "device": "/dev/sdb1",
    "mount_point": "/run/media/user/LABEL",
    "label": "LABEL",
    "uuid": "UUID-STRING",
    "fs_type": "vfat"
  }
}
```

Implementation note: `payload` should always be handled as optional and type-checked (`dict`), because clients may send custom actions.


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


DEBUGGING NOTEBOOK + PROGRESSBAR (LINUX/GTK)
---------------------------------------------

For manual GUIs and swx-builder generated GUIs, the following environment flags are useful when troubleshooting Notebook/ProgressBar behavior:

- `SWX_PROGRESSBAR_DEBUG=1`
  - enables concise progress-bar debug output (`create`, `layout`, `paint`, `size`)
- `SWX_NOTEBOOK_DEBUG=1`
  - enables notebook geometry drift/fix logs
- default runtime behavior:
  - in debugger/dev runs (`sys.gettrace`/debugpy envs or `Base=0`) progress bars use native `wx.Gauge` with gray underlay
  - in normal runtime progress bars use owner-drawn mode
- `SWX_PROGRESSBAR_FORCE_OWNERDRAW=1`
  - forces owner-draw progress bar, even on notebook pages

Examples:

    SWX_PROGRESSBAR_DEBUG=1 SWX_NOTEBOOK_DEBUG=1 python your_gui.py

    SWX_PROGRESSBAR_FORCE_OWNERDRAW=1 SWX_PROGRESSBAR_DEBUG=1 python your_gui.py


DOCUMENTATION
-------------

Pre-built documentation is included in the repository:

- HTML: docs/html/index.html
- Manpage: doc/simplewx.1  (install with: man doc/simplewx.1)

To rebuild from source (requires dev dependencies):

  make docs-html
  make docs-man

To deploy the rebuilt output back into the repository:

  make docs-deploy-html
  make docs-deploy-man


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

Please send bug reports or suggestions for improvements to <t.funk@web.de> or over the project page under [ISSUES](https://github.com/ThomasFunk/SimpleWx/issues).
