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


@dataclass
class WindowSpec:
    name: str
    title: str
    size: Optional[Tuple[int, int]]
    statusbar: bool


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


@dataclass
class MenuItemSpec:
    name: str
    title: str
    handler_name: Optional[str] = None


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
}


def sanitize_name(name: str, fallback_prefix: str, index: int) -> str:
    candidate = "".join(char if (char.isalnum() or char == "_") else "_" for char in name.strip())
    if not candidate:
        candidate = f"{fallback_prefix}_{index}"
    if candidate[0].isdigit():
        candidate = f"{fallback_prefix}_{candidate}"
    return candidate


def _find_property(widget: ET.Element, name: str) -> Optional[ET.Element]:
    for prop in widget.findall("property"):
        if (prop.get("name") or "").strip() == name:
            return prop
    return None


def _property_string(widget: ET.Element, name: str) -> Optional[str]:
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
    value = (_property_string(widget, name) or "").strip().lower()
    return 1 if value in {"1", "true", "yes"} else 0


def _property_rect(widget: ET.Element, name: str, widget_name: str) -> Optional[Tuple[int, int, int, int]]:
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
    dynamic_layout = root.find(".//layout")
    if dynamic_layout is not None:
        class_name = (dynamic_layout.get("class") or "layout").strip()
        name = (dynamic_layout.get("name") or class_name or "<unnamed>").strip()
        raise BuilderError(
            f"Nicht unterstützt: dynamisches Layout-Element '{class_name}' in '{name}'. "
            "Dieses Tool verarbeitet nur statische Qt-Designer UIs ohne Layout/Sizer."
        )


def _normalize_signal_name(raw: str) -> str:
    signal_name = raw.split("(", 1)[0].strip().lower()
    clean = "".join(ch if ch.isalnum() else "_" for ch in signal_name)
    clean = clean.strip("_")
    return clean or "signal"


def parse_connections(root: ET.Element) -> Dict[str, str]:
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
    menubar_widget = main_widget.find("./widget[@class='QMenuBar']")
    if menubar_widget is None:
        return None, [], 0

    menubar_name = sanitize_name((menubar_widget.get("name") or "menubar").strip(), "menubar", 0)
    menubar_geometry = _property_rect(menubar_widget, "geometry", menubar_name)
    menu_height = menubar_geometry[3] if menubar_geometry is not None else 0

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

        items: List[MenuItemSpec] = []
        for addaction in menu_widget.findall("addaction"):
            raw_action_name = (addaction.get("name") or "").strip()
            if not raw_action_name:
                continue
            action_name = sanitize_name(raw_action_name, "action", len(items) + 1)
            action_title = action_titles.get(action_name, action_name)

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
    items: List[ET.Element] = []
    for child in parent.findall("widget"):
        child_class = (child.get("class") or "").strip()
        if child_class in SUPPORTED_WIDGET_CLASSES:
            items.append(child)
        items.extend(_iter_supported_widgets(child))
    return items


def parse_widgets(root: ET.Element, handlers: Dict[str, str]) -> List[WidgetSpec]:
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

    widgets: List[WidgetSpec] = []
    running_index = 1

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

        text = _property_string(widget, "text") or ""
        tooltip = _property_string(widget, "toolTip")
        checked = _property_bool(widget, "checked") if qt_class == "QCheckBox" else 0
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

    return widgets


def quote(text: str) -> str:
    return repr(text)


def _format_call(function_name: str, args: List[str]) -> str:
    if len(args) <= 4:
        return f"{function_name}({', '.join(args)})"

    lines = [f"{function_name}("]
    for arg in args:
        lines.append(f"    {arg},")
    lines.append(")")
    return "\n".join(lines)


def build_widget_call(widget: WidgetSpec) -> str:
    x, y = widget.position
    width, height = widget.size if widget.size is not None else (120, 28)

    if widget.qt_class == "QLabel":
        title = widget.title or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
        ]
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
        if widget.tooltip:
            args.append(f"Tooltip={quote(widget.tooltip)}")
        return _format_call("win.add_check_button", args)

    raise BuilderError(f"Interner Fehler: Keine Mapping-Regel für {widget.qt_class}")


def render_python(
    window: WindowSpec,
    widgets: List[WidgetSpec],
    handlers: Dict[str, str],
    menubar_name: Optional[str],
    menus: List[MenuSpec],
    dev_mode: bool = False,
) -> str:
    lines: List[str] = []
    lines.append("#!/usr/bin/env python3")
    lines.append("from simplewx import SimpleWx as simplewx")
    lines.append("")
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

    emitted: List[str] = []
    for handler_name in handlers.values():
        if handler_name in emitted:
            continue
        emitted.append(handler_name)
        lines.append(f"def {handler_name}(_event):")
        lines.append("    pass")
        lines.append("")

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

    for widget in widgets:
        lines.append(build_widget_call(widget))

    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    win.show_and_run()")
    lines.append("")

    return "\n".join(lines)


def convert_ui_to_simplewx(input_path: Path, dev_mode: bool = False) -> str:
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as exc:
        raise BuilderError(f"XML-Parsing fehlgeschlagen für {input_path}: {exc}") from exc

    root = tree.getroot()
    validate_static_only(root)
    main_widget = root.find("./widget[@class='QMainWindow']")
    if main_widget is None:
        raise BuilderError("Keine QMainWindow-Definition gefunden. Erwartet wird eine Qt-Designer .ui Datei.")

    handlers = parse_connections(root)
    menubar_name, menus, menu_height = parse_menus(main_widget, handlers)
    window = parse_window(main_widget, menu_height=menu_height)
    widgets = parse_widgets(root, handlers)
    return render_python(window, widgets, handlers, menubar_name, menus, dev_mode=dev_mode)


def convert_fbp_to_simplewx(input_path: Path) -> str:
    return convert_ui_to_simplewx(input_path)


def build_arg_parser() -> argparse.ArgumentParser:
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
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Fehler: Datei nicht gefunden: {input_path}", file=sys.stderr)
        return 2

    if input_path.suffix.lower() != ".ui":
        print(f"Fehler: Erwartet eine .ui-Datei, erhalten: {input_path.name}", file=sys.stderr)
        return 2

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

    try:
        code = convert_ui_to_simplewx(input_path, dev_mode=bool(args.dev))
    except BuilderError as exc:
        print(f"Abbruch: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(code, encoding="utf-8")
    print(f"OK: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
