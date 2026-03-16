#!/usr/bin/env python3
from __future__ import annotations

__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot'
__date__ = "2026/03/16"

import argparse
import datetime
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
    frame: Optional[str] = None
    frame_title_height: int = 0
    # Radio group name extracted from a containing QGroupBox, if present.
    group: Optional[str] = None
    # Logical container scope (e.g. notebook page name) used for frame matching.
    container: Optional[str] = None
    # Additional widget-specific metadata for renderer mappings.
    extra: Dict[str, str] = field(default_factory=dict)


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


# Represents a single menu item from the QMenu/QAction structure.
@dataclass
class MenuItemSpec:
    name: str
    title: str
    handler_name: Optional[str] = None


# Bundles one complete menu with all of its contained items.
@dataclass
class MenuSpec:
    name: str
    title: str
    items: List[MenuItemSpec]


SUPPORTED_WIDGET_CLASSES = {
    "QLabel",
    "QPushButton",
    "QLineEdit",
    "QCheckBox",
    "QRadioButton",
    "QFrame",
    "QTextEdit",
    "QSpinBox",
}

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


def _normalize_signal_name(raw: str) -> str:
    # Turn e.g. "clicked()" into a Python-safe signal name so stable handler
    # names can be generated from it.
    signal_name = raw.split("(", 1)[0].strip().lower()
    clean = "".join(ch if ch.isalnum() else "_" for ch in signal_name)
    clean = clean.strip("_")
    return clean or "signal"


def parse_connections(root: ET.Element) -> Dict[str, str]:
    # Build a mapping "widget name -> handler name" from the Qt <connections>
    # block. The renderer later turns this back into `Function=...`.
    handlers: Dict[str, str] = {}
    for conn in root.findall("./connections/connection"):
        sender = (conn.findtext("sender") or "").strip()
        signal = (conn.findtext("signal") or "").strip()
        if not sender or not signal:
            continue
        sender_name = sanitize_name(sender, "widget", 0)
        signal_name = _normalize_signal_name(signal)
        handlers[sender_name] = f"on_{sender_name}_{signal_name}"
    return handlers


def parse_menus(main_widget: ET.Element, handlers: Dict[str, str]) -> Tuple[Optional[str], List[MenuSpec], int]:
    # Menus are processed separately from the normal widget stream because Qt
    # describes them as a QMenuBar/QMenu/QAction structure rather than ordinary
    # visible widgets in the central area.
    menubar_widget = main_widget.find("./widget[@class='QMenuBar']")
    if menubar_widget is None:
        return None, [], 0

    menubar_name = sanitize_name((menubar_widget.get("name") or "menubar").strip(), "menubar", 0)
    menubar_geometry = _property_rect(menubar_widget, "geometry", menubar_name)
    menu_height = menubar_geometry[3] if menubar_geometry is not None else 0

    # Collect QAction titles first so later addaction references can resolve to
    # their visible menu text.
    action_titles: Dict[str, str] = {}
    for action in main_widget.findall("./action"):
        action_name = sanitize_name((action.get("name") or "").strip(), "action", len(action_titles) + 1)
        action_title = _property_string(action, "text") or action_name
        action_titles[action_name] = action_title

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
            action_name = sanitize_name(raw_action_name, "action", len(items) + 1)
            action_title = action_titles.get(action_name, action_name)

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
                    handler_name=handlers.get(action_name),
                )
            )

        menus.append(MenuSpec(name=menu_name, title=menu_title, items=items))
        running_menu_index += 1

    return menubar_name, menus, menu_height


def parse_window(main_widget: ET.Element, menu_height: int = 0) -> WindowSpec:
    # Read only the main window's basic data here. Actual widget generation is
    # handled later in a separate step.
    frame_name = sanitize_name(main_widget.get("name") or "mainWindow", "window", 0)
    frame_title = _property_string(main_widget, "windowTitle") or frame_name
    has_statusbar = main_widget.find("./widget[@class='QStatusBar']") is not None

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
        if child_class in SUPPORTED_WIDGET_CLASSES:
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
        else:
            # Any other non-supported container: recurse without changing offsets.
            items.extend(_iter_supported_widgets(child, _offset_x, _offset_y, _group_name))
    return items


