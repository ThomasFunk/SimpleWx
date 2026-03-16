# swx-builder

`swx-builder.py` converts a Qt Designer `.ui` (XML) file into a SimpleWx starter script.

**Important**: only pure static layouts are supported.

If the `.ui` contains `QLayout`/Sizer-style layout elements, the converter aborts with an error message.

Supported widget mapping (current subset):

- `QPushButton` -> `add_button`
- `QLabel` -> `add_label`
- `QFrame` -> `add_frame`
- `QLineEdit` -> `add_entry`
- `QCheckBox` -> `add_check_button`
- `QRadioButton` -> `add_radio_button`
- `QTabWidget` -> `add_notebook` + `add_nb_page`
- `QTextEdit` -> `add_text_view`
- `QSpinBox` -> `add_spin_button`
- `QMenuBar` / `QMenu` / `QAction` -> `add_menu_bar` / `add_menu` / `add_menu_item`

Special handling:

- `QFrame` children are detected geometrically and emitted with `Frame=<name>`.
- `QLabel` widgets named `label_<frame_name>` are consumed as frame titles instead of being emitted as standalone labels.
- `QTabWidget` pages are emitted as notebook pages; widgets on each tab are emitted with `Frame=<tab_page_name>`.

## Usage

Convert a form:

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui
```

This creates `path/to/form_swx.py` by default (same directory as input).

Set an explicit output file or directory:

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui -o path/to/generated_form.py
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui -o path/to/output_dir
```

Default mode (pixel-accurate geometry debugging):

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -i path/to/form.ui
```

By default, the generated `new_window(...)` call includes `Base=0`.

SimpleWx normally scales the GUI and all its widgets based on the default font size. This ensures that a SimpleWx application appears at a usable size across different screen resolutions. `Base=0` disables this behaviour so the generated output stays closer to the original Qt Designer geometry.

## Quick workflow

1. Generate the form directly.
2. The generated output uses `Base=0` by default to preserve Qt geometry.
3. If you want scaled runtime behavior later, adjust the generated `new_window(...)` call manually.

## Geometry and scaling notes

- Default builder output uses `Base=0` and disables geometry scaling from SimpleWx base-font logic.
- This keeps generated coordinates closer to the static Qt Designer file.

## Known pitfalls

- Menu bar and status bar heights are theme-dependent. Visible content area can differ across desktops.
- With default scaling, fixed-position widgets may shift slightly if runtime font metrics differ.
- If you want SimpleWx scaling instead, remove `Base=0` from the generated `new_window(...)` call.
- `Statusbar=0` means no statusbar should be created; if one still appears, verify the generated script and rerun.
