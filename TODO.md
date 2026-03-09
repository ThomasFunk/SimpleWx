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

- [ ] Smoke-Tests für Kernbeispiele (Start + Grundinteraktionen).
- [ ] Dokumentation nachziehen, sobald `AuiManager`/`TaskBarIcon` umgesetzt sind.
- [ ] Optional: Release-Checkliste für ersten stabilen Tag (`v0.1.x`) anlegen.

## Kurzfazit

- Feature-Abdeckung ist bereits sehr hoch.
- Offene Arbeit ist vor allem bei den zwei großen Themen (`AuiManager`, `TaskBarIcon`).