def _widget_from_element(
    widget_el: ET.Element,
    handlers: Dict[str, str],
    running_index: int,
    offset_x: int = 0,
    offset_y: int = 0,
    group_name: Optional[str] = None,
    container: Optional[str] = None,
) -> WidgetSpec:
    qt_class = (widget_el.get("class") or "").strip()
    raw_name = (widget_el.get("name") or "").strip()
    widget_name = sanitize_name(raw_name, "widget", running_index)

    geometry = _property_rect(widget_el, "geometry", widget_name)
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
    handler_name = handlers.get(widget_name)

    extra: Dict[str, str] = {}
    if qt_class == "QTextEdit":
        text_view_text = _property_string(widget_el, "plainText") or _property_string(widget_el, "html") or ""
        if text_view_text:
            extra["text"] = text_view_text
    if qt_class == "QSpinBox":
        spin_value = _property_string(widget_el, "value")
        if spin_value is not None and spin_value.strip() != "":
            extra["start"] = spin_value.strip()

    return WidgetSpec(
        qt_class=qt_class,
        name=widget_name,
        position=(x, y),
        size=(width, height),
        title=text,
        tooltip=tooltip,
        checked=checked,
        handler_name=handler_name,
        group=group_name,
        container=container,
        extra=extra,
    )


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


