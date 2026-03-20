# swx-builder

`swx-builder.py` converts a Qt Designer `.ui` (XML) file into a SimpleWx starter script.

**Important**: only pure static layouts are supported.

If the `.ui` contains `QLayout`/Sizer-style layout elements, the converter aborts with an error message.

Supported widget mapping (current subset):

- `QPushButton`            ->     `add_button`
- `QLabel`                 ->     `add_label`
- `QFrame`                 ->     `add_frame`
- `QLineEdit`              ->     `add_entry`
- `QCheckBox`              ->     `add_check_button`
- `QRadioButton`           ->     `add_radio_button`
- `QTabWidget`             ->     `add_notebook` + `add_nb_page`
- `QTextEdit`              ->     `add_text_view`
- `QSpinBox`               ->     `add_spin_button`
- `QComboBox`              ->     `add_combo_box`
- `QSlider`                ->     `add_slider`
- `QProgressBar`           ->     `add_progress_bar`
- `QFontComboBox`          ->     `add_font_button`
- `QGraphicsView`          ->     `add_image` (when stylesheet `background-image` resolves), fallback `add_frame`
- `QToolBar` + contained `QAction` entries
                           ->     `add_toolbar` (as `Data=[...]` tool items)
- `QSplitter`              ->     `add_splitter` + `add_splitter_pane`
- `QMenuBar`               ->     `add_menu_bar`
- `QMenu`                  ->     `add_menu`
- `QAction` inside `QMenu` ->     `add_menu_item`

Explicitly not supported:

- `QDockWidget` (no SimpleWx docking equivalent; this belongs to future `AuiManager` work)
- `QTabBar` (SimpleWx supports `Notebook`, but not a standalone tab-bar widget)
- `QToolButton` (SimpleWx supports toolbar tools via `add_toolbar`, but not a standalone tool-button widget)
- `QHeaderView` (SimpleWx handles headers via widget data/columns, not as a standalone header-view widget)
- `QStackedWidget` (no direct SimpleWx stacked-container equivalent)
- `QCalendarWidget` (no direct SimpleWx calendar widget equivalent)
- `QScrollBar` (scrollbars appear automatically in container widgets like `TextView`, `TreeView`, etc.; a standalone `QScrollBar` is only needed for custom scroll mechanisms, which have no SimpleWx equivalent)
- `QDateTimeEdit` (intentionally unsupported in static import; use separate `QDateEdit` and `QTimeEdit`)

Special handling:

- `QFrame` children are detected geometrically and emitted with `Frame=<name>`.
- `QLabel` widgets named `label_<frame_name>` are consumed as frame titles instead of being emitted as standalone labels.
- `QTabWidget` pages are emitted as notebook pages; widgets on each tab are emitted with `Frame=<tab_page_name>`.
- `QToolBar` actions are exported as toolbar tool descriptors in `Data=[...]` for `add_toolbar(...)`.
- `QSplitter` is exported as one `add_splitter(...)` call plus two `add_splitter_pane(...)` calls; direct pane widgets fill their pane automatically when Qt Designer omits explicit child geometry.
- Supported Qt connections are mapped to matching wx/SimpleWx events where possible (for example `QPushButton.clicked()` -> `wx.EVT_BUTTON`, `QAction.triggered()` -> `wx.EVT_MENU`).
- Menu separators are emitted as `add_menu_item(..., Type="separator")`.
- Common themed Qt action icons like `document-open`, `document-save`, `document-new`, `application-exit` are mapped to matching SimpleWx/wx stock icon names.
- Icon file paths from Qt are resolved against the `.ui` file; paths from `.qrc` includes are resolved against the `.qrc` file.
- If a referenced icon file or `.qrc` resource cannot be found, the builder aborts with a clear error message.
- On GTK, `wx.SpinCtrl` often needs more width than a narrow Qt `QSpinBox` geometry to render cleanly.
  - The builder enforces a minimum generated spin width of about `80px`.
  - If a label is placed directly to the right of a spin control, keep enough horizontal spare space so the label is not overlapped.
  - Practical rule of thumb:
    - required extra space = `max(0, 80 - spin_width)`
    - example: `spin_width=61` -> extra `19px`
    - if the label was at `x=110`, move it to `x=129` (`110 + 19`)
  - This keeps the original visual gap stable across GTK themes.
- On GTK, `QTimeEdit` exported to SimpleWx `add_time_picker(...)` should have at least `135px` width.
  - With smaller widths, the GTK time picker can truncate parts of the displayed time text.
  - Practical recommendation in Qt Designer: set `QTimeEdit.width >= 135` before exporting.

## Usage

Convert a form:

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui
```

Optional metadata header options:

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui -a swxbuilder -v 0.1.0 -d 2026/03/16
```

- `-i` / `--input`: mandatory input `.ui` file
- `-o` / `--output`: optional output file or directory
- `-a` / `--author`: author string in generated header (default: `swxbuilder`)
- `-v` / `--version`: version string in generated header (default: `0.1.0`)
- `-d` / `--date`: date string in generated header (default: current date, format `YYYY/MM/DD`)
- `--debug`: optional debug mode for pixel-accurate geometry; generated `new_window(...)` includes `Base=0`
- `--no-debug`: disables debug mode and keeps SimpleWx scaling enabled

This creates `path/to/form_swx.py` by default (same directory as input).

Set an explicit output file or directory:

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui -o path/to/generated_form.py
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui -o path/to/output_dir
```

Default mode (scaled runtime behavior):

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui
```

By default, the generated `new_window(...)` call keeps SimpleWx scaling enabled.

SimpleWx normally scales the GUI and all its widgets based on the default font size. This ensures that a SimpleWx application appears at a usable size across different screen resolutions.

If you want pixel-accurate Qt geometry for debugging, use `--debug`; in that mode the generated `new_window(...)` call uses `Base=0`, which disables scaling.

## Quick workflow

1. Generate the form directly for normal scaled runtime behavior.
2. If you want pixel-accurate Qt coordinates, generate with `--debug`.
3. In debug output, `Base=0` is set in `new_window(...)` to disable scaling.

## Geometry and scaling notes

- Default builder output keeps SimpleWx geometry scaling enabled.
- For exact Qt Designer coordinates, run the builder with `--debug`; this emits `Base=0` and disables scaling.

## Known pitfalls

- Menu bar and status bar heights are theme-dependent. Visible content area can differ across desktops.
- With default scaling, fixed-position widgets may shift slightly if runtime font metrics differ.
- If you want exact Qt geometry, run with `--debug` so the generated `new_window(...)` call includes `Base=0`.
- `Statusbar=0` means no statusbar should be created; if one still appears, verify the generated script and rerun.
