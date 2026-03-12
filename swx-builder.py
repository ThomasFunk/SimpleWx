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


@dataclass
class WidgetSpec:
    class_name: str
    name: str
    position: Tuple[int, int]
    size: Optional[Tuple[int, int]]
    properties: Dict[str, str]


ALLOWED_INFRA_CLASSES = {
    "Project",
    "wxFrame",
    "wxPanel",
}

ALLOWED_WIDGET_CLASSES = {
    "wxStaticText",
    "wxButton",
    "wxTextCtrl",
    "wxCheckBox",
}

DYNAMIC_CLASSES = {
    "sizeritem",
    "spacer",
    "wxNotebook",
    "wxAuiNotebook",
    "wxSimplebook",
    "wxListbook",
    "wxChoicebook",
    "wxTreebook",
    "wxSplitterWindow",
    "wxScrolledWindow",
    "wxCollapsiblePane",
    "wxPropertyGrid",
    "wxDataViewCtrl",
    "wxGrid",
    "wxTreeCtrl",
    "wxListCtrl",
}

DYNAMIC_PROPERTY_NAMES = {
    "proportion",
    "flag",
    "border",
    "cellpos",
    "span",
    "minsize",
}


def read_property_map(obj: ET.Element) -> Dict[str, str]:
    properties: Dict[str, str] = {}
    for prop in obj.findall("property"):
        pname = (prop.get("name") or "").strip()
        pvalue = "".join(prop.itertext()).strip()
        properties[pname] = pvalue
    return properties


def parse_int_pair(raw: str, prop_name: str, widget_name: str) -> Tuple[int, int]:
    parts = [segment.strip() for segment in raw.split(",")]
    if len(parts) != 2:
        raise BuilderError(f"Ungültiger Wert für '{prop_name}' in Objekt '{widget_name}': {raw!r}")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise BuilderError(f"Nicht-numerischer Wert für '{prop_name}' in Objekt '{widget_name}': {raw!r}") from exc


def looks_dynamic_class(class_name: str) -> bool:
    if class_name in DYNAMIC_CLASSES:
        return True
    if "Sizer" in class_name:
        return True
    if class_name.startswith("wxAui"):
        return True
    return False


def sanitize_name(name: str, fallback_prefix: str, index: int) -> str:
    candidate = "".join(char if (char.isalnum() or char == "_") else "_" for char in name.strip())
    if not candidate:
        candidate = f"{fallback_prefix}_{index}"
    if candidate[0].isdigit():
        candidate = f"{fallback_prefix}_{candidate}"
    return candidate


def validate_static_only(root: ET.Element) -> None:
    for obj in root.iter("object"):
        class_name = (obj.get("class") or "").strip()
        object_name = (obj.get("name") or class_name or "<unnamed>").strip()

        if looks_dynamic_class(class_name):
            raise BuilderError(
                f"Nicht unterstützt: dynamisches Layout-Element '{class_name}' in '{object_name}'. "
                "Dieses Tool verarbeitet nur reine statische Layouts ohne Sizer/dynamische Container."
            )

        if class_name not in ALLOWED_INFRA_CLASSES and class_name not in ALLOWED_WIDGET_CLASSES:
            raise BuilderError(
                f"Nicht unterstützt: Objektklasse '{class_name}' in '{object_name}'. "
                "Erlaubt sind nur statische Basis-Widgets (wxStaticText, wxButton, wxTextCtrl, wxCheckBox)."
            )

        props = read_property_map(obj)
        for prop_name in DYNAMIC_PROPERTY_NAMES:
            if prop_name in props:
                raise BuilderError(
                    f"Nicht unterstützt: dynamische Layout-Property '{prop_name}' in '{object_name}'. "
                    "Bitte in wxFormBuilder ein reines statisches Layout ohne Sizer verwenden."
                )


def parse_window(root: ET.Element) -> WindowSpec:
    frame_obj: Optional[ET.Element] = None
    for obj in root.iter("object"):
        if (obj.get("class") or "").strip() == "wxFrame":
            frame_obj = obj
            break

    if frame_obj is None:
        raise BuilderError("Keine wxFrame-Definition gefunden. Das Tool erwartet ein statisches wxFrame-Layout.")

    frame_name = sanitize_name(frame_obj.get("name") or "mainWindow", "frame", 0)
    props = read_property_map(frame_obj)
    frame_title = props.get("title") or frame_name

    raw_size = props.get("size")
    frame_size: Optional[Tuple[int, int]] = None
    if raw_size:
        size_pair = parse_int_pair(raw_size, "size", frame_name)
        if size_pair != (-1, -1):
            frame_size = size_pair

    return WindowSpec(name=frame_name, title=frame_title, size=frame_size)


