# swx-builder

`swx-builder.py` converts a Qt Designer `.ui` (XML) file into a SimpleWx starter script.

Important: only pure static layouts are supported.
If the `.ui` contains `QLayout`/Sizer-style layout elements, the converter aborts with an error message.

Supported widget mapping (current subset):

- `QPushButton` -> `add_button`
- `QLabel` -> `add_label`
- `QLineEdit` -> `add_entry`
- `QCheckBox` -> `add_check_button`
- `QMenuBar` / `QMenu` / `QAction` -> `add_menu_bar` / `add_menu` / `add_menu_item`

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

Dev mode (pixel-accurate geometry debugging):

```bash
./venv/bin/python tools/swx-builder/swx-builder.py -d -i path/to/form.ui
```

With `-d` / `--dev`, the generated `new_window(...)` call includes `Base=0`.
Without the flag, no `Base` argument is written and the SimpleWx default is used.

## Quick workflow

1. Start with default mode (no `-d`) for regular app behavior.
2. If measured sizes/positions differ from Qt Designer, regenerate with `--dev`.
3. Compare both outputs and keep the mode that matches your target runtime behavior.

## Geometry and scaling notes

- `--dev` (`Base=0`) disables geometry scaling from SimpleWx base-font logic.
- Default mode uses SimpleWx defaults and can scale geometry depending on theme/font metrics.
- The same `.ui` can look slightly different between environments unless `--dev` is used.

## Known pitfalls

- Menu bar and status bar heights are theme-dependent. Visible content area can differ across desktops.
- With default scaling, fixed-position widgets may shift slightly if runtime font metrics differ.
- If measured runtime geometry does not match Qt Designer values, regenerate with `--dev` and compare.
- `Statusbar=0` means no statusbar should be created; if one still appears, verify the generated script and rerun.
