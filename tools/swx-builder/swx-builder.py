#!/usr/bin/env python3
from __future__ import annotations

__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/19"

import argparse
import datetime
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple


class BuilderError(Exception):
    pass


# Describes the source file's main window in a compact structure that is easy
# to pass through later conversion stages.
@dataclass
class WindowSpec:
    name: str
    title: str
    size: Optional[Tuple[int, int]]
    statusbar: bool


@dataclass
class ConnectionSpec:
    handler_name: str
    qt_signal: str
    body: List[str] = field(default_factory=list)


# Represents a single Qt widget after parsing.
# `frame` later stores the surrounding frame name when the widget is assigned
# to a containing `QFrame` by geometric inspection.
@dataclass
class WidgetSpec:
    qt_class: str
    name: str
    position: Tuple[int, int]
    size: Optional[Tuple[int, int]]
    title: str
    tooltip: Optional[str]
    checked: int = 0
    handler_name: Optional[str] = None
    handler_body: List[str] = field(default_factory=list)
    signal: Optional[str] = None
    frame: Optional[str] = None
    frame_title_height: int = 0
    # Radio group name extracted from a containing QGroupBox, if present.
    group: Optional[str] = None
    # Logical container scope (e.g. notebook page name) used for frame matching.
    container: Optional[str] = None
    # Additional widget-specific metadata for renderer mappings.
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotebookPageSpec:
    name: str
    title: str
    notebook: str
    position_number: int


@dataclass
class NotebookSpec:
    name: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    pages: List[NotebookPageSpec]
    handler_name: Optional[str] = None
    signal: Optional[str] = None


# Represents a single menu item from the QMenu/QAction structure.
@dataclass
class MenuItemSpec:
    name: str
    title: str
    item_type: str = "item"
    tooltip: Optional[str] = None
    icon: Optional[str] = None
    handler_name: Optional[str] = None
    signal: Optional[str] = None


# Bundles one complete menu with all of its contained items.
@dataclass
class MenuSpec:
    name: str
    title: str
    items: List[MenuItemSpec]


@dataclass
class ActionSpec:
    name: str
    title: str
    tooltip: Optional[str] = None
    icon: Optional[str] = None
    checkable: int = 0
    checked: int = 0
    handler_name: Optional[str] = None
    signal: Optional[str] = None


@dataclass
class ToolbarItemSpec:
    name: str
    title: str
    kind: str = "normal"
    tooltip: Optional[str] = None
    icon: Optional[str] = None
    active: int = 0


@dataclass
class ToolbarSpec:
    name: str
    title: str
    position: Tuple[int, int]
    size: Optional[Tuple[int, int]]
    orient: str
    items: List[ToolbarItemSpec]


@dataclass
class SplitterPaneSpec:
    name: str
    side: str
    widgets: List[WidgetSpec]


@dataclass
class SplitterSpec:
    name: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    orient: str
    split: int
    panes: List[SplitterPaneSpec]
    handler_name: Optional[str] = None
    signal: Optional[str] = None


SUPPORTED_WIDGET_CLASSES = {
    "Line",
    "QLabel",
    "QPushButton",
    "QLineEdit",
    "QCheckBox",
    "QRadioButton",
    "QFrame",
    "QTextEdit",
    "QSpinBox",
    "QComboBox",
    "QSlider",
    "QProgressBar",
    "QListWidget",
    "QListView",
    "QTableWidget",
    "QTableView",
    "QTreeWidget",
    "QTreeView",
    "QFontComboBox",
    "QGraphicsView",
}

UNSUPPORTED_WIDGET_CLASSES: Dict[str, str] = {
    "QDateTimeEdit": "Please use separate QDateEdit and QTimeEdit widgets in Qt Designer.",
}

SUPPORTED_TOP_LEVEL_CLASSES = {
    "QMainWindow",
    "QDialog",
    "QFileDialog",
    "QMessageBox",
}

SUPPORTED_DIALOG_BUTTON_BOX_CLASS = "QDialogButtonBox"

MIN_SPINBOX_WIDTH = 80


def sanitize_name(name: str, fallback_prefix: str, index: int) -> str:
    # Qt names may contain characters that are awkward or invalid in Python /
    # SimpleWx identifiers. Reduce them to a safe letters/digits/underscore form.
    candidate = "".join(char if (char.isalnum() or char == "_") else "_" for char in name.strip())
    if not candidate:
        candidate = f"{fallback_prefix}_{index}"
    if candidate[0].isdigit():
        candidate = f"{fallback_prefix}_{candidate}"
    return candidate


def _find_property(widget: ET.Element, name: str) -> Optional[ET.Element]:
    # Helper: find a Qt property with the requested name directly under a widget.
    for prop in widget.findall("property"):
        if (prop.get("name") or "").strip() == name:
            return prop
    return None


def _property_string(widget: ET.Element, name: str) -> Optional[str]:
    # Read a string property robustly whether Qt stores the text directly on the
    # property node or in a nested element such as <string>.
    prop = _find_property(widget, name)
    if prop is None:
        return None
    if len(prop) == 0:
        raw = "".join(prop.itertext()).strip()
        return raw if raw else None
    child = prop[0]
    raw = "".join(child.itertext()).strip()
    return raw if raw else None


def _property_bool(widget: ET.Element, name: str) -> int:
    # Intentionally returns 0/1 instead of True/False because SimpleWx uses
    # numeric flags in many places.
    value = (_property_string(widget, name) or "").strip().lower()
    return 1 if value in {"1", "true", "yes"} else 0


def _property_number(widget: ET.Element, name: str) -> Optional[str]:
    prop = _find_property(widget, name)
    if prop is None:
        return None
    for child_name in ("number", "numberint", "double", "float"):
        value = prop.findtext(child_name)
        if value is not None:
            stripped = value.strip()
            if stripped:
                return stripped
    raw = "".join(prop.itertext()).strip()
    return raw if raw else None


def _property_enum(widget: ET.Element, name: str) -> Optional[str]:
    prop = _find_property(widget, name)
    if prop is None:
        return None
    value = prop.findtext("enum")
    if value is not None:
        stripped = value.strip()
        if stripped:
            return stripped
    raw = "".join(prop.itertext()).strip()
    return raw if raw else None


def _int_from_property(widget: ET.Element, name: str, default: int = 0) -> int:
    raw = _property_number(widget, name)
    if raw is None:
        return default
    try:
        return int(round(float(raw.strip())))
    except (TypeError, ValueError):
        return default


def _normalize_qt_resource_path(raw_path: str) -> str:
    stripped = raw_path.strip().replace("\\", "/")
    if not stripped:
        return ""

    if stripped.startswith(":"):
        stripped = stripped[1:]

    parts: List[str] = []
    for part in PurePosixPath(stripped).parts:
        if part in ("", "/", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)

    return "/" + "/".join(parts) if parts else "/"