def parse_widgets(root: ET.Element) -> List[WidgetSpec]:
    widgets: List[WidgetSpec] = []
    running_index = 1

    for obj in root.iter("object"):
        class_name = (obj.get("class") or "").strip()
        if class_name not in ALLOWED_WIDGET_CLASSES:
            continue

        props = read_property_map(obj)
        raw_name = (obj.get("name") or "").strip()
        widget_name = sanitize_name(raw_name, "widget", running_index)

        if "pos" not in props:
            raise BuilderError(
                f"Widget '{widget_name}' ({class_name}) hat keine 'pos'-Property. "
                "Für statische Layouts sind absolute Koordinaten zwingend erforderlich."
            )

        position = parse_int_pair(props["pos"], "pos", widget_name)
        size: Optional[Tuple[int, int]] = None

        raw_size = props.get("size")
        if raw_size:
            size_pair = parse_int_pair(raw_size, "size", widget_name)
            if size_pair != (-1, -1):
                size = size_pair

        if class_name == "wxTextCtrl" and size is None:
            raise BuilderError(
                f"Widget '{widget_name}' ({class_name}) hat keine verwertbare 'size'-Property. "
                "SimpleWx benötigt bei add_entry/add_text_view eine feste Größe."
            )

        widgets.append(
            WidgetSpec(
                class_name=class_name,
                name=widget_name,
                position=position,
                size=size,
                properties=props,
            )
        )
        running_index += 1

    return widgets


def quote(text: str) -> str:
    return repr(text)


def build_widget_call(widget: WidgetSpec) -> str:
    x, y = widget.position

    if widget.class_name == "wxStaticText":
        title = widget.properties.get("label") or widget.properties.get("title") or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
        ]
        return f"win.add_label({', '.join(args)})"

    if widget.class_name == "wxButton":
        title = widget.properties.get("label") or widget.properties.get("title") or widget.name
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Function=on_{widget.name}_click",
        ]
        if widget.size is not None:
            args.append(f"Size=[{widget.size[0]}, {widget.size[1]}]")
        return f"win.add_button({', '.join(args)})"

    if widget.class_name == "wxTextCtrl":
        raw_style = (widget.properties.get("style") or "").lower()
        text = widget.properties.get("value") or widget.properties.get("text") or ""
        width, height = widget.size if widget.size is not None else (140, 24)

        if "wxte_multiline" in raw_style:
            args = [
                f"Name={quote(widget.name)}",
                f"Position=[{x}, {y}]",
                f"Size=[{width}, {height}]",
            ]
            if text:
                args.append(f"Text={quote(text)}")
            return f"win.add_text_view({', '.join(args)})"

        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Size=[{width}, {height}]",
        ]
        if text:
            args.append(f"Title={quote(text)}")
        return f"win.add_entry({', '.join(args)})"

    if widget.class_name == "wxCheckBox":
        title = widget.properties.get("label") or widget.properties.get("title") or widget.name
        checked = (widget.properties.get("checked") or "0").strip().lower()
        active = 1 if checked in {"1", "true", "yes"} else 0
        args = [
            f"Name={quote(widget.name)}",
            f"Position=[{x}, {y}]",
            f"Title={quote(title)}",
            f"Active={active}",
        ]
        return f"win.add_check_button({', '.join(args)})"

    raise BuilderError(f"Interner Fehler: Keine Mapping-Regel für {widget.class_name}")


def render_python(window: WindowSpec, widgets: List[WidgetSpec]) -> str:
    lines: List[str] = []
    lines.append("#!/usr/bin/env python3")
    lines.append("from simplewx import SimpleWx as simplewx")
    lines.append("")
    lines.append("win = simplewx()")

    window_args = [
        f"Name={quote(window.name)}",
        f"Title={quote(window.title)}",
        "Fixed=1",
    ]
    if window.size is not None:
        window_args.append(f"Size=[{window.size[0]}, {window.size[1]}]")

    lines.append(f"win.new_window({', '.join(window_args)})")
    lines.append("")

    button_widgets = [widget for widget in widgets if widget.class_name == "wxButton"]
    for widget in button_widgets:
        lines.append(f"def on_{widget.name}_click(_event):")
        lines.append("    pass")
        lines.append("")

    for widget in widgets:
        lines.append(build_widget_call(widget))

    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    win.show_and_run()")
    lines.append("")

    return "\n".join(lines)


def convert_fbp_to_simplewx(input_path: Path) -> str:
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as exc:
        raise BuilderError(f"XML-Parsing fehlgeschlagen für {input_path}: {exc}") from exc

    root = tree.getroot()
    validate_static_only(root)
    window = parse_window(root)
    widgets = parse_widgets(root)
    return render_python(window, widgets)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parst eine wxFormBuilder .fbp-Datei und erzeugt ein SimpleWx-Grundgerüst. "
            "Nur reine statische Layouts sind erlaubt."
        )
    )
    parser.add_argument("-i", "--input", type=Path, required=True, help="Pfad zur .fbp-Datei")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Ausgabepfad für das Grundgerüst (.py) oder Zielverzeichnis; "
            "Standard: gleiches Verzeichnis wie Input mit Namen <input>_swx.py"
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Fehler: Datei nicht gefunden: {input_path}", file=sys.stderr)
        return 2

    if input_path.suffix.lower() != ".fbp":
        print(f"Fehler: Erwartet eine .fbp-Datei, erhalten: {input_path.name}", file=sys.stderr)
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
        code = convert_fbp_to_simplewx(input_path)
    except BuilderError as exc:
        print(f"Abbruch: {exc}", file=sys.stderr)
        return 1

    output_path.write_text(code, encoding="utf-8")
    print(f"OK: {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
