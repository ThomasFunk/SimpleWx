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

- Extended `tools/swx-builder/swx-builder.py` static Qt import support for `QDialog` top-level windows (alongside `QMainWindow`).
- Added `QDialogButtonBox` conversion support by expanding standard buttons into generated SimpleWx `add_button(...)` calls.
- Added builder-side generation of handler bodies for selected Qt receiver slots (`click()`, `show()`, `hide()`) so generated callbacks can directly act on target widgets.
- Added/extended builder regression coverage in `tests/test_swx_builder.py` for dialog top-level conversion, `QDialogButtonBox` accepted/rejected mapping, `click()` slot body generation, and colon-prefixed absolute icon-path fallback.
- Added static Qt import mapping for `QFontComboBox` to generated SimpleWx `add_font_button(...)` calls.
- Added static Qt import mapping for `QGraphicsView` by reading stylesheet `background-image: url(...)`, resolving `.qrc` paths, and generating `add_image(...)` (or fallback `add_frame(...)` when no image is resolvable).

### Changed

- Refined generated code formatting in `swx-builder.py` with inline comments for widgets/menu items/toolbar items and consistent placement of comments above associated handler definitions.
- Refined grouped widget section formatting so `# Widgets on ...` sections and first-widget spacing are consistent across main area, notebook pages, and splitter panes.
- Updated `examples/formbuilder/qt_minimal_expected.py` to match the current generated comment layout.
- Documented/standardized builder call formatting rule in `_format_call(...)`: fewer than 5 parameters stay single-line; 5+ parameters are emitted multiline with one argument per line.
- Declared `QDateTimeEdit` intentionally unsupported in the static importer; users should model date/time with separate `QDateEdit` and `QTimeEdit` widgets.
- Documented GTK-specific sizing guidance for `QTimeEdit` in the builder docs: use at least `135px` width to avoid truncated time text in generated SimpleWx time pickers.

### Fixed

- Fixed progressbar mode split in `simplewx.py`: debugger/dev runs use native `wx.Gauge` with gray underlay, normal runtime uses owner-draw mode, and `SWX_PROGRESSBAR_FORCE_OWNERDRAW=1` remains an explicit override.
- Fixed `QDialogButtonBox` multi-connection handling in `swx-builder.py` by preserving all sender connections instead of last-write-wins, so accepted/rejected can both be wired correctly.
- Fixed Qt icon resolution in `swx-builder.py` for colon-prefixed absolute path forms (for example `:/home/.../icon.png`) via basename and direct-path fallbacks when qrc key lookup does not match.
- Fixed builder CLI error wording for unsupported widgets by emitting an English abort prefix (`Abort:`) and explicit unsupported-class guidance text.

## [0.5.2] - 2026-03-17

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.5.2"`.
- Updated the README headline version from `0.5.1` to `0.5.2`.

### Fixed

- Fixed scroll range handling in `simplewx.py` for non-fixed main windows by preserving the `wx.ScrolledWindow` virtual size from actual child geometry, so shrinking the frame shows scrollbars again.

## [0.5.1] - 2026-03-17

### Added

- Extended `swx-builder.py` static Qt import support to include `QFrame`, `QLineEdit`, `QRadioButton`, and `QCheckBox` in the documented supported subset, including frame-local widget export.
- Added builder regression coverage for `QFrame` title mapping and frame-contained widgets.
- Added builder regression coverage for `QSplitter` / `QToolBar` generation and CLI parsing with explicit `--no-debug` opt-out.

### Changed

- Updated Qt import documentation in [README.md](README.md) and [tools/swx-builder/README.md](tools/swx-builder/README.md) to reflect the current supported widget subset and frame-title handling.
- Marked the static Qt Designer importer task as completed in [TODO.md](TODO.md).
- Updated `swx-builder.py` CLI to support explicit debug mode selection via `--debug` / `--no-debug` while keeping scaled output as default when no debug flag is provided.
- Bumped library metadata in `simplewx.py` to `__version__ = "0.5.1"`.
- Updated the README headline version from `0.5.0` to `0.5.1`.

### Fixed

- Fixed `Frame` rendering in `simplewx.py` so frame geometry stays externally stable while title and child placement match the imported Qt layout more closely.
- Fixed Qt-to-SimpleWx splitter orientation mapping for generated `QSplitter` output.
- Fixed `ToolBar` parenting/rendering in `simplewx.py` by attaching toolbars to the top-level frame (`SetToolBar`) instead of the scrollable content container.
- Fixed splitter pane resize behavior in `simplewx.py` by using pane sizers so child widgets expand/shrink with sash movement instead of leaving empty gaps.

## [0.5.0] - 2026-03-13

### Added

- Added the Qt Designer importer `swx-builder.py` (static-only `.ui` conversion to a SimpleWx scaffold).
- Added `-d` / `--dev` mode to `swx-builder.py`; in dev mode generated `new_window(...)` includes `Base=0` for pixel-accurate geometry debugging.
- Added builder regression coverage in `tests/test_swx_builder.py` to validate dev-mode output includes `Base=0`.
- Added Sphinx documentation with HTML and manpage output.
- Added one page per public method under `docs/api/methods/`.
- Added pre-built documentation to the repository (`docs/html/`, `doc/simplewx.1`).
- Added Makefile targets `docs-html`, `docs-man`, `docs-deploy-html`, `docs-deploy-man`, `docs-clean`.

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.5.0"`.
- Updated the README headline version from `0.4.1` to `0.5.0`.
- Refined geometry scaling in `simplewx.py` by switching `_calc_scalefactor(...)` to a font-metric-based approach using monospace text extents, with rounded fallback behavior.
- Updated `README.md` Qt Designer import section with documented `--dev` usage and behavior.
- Organized the new builder workflow under `tools/swx-builder/` with dedicated documentation in `tools/swx-builder/README.md`.

