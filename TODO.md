# TODO (Restarbeiten)

## P0 – Große Brocken

- [ ] AUI/Docking (`AuiManager`):
	- dockbare/andockbare Panels,
	- persistente Layout-Zustände,
	- robuste Wayland/X11-Verträglichkeit.

- [ ] Tray/Status-Integration (`TaskBarIcon` / StatusIcon):
	- Icon anzeigen/ändern,
	- Kontextmenü,
	- Klick-/Doppelklick-Events,
	- sauberes Verhalten beim Beenden.

## P1 – API-Parität (kleiner Rest)

- [x] i18n-Helfer aus Referenz ergänzen:
	- `use_gettext`
	- `translate`

## P2 – Stabilisierung

- [x] Smoke-Tests für Kernbeispiele (Start + Grundinteraktionen).
- [x] Unit-Test-Basis für Core-Helper (Alias-Normalisierung, Filterbau, Art-ID-Mapping, Skalierungsberechnung).
- [ ] Dokumentation nachziehen, sobald `AuiManager`/`TaskBarIcon` umgesetzt sind.
- [ ] Optional: Release-Checkliste für ersten stabilen Tag (`v0.1.x`) anlegen.

## P3 – Weitere automatisierte Tests

- [ ] Widget-State Roundtrip-Tests (`set_value`/`get_value`) für: CheckButton, RadioButton, ComboBox, Slider, SpinButton, ProgressBar.
- [ ] Notebook-Regressionstests: Page add/remove, CurrentPage, Icon-Zuweisung, Event-Wiring.
- [ ] Menü-/Toolbar-Regressionen: Sensitivity, Radio-Groups, Callback-Bindings.
- [ ] Data-Widget-Tests: ListView/Grid/DataView Datenupdate, Zellzugriff, Sortierverhalten.
- [ ] Dialog-Tests mit Mocking (`ShowModal`/Rückgabecodes) statt nativer Interaktion.

## Kurzfazit

- Feature-Abdeckung ist bereits sehr hoch.
- Offene Arbeit ist vor allem bei den zwei großen Themen (`AuiManager`, `TaskBarIcon`).