def _resolve_icon_file_path(icon_path: str, ui_path: Path, owner_name: str) -> str:
    candidate = Path(icon_path)
    if not candidate.is_absolute():
        candidate = (ui_path.parent / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if not candidate.exists():
        raise BuilderError(
            f"Icon-Datei für '{owner_name}' nicht gefunden: {candidate}"
        )

    return str(candidate)


def _collect_qt_resource_paths(root: ET.Element, ui_path: Path) -> Dict[str, str]:
    resource_paths: Dict[str, str] = {}

    for include in root.findall("./resources/include"):
        location = (include.get("location") or "").strip()
        if not location:
            continue

        qrc_path = Path(location)
        if not qrc_path.is_absolute():
            qrc_path = (ui_path.parent / qrc_path).resolve()
        else:
            qrc_path = qrc_path.resolve()

        if not qrc_path.exists():
            raise BuilderError(f"Qt-Ressourcendatei nicht gefunden: {qrc_path}")

        try:
            qrc_tree = ET.parse(qrc_path)
        except ET.ParseError as exc:
            raise BuilderError(f"Qt-Ressourcendatei konnte nicht gelesen werden: {qrc_path}: {exc}") from exc

        qrc_root = qrc_tree.getroot()
        for qresource in qrc_root.findall("./qresource"):
            prefix = (qresource.get("prefix") or "").strip()
            for file_node in qresource.findall("file"):
                file_ref = "".join(file_node.itertext()).strip()
                if not file_ref:
                    continue

                alias = (file_node.get("alias") or "").strip()
                resource_name = _normalize_qt_resource_path(f"{prefix}/{alias or file_ref}")

                file_path = Path(file_ref)
                if not file_path.is_absolute():
                    file_path = (qrc_path.parent / file_path).resolve()
                else:
                    file_path = file_path.resolve()

                if not file_path.exists():
                    raise BuilderError(
                        f"Qt-Ressource '{resource_name}' verweist auf fehlende Datei: {file_path}"
                    )

                resource_paths[resource_name] = str(file_path)

    return resource_paths


def _property_icon(
    widget: ET.Element,
    name: str,
    ui_path: Path,
    resource_paths: Dict[str, str],
    owner_name: str,
) -> Optional[str]:
    prop = _find_property(widget, name)
    if prop is None:
        return None

    iconset = prop.find("iconset")
    if iconset is None:
        return None

    theme_name = (iconset.get("theme") or "").strip()
    if theme_name:
        return _map_qt_icon_to_simplewx_icon(theme_name)

    for tag in ("normaloff", "normalon", "selectedoff", "selectedon"):
        value = iconset.findtext(tag)
        if value is None:
            continue
        stripped = value.strip()
        if not stripped:
            continue

        if stripped.startswith(":"):
            resource_name = _normalize_qt_resource_path(stripped)
            resolved = resource_paths.get(resource_name)
            if resolved is None:
                basename_key = "/" + PurePosixPath(resource_name).name
                if basename_key != resource_name:
                    resolved = resource_paths.get(basename_key)
            if resolved is None:
                # Some .ui files embed a direct file path inside a ":/..." value
                # instead of a canonical qrc key. In that case try treating the
                # part after ':' as an ordinary file path.
                raw_file_path = stripped[1:]
                if raw_file_path:
                    try:
                        return _resolve_icon_file_path(raw_file_path, ui_path, owner_name)
                    except BuilderError:
                        pass
            if resolved is None:
                raise BuilderError(
                    f"Qt-Ressource für '{owner_name}' nicht gefunden: {resource_name}"
                )
            return resolved

        return _resolve_icon_file_path(stripped, ui_path, owner_name)

    return None


def _property_rect(widget: ET.Element, name: str, widget_name: str) -> Optional[Tuple[int, int, int, int]]:
    # Extract a Qt geometry as a tuple `(x, y, width, height)`.
    # These absolute coordinates are the basis of the static SimpleWx export.
    prop = _find_property(widget, name)
    if prop is None:
        return None
    rect = prop.find("rect")
    if rect is None:
        return None
    try:
        x = int((rect.findtext("x") or "0").strip())
        y = int((rect.findtext("y") or "0").strip())
        width = int((rect.findtext("width") or "0").strip())
        height = int((rect.findtext("height") or "0").strip())
    except ValueError as exc:
        raise BuilderError(f"Ungültige geometry-Property in '{widget_name}'.") from exc
    return (x, y, width, height)


def validate_static_only(root: ET.Element) -> None:
    # The builder intentionally supports only purely static UIs.
    # As soon as Qt layouts/sizers appear in the XML, abort with a clear error
    # instead of producing a half-correct output.
    dynamic_layout = root.find(".//layout")
    if dynamic_layout is not None:
        class_name = (dynamic_layout.get("class") or "layout").strip()
        name = (dynamic_layout.get("name") or class_name or "<unnamed>").strip()
        raise BuilderError(
            f"Nicht unterstützt: dynamisches Layout-Element '{class_name}' in '{name}'. "
            "Dieses Tool verarbeitet nur statische Qt-Designer UIs ohne Layout/Sizer."
        )

    for widget in root.findall(".//widget"):
        widget_class = (widget.get("class") or "").strip()
        if widget_class not in UNSUPPORTED_WIDGET_CLASSES:
            continue
        widget_name = (widget.get("name") or widget_class or "<unnamed>").strip()
        raise BuilderError(
            f"Unsupported widget class '{widget_class}' in '{widget_name}'. "
            f"{UNSUPPORTED_WIDGET_CLASSES[widget_class]}"
        )


def _find_top_level_widget(root: ET.Element) -> ET.Element:
    for widget in root.findall("./widget"):
        widget_class = (widget.get("class") or "").strip()
        if widget_class in SUPPORTED_TOP_LEVEL_CLASSES:
            return widget

    raise BuilderError(
        "Keine unterstützte Top-Level-Widget-Definition gefunden. "
        "Erwartet wird eine Qt-Designer .ui Datei mit QMainWindow, QDialog, QFileDialog oder QMessageBox."
    )


def _normalize_signal_name(raw: str) -> str:
    # Turn e.g. "clicked()" into a Python-safe signal name so stable handler
    # names can be generated from it.
    signal_name = raw.split("(", 1)[0].strip().lower()
    clean = "".join(ch if ch.isalnum() else "_" for ch in signal_name)
    clean = clean.strip("_")
    return clean or "signal"


def _map_qt_icon_to_simplewx_icon(icon_name: str) -> Optional[str]:
    normalized = icon_name.strip()
    if "::" in normalized:
        normalized = normalized.split("::")[-1]

    if normalized and any(ch.isupper() for ch in normalized):
        parts: List[str] = []
        for index, char in enumerate(normalized):
            if index > 0 and char.isupper() and (
                normalized[index - 1].islower()
                or (index + 1 < len(normalized) and normalized[index + 1].islower())
            ):
                parts.append("-")
            parts.append(char.lower())
        normalized = "".join(parts)

    normalized = normalized.replace("_", "-").strip().lower()
    if not normalized:
        return None

    icon_map = {
        "document-open": "gtk-open",
        "document-save": "gtk-save",
        "document-save-as": "gtk-save-as",
        "document-new": "gtk-new",
        "edit-copy": "gtk-copy",
        "edit-cut": "gtk-cut",
        "edit-paste": "gtk-paste",
        "edit-delete": "gtk-delete",
        "application-exit": "gtk-quit",
        "help-browser": "gtk-help",
        "edit-find": "gtk-find",
        "go-home": "gtk-home",
        "go-previous": "gtk-go-back",
        "go-next": "gtk-go-forward",
        "view-refresh": "gtk-refresh",
        "edit-undo": "gtk-undo",
        "dialog-information": "gtk-info",
        "dialog-warning": "gtk-warning",
        "dialog-error": "gtk-error",
    }
    return icon_map.get(normalized, normalized)


def _map_qt_signal_to_simplewx_event(qt_class: str, qt_signal: str) -> Optional[str]:
    signal_name = _normalize_signal_name(qt_signal)
    signal_map: Dict[str, Dict[str, str]] = {
        "QAction": {
            "triggered": "wx.EVT_MENU",
            "toggled": "wx.EVT_MENU",
        },
        "QPushButton": {
            "clicked": "wx.EVT_BUTTON",
        },
        "QCheckBox": {
            "clicked": "wx.EVT_CHECKBOX",
            "toggled": "wx.EVT_CHECKBOX",
            "statechanged": "wx.EVT_CHECKBOX",
        },
        "QRadioButton": {
            "clicked": "wx.EVT_RADIOBUTTON",
            "toggled": "wx.EVT_RADIOBUTTON",
        },
        "QLineEdit": {
            "textchanged": "wx.EVT_TEXT",
            "textedited": "wx.EVT_TEXT",
        },
        "QTextEdit": {
            "textchanged": "wx.EVT_TEXT",
        },
        "QSpinBox": {
            "valuechanged": "wx.EVT_SPINCTRL",
        },
        "QComboBox": {
            "activated": "wx.EVT_COMBOBOX",
            "currentindexchanged": "wx.EVT_COMBOBOX",
            "currenttextchanged": "wx.EVT_COMBOBOX",
        },
        "QSlider": {
            "actiontriggered": "wx.EVT_SLIDER",
            "slidermoved": "wx.EVT_SLIDER",
            "sliderpressed": "wx.EVT_SLIDER",
            "sliderreleased": "wx.EVT_SLIDER",
            "valuechanged": "wx.EVT_SLIDER",
        },
        "QTabWidget": {
            "currentchanged": "wx.EVT_NOTEBOOK_PAGE_CHANGED",
        },
        "QFontComboBox": {
            "currentfontchanged": "wx.EVT_FONTPICKER_CHANGED",
            "currentindexchanged": "wx.EVT_COMBOBOX",
        },
    }
    return signal_map.get(qt_class, {}).get(signal_name)


def _slot_body_lines(receiver_name: str, qt_slot: str) -> List[str]:
    """Map a Qt receiver slot to simplewx handler body lines."""
    slot_base = qt_slot.split("(")[0].strip()
    if slot_base == "click":
        return [
            f"    {receiver_name} = win.get_widget({quote(receiver_name)})",
            f"    if {receiver_name}: {receiver_name}.SetValue(not {receiver_name}.GetValue())",
        ]
    if slot_base == "show":
        return [
            f"    {receiver_name} = win.get_widget({quote(receiver_name)})",
            f"    if {receiver_name}: {receiver_name}.Show()",
        ]
    if slot_base == "hide":
        return [
            f"    {receiver_name} = win.get_widget({quote(receiver_name)})",
            f"    if {receiver_name}: {receiver_name}.Hide()",
        ]
    return []


def parse_connections(root: ET.Element) -> Dict[str, List[ConnectionSpec]]:
    # Build a mapping "widget name -> handler name" from the Qt <connections>
    # block. The renderer later turns this back into `Function=...`.
    handlers: Dict[str, List[ConnectionSpec]] = {}
    for conn in root.findall("./connections/connection"):
        sender = (conn.findtext("sender") or "").strip()
        signal = (conn.findtext("signal") or "").strip()
        if not sender or not signal:
            continue
        receiver = (conn.findtext("receiver") or "").strip()
        slot = (conn.findtext("slot") or "").strip()
        sender_name = sanitize_name(sender, "widget", 0)
        signal_name = _normalize_signal_name(signal)
        receiver_name = sanitize_name(receiver, "widget", 0) if receiver else ""
        body = _slot_body_lines(receiver_name, slot) if receiver_name and slot else []
        handlers.setdefault(sender_name, []).append(
            ConnectionSpec(
                handler_name=f"on_{sender_name}_{signal_name}",
                qt_signal=signal,
                body=body,
            )
        )
    return handlers


def _pick_widget_connection(
    qt_class: str,
    connections: List[ConnectionSpec],
) -> Tuple[Optional[ConnectionSpec], Optional[str], Optional[str]]:
    if not connections:
        return None, None, None

    for connection in connections:
        mapped_signal = _map_qt_signal_to_simplewx_event(qt_class, connection.qt_signal)
        if mapped_signal is not None:
            return connection, connection.handler_name, mapped_signal

    fallback = connections[0]
    return fallback, fallback.handler_name, _map_qt_signal_to_simplewx_event(qt_class, fallback.qt_signal)


def _collect_action_specs(
    main_widget: ET.Element,
    handlers: Dict[str, List[ConnectionSpec]],
    ui_path: Path,
    resource_paths: Dict[str, str],
) -> Dict[str, ActionSpec]:
    action_specs: Dict[str, ActionSpec] = {}

    for action in main_widget.findall("./action"):
        action_name = sanitize_name((action.get("name") or "").strip(), "action", len(action_specs) + 1)
        action_title = _property_string(action, "text") or action_name
        action_connections = handlers.get(action_name, [])
        connection, handler_name, mapped_signal = _pick_widget_connection("QAction", action_connections)
        action_specs[action_name] = ActionSpec(
            name=action_name,
            title=action_title,
            tooltip=_property_string(action, "toolTip"),
            icon=_property_icon(action, "icon", ui_path, resource_paths, action_name),
            checkable=_property_bool(action, "checkable"),
            checked=_property_bool(action, "checked"),
            handler_name=handler_name,
            signal=mapped_signal,
        )

    return action_specs


def parse_menus(
    main_widget: ET.Element,
    action_specs: Dict[str, ActionSpec],
) -> Tuple[Optional[str], List[MenuSpec], int]:
    # Menus are processed separately from the normal widget stream because Qt
    # describes them as a QMenuBar/QMenu/QAction structure rather than ordinary
    # visible widgets in the central area.
    menubar_widget = main_widget.find("./widget[@class='QMenuBar']")
    if menubar_widget is None:
        return None, [], 0

    menubar_name = sanitize_name((menubar_widget.get("name") or "menubar").strip(), "menubar", 0)
    menubar_geometry = _property_rect(menubar_widget, "geometry", menubar_name)
    menu_height = menubar_geometry[3] if menubar_geometry is not None else 0

    menus: List[MenuSpec] = []
    running_menu_index = 1
    used_item_names: Dict[str, int] = {}

    for menu_widget in menubar_widget.findall("./widget[@class='QMenu']"):
        menu_name = sanitize_name((menu_widget.get("name") or "").strip(), "menu", running_menu_index)
        menu_title = _property_string(menu_widget, "title") or menu_name

        # Within each menu, referenced actions are converted into concrete menu
        # item specs for output generation.
        items: List[MenuItemSpec] = []
        for addaction in menu_widget.findall("addaction"):
            raw_action_name = (addaction.get("name") or "").strip()
            if not raw_action_name:
                continue

            if raw_action_name == "separator":
                separator_name = sanitize_name(f"{menu_name}_separator_{len(items) + 1}", "separator", len(items) + 1)
                items.append(MenuItemSpec(name=separator_name, title="", item_type="separator"))
                continue

            action_name = sanitize_name(raw_action_name, "action", len(items) + 1)
            action_spec = action_specs.get(action_name)
            action_title = action_spec.title if action_spec is not None else action_name

            # The same QAction name can appear in multiple menus, so enforce a
            # unique internal name here.
            unique_name = action_name
            seen = used_item_names.get(unique_name, 0)
            if seen > 0:
                unique_name = f"{menu_name}_{action_name}_{seen + 1}"
            used_item_names[action_name] = seen + 1

            items.append(
                MenuItemSpec(
                    name=unique_name,
                    title=action_title,
                    item_type="item",
                    tooltip=action_spec.tooltip if action_spec is not None else None,
                    icon=action_spec.icon if action_spec is not None else None,
                    handler_name=action_spec.handler_name if action_spec is not None else None,
                    signal=action_spec.signal if action_spec is not None else None,
                )
            )

        menus.append(MenuSpec(name=menu_name, title=menu_title, items=items))
        running_menu_index += 1

    return menubar_name, menus, menu_height


def _toolbar_orientation(toolbar_el: ET.Element) -> str:
    orientation = (_property_enum(toolbar_el, "orientation") or "").lower()
    if "vertical" in orientation:
        return "vertical"

    for attr in toolbar_el.findall("attribute"):
        if (attr.get("name") or "").strip() != "toolBarArea":
            continue
        area_text = "".join(attr.itertext()).strip().lower()
        if "left" in area_text or "right" in area_text:
            return "vertical"
        break

    return "horizontal"


def parse_toolbars(main_widget: ET.Element, action_specs: Dict[str, ActionSpec]) -> List[ToolbarSpec]:
    toolbars: List[ToolbarSpec] = []

    for index, toolbar_el in enumerate(main_widget.findall("./widget[@class='QToolBar']"), start=1):
        toolbar_name = sanitize_name((toolbar_el.get("name") or "toolbar").strip(), "toolbar", index)
        geometry = _property_rect(toolbar_el, "geometry", toolbar_name)
        position = (geometry[0], geometry[1]) if geometry is not None else (0, 0)
        size = (geometry[2], geometry[3]) if geometry is not None else None
        title = _property_string(toolbar_el, "windowTitle") or toolbar_name
        orient = _toolbar_orientation(toolbar_el)

        items: List[ToolbarItemSpec] = []
        for addaction in toolbar_el.findall("addaction"):
            raw_action_name = (addaction.get("name") or "").strip()
            if not raw_action_name:
                continue

            if raw_action_name == "separator":
                items.append(ToolbarItemSpec(name=f"{toolbar_name}_separator_{len(items) + 1}", title="", kind="separator"))
                continue

            action_name = sanitize_name(raw_action_name, "action", len(items) + 1)
            action_spec = action_specs.get(action_name)
            kind = "check" if action_spec is not None and action_spec.checkable else "normal"
            active = action_spec.checked if action_spec is not None else 0
            items.append(
                ToolbarItemSpec(
                    name=action_name,
                    title=action_spec.title if action_spec is not None else action_name,
                    kind=kind,
                    tooltip=action_spec.tooltip if action_spec is not None else None,
                    icon=action_spec.icon if action_spec is not None else None,
                    active=active,
                )
            )

        toolbars.append(
            ToolbarSpec(
                name=toolbar_name,
                title=title,
                position=position,
                size=size,
                orient=orient,
                items=items,
            )
        )

    return toolbars


def parse_window(main_widget: ET.Element, menu_height: int = 0) -> WindowSpec:
    # Read only the main window's basic data here. Actual widget generation is
    # handled later in a separate step.
    frame_name = sanitize_name(main_widget.get("name") or "mainWindow", "window", 0)
    frame_title = _property_string(main_widget, "windowTitle") or frame_name
    has_statusbar = (
        (main_widget.get("class") or "").strip() == "QMainWindow"
        and main_widget.find("./widget[@class='QStatusBar']") is not None
    )

    geometry = _property_rect(main_widget, "geometry", frame_name)
    frame_size: Optional[Tuple[int, int]] = None
    if geometry is not None:
        width = geometry[2]
        height = geometry[3]
        frame_size = (width, height)

    return WindowSpec(name=frame_name, title=frame_title, size=frame_size, statusbar=has_statusbar)


def _iter_supported_widgets(
    parent: ET.Element,
    _offset_x: int = 0,
    _offset_y: int = 0,
    _group_name: Optional[str] = None,
) -> List[Tuple[ET.Element, int, int, Optional[str]]]:
    """
    Walk the XML tree recursively and collect only widget classes that this
    builder can actually translate into SimpleWx calls.

    Non-supported containers like QGroupBox are transparently traversed and
    their coordinates are accumulated so child widgets land at correct
    absolute (centralwidget-relative) positions.

    Returns a list of (element, offset_x, offset_y, group_name) tuples.
    The caller must add offset_x/offset_y to the XML-stored x/y values to
    obtain the correct absolute position.
    """
    items: List[Tuple[ET.Element, int, int, Optional[str]]] = []
    for child in parent.findall("widget"):
        child_class = (child.get("class") or "").strip()
        child_name_raw = sanitize_name((child.get("name") or "widget").strip(), "widget", 0)
        if child_class in SUPPORTED_WIDGET_CLASSES or child_class == SUPPORTED_DIALOG_BUTTON_BOX_CLASS:
            items.append((child, _offset_x, _offset_y, _group_name))
            # Keep legacy behavior for most supported classes.
            # Exception: QFrame is a real geometric container, so propagate its
            # offset for nested content (e.g. QGroupBox -> QRadioButton).
            if child_class == "QFrame":
                child_rect = _property_rect(child, "geometry", child_name_raw)
                if child_rect is not None:
                    next_ox = _offset_x + child_rect[0]
                    next_oy = _offset_y + child_rect[1]
                else:
                    next_ox, next_oy = _offset_x, _offset_y
            else:
                next_ox, next_oy = _offset_x, _offset_y
            items.extend(_iter_supported_widgets(child, next_ox, next_oy, _group_name))
        elif child_class == "QGroupBox":
            # QGroupBox is a logical grouping container (commonly used for radio
            # buttons). It is not rendered in output but its position must be
            # added to all child coordinates.
            child_rect = _property_rect(child, "geometry", child_name_raw)
            if child_rect is not None:
                gb_ox = _offset_x + child_rect[0]
                gb_oy = _offset_y + child_rect[1]
            else:
                gb_ox, gb_oy = _offset_x, _offset_y
            gb_title = _property_string(child, "title") or (child.get("name") or "")
            gb_group = sanitize_name(gb_title, "group", 0) if gb_title else _group_name
            items.extend(_iter_supported_widgets(child, gb_ox, gb_oy, gb_group))
        elif child_class == "QTabWidget":
            # Notebook widgets are parsed in a dedicated pass so page scoping
            # can be preserved in the generated output.
            continue
        elif child_class in {"QSplitter", "QToolBar"}:
            # Splitters and toolbars are rendered in dedicated passes because
            # they need multi-call output and/or action resolution.
            continue
        else:
            # Any other non-supported container: recurse without changing offsets.
            items.extend(_iter_supported_widgets(child, _offset_x, _offset_y, _group_name))
    return items


def _widget_from_element(
    widget_el: ET.Element,
    handlers: Dict[str, List[ConnectionSpec]],
    running_index: int,
    offset_x: int = 0,
    offset_y: int = 0,
    group_name: Optional[str] = None,
    container: Optional[str] = None,
    geometry_override: Optional[Tuple[int, int, int, int]] = None,
) -> WidgetSpec:
    qt_class = (widget_el.get("class") or "").strip()
    raw_name = (widget_el.get("name") or "").strip()
    widget_name = sanitize_name(raw_name, "widget", running_index)

    geometry = _property_rect(widget_el, "geometry", widget_name)
    if geometry is None:
        geometry = geometry_override
    if geometry is None:
        raise BuilderError(
            f"Widget '{widget_name}' ({qt_class}) hat keine geometry-Property. "
            "Für statische Qt-Layouts sind absolute Koordinaten zwingend erforderlich."
        )

    raw_x, raw_y, width, height = geometry
    x = raw_x + offset_x
    y = raw_y + offset_y

    text = _property_string(widget_el, "text") or _property_string(widget_el, "title") or ""
    tooltip = _property_string(widget_el, "toolTip")
    checked = _property_bool(widget_el, "checked") if qt_class in {"QCheckBox", "QRadioButton"} else 0
    widget_connections = handlers.get(widget_name, [])
    _connection, handler_name, signal = _pick_widget_connection(qt_class, widget_connections)

    extra: Dict[str, Any] = {}
    if qt_class == "QTextEdit":
        text_view_text = _property_string(widget_el, "plainText") or _property_string(widget_el, "html") or ""
        if text_view_text:
            extra["text"] = text_view_text
    if qt_class == "QSpinBox":
        spin_value = _property_string(widget_el, "value")
        if spin_value is not None and spin_value.strip() != "":
            extra["start"] = spin_value.strip()
    if qt_class == "QComboBox":
        combo_items: List[str] = []
        for item in widget_el.findall("item"):
            item_text = _property_string(item, "text")
            if item_text is not None:
                combo_items.append(item_text)
        extra["data"] = combo_items
        combo_index = _property_number(widget_el, "currentIndex")
        if combo_index is not None and combo_index.strip() != "":
            extra["start"] = combo_index.strip()
    if qt_class == "QSlider":
        orientation = (_property_enum(widget_el, "orientation") or "Qt::Orientation::Horizontal").lower()
        extra["orientation"] = "vertical" if "vertical" in orientation else "horizontal"
        for source_name, target_name in (
            ("minimum", "minimum"),
            ("maximum", "maximum"),
            ("singleStep", "step"),
            ("value", "start"),
        ):
            number_value = _property_number(widget_el, source_name)
            if number_value is not None and number_value.strip() != "":
                extra[target_name] = number_value.strip()
    if qt_class == "QProgressBar":
        orientation = (_property_enum(widget_el, "orientation") or "Qt::Orientation::Horizontal").lower()
        extra["orientation"] = "vertical" if "vertical" in orientation else "horizontal"
        minimum_raw = _property_number(widget_el, "minimum") or "0"
        maximum_raw = _property_number(widget_el, "maximum") or "100"
        value_raw = _property_number(widget_el, "value") or "0"
        try:
            minimum_value = int(round(float(minimum_raw)))
            maximum_value = int(round(float(maximum_raw)))
            current_value = int(round(float(value_raw)))
        except ValueError:
            minimum_value = 0
            maximum_value = 100
            current_value = 0
        if maximum_value < minimum_value:
            minimum_value, maximum_value = maximum_value, minimum_value
        steps = max(1, maximum_value - minimum_value)
        current_value = max(minimum_value, min(current_value, maximum_value))
        extra["steps"] = steps
        extra["value"] = current_value - minimum_value
    if qt_class in {"QListWidget", "QListView"}:
        list_items: List[List[str]] = []
        if qt_class == "QListWidget":
            for item in widget_el.findall("item"):
                item_text = _property_string(item, "text")
                if item_text is not None:
                    list_items.append([item_text])
        extra["headers"] = ["Items"]
        extra["data"] = list_items
    if qt_class in {"QTableWidget", "QTableView"}:
        columns = _int_from_property(widget_el, "columnCount", default=0)
        rows = _int_from_property(widget_el, "rowCount", default=0)

        headers: List[str] = []
        for index, column in enumerate(widget_el.findall("column"), start=1):
            header_text = _property_string(column, "text")
            headers.append(header_text if header_text else f"Column {index}")

        required_columns = max(columns, len(headers), 1)
        while len(headers) < required_columns:
            headers.append(f"Column {len(headers) + 1}")

        table_data = [["" for _ in range(required_columns)] for _ in range(max(rows, 0))]
        extra["headers"] = headers
        extra["data"] = table_data
    if qt_class in {"QTreeWidget", "QTreeView"}:
        tree_headers: List[str] = []
        for index, column in enumerate(widget_el.findall("column"), start=1):
            header_text = _property_string(column, "text")
            tree_headers.append(header_text if header_text else f"Column {index}")
        if not tree_headers:
            tree_headers = ["Tree"]
        extra["headers"] = tree_headers
        extra["data"] = []
        extra["tree_type"] = "Tree"
    if qt_class == "QFrame":
        frame_shape = (_property_enum(widget_el, "frameShape") or "").lower()
        if "hline" in frame_shape:
            extra["separator_orientation"] = "horizontal"
        elif "vline" in frame_shape:
            extra["separator_orientation"] = "vertical"
    if qt_class == "Line":
        line_orient = (_property_enum(widget_el, "orientation") or "").lower()
        if "vertical" in line_orient:
            extra["separator_orientation"] = "vertical"
        else:
            extra["separator_orientation"] = "horizontal"
    if qt_class == "QFontComboBox":
        font_prop = _find_property(widget_el, "currentFont")
        if font_prop is not None:
            font_el = font_prop.find("font")
            if font_el is not None:
                family = (font_el.findtext("family") or "").strip()
                try:
                    size_pt = int((font_el.findtext("pointsize") or "0").strip())
                except ValueError:
                    size_pt = 0
                bold_text = (font_el.findtext("bold") or "").strip().lower()
                bold = bold_text in ("true", "1", "yes")
                if family:
                    extra["font_family"] = family
                if size_pt > 0:
                    extra["font_size"] = size_pt
                if bold:
                    extra["font_bold"] = True
    if qt_class == "QGraphicsView":
        stylesheet = _property_string(widget_el, "styleSheet") or ""
        if stylesheet:
            extra["raw_stylesheet"] = stylesheet

    return WidgetSpec(
        qt_class=qt_class,
        name=widget_name,
        position=(x, y),
        size=(width, height),
        title=text,
        tooltip=tooltip,
        checked=checked,
        handler_name=handler_name,
        signal=signal,
        group=group_name,
        container=container,
        extra=extra,
    )


def _parse_dialog_button_box_buttons(widget_el: ET.Element) -> List[str]:
    raw_buttons = _property_string(widget_el, "standardButtons") or ""
    button_tokens: List[str] = []

    for part in raw_buttons.split("|"):
        token = part.strip()
        if not token:
            continue
        if "::" in token:
            token = token.split("::")[-1]
        token = token.strip()
        if token:
            button_tokens.append(token)

    return button_tokens


def _dialog_button_box_button_title(token: str) -> str:
    title_map = {
        "Ok": "Ok",
        "Open": "Open",
        "Save": "Save",
        "SaveAll": "Save All",
        "Cancel": "Cancel",
        "Close": "Close",
        "Discard": "Discard",
        "Apply": "Apply",
        "Reset": "Reset",
        "RestoreDefaults": "Restore Defaults",
        "Help": "Help",
        "Yes": "Yes",
        "YesToAll": "Yes To All",
        "No": "No",
        "NoToAll": "No To All",
        "Abort": "Abort",
        "Retry": "Retry",
        "Ignore": "Ignore",
    }
    if token in title_map:
        return title_map[token]

    parts: List[str] = []
    for index, char in enumerate(token):
        if index > 0 and char.isupper() and token[index - 1].islower():
            parts.append(" ")
        parts.append(char)
    return "".join(parts) or token


def _dialog_button_matches_connection(token: str, connection: Optional[ConnectionSpec]) -> bool:
    if connection is None:
        return False

    signal_name = _normalize_signal_name(connection.qt_signal)
    accept_tokens = {"ok", "open", "save", "saveall", "apply", "yes", "yestoall", "retry"}
    reject_tokens = {"cancel", "close", "discard", "abort", "ignore", "no", "notoall", "reset"}
    lowered = token.strip().lower()

    if signal_name == "accepted":
        return lowered in accept_tokens
    if signal_name == "rejected":
        return lowered in reject_tokens
    return False


def _dialog_button_connection_for_token(
    token: str,
    connections: List[ConnectionSpec],
) -> Optional[ConnectionSpec]:
    for connection in connections:
        if _dialog_button_matches_connection(token, connection):
            return connection
    return None


def _dialog_button_box_specs_from_element(
    widget_el: ET.Element,
    handlers: Dict[str, List[ConnectionSpec]],
    running_index: int,
    offset_x: int = 0,
    offset_y: int = 0,
    container: Optional[str] = None,
) -> List[WidgetSpec]:
    raw_name = (widget_el.get("name") or "").strip()
    widget_name = sanitize_name(raw_name, "buttonbox", running_index)
    geometry = _property_rect(widget_el, "geometry", widget_name)
    if geometry is None:
        raise BuilderError(
            f"Widget '{widget_name}' ({SUPPORTED_DIALOG_BUTTON_BOX_CLASS}) hat keine geometry-Property. "
            "Für statische Qt-Layouts sind absolute Koordinaten zwingend erforderlich."
        )

    x = geometry[0] + offset_x
    y = geometry[1] + offset_y
    width = geometry[2]
    height = geometry[3]
    button_tokens = _parse_dialog_button_box_buttons(widget_el)
    if not button_tokens:
        return []

    orientation = (_property_enum(widget_el, "orientation") or "Qt::Orientation::Horizontal").lower()
    is_vertical = "vertical" in orientation
    spacing = 10
    buttonbox_connections = handlers.get(widget_name, [])
    specs: List[WidgetSpec] = []

    if is_vertical:
        total_spacing = spacing * max(0, len(button_tokens) - 1)
        button_height = max(24, (height - total_spacing) // max(1, len(button_tokens)))
        current_y = y
        for index, token in enumerate(button_tokens, start=0):
            button_name = sanitize_name(f"{widget_name}_{token.lower()}", "button", running_index + index)
            matched_connection = _dialog_button_connection_for_token(token, buttonbox_connections)
            handler_name = matched_connection.handler_name if matched_connection is not None else None
            handler_body = matched_connection.body if matched_connection is not None else []
            signal = "wx.EVT_BUTTON" if handler_name is not None else None
            specs.append(
                WidgetSpec(
                    qt_class="QPushButton",
                    name=button_name,
                    position=(x, current_y),
                    size=(width, button_height),
                    title=_dialog_button_box_button_title(token),
                    tooltip=None,
                    handler_name=handler_name,
                    handler_body=handler_body,
                    signal=signal,
                    container=container,
                )
            )
            current_y += button_height + spacing
        return specs

    total_spacing = spacing * max(0, len(button_tokens) - 1)
    button_width = max(80, (width - total_spacing) // max(1, len(button_tokens)))
    total_width = button_width * len(button_tokens) + total_spacing
    current_x = x + max(0, width - total_width)

    for index, token in enumerate(button_tokens, start=0):
        button_name = sanitize_name(f"{widget_name}_{token.lower()}", "button", running_index + index)
        matched_connection = _dialog_button_connection_for_token(token, buttonbox_connections)
        handler_name = matched_connection.handler_name if matched_connection is not None else None
        handler_body = matched_connection.body if matched_connection is not None else []
        signal = "wx.EVT_BUTTON" if handler_name is not None else None
        specs.append(
            WidgetSpec(
                qt_class="QPushButton",
                name=button_name,
                position=(current_x, y),
                size=(button_width, height),
                title=_dialog_button_box_button_title(token),
                tooltip=None,
                handler_name=handler_name,
                handler_body=handler_body,
                signal=signal,
                container=container,
            )
        )
        current_x += button_width + spacing

    return specs


def _widget_specs_from_element(
    widget_el: ET.Element,
    handlers: Dict[str, List[ConnectionSpec]],
    running_index: int,
    offset_x: int = 0,
    offset_y: int = 0,
    group_name: Optional[str] = None,
    container: Optional[str] = None,
    geometry_override: Optional[Tuple[int, int, int, int]] = None,
) -> List[WidgetSpec]:
    qt_class = (widget_el.get("class") or "").strip()
    if qt_class == SUPPORTED_DIALOG_BUTTON_BOX_CLASS:
        return _dialog_button_box_specs_from_element(
            widget_el,
            handlers,
            running_index,
            offset_x=offset_x,
            offset_y=offset_y,
            container=container,
        )

    return [
        _widget_from_element(
            widget_el,
            handlers,
            running_index,
            offset_x=offset_x,
            offset_y=offset_y,
            group_name=group_name,
            container=container,
            geometry_override=geometry_override,
        )
    ]


def _estimate_splitter_pane_sizes(size: Tuple[int, int], orient: str, split: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    width, height = size
    if orient == "horizontal":
        split_pos = max(1, min(split, max(1, width - 1)))
        return (split_pos, height), (max(1, width - split_pos), height)

    split_pos = max(1, min(split, max(1, height - 1)))
    return (width, split_pos), (width, max(1, height - split_pos))


def _iter_splitter_elements(
    parent: ET.Element,
    offset_x: int = 0,
    offset_y: int = 0,
) -> List[Tuple[ET.Element, int, int]]:
    items: List[Tuple[ET.Element, int, int]] = []
    for child in parent.findall("widget"):
        child_class = (child.get("class") or "").strip()
        child_name = sanitize_name((child.get("name") or "widget").strip(), "widget", 0)
        child_rect = _property_rect(child, "geometry", child_name)
        next_offset_x = offset_x + (child_rect[0] if child_rect is not None else 0)
        next_offset_y = offset_y + (child_rect[1] if child_rect is not None else 0)

        if child_class == "QSplitter":
            items.append((child, offset_x, offset_y))
            continue

        if child_class == "QTabWidget":
            continue

        items.extend(_iter_splitter_elements(child, next_offset_x, next_offset_y))

    return items


def parse_splitters(root: ET.Element, handlers: Dict[str, List[ConnectionSpec]]) -> List[SplitterSpec]:
    main_widget = _find_top_level_widget(root)

    splitters: List[SplitterSpec] = []
    running_index = 1

    for splitter_el, offset_x, offset_y in _iter_splitter_elements(main_widget):
        raw_name = (splitter_el.get("name") or "").strip()
        splitter_name = sanitize_name(raw_name, "splitter", len(splitters) + 1)
        geometry = _property_rect(splitter_el, "geometry", splitter_name)
        if geometry is None:
            raise BuilderError(
                f"Widget '{splitter_name}' (QSplitter) hat keine geometry-Property. "
                "Für statische Qt-Layouts sind absolute Koordinaten zwingend erforderlich."
            )

        x = geometry[0] + offset_x
        y = geometry[1] + offset_y
        width = geometry[2]
        height = geometry[3]
        orientation = (_property_enum(splitter_el, "orientation") or "Qt::Orientation::Vertical").lower()
        qt_layout = "horizontal" if "horizontal" in orientation else "vertical"

        # Recent fix: Qt and SimpleWx use opposite orientation labels for splitter direction:
        # - Qt horizontal   => side-by-side panes (vertical sash)
        # - SimpleWx vertical => SplitVertically (side-by-side panes)
        # - Qt vertical     => top/bottom panes (horizontal sash)
        # - SimpleWx horizontal => SplitHorizontally (top/bottom panes)
        orient = "vertical" if qt_layout == "horizontal" else "horizontal"

        split = (width // 2) if qt_layout == "horizontal" else (height // 2)
        pane_sizes = _estimate_splitter_pane_sizes((width, height), qt_layout, split)
        splitter_connections = handlers.get(splitter_name, [])
        connection = splitter_connections[0] if splitter_connections else None

        panes: List[SplitterPaneSpec] = []
        pane_index = 0
        for child in splitter_el.findall("widget"):
            side = "first" if pane_index == 0 else "second"
            pane_name = f"{splitter_name}_{side}pane"
            pane_widget_items: List[WidgetSpec] = []
            child_class = (child.get("class") or "").strip()

            if child_class in SUPPORTED_WIDGET_CLASSES or child_class == SUPPORTED_DIALOG_BUTTON_BOX_CLASS:
                pane_width, pane_height = pane_sizes[min(pane_index, 1)]
                created_widgets = _widget_specs_from_element(
                    child,
                    handlers,
                    running_index,
                    container=pane_name,
                    geometry_override=(0, 0, pane_width, pane_height),
                )
                pane_widget_items.extend(created_widgets)
                running_index += len(created_widgets)
            else:
                for widget_el, child_offset_x, child_offset_y, group_name in _iter_supported_widgets(child):
                    created_widgets = _widget_specs_from_element(
                        widget_el,
                        handlers,
                        running_index,
                        offset_x=child_offset_x,
                        offset_y=child_offset_y,
                        group_name=group_name,
                        container=pane_name,
                    )
                    pane_widget_items.extend(created_widgets)
                    running_index += len(created_widgets)

            panes.append(SplitterPaneSpec(name=pane_name, side=side, widgets=pane_widget_items))
            pane_index += 1
            if pane_index >= 2:
                break

        splitters.append(
            SplitterSpec(
                name=splitter_name,
                position=(x, y),
                size=(width, height),
                orient=orient,
                split=split,
                panes=panes,
                handler_name=connection.handler_name if connection is not None else None,
                signal=None,
            )
        )

    return splitters


def _tab_page_title(page_widget: ET.Element, fallback: str) -> str:
    for attr in page_widget.findall("attribute"):
        if (attr.get("name") or "").strip() == "title":
            if len(attr) > 0:
                title = "".join(attr[0].itertext()).strip()
                if title:
                    return title
            raw = "".join(attr.itertext()).strip()
            if raw:
                return raw
    return fallback


def parse_notebooks(root: ET.Element, handlers: Dict[str, List[ConnectionSpec]]) -> Tuple[List[NotebookSpec], List[WidgetSpec]]:
    main_widget = _find_top_level_widget(root)

    notebooks: List[NotebookSpec] = []
    page_widgets: List[WidgetSpec] = []
    running_index = 1

    for notebook_el in main_widget.findall(".//widget[@class='QTabWidget']"):
        raw_name = (notebook_el.get("name") or "").strip()
        notebook_name = sanitize_name(raw_name, "notebook", len(notebooks) + 1)
        geometry = _property_rect(notebook_el, "geometry", notebook_name)
        if geometry is None:
            raise BuilderError(
                f"Widget '{notebook_name}' (QTabWidget) hat keine geometry-Property. "
                "Für statische Qt-Layouts sind absolute Koordinaten zwingend erforderlich."
            )

        x, y, width, height = geometry
        notebook_connections = handlers.get(notebook_name, [])
        connection = notebook_connections[0] if notebook_connections else None
        pages: List[NotebookPageSpec] = []

        page_index = 0
        for page_el in notebook_el.findall("widget"):
            if (page_el.get("class") or "").strip() != "QWidget":
                continue

            page_raw_name = (page_el.get("name") or "").strip()
            page_name = sanitize_name(page_raw_name, f"{notebook_name}_page", page_index + 1)
            page_title = _tab_page_title(page_el, page_name)

            pages.append(
                NotebookPageSpec(
                    name=page_name,
                    title=page_title,
                    notebook=notebook_name,
                    position_number=page_index,
                )
            )

            for widget_el, offset_x, offset_y, group_name in _iter_supported_widgets(page_el):
                created_widgets = _widget_specs_from_element(
                    widget_el,
                    handlers,
                    running_index,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    group_name=group_name,
                    container=page_name,
                )
                page_widgets.extend(created_widgets)
                running_index += len(created_widgets)

            page_index += 1

        notebooks.append(
            NotebookSpec(
                name=notebook_name,
                position=(x, y),
                size=(width, height),
                pages=pages,
                handler_name=connection.handler_name if connection is not None else None,
                signal=_map_qt_signal_to_simplewx_event("QTabWidget", connection.qt_signal) if connection is not None else None,
            )
        )

    return notebooks, page_widgets


def _apply_frame_title_labels(widgets: List[WidgetSpec]) -> List[WidgetSpec]:
    """
    Maps QLabel widgets named `label_<frame_name>` to QFrame titles.

    The matched label text is moved into the target frame `title` and the
    QLabel is removed from output so the generated starter script does not
    emit a separate `add_label(...)` call for frame captions.
    """
    frame_by_name: Dict[str, WidgetSpec] = {
        widget.name: widget for widget in widgets if widget.qt_class == "QFrame"
    }
    frame_by_name_lower: Dict[str, WidgetSpec] = {
        widget.name.lower(): widget for widget in widgets if widget.qt_class == "QFrame"
    }

    consumed_labels: set[str] = set()

    def _candidate_frame_names(label_name: str) -> List[str]:
        if not label_name.startswith("label_"):
            return []

        suffix = label_name[len("label_"):]
        candidates: List[str] = []

        # Direct case: label_<frame_name> -> <frame_name>
        candidates.append(suffix)

        # Common naming variant from imported files: ..._Frame
        if suffix.endswith("_Frame"):
            candidates.append(suffix[:-6])
        if suffix.endswith("_frame"):
            candidates.append(suffix[:-6])

        # Also allow variants that already include an explicit frame_ prefix.
        if suffix.startswith("frame_"):
            candidates.append(suffix)
            if suffix.endswith("_Frame"):
                candidates.append(suffix[:-6])
            if suffix.endswith("_frame"):
                candidates.append(suffix[:-6])
        else:
            candidates.append(f"frame_{suffix}")
            if suffix.endswith("_Frame"):
                candidates.append(f"frame_{suffix[:-6]}")
            if suffix.endswith("_frame"):
                candidates.append(f"frame_{suffix[:-6]}")

        # Preserve order while removing duplicates.
        seen: set[str] = set()
        ordered: List[str] = []
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                ordered.append(candidate)
        return ordered

    for widget in widgets:
        if widget.qt_class != "QLabel":
            continue
        if not widget.name.startswith("label_"):
            continue

        # Find the first matching target frame using the possible name variants.
        frame_widget: Optional[WidgetSpec] = None
        for target_frame_name in _candidate_frame_names(widget.name):
            frame_widget = frame_by_name.get(target_frame_name)
            if frame_widget is None:
                frame_widget = frame_by_name_lower.get(target_frame_name.lower())
            if frame_widget is not None:
                break
        if frame_widget is None:
            continue

        # When a matching label is found, move its text into the frame title and
        # suppress the label itself from the generated output.
        if widget.title:
            frame_widget.title = widget.title
        if widget.size is not None:
            frame_widget.frame_title_height = max(0, int(widget.size[1]))
        consumed_labels.add(widget.name)

    filtered_widgets: List[WidgetSpec] = []
    for widget in widgets:
        if widget.qt_class == "QLabel" and widget.name in consumed_labels:
            continue
        filtered_widgets.append(widget)
    return filtered_widgets


def _assign_widgets_to_frames(widgets: List[WidgetSpec]) -> List[WidgetSpec]:
    """
    Assigns widgets to the smallest containing frame and converts positions to
    frame-local coordinates for `Frame=<name>` output.
    """
    # Only real QFrames with geometry are valid container candidates.
    frames = [
        widget
        for widget in widgets
        if widget.qt_class == "QFrame"
        and widget.size is not None
        and "separator_orientation" not in widget.extra
    ]
    if not frames:
        return widgets

    for widget in widgets:
        if widget.qt_class == "QFrame" or widget.size is None:
            continue

        wx, wy = widget.position
        ww, wh = widget.size

        # A widget may geometrically fit into multiple frames.
        # In that case, choose the smallest matching frame below.
        candidates: List[WidgetSpec] = []
        for frame in frames:
            if frame.container != widget.container:
                continue
            fx, fy = frame.position
            fw, fh = frame.size
            if wx >= fx and wy >= fy and (wx + ww) <= (fx + fw) and (wy + wh) <= (fy + fh):
                candidates.append(frame)

        if not candidates:
            continue

        # The smallest enclosing frame wins.
        candidates.sort(key=lambda frame: frame.size[0] * frame.size[1] if frame.size is not None else 0)
        target = candidates[0]

        # Convert to frame-local coordinates without any extra border subtraction.
        widget.frame = target.name
        local_x = wx - target.position[0]
        local_y = wy - target.position[1]
        widget.position = (max(0, local_x), max(0, local_y))

    # Short title frames lose usable height at the top in wx because of the
    # StaticBox title area. Enlarge compact frames by the top gap to the first
    # child widget so the bottom spacing stays closer to the Qt original.
    for frame in frames:
        if frame.size is None:
            continue

        frame_width, frame_height = frame.size
        if frame_height > 80:
            continue

        # Only the Y positions of already assigned child widgets matter here.
        child_positions = [
            child.position[1]
            for child in widgets
            if child.frame == frame.name and child.size is not None
        ]
        if not child_positions:
            continue

        top_margin = min(child_positions)
        if top_margin <= 0:
            continue

        frame.size = (frame_width, frame_height + top_margin)

    return widgets


def _adjust_spinbox_min_size_and_adjacent_labels(widgets: List[WidgetSpec]) -> List[WidgetSpec]:
    """
    Enforces a minimum QSpinBox width and shifts directly adjacent right-side
    labels by the same delta so the original horizontal gap is preserved.
    """
    spin_widgets = [widget for widget in widgets if widget.qt_class == "QSpinBox" and widget.size is not None]
    if not spin_widgets:
        return widgets

    for spin in spin_widgets:
        spin_x, spin_y = spin.position
        spin_width, spin_height = spin.size
        if spin_width >= MIN_SPINBOX_WIDTH:
            continue

        delta = MIN_SPINBOX_WIDTH - spin_width
        spin_old_right = spin_x + spin_width
        spin_bottom = spin_y + spin_height
        spin.size = (MIN_SPINBOX_WIDTH, spin_height)

        for label in widgets:
            if label.qt_class != "QLabel" or label.size is None:
                continue
            if label is spin:
                continue
            if label.frame != spin.frame:
                continue
            if label.container != spin.container:
                continue

            label_x, label_y = label.position
            _label_width, label_height = label.size

            if label_x < spin_old_right:
                continue

            # Keep the adjustment tight: only labels that are horizontally to
            # the right and vertically aligned to the spin control are shifted.
            label_center_y = label_y + (label_height / 2.0)
            if label_center_y < (spin_y - 4) or label_center_y > (spin_bottom + 4):
                continue

            original_gap = label_x - spin_old_right
            if original_gap < 0 or original_gap > 60:
                continue

            label.position = (label_x + delta, label_y)

    return widgets


def parse_widgets(root: ET.Element, handlers: Dict[str, List[ConnectionSpec]]) -> List[WidgetSpec]:
    # Central parser for all visible, supported Qt widgets.
    # Raw XML nodes are converted into `WidgetSpec` objects here.
    main_widget = _find_top_level_widget(root)

    widgets: List[WidgetSpec] = []
    running_index = 1

    # First read all widgets with their absolute geometry.
    for widget_el, offset_x, offset_y, group_name in _iter_supported_widgets(main_widget):
        created_widgets = _widget_specs_from_element(
            widget_el,
            handlers,
            running_index,
            offset_x=offset_x,
            offset_y=offset_y,
            group_name=group_name,
            container=None,
        )
        widgets.extend(created_widgets)
        running_index += len(created_widgets)

    return widgets


def quote(text: str) -> str:
    # `repr` directly produces Python-compatible string literals for output.
    return repr(text)


def _format_call(function_name: str, args: List[str], force_multiline: bool = False) -> str:
    # Global output rule:
    # - fewer than 5 parameters => single line
    # - 5 or more parameters  => one parameter per line
    if len(args) <= 4 and not force_multiline:
        return f"{function_name}({', '.join(args)})"

    lines = [f"{function_name}("]
    for arg in args:
        lines.append(f"    {arg},")
    lines.append(")")
    return "\n".join(lines)


def build_widget_call(widget: WidgetSpec, container_frame: Optional[str] = None) -> str:
    # Translate one parsed widget into exactly one SimpleWx call.
    x, y = widget.position
    width, height = widget.size if widget.size is not None else (120, 28)
    effective_frame = widget.frame if widget.frame else container_frame

    if widget.qt_class == "QLabel":
        title = widget.title or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_label", args)

    if widget.qt_class == "QPushButton":
        title = widget.title or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Size=[{width}, {height}]",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_button", args)

    if widget.qt_class == "QLineEdit":
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if widget.title:
            args.append(f"Title={quote(widget.title)}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_entry", args)

    if widget.qt_class == "QCheckBox":
        title = widget.title or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Active={widget.checked}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_check_button", args)

    if widget.qt_class == "QRadioButton":
        title = widget.title or widget.name
        # Radio buttons always need a group in SimpleWx.
        # Use the QGroupBox title as the group when available; otherwise fall
        # back to a frame-specific or global default name.
        default_group = widget.group or (f"group_{effective_frame}" if effective_frame else "group_main")
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Group={quote(default_group)}",
            f"Active={widget.checked}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_radio_button", args)

    if widget.qt_class == "QTextEdit":
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if "text" in widget.extra:
            args.append(f"Text={quote(widget.extra['text'])}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_text_view", args)

    if widget.qt_class == "QSpinBox":
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if "start" in widget.extra:
            args.append(f"Start={widget.extra['start']}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_spin_button", args)

    if widget.qt_class == "QComboBox":
        data = widget.extra.get("data", [])
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Data={repr(data)}",
            f"Size=[{width}, {height}]",
        ]
        if "start" in widget.extra:
            args.append(f"Start={widget.extra['start']}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_combo_box", args)

    if widget.qt_class == "QSlider":
        orientation = str(widget.extra.get("orientation", "horizontal"))
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Orientation={quote(orientation)}",
            f"Size=[{width}, {height}]",
        ]
        for key, label in (("start", "Start"), ("minimum", "Minimum"), ("maximum", "Maximum"), ("step", "Step")):
            if key in widget.extra:
                args.append(f"{label}={widget.extra[key]}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_slider", args)

    if widget.qt_class == "QProgressBar":
        orientation = str(widget.extra.get("orientation", "horizontal"))
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
            f"Orient={quote(orientation)}",
        ]
        if "steps" in widget.extra:
            args.append(f"Steps={widget.extra['steps']}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_progress_bar", args)

    if widget.qt_class in {"QListWidget", "QListView"}:
        headers = widget.extra.get("headers", ["Items"])
        data = widget.extra.get("data", [])
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Headers={repr(headers)}",
            f"Data={repr(data)}",
            f"Size=[{width}, {height}]",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_listview", args)

    if widget.qt_class == "QTableWidget":
        headers = widget.extra.get("headers", ["Column 1"])
        data = widget.extra.get("data", [])
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
            f"Headers={repr(headers)}",
            f"Data={repr(data)}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_grid", args)

    if widget.qt_class == "QTableView":
        headers = widget.extra.get("headers", ["Column 1"])
        data = widget.extra.get("data", [])
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
            f"Headers={repr(headers)}",
            f"Data={repr(data)}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_dataview", args)

    if widget.qt_class in {"QTreeWidget", "QTreeView"}:
        headers = widget.extra.get("headers", ["Tree"])
        data = widget.extra.get("data", [])
        tree_type = str(widget.extra.get("tree_type") or "Tree")
        args = [
            f"Name={quote(widget.name)}",
            f"Type={quote(tree_type)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
            f"Headers={repr(headers)}",
            f"Data={repr(data)}",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_treeview", args)

    if widget.qt_class == "QFrame":
        separator_orientation = widget.extra.get("separator_orientation")
        if isinstance(separator_orientation, str) and separator_orientation in ("horizontal", "vertical"):
            args = [
                f"Name={quote(widget.name)}",
                f"Orientation={quote(separator_orientation)}",
                f"Position=[{x}, {y}]",
                f"Size=[{width}, {height}]",
            ]
            if effective_frame:
                args.append(f"Frame={quote(effective_frame)}")
            return _format_call("win.add_separator", args)

        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if widget.title:
            args.append(f"Title={quote(widget.title)}")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_frame", args)

    if widget.qt_class == "Line":
        separator_orientation = str(widget.extra.get("separator_orientation") or "horizontal")
        if separator_orientation not in ("horizontal", "vertical"):
            separator_orientation = "horizontal"
        args = [
            f"Name={quote(widget.name)}",
            f"Orientation={quote(separator_orientation)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        return _format_call("win.add_separator", args)

    if widget.qt_class == "QFontComboBox":
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        font_parts: list[str] = []
        if "font_family" in widget.extra:
            font_parts.append(quote(widget.extra["font_family"]))
        if "font_size" in widget.extra:
            font_parts.append(str(widget.extra["font_size"]))
        if "font_bold" in widget.extra:
            font_parts.append(quote("bold"))
        if font_parts:
            args.append(f"Font=[{', '.join(font_parts)}]")
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        if widget.signal:
            args.append(f"Signal={widget.signal}")
        if widget.handler_name:
            args.append(f"Function={widget.handler_name}")
        return _format_call("win.add_font_button", args)

    if widget.qt_class == "QGraphicsView":
        image_path = widget.extra.get("image_path")
        if image_path:
            args = [
                f"Name={quote(widget.name)}",
                f"Position=[{x}, {y}]",
                f"Size=[{width}, {height}]",
                f"Path={quote(image_path)}",
            ]
            if effective_frame:
                args.append(f"Frame={quote(effective_frame)}")
            if widget.tooltip:
                args.append(f"Tooltip={quote(widget.tooltip)}")
            if widget.signal:
                args.append(f"Signal={widget.signal}")
            if widget.handler_name:
                args.append(f"Function={widget.handler_name}")
            return _format_call("win.add_image", args)
        # No image resolved — fall back to an empty frame placeholder.
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if effective_frame:
            args.append(f"Frame={quote(effective_frame)}")
        return _format_call("win.add_frame", args)

    raise BuilderError(f"Interner Fehler: Keine Mapping-Regel für {widget.qt_class}")


def _widget_sort_key(widget: WidgetSpec) -> tuple[int, int, str]:
    """Sort widgets strictly top-to-bottom, then left-to-right."""
    y = int(widget.position[1])
    x = int(widget.position[0])
    return (y, x, widget.name)


def _notebook_sort_key(notebook: NotebookSpec) -> tuple[int, int, str]:
    y = int(notebook.position[1])
    x = int(notebook.position[0])
    return (y, x, notebook.name)


def _toolbar_sort_key(toolbar: ToolbarSpec) -> tuple[int, int, str]:
    y = int(toolbar.position[1])
    x = int(toolbar.position[0])
    return (y, x, toolbar.name)


def _splitter_sort_key(splitter: SplitterSpec) -> tuple[int, int, str]:
    y = int(splitter.position[1])
    x = int(splitter.position[0])
    return (y, x, splitter.name)


def _widget_comment_title(widget: WidgetSpec) -> str:
    """Return a readable title for section comments."""
    return widget.title if widget.title else widget.name


def _widget_inline_comment(widget: WidgetSpec) -> Optional[str]:
    """Return a per-widget comment line for generated output."""
    kind_map = {
        "QLabel": "Label",
        "QPushButton": "Button",
        "QLineEdit": "Entry",
        "QCheckBox": "Checkbox",
        "QRadioButton": "Radio",
        "QTextEdit": "Text view",
        "QSpinBox": "Spin button",
        "QComboBox": "Combo box",
        "QSlider": "Slider",
        "QProgressBar": "Progress bar",
        "QListWidget": "List view",
        "QListView": "List view",
        "QTableWidget": "Grid",
        "QTableView": "Data view",
        "QTreeWidget": "Tree view",
        "QTreeView": "Tree view",
        "Line": "Separator",
        "QFontComboBox": "Font combo",
        "QGraphicsView": "Graphics view",
    }

    kind = kind_map.get(widget.qt_class)
    if kind is None:
        return None

    title = (widget.title or "").strip()
    if widget.qt_class in {"QProgressBar", "Line"} or not title:
        title = widget.name

    return f"# {kind} {quote(title)}"


def _emit_widget_block(
    lines: List[str],
    widget: WidgetSpec,
    emitted_handlers: set[str],
    leading_blank_before_comment: bool = True,
    default_frame: Optional[str] = None,
) -> None:
    """Emit optional widget comment, handler defs, then widget call."""
    widget_comment = _widget_inline_comment(widget)
    if widget_comment:
        if leading_blank_before_comment and lines and lines[-1] != "":
            lines.append("")
        lines.append(widget_comment)

    _emit_handler_stub(lines, emitted_handlers, widget.handler_name, widget.handler_body or None)
    lines.append(build_widget_call(widget, container_frame=default_frame))
    if widget.qt_class == "QProgressBar" and "value" in widget.extra:
        lines.append(f"win.set_value({quote(widget.name)}, 'Value', {widget.extra['value']})")


def _menu_item_inline_comment(item: MenuItemSpec) -> str:
    title = (item.title or item.name or "").strip() or item.name
    item_kind = "Menu separator" if item.item_type == "separator" else "Menu item"
    return f"# {item_kind} {quote(title)}"


def _emit_menu_item_block(
    lines: List[str],
    menu_name: str,
    item: MenuItemSpec,
    emitted_handlers: set[str],
) -> None:
    if lines and lines[-1] != "":
        lines.append("")
    lines.append(_menu_item_inline_comment(item))

    args = [
        f"Name={quote(item.name)}",
        f"Menu={quote(menu_name)}",
    ]
    if item.item_type != "item":
        args.append(f"Type={quote(item.item_type)}")
    if item.title:
        args.append(f"Title={quote(item.title)}")
    if item.tooltip:
        args.append(f"Tooltip={quote(item.tooltip)}")
    if item.icon:
        args.append(f"Icon={quote(item.icon)}")
    if item.signal:
        args.append(f"Signal={item.signal}")
    if item.handler_name:
        args.append(f"Function={item.handler_name}")
        _emit_handler_stub(lines, emitted_handlers, item.handler_name)
    lines.append(_format_call("win.add_menu_item", args))


def _emit_widgets_header(
    lines: List[str],
    section_title: str,
    outside_are_buttons: bool,
    header_state: Dict[str, bool],
) -> None:
    """Emit '# Widgets on ...' / '# Buttons at the bottom' with controlled spacing.

    Rule: first emitted widgets header has no leading blank line; all following
    widgets headers get one leading blank line.
    """
    if header_state.get("widgets_header_emitted_any", False):
        if lines and lines[-1] != "":
            lines.append("")
    header_state["widgets_header_emitted_any"] = True

    if outside_are_buttons:
        lines.append("# Buttons at the bottom")
    else:
        lines.append(f"# Widgets on {quote(section_title)}")


def _emit_handler_stub(
    lines: List[str],
    emitted: set[str],
    handler_name: Optional[str],
    body: Optional[List[str]] = None,
) -> None:
    """Emit one handler stub once, directly before its source widget/menu item."""
    if not handler_name or handler_name in emitted:
        return
    emitted.add(handler_name)
    lines.append(f"def {handler_name}(_event):")
    if body:
        lines.extend(body)
    else:
        lines.append("    pass")
    lines.append("")


def _collect_scope_widgets(
    widgets: List[WidgetSpec],
) -> Tuple[List[WidgetSpec], Dict[str, List[WidgetSpec]], List[WidgetSpec]]:
    frames = [
        widget
        for widget in widgets
        if widget.qt_class == "QFrame" and "separator_orientation" not in widget.extra
    ]
    frame_names = {frame.name for frame in frames}

    children_by_frame: Dict[str, List[WidgetSpec]] = {frame.name: [] for frame in frames}
    outside_widgets: List[WidgetSpec] = []

    for widget in widgets:
        if widget.qt_class == "QFrame" and "separator_orientation" not in widget.extra:
            continue
        if widget.frame and widget.frame in frame_names:
            children_by_frame[widget.frame].append(widget)
        else:
            outside_widgets.append(widget)

    return frames, children_by_frame, outside_widgets


def _render_frame_block(
    lines: List[str],
    frame: WidgetSpec,
    frame_children: List[WidgetSpec],
    emitted_handlers: set[str],
    default_frame: Optional[str] = None,
) -> None:
    lines.append(f"# Frame {quote(_widget_comment_title(frame))}")
    lines.append(build_widget_call(frame, container_frame=default_frame))

    last_groupbox_comment: Optional[str] = None
    for child in sorted(frame_children, key=_widget_sort_key):
        if child.qt_class == "QRadioButton" and child.group and child.group.startswith("groupBox_"):
            groupbox_comment = child.group[len("groupBox_"):]
            if groupbox_comment and groupbox_comment != last_groupbox_comment:
                lines.append(f"# GroupBox {quote(groupbox_comment)}")
            last_groupbox_comment = groupbox_comment
        else:
            last_groupbox_comment = None
        _emit_widget_block(lines, child, emitted_handlers, default_frame=default_frame)


def _render_grouped_widgets(
    lines: List[str],
    widgets: List[WidgetSpec],
    emitted_handlers: set[str],
    section_title: str,
    header_state: Dict[str, bool],
    default_frame: Optional[str] = None,
) -> None:
    frames, children_by_frame, outside_widgets = _collect_scope_widgets(widgets)

    top_entries: List[Tuple[str, WidgetSpec]] = []
    top_entries.extend(("frame", frame) for frame in frames)
    top_entries.extend(("widget", widget) for widget in outside_widgets)
    top_entries.sort(key=lambda entry: _widget_sort_key(entry[1]))

    outside_widgets_sorted = sorted(outside_widgets, key=_widget_sort_key)
    outside_header_emitted = False
    outside_are_buttons = bool(outside_widgets_sorted) and all(
        widget.qt_class == "QPushButton" for widget in outside_widgets_sorted
    )
    first_widget_after_header = False

    for kind, item in top_entries:
        if kind == "frame":
            _render_frame_block(
                lines,
                item,
                children_by_frame.get(item.name, []),
                emitted_handlers,
                default_frame=default_frame,
            )
            lines.append("")
            continue

        if not outside_header_emitted:
            _emit_widgets_header(lines, section_title, outside_are_buttons, header_state)
            outside_header_emitted = True
            first_widget_after_header = True
        _emit_widget_block(
            lines,
            item,
            emitted_handlers,
            leading_blank_before_comment=not first_widget_after_header,
            default_frame=default_frame,
        )
        first_widget_after_header = False

    if outside_header_emitted:
        lines.append("")


def _render_notebook_block(
    lines: List[str],
    notebook: NotebookSpec,
    widgets: List[WidgetSpec],
    emitted_handlers: set[str],
    header_state: Dict[str, bool],
) -> None:
    notebook_args = [
        f"Name={quote(notebook.name)}",
        f"Position=[{notebook.position[0]}, {notebook.position[1]}]",
        f"Size=[{notebook.size[0]}, {notebook.size[1]}]",
        "Scrollable=0",
    ]
    if notebook.signal:
        notebook_args.append(f"Signal={notebook.signal}")
    if notebook.handler_name:
        notebook_args.append(f"Function={notebook.handler_name}")

    lines.append(f"# Notebook {quote(notebook.name)}")
    lines.append(_format_call("win.add_notebook", notebook_args))

    pages_sorted = sorted(notebook.pages, key=lambda page: page.position_number)
    for page in pages_sorted:
        lines.append(f"# NotebookPage {quote(page.title)}")
        lines.append(
            _format_call(
                "win.add_nb_page",
                [
                    f"Name={quote(page.name)}",
                    f"Notebook={quote(notebook.name)}",
                    f"Title={quote(page.title)}",
                    f"PositionNumber={page.position_number}",
                ],
            )
        )

        page_widget_items = [widget for widget in widgets if widget.container == page.name]
        if page_widget_items and lines and lines[-1] != "":
            lines.append("")
        _render_grouped_widgets(
            lines,
            page_widget_items,
            emitted_handlers,
            page.name,
            header_state,
            default_frame=page.name,
        )

    lines.append("")


def _render_toolbar_block(lines: List[str], toolbar: ToolbarSpec) -> None:
    lines.append(f"# Toolbar {quote(toolbar.title)}")
    lines.append("win.add_toolbar(")
    lines.append(f"    Name={quote(toolbar.name)},")
    lines.append(f"    Position=[{toolbar.position[0]}, {toolbar.position[1]}],")
    lines.append("    Data=[")
    for item in toolbar.items:
        item_title = (item.title or item.name or "").strip() or item.name
        item_kind = "separator" if item.kind == "separator" else "item"
        lines.append(f"        # Toolbar {item_kind} {quote(item_title)}")
        lines.append("        {")
        lines.append(f"            'label': {quote(item.title)},")
        lines.append(f"            'icon': {repr(item.icon)},")
        lines.append(f"            'kind': {quote(item.kind)},")
        lines.append(f"            'active': {item.active},")
        lines.append(f"            'tooltip': {repr(item.tooltip)},")
        lines.append("        },")
    lines.append("    ],")
    lines.append(f"    Orient={quote(toolbar.orient)},")
    if toolbar.size is not None:
        lines.append(f"    Size=[{toolbar.size[0]}, {toolbar.size[1]}],")
    lines.append(")")
    lines.append("")


def _render_splitter_block(
    lines: List[str],
    splitter: SplitterSpec,
    emitted_handlers: set[str],
    header_state: Dict[str, bool],
) -> None:
    splitter_args = [
        f"Name={quote(splitter.name)}",
        f"Position=[{splitter.position[0]}, {splitter.position[1]}]",
        f"Size=[{splitter.size[0]}, {splitter.size[1]}]",
        f"Orient={quote(splitter.orient)}",
        f"Split={splitter.split}",
    ]
    if splitter.signal:
        splitter_args.append(f"Signal={splitter.signal}")
    if splitter.handler_name:
        splitter_args.append(f"Function={splitter.handler_name}")

    lines.append(f"# Splitter {quote(splitter.name)}")
    lines.append(_format_call("win.add_splitter", splitter_args))

    for pane in splitter.panes:
        lines.append(
            f"# Splitter pane {quote(pane.name)} attached to {quote(splitter.name)} on the {quote(pane.side)} side"
        )
        lines.append(
            _format_call(
                "win.add_splitter_pane",
                [
                    f"Name={quote(pane.name)}",
                    f"Splitter={quote(splitter.name)}",
                    f"Side={quote(pane.side)}",
                ],
            )
        )
        if pane.widgets and lines and lines[-1] != "":
            lines.append("")
        _render_grouped_widgets(
            lines,
            pane.widgets,
            emitted_handlers,
            pane.name,
            header_state,
            default_frame=pane.name,
        )

    lines.append("")


def render_python(
    window: WindowSpec,
    widgets: List[WidgetSpec],
    notebooks: List[NotebookSpec],
    splitters: List[SplitterSpec],
    toolbars: List[ToolbarSpec],
    handlers: Dict[str, str],
    menubar_name: Optional[str],
    menus: List[MenuSpec],
    dev_mode: bool = False,
    author: str = "swxbuilder",
    version: str = "0.1.0",
    build_date: Optional[str] = None,
) -> str:
    # Build the final Python source text from the parsed data.
    resolved_date = (build_date or datetime.date.today().strftime("%Y/%m/%d")).strip()

    signal_refs: List[str] = []
    signal_refs.extend(widget.signal for widget in widgets if widget.signal)
    signal_refs.extend(item.signal for menu in menus for item in menu.items if item.signal)
    signal_refs.extend(notebook.signal for notebook in notebooks if notebook.signal)
    signal_refs.extend(splitter.signal for splitter in splitters if splitter.signal)

    lines: List[str] = []
    lines.append("#!/usr/bin/env python3")
    lines.append("")
    lines.append(f"__author__ = {quote(author)}")
    lines.append(f'__date__ = "{resolved_date}"')
    lines.append(f'__version__ = "{version}"')
    lines.append("")
    if any(signal.startswith("wx.") for signal in signal_refs):
        lines.append("import wx")
    if any(signal.startswith("wx.adv.") for signal in signal_refs):
        lines.append("import wx.adv")
    lines.append("from simplewx import SimpleWx as simplewx")
    lines.append("")

    lines.append(f"# Main Window {quote(window.title)}")
    lines.append("win = simplewx()")

    window_args = [
        f"Name={quote(window.name)}",
        f"Title={quote(window.title)}",
    ]
    if dev_mode:
        window_args.append("Base=0")
    if window.size is not None:
        window_args.append(f"Size=[{window.size[0]}, {window.size[1]}]")
    if window.statusbar:
        window_args.append("Statusbar=1")

    lines.append(_format_call("win.new_window", window_args))
    lines.append("")

    emitted_handlers: set[str] = set()

    # Emit the menu structure before ordinary widgets.
    if menubar_name and menus:
        lines.append("# Menubar and menu items")
        lines.append(_format_call("win.add_menu_bar", [f"Name={quote(menubar_name)}"]))
        lines.append("")
        for menu in menus:
            lines.append(f"# Menu {quote(menu.title)}")
            lines.append(
                _format_call(
                    "win.add_menu",
                    [
                        f"Name={quote(menu.name)}",
                        f"Menubar={quote(menubar_name)}",
                        f"Title={quote(menu.title)}",
                    ],
                )
            )
            for item in menu.items:
                _emit_menu_item_block(lines, menu.name, item, emitted_handlers)
            lines.append("")

    main_widgets = [widget for widget in widgets if widget.container is None]
    main_frames, main_children_by_frame, main_outside_widgets = _collect_scope_widgets(main_widgets)

    top_entries: List[Tuple[str, object]] = []
    top_entries.extend(("frame", frame) for frame in main_frames)
    top_entries.extend(("widget", widget) for widget in main_outside_widgets)
    top_entries.extend(("notebook", notebook) for notebook in notebooks)
    top_entries.extend(("splitter", splitter) for splitter in splitters)
    top_entries.extend(("toolbar", toolbar) for toolbar in toolbars)
    top_entries.sort(
        key=lambda entry: (
            _notebook_sort_key(entry[1])
            if entry[0] == "notebook"
            else _splitter_sort_key(entry[1])
            if entry[0] == "splitter"
            else _toolbar_sort_key(entry[1])
            if entry[0] == "toolbar"
            else _widget_sort_key(entry[1])
        )
    )

    outside_widgets_sorted = sorted(main_outside_widgets, key=_widget_sort_key)
    outside_header_emitted = False
    header_state: Dict[str, bool] = {"widgets_header_emitted_any": False}
    outside_are_buttons = bool(outside_widgets_sorted) and all(
        widget.qt_class == "QPushButton" for widget in outside_widgets_sorted
    )

    for kind, item in top_entries:
        if kind == "frame":
            _render_frame_block(lines, item, main_children_by_frame.get(item.name, []), emitted_handlers)
            lines.append("")
            continue

        if kind == "widget":
            if not outside_header_emitted:
                _emit_widgets_header(lines, window.name, outside_are_buttons, header_state)
                outside_header_emitted = True
            _emit_widget_block(lines, item, emitted_handlers)
            continue

        if kind == "toolbar":
            _render_toolbar_block(lines, item)
            continue

        if kind == "splitter":
            _render_splitter_block(lines, item, emitted_handlers, header_state)
            continue

        _render_notebook_block(lines, item, widgets, emitted_handlers, header_state)

    if outside_header_emitted:
        lines.append("")

    lines.append("if __name__ == '__main__':")
    lines.append("    win.show_and_run()")
    lines.append("")

    return "\n".join(lines)


def _extract_stylesheet_image_url(css: str) -> Optional[str]:
    """Return the first background-image url() value found in a CSS string."""
    m = re.search(r'background-image\s*:\s*url\s*\(\s*([^)]+)\s*\)', css)
    if m:
        return m.group(1).strip().strip('"\'')
    return None


def _try_resolve_stylesheet_resource(
    url: str,
    ui_path: Path,
    resource_paths: Dict[str, str],
) -> Optional[str]:
    """Resolve a Qt stylesheet url(:/...) to a real file path, or None on failure."""
    if url.startswith(":"):
        resource_name = _normalize_qt_resource_path(url)
        resolved = resource_paths.get(resource_name)
        if resolved is None:
            basename_key = "/" + PurePosixPath(resource_name).name
            if basename_key != resource_name:
                resolved = resource_paths.get(basename_key)
        return resolved
    # Plain file path (absolute or relative to the .ui directory).
    candidate = Path(url)
    if not candidate.is_absolute():
        candidate = (ui_path.parent / candidate).resolve()
    return str(candidate) if candidate.exists() else None


def convert_ui_to_simplewx(
    input_path: Path,
    dev_mode: bool = False,
    author: str = "swxbuilder",
    version: str = "0.1.0",
    build_date: Optional[str] = None,
) -> str:
    # Top-level conversion entry point for Qt `.ui` files.
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as exc:
        raise BuilderError(f"XML-Parsing fehlgeschlagen für {input_path}: {exc}") from exc

    root = tree.getroot()
    validate_static_only(root)
    main_widget = _find_top_level_widget(root)

    # Parse in clearly separated phases: signals, menus, window, widgets, render.
    handlers = parse_connections(root)
    resource_paths = _collect_qt_resource_paths(root, input_path)
    action_specs = _collect_action_specs(main_widget, handlers, input_path, resource_paths)
    is_main_window = (main_widget.get("class") or "").strip() == "QMainWindow"
    menubar_name, menus, menu_height = parse_menus(main_widget, action_specs) if is_main_window else (None, [], 0)
    toolbars = parse_toolbars(main_widget, action_specs) if is_main_window else []
    window = parse_window(main_widget, menu_height=menu_height)
    notebooks, notebook_widgets = parse_notebooks(root, handlers)
    splitters = parse_splitters(root, handlers)
    widgets = parse_widgets(root, handlers)
    widgets.extend(notebook_widgets)
    for splitter in splitters:
        for pane in splitter.panes:
            widgets.extend(pane.widgets)
    # Post-process: resolve QGraphicsView stylesheet background-image paths.
    for _w in widgets:
        if _w.qt_class == "QGraphicsView":
            stylesheet = _w.extra.get("raw_stylesheet", "")
            if stylesheet:
                image_url = _extract_stylesheet_image_url(stylesheet)
                if image_url:
                    resolved = _try_resolve_stylesheet_resource(image_url, input_path, resource_paths)
                    if resolved:
                        _w.extra["image_path"] = resolved
    widgets = _apply_frame_title_labels(widgets)
    widgets = _assign_widgets_to_frames(widgets)
    widgets = _adjust_spinbox_min_size_and_adjacent_labels(widgets)
    return render_python(
        window,
        widgets,
        notebooks,
        splitters,
        toolbars,
        handlers,
        menubar_name,
        menus,
        dev_mode=dev_mode,
        author=author,
        version=version,
        build_date=build_date,
    )


def convert_fbp_to_simplewx(input_path: Path) -> str:
    # Placeholder / compatibility wrapper: currently uses the same path as `.ui`.
    return convert_ui_to_simplewx(input_path)


def build_arg_parser() -> argparse.ArgumentParser:
    # Central definition of the CLI parameters.
    parser = argparse.ArgumentParser(
        description=(
            "Parst eine Qt-Designer .ui-Datei und erzeugt ein SimpleWx-Grundgerüst. "
            "Nur reine statische Layouts ohne QLayout/Sizer sind erlaubt."
        )
    )
    parser.add_argument("-i", "--input", type=Path, required=True, help="Pfad zur .ui-Datei")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Ausgabepfad für das Grundgerüst (.py) oder Zielverzeichnis; "
            "Standard: gleiches Verzeichnis wie Input mit Namen <input>_swx.py"
        ),
    )
    # Keep debug flags mutually exclusive so CLI behavior is explicit.
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help="Debug-Modus: generiert den new_window()-Aufruf mit Base=0 für pixelgenaue Qt-Geometrie.",
    )
    debug_group.add_argument(
        "--no-debug",
        dest="debug",
        action="store_false",
        help="Deaktiviert Debug-Modus und lässt SimpleWx-Skalierung aktiv (kein Base=0).",
    )
    # Default stays scaled output (no Base=0) unless --debug is passed.
    parser.set_defaults(debug=False)
    parser.add_argument(
        "-a",
        "--author",
        default="swxbuilder",
        help="Autor für den Header im generierten Script (Default: swxbuilder).",
    )
    parser.add_argument(
        "-v",
        "--version",
        default="0.1.0",
        help="Version für den Header im generierten Script (Default: 0.1.0).",
    )
    parser.add_argument(
        "-d",
        "--date",
        default=None,
        help="Datum für den Header im Format YYYY/MM/DD (Default: aktuelles Datum).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    # CLI entry point: validate arguments, convert, write file.
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Fehler: Datei nicht gefunden: {input_path}", file=sys.stderr)
        return 2

    if input_path.suffix.lower() != ".ui":
        print(f"Fehler: Erwartet eine .ui-Datei, erhalten: {input_path.name}", file=sys.stderr)
        return 2

    # Determine the output path: explicit file, directory, or default name.
    if args.output is None:
        output_path = input_path.with_name(f"{input_path.stem}_swx.py")
    else:
        output_candidate: Path = args.output
        if output_candidate.exists() and output_candidate.is_dir():
            output_path = output_candidate / f"{input_path.stem}_swx.py"
        elif output_candidate.suffix == "":
            output_path = output_candidate / f"{input_path.stem}_swx.py"
        else:
            output_path = output_candidate

    # Run the conversion and report errors in a user-friendly way.
    try:
        code = convert_ui_to_simplewx(
            input_path,
            dev_mode=bool(args.debug),
            author=str(args.author),
            version=str(args.version),
            build_date=str(args.date).strip() if args.date is not None else None,
        )
    except BuilderError as exc:
        print(f"Abort: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(code, encoding="utf-8")
    output_path.chmod(0o755)
    print(f"OK: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
