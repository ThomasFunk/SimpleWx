#!/usr/bin/env python3

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest


def _unit_passed(check: str) -> None:
    print("", flush=True)
    left = f"SWX builder: {check}"
    print(f"{left:<72} [PASSED]", flush=True)


def _load_builder_module():
    root = Path(__file__).resolve().parent.parent
    module_path = root / "tools" / "swx-builder" / "swx-builder.py"
    spec = spec_from_file_location("swx_builder", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_convert_static_ui_matches_expected_reference() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_minimal.ui"
    expected_path = root / "examples" / "formbuilder" / "qt_minimal_expected.py"

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(sample_path)
    expected = expected_path.read_text(encoding="utf-8")

    assert generated == expected
    _unit_passed("static ui conversion matches expected output")


def test_convert_dynamic_ui_fails_on_layout() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_with_layout.ui"

    builder = _load_builder_module()

    with pytest.raises(builder.BuilderError, match="dynamisches Layout-Element"):
        builder.convert_ui_to_simplewx(sample_path)

    _unit_passed("dynamic/layout ui rejected with clear error")


def test_convert_static_ui_dev_mode_sets_base_zero() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_minimal.ui"

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(sample_path, dev_mode=True)

    assert "Base=0" in generated
    _unit_passed("dev mode emits Base=0 in new_window")


def test_convert_static_ui_qframe_maps_to_add_frame(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_only.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>320</width><height>240</height></rect>
  </property>
  <property name=\"windowTitle\"><string>Frame Test</string></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame\">
    <property name=\"geometry\">
     <rect><x>10</x><y>20</y><width>120</width><height>80</height></rect>
    </property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "win.add_frame(" in generated
    assert "Name='frame'" in generated
    assert "Position=[10, 20]" in generated
    assert "Size=[120, 80]" in generated
    _unit_passed("qframe conversion maps to add_frame")


def test_convert_static_ui_frame_label_is_mapped_to_frame_title(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_with_label.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>420</width><height>260</height></rect>
  </property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Composite_Manager\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>380</width><height>120</height></rect>
    </property>
   </widget>
   <widget class=\"QLabel\" name=\"label_frame_Composite_Manager\">
    <property name=\"geometry\">
     <rect><x>20</x><y>3</y><width>180</width><height>16</height></rect>
    </property>
    <property name=\"text\"><string>Composite Manager</string></property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "win.add_frame(" in generated
    assert "Name='frame_Composite_Manager'" in generated
    assert "Title='Composite Manager'" in generated
    assert "win.add_label(Name='label_frame_Composite_Manager'" not in generated
    _unit_passed("frame title label is mapped to add_frame title")


def test_convert_static_ui_widgets_inside_frame_use_frame_parenting(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_children.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>420</width><height>260</height></rect>
  </property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Main\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>300</width><height>120</height></rect>
    </property>
   </widget>
   <widget class=\"QRadioButton\" name=\"radioButton\">
    <property name=\"geometry\">
     <rect><x>30</x><y>30</y><width>100</width><height>20</height></rect>
    </property>
    <property name=\"text\"><string>Option A</string></property>
   </widget>
   <widget class=\"QLineEdit\" name=\"lineEdit\">
    <property name=\"geometry\">
     <rect><x>40</x><y>60</y><width>120</width><height>24</height></rect>
    </property>
    <property name=\"text\"><string>abc</string></property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "win.add_frame(Name='frame_Main'" in generated
    assert "win.add_radio_button(" in generated
    assert "Name='radioButton'" in generated
    assert "Frame='frame_Main'" in generated
    assert "Group='group_frame_Main'" in generated
    assert "Position=[20, 20]" in generated
    assert "win.add_entry(" in generated
    assert "Name='lineEdit'" in generated
    assert "Position=[30, 50]" in generated
    _unit_passed("frame-contained widgets use Frame parenting and radio mapping")


def test_convert_static_ui_frame_title_height_adjusts_child_y(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_title_height_adjust.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>420</width><height>260</height></rect>
  </property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Main\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>300</width><height>120</height></rect>
    </property>
   </widget>
   <widget class=\"QLabel\" name=\"label_frame_Main\">
    <property name=\"geometry\">
     <rect><x>20</x><y>3</y><width>120</width><height>16</height></rect>
    </property>
    <property name=\"text\"><string>Main</string></property>
   </widget>
   <widget class=\"QLineEdit\" name=\"lineEdit\">
    <property name=\"geometry\">
     <rect><x>30</x><y>30</y><width>120</width><height>24</height></rect>
    </property>
    <property name=\"text\"><string>abc</string></property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "Name='frame_Main'" in generated
    assert "Title='Main'" in generated
    assert "Frame='frame_Main'" in generated
    assert "Position=[20, 20]" in generated
    _unit_passed("frame title height does not shift frame-local child y")
