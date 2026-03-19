# TODO (Open Work)

## P0 – Major Features


- [x] Qt Designer import (`swx-builder.py`):
	- parse `.ui` (XML) and generate a SimpleWx scaffold,
	- accept only pure static layouts,
	- abort with a clear error message when Sizer or dynamic elements are present.

- [ ] Tray / status integration (`TaskBarIcon` / StatusIcon):
	- show and update the tray icon,
	- context menu,
	- left-click and double-click events,
	- clean shutdown behaviour.

- [ ] AUI / docking (`AuiManager`):
	- dockable and floating panels,
	- persistent layout state,
	- robust Wayland / X11 compatibility.

## P1 – API Parity (small remainder)

- [x] Add i18n helpers from reference:
	- `use_gettext`
	- `translate`

- [ ] swx-builder: remaining Qt widget mappings (prioritised)
	- [x] Priority 1 (basic): `QComboBox`, `QSlider`, `QProgressBar`
	- [x] Priority 2 (basic): `QFrame` (`HLine` / `VLine` -> `Separator`)
	- [x] Priority 3: `QTreeWidget`, `QTableWidget`, `QListWidget`/`QListView`, `QTableView`, `QTreeView`
	- [x] Priority 4: `QSplitter`, `QToolBar`
	- [x] Priority 5 (dialogs): `QDialog`, `QDialogButtonBox`
	- [x] Priority 6: `QFontComboBox` (`QDateTimeEdit` intentionally unsupported; use `QDateEdit` + `QTimeEdit`)
	- [x] Priority 7 (complex widgets): `QGraphicsView`

## P2 – Stabilisation

- [x] Smoke tests for core examples (startup + basic interactions).
- [x] Unit test base for core helpers (alias normalisation, filter builder, art-ID mapping, scale factor calculation).
- [x] Set up Sphinx documentation for SimpleWx with both HTML output and manpage generation.
- [ ] GUI scaling checks across multiple resolutions / DPI levels:
	- verify frame/content spacing (top and bottom margins) remains visually balanced,
	- verify border offsets for Frame/Panel/ScrolledWindow/NotebookPage containers,
	- capture before/after screenshots for regression comparison.
- [ ] Update documentation once `AuiManager` / `TaskBarIcon` are implemented.
- [ ] Optional: create a release checklist for the first stable tag (`v0.1.x`).

## P3 – Additional Automated Tests

- [x] Widget state round-trip tests (`set_value` / `get_value`) for: CheckButton, RadioButton, ComboBox, Slider, SpinButton, ProgressBar.
- [x] Notebook regression tests: page add / remove, CurrentPage, icon assignment, event wiring.
- [x] Menu / toolbar regressions: radio groups, callback bindings.
- [ ] NotebookPage sensitivity: refactor and integrate cleanly in wx.
- [ ] NotebookPage show / hide: refactor and integrate cleanly in wx.
- [x] Data-widget tests: ListView / Grid / DataView data updates, cell access, sort behaviour.
- [x] Dialog tests with mocking (`ShowModal` / return codes) instead of native interaction.

## Parking Lot (later, low priority)

- [ ] labwc-nightshade use case:
	- tray-first launch (open control centre via systray menu),
	- optionally windowless / no title bar / no taskbar entry,
	- only worth tackling after `AuiManager` + `TaskBarIcon` are in place.

## Summary

- Feature coverage is already very high.
- The test suite is largely complete except for the two NotebookPage items (sensitivity, show/hide).
- Remaining major work centres on `AuiManager` and `TaskBarIcon`.
