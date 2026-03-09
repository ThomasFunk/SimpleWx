# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## Release Notes

- Major feature coverage was completed across core UI areas (toolbar, notebook enhancements, pickers, rich text, printing pipeline, grid/dataview, splitter).
- API parity with the SimpleGtk2 reference was closed by adding localization helpers (`use_gettext`, `translate`).
- Project examples and docs were expanded and standardized (English text cleanup, i18n demo with German `.po`/`.mo`, relative command paths).
- Debug/developer workflow was improved with current-file VS Code debugging and a repaired `venv` setup for system `wx` usage.


## [Unreleased]


### Added

- `ToolBar` support including tool setup helpers.
- Notebook enhancements:
	- close tabs (middle-click),
	- tab images/icons,
	- improved default notebook event wiring.
- New picker controls:
	- `DirPickerCtrl`,
	- `DatePickerCtrl`,
	- `TimePickerCtrl`.
- Rich text mode for text editor via `add_text_view(..., Rich=1)` (`wx.richtext.RichTextCtrl`).
- Printing pipeline:
	- `Printout` model,
	- print preview,
	- printer execution,
	- template-based header/footer placeholders.
- Table/data widgets:
	- `Grid` (editable + sortable),
	- `DataViewCtrl` (editable + sortable).
- Splitter support:
	- `SplitterWindow`,
	- `SplitterPane`,
	- collapse/expand helpers.
- Localization helpers:
	- `use_gettext`
	- `translate`
- New example scripts:
	- `examples/notebook_extensions.py`
	- `examples/dirpicker_ctrl.py`
	- `examples/date_time_picker.py`
	- `examples/textview_richtext.py`
	- `examples/print_pipeline.py`
	- `examples/print_pipeline_template.py`
	- `examples/grid_basic.py`
	- `examples/dataview_basic.py`
	- `examples/splitter_basic.py`
	- `examples/windows_basic.py`
	- `examples/buttons_toggles_basic.py`
	- `examples/numeric_text_entries_basic.py`
	- `examples/treeview_basic.py`
	- `examples/listview_basic.py`
	- `examples/i18n_basic.py`
	- `locale/de/LC_MESSAGES/simplewx_demo.po`
	- `locale/de/LC_MESSAGES/simplewx_demo.mo`

### Changed

- Examples and snippets were aligned to alias-style usage:
	- `from simplewx import SimpleWx as simplewx`
	- `win = simplewx()`
- VS Code debug configuration updated to run/debug the currently open file (`${file}`) with workspace-root `cwd` and `PYTHONPATH` support.
- Local `venv` was recreated with `--system-site-packages` to support system-installed `wx` packages.
- User-facing default strings in `simplewx.py` were normalized to English (file/folder/date/time pickers, print/page setup, font/color dialogs).
- Example script UI labels and console output were translated to English for consistency.
- Inline comments in `simplewx.py` were translated to English.

### Fixed

- Fixed `TypeError: SimpleWx._set_commons() got multiple values for argument 'name'` by renaming the first `_set_commons` parameter to avoid collision with normalized `name` in `**params`.
- Corrected an internal `_set_commons` callback binding reference after the parameter rename.

### Documentation

- Updated `README.md` to reflect newly implemented widgets and added example references, including the new basic starter examples.
- Translated README example/i18n sections to English.
- Added i18n usage notes in README for `.po`/`.mo`, `msgfmt`, and running with `LANGUAGE=de_DE`.
- Replaced absolute project paths in README commands with project-root relative paths.

### Removed

- None.

