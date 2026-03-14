#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
}


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


def _iter_supported_widgets(parent: ET.Element) -> List[ET.Element]:
    # Walk the XML tree recursively and collect only widget classes that this
    # builder can actually translate into SimpleWx calls.
    items: List[ET.Element] = []
    for child in parent.findall("widget"):
        child_class = (child.get("class") or "").strip()
        if child_class in SUPPORTED_WIDGET_CLASSES:
            items.append(child)
        items.extend(_iter_supported_widgets(child))
    return items


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


def parse_widgets(root: ET.Element, handlers: Dict[str, str]) -> List[WidgetSpec]:
    # Central parser for all visible, supported Qt widgets.
    # Raw XML nodes are converted into `WidgetSpec` objects here.
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

    widgets: List[WidgetSpec] = []
    running_index = 1

    # First read all widgets with their absolute geometry.
    for widget in _iter_supported_widgets(main_widget):
        qt_class = (widget.get("class") or "").strip()
        raw_name = (widget.get("name") or "").strip()
        widget_name = sanitize_name(raw_name, "widget", running_index)

        geometry = _property_rect(widget, "geometry", widget_name)
        if geometry is None:
            raise BuilderError(
                f"Widget '{widget_name}' ({qt_class}) hat keine geometry-Property. "
                "Für statische Qt-Layouts sind absolute Koordinaten zwingend erforderlich."
            )

        x, y, width, height = geometry

        # QFrame usually has no `text`, but some variants expose a `title`.
        # Accept both so no useful captions are lost.
        text = _property_string(widget, "text") or _property_string(widget, "title") or ""
        tooltip = _property_string(widget, "toolTip")
        checked = _property_bool(widget, "checked") if qt_class in {"QCheckBox", "QRadioButton"} else 0
        handler_name = handlers.get(widget_name)

        widgets.append(
            WidgetSpec(
                qt_class=qt_class,
                name=widget_name,
                position=(x, y),
                size=(width, height),
                title=text,
                tooltip=tooltip,
                checked=checked,
                handler_name=handler_name,
            )
        )
        running_index += 1

    # Then run two semantic post-processing steps:
    # 1. turn special QLabel captions into actual frame titles
    # 2. assign widgets to frames based on geometry
    widgets = _apply_frame_title_labels(widgets)
    widgets = _assign_widgets_to_frames(widgets)
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


def build_widget_call(widget: WidgetSpec) -> str:
    # Translate one parsed widget into exactly one SimpleWx call.
    x, y = widget.position
    width, height = widget.size if widget.size is not None else (120, 28)

    if widget.qt_class == "QLabel":
        title = widget.title or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
        ]
        if widget.frame:
            args.append(f"Frame={quote(widget.frame)}")
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
        if widget.frame:
            args.append(f"Frame={quote(widget.frame)}")
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
        if widget.frame:
            args.append(f"Frame={quote(widget.frame)}")
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
        if widget.frame:
            args.append(f"Frame={quote(widget.frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_check_button", args)

    if widget.qt_class == "QRadioButton":
        title = widget.title or widget.name
        # Radio buttons always need a group in SimpleWx.
        # Inside a frame, automatically create a frame-specific group name.
        default_group = f"group_{widget.frame}" if widget.frame else "group_main"
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Group={quote(default_group)}",
            f"Active={widget.checked}",
        ]
        if widget.frame:
            args.append(f"Frame={quote(widget.frame)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_radio_button", args)

    if widget.qt_class == "QFrame":
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if widget.title:
            args.append(f"Title={quote(widget.title)}")
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_frame", args)

    raise BuilderError(f"Interner Fehler: Keine Mapping-Regel für {widget.qt_class}")


def _widget_sort_key(widget: WidgetSpec) -> tuple[int, int, str]:
    """Sort widgets visually by row first, then left to right within a row."""
    y = int(widget.position[1])
    x = int(widget.position[0])
    row_bucket = y // 15
    return (row_bucket, x, y, widget.name)


def _widget_comment_title(widget: WidgetSpec) -> str:
    """Return a readable title for section comments."""
    return widget.title if widget.title else widget.name


def render_python(
    window: WindowSpec,
    widgets: List[WidgetSpec],
    handlers: Dict[str, str],
    menubar_name: Optional[str],
    menus: List[MenuSpec],
    dev_mode: bool = False,
) -> str:
    # Build the final Python source text from the parsed data.
    lines: List[str] = []
    lines.append("#!/usr/bin/env python3")
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

    frames = sorted(
        [widget for widget in widgets if widget.qt_class == "QFrame"],
        key=_widget_sort_key,
    )
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

    for frame in frames:
        lines.append(f"# Frame {quote(_widget_comment_title(frame))}")
        lines.append(build_widget_call(frame))

        frame_children = sorted(children_by_frame.get(frame.name, []), key=_widget_sort_key)
        for child in frame_children:
            lines.append(build_widget_call(child))
        lines.append("")

    outside_widgets = sorted(outside_widgets, key=_widget_sort_key)
    if outside_widgets:
        if all(widget.qt_class == "QPushButton" for widget in outside_widgets):
            lines.append("# Buttons at the bottom")
        else:
            lines.append("# Widgets outside frames")
        for widget in outside_widgets:
            lines.append(build_widget_call(widget))
        lines.append("")

    lines.append("if __name__ == '__main__':")
    lines.append("    win.show_and_run()")
    lines.append("")

    return "\n".join(lines)


def convert_ui_to_simplewx(input_path: Path, dev_mode: bool = False) -> str:
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
    widgets = parse_widgets(root, handlers)
    return render_python(window, widgets, handlers, menubar_name, menus, dev_mode=dev_mode)


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
        "-d",
        "--dev",
        action="store_true",
        help="Dev-Modus: setzt Base=0 im generierten new_window()-Aufruf.",
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
        code = convert_ui_to_simplewx(input_path, dev_mode=bool(args.dev))
    except BuilderError as exc:
        print(f"Abbruch: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(code, encoding="utf-8")
    output_path.chmod(0o755)
    print(f"OK: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