def parse_notebooks(root: ET.Element, handlers: Dict[str, str]) -> Tuple[List[NotebookSpec], List[WidgetSpec]]:
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

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
                page_widgets.append(
                    _widget_from_element(
                        widget_el,
                        handlers,
                        running_index,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        group_name=group_name,
                        container=page_name,
                    )
                )
                running_index += 1

            page_index += 1

        notebooks.append(
            NotebookSpec(
                name=notebook_name,
                position=(x, y),
                size=(width, height),
                pages=pages,
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
    frames = [widget for widget in widgets if widget.qt_class == "QFrame" and widget.size is not None]
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


def parse_widgets(root: ET.Element, handlers: Dict[str, str]) -> List[WidgetSpec]:
    # Central parser for all visible, supported Qt widgets.
    # Raw XML nodes are converted into `WidgetSpec` objects here.
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

    widgets: List[WidgetSpec] = []
    running_index = 1

    # First read all widgets with their absolute geometry.
    for widget_el, offset_x, offset_y, group_name in _iter_supported_widgets(main_widget):
        widgets.append(
            _widget_from_element(
                widget_el,
                handlers,
                running_index,
                offset_x=offset_x,
                offset_y=offset_y,
                group_name=group_name,
                container=None,
            )
        )
        running_index += 1

    return widgets


def quote(text: str) -> str:
    # `repr` directly produces Python-compatible string literals for output.
    return repr(text)


def _format_call(function_name: str, args: List[str]) -> str:
    # Keep short calls on one line; automatically format longer ones across
    # multiple lines for readability.
    if len(args) <= 4:
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
        return _format_call("win.add_spin_button", args)

    if widget.qt_class == "QFrame":
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


def _widget_comment_title(widget: WidgetSpec) -> str:
    """Return a readable title for section comments."""
    return widget.title if widget.title else widget.name


def _collect_scope_widgets(
    widgets: List[WidgetSpec],
) -> Tuple[List[WidgetSpec], Dict[str, List[WidgetSpec]], List[WidgetSpec]]:
    frames = [widget for widget in widgets if widget.qt_class == "QFrame"]
    frame_names = {frame.name for frame in frames}

    children_by_frame: Dict[str, List[WidgetSpec]] = {frame.name: [] for frame in frames}
    outside_widgets: List[WidgetSpec] = []

    for widget in widgets:
        if widget.qt_class == "QFrame":
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
        lines.append(build_widget_call(child, container_frame=default_frame))


def _render_grouped_widgets(
    lines: List[str],
    widgets: List[WidgetSpec],
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

    for kind, item in top_entries:
        if kind == "frame":
            _render_frame_block(lines, item, children_by_frame.get(item.name, []), default_frame=default_frame)
            lines.append("")
            continue

        if not outside_header_emitted:
            if outside_are_buttons:
                lines.append("# Buttons at the bottom")
            else:
                lines.append("# Widgets outside frames")
            outside_header_emitted = True
        lines.append(build_widget_call(item, container_frame=default_frame))

    if outside_header_emitted:
        lines.append("")


def _render_notebook_block(
    lines: List[str],
    notebook: NotebookSpec,
    widgets: List[WidgetSpec],
) -> None:
    lines.append(f"# Notebook {quote(notebook.name)}")
    lines.append(
        _format_call(
            "win.add_notebook",
            [
                f"Name={quote(notebook.name)}",
                f"Position=[{notebook.position[0]}, {notebook.position[1]}]",
                f"Size=[{notebook.size[0]}, {notebook.size[1]}]",
            ],
        )
    )

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
        _render_grouped_widgets(lines, page_widget_items, default_frame=page.name)

    lines.append("")


def render_python(
    window: WindowSpec,
    widgets: List[WidgetSpec],
    notebooks: List[NotebookSpec],
    handlers: Dict[str, str],
    menubar_name: Optional[str],
    menus: List[MenuSpec],
    dev_mode: bool = True,
    author: str = "swxbuilder",
    version: str = "0.1.0",
    build_date: Optional[str] = None,
) -> str:
    # Build the final Python source text from the parsed data.
    resolved_date = (build_date or datetime.date.today().strftime("%Y/%m/%d")).strip()

    lines: List[str] = []
    lines.append("#!/usr/bin/env python3")
    lines.append("")
    lines.append(f"__author__ = {quote(author)}")
    lines.append(f'__date__ = "{resolved_date}"')
    lines.append(f'__version__ = "{version}"')
    lines.append("")
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

    # Emit handler stubs only once per name even if Qt references the same
    # connection multiple times internally.
    emitted: List[str] = []
    for handler_name in handlers.values():
        if handler_name in emitted:
            continue
        emitted.append(handler_name)
        lines.append(f"def {handler_name}(_event):")
        lines.append("    pass")
        lines.append("")

    # Emit the menu structure before ordinary widgets.
    if menubar_name and menus:
        lines.append(_format_call("win.add_menu_bar", [f"Name={quote(menubar_name)}"]))
        for menu in menus:
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
                args = [
                    f"Name={quote(item.name)}",
                    f"Menu={quote(menu.name)}",
                    f"Title={quote(item.title)}",
                ]
                if item.handler_name:
                    args.append(f"Function={item.handler_name}")
                lines.append(_format_call("win.add_menu_item", args))
        lines.append("")

    main_widgets = [widget for widget in widgets if widget.container is None]
    main_frames, main_children_by_frame, main_outside_widgets = _collect_scope_widgets(main_widgets)

    top_entries: List[Tuple[str, object]] = []
    top_entries.extend(("frame", frame) for frame in main_frames)
    top_entries.extend(("widget", widget) for widget in main_outside_widgets)
    top_entries.extend(("notebook", notebook) for notebook in notebooks)
    top_entries.sort(
        key=lambda entry: _widget_sort_key(entry[1]) if entry[0] != "notebook" else _notebook_sort_key(entry[1])
    )

    outside_widgets_sorted = sorted(main_outside_widgets, key=_widget_sort_key)
    outside_header_emitted = False
    outside_are_buttons = bool(outside_widgets_sorted) and all(
        widget.qt_class == "QPushButton" for widget in outside_widgets_sorted
    )

    for kind, item in top_entries:
        if kind == "frame":
            _render_frame_block(lines, item, main_children_by_frame.get(item.name, []))
            lines.append("")
            continue

        if kind == "widget":
            if not outside_header_emitted:
                if outside_are_buttons:
                    lines.append("# Buttons at the bottom")
                else:
                    lines.append("# Widgets outside frames")
                outside_header_emitted = True
            lines.append(build_widget_call(item))
            continue

        _render_notebook_block(lines, item, widgets)

    if outside_header_emitted:
        lines.append("")

    lines.append("if __name__ == '__main__':")
    lines.append("    win.show_and_run()")
    lines.append("")

    return "\n".join(lines)


def convert_ui_to_simplewx(
    input_path: Path,
    dev_mode: bool = True,
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
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

    # Parse in clearly separated phases: signals, menus, window, widgets, render.
    handlers = parse_connections(root)
    menubar_name, menus, menu_height = parse_menus(main_widget, handlers)
    window = parse_window(main_widget, menu_height=menu_height)
    notebooks, notebook_widgets = parse_notebooks(root, handlers)
    widgets = parse_widgets(root, handlers)
    widgets.extend(notebook_widgets)
    widgets = _apply_frame_title_labels(widgets)
    widgets = _assign_widgets_to_frames(widgets)
    widgets = _adjust_spinbox_min_size_and_adjacent_labels(widgets)
    return render_python(
        window,
        widgets,
        notebooks,
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
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Kompatibilitätsflag: Base=0 ist bereits Standard im generierten new_window()-Aufruf.",
    )
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
            dev_mode=True,
            author=str(args.author),
            version=str(args.version),
            build_date=str(args.date).strip() if args.date is not None else None,
        )
    except BuilderError as exc:
        print(f"Abbruch: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(code, encoding="utf-8")
    output_path.chmod(0o755)
    print(f"OK: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