### Fixed

- Fixed statusbar creation logic in `new_window(...)`: `Statusbar=0` no longer creates a statusbar.
- Improved main content container synchronization for non-fixed windows so scrolled content sizing better tracks frame/client changes.

## [0.4.1] - 2026-03-12

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.4.1"`.
- Updated the README headline version from `0.4.0` to `0.4.1`.
- Added a practical project `Makefile` with targets for environment setup, dependency install, tests, headless tests, and running examples.

### Added

- Populated `requirements.txt` with runtime dependency declaration (`wxPython`).
- Updated `requirements-dev.txt` to include runtime requirements plus pytest.

### Documentation

- Updated README installation instructions to use `requirements.txt` / `requirements-dev.txt`.

## [0.4.0] - 2026-03-12

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.4.0"`.
- Updated the README headline version from `0.3.3` to `0.4.0`.
- Updated `examples/samples/windows_basic.py` so the button demonstrates statusbar output (`set_sb_text`) instead of stdout printing.

### Added

- Added one-shot modal override support for message dialogs via `show_msg_dialog(..., Modal=0|1)`.
- Added standalone message dialog demo mode switch in `examples/samples/standalone_msg_dialog_simple.py` to contrast modal (return value) vs non-modal (callback) flow.

### Fixed

- Changed one-shot message-dialog default behavior to non-modal when `Modal` is omitted (`Modal=None -> 0`).
- Extended dialog regression coverage in `tests/test_dialog_mocking.py` for one-shot default non-modal mode and explicit modal override mode.

## [0.3.3] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.3.3"`.
- Updated the README headline version from `0.3.2` to `0.3.3`.

### Added

- Added dialog tests with mocked `ShowModal`/return-code handling in `tests/test_dialog_mocking.py`.
- Added data-widget regression tests for ListView/Grid/DataView in `tests/test_data_widget_regressions.py`.

### Fixed

- Improved ListView resize guard behavior for test stability in headless GTK runs.

### Documentation

- Documented known GTK/Pixman renderer log noise and sequential-run behavior in `README.md`.
- Updated test output structure with ordered English section headers and matching separator lines.

## [0.3.2] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.3.2"`.
- Updated the README headline version from `0.3.1` to `0.3.2`.

### Added

- Added regression coverage for menu/toolbar behavior (`tests/test_menu_toolbar_regressions.py`) focused on radio groups and callback bindings.

### Fixed

- Fixed toolbar tool-id handling for wx so tool creation and state switching are stable during automated tests.
- Added `MenuItem` `Active` handling in `set_value`/`set_values`, including radio-group synchronization.

## [0.3.1] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.3.1"`.
- Updated the README headline version from `0.3.0` to `0.3.1`.
- Added/updated local automated tests for core helper behavior in `tests/test_unit_core.py`.

### Documentation

- Extended `TODO.md` with next-step automated test areas for future coverage expansion.

## [0.3.0] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.3.0"`.
- Updated the README headline version from `0.2.2` to `0.3.0`.
- Marked smoke tests as completed in `TODO.md`.

### Added

- Added pytest-based GUI smoke test infrastructure:
	- `tests/conftest.py` shared GUI fixtures,
	- `tests/test_smoke_gui.py` smoke scenarios for window/button/menu flows,
	- `requirements-dev.txt` with test dependency setup,
	- `pytest.ini` to show readable smoke test step output.

### Fixed

- Avoided repeated wx image-handler initialization by guarding `wx.InitAllImageHandlers()` with a runtime check, removing duplicate "Adding duplicate image handler" debug noise during test runs.

### Documentation

- Added/updated README testing instructions (`pytest -q`, headless `xvfb-run -a pytest -q`) and described the human-readable smoke test output format.

## [0.2.2] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.2.2"` and kept the release date current.
- Updated the README headline version from `0.2.0` to `0.2.2`.

### Fixed

- Fixed wxGTK menu item icons by applying `SetBitmap()` before `Append()` in `add_menu_item()`.
- Fixed notebook pages inside scrolled containers so absolute-positioned children expand the virtual size correctly.
- Rejected unsupported per-page tab font/color styling on `wx.Notebook` with explicit error handling instead of silently doing nothing.

### Documentation

- Added inline comments to `add_menu_bar()`, `add_menu()`, and `add_menu_item()` for easier maintenance and code navigation.

## [0.2.0] - 2026-03-11

### Changed

- Bumped library metadata in `simplewx.py` to `__version__ = "0.2.0"` and updated release date.
- Finalized notebook tab tooltip handling (name-based mapping + robust hover hit-testing) for stable behavior on tab reorder/remove.

### Documentation

- Updated README headline version from `0.1.0` to `0.2.0`.


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
	- `examples/samples/notebook_extensions.py`
	- `examples/samples/dirpicker_ctrl.py`
	- `examples/samples/date_time_picker.py`
	- `examples/samples/textview_richtext.py`
	- `examples/samples/print_pipeline.py`
	- `examples/samples/print_pipeline_template.py`
	- `examples/samples/grid_basic.py`
	- `examples/samples/dataview_basic.py`
	- `examples/samples/splitter_basic.py`
	- `examples/samples/windows_basic.py`
	- `examples/samples/buttons_toggles_basic.py`
	- `examples/samples/numeric_text_entries_basic.py`
	- `examples/samples/treeview_basic.py`
	- `examples/samples/listview_basic.py`
	- `examples/samples/i18n_basic.py`
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
- Fixed README markdown list formatting for the "Implemented widgets" section so GitHub renders category items as proper bullet lists (not collapsed inline text).

### Removed

- None.

