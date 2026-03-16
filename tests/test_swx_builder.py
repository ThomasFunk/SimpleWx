#!/usr/bin/env python3

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
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
    generated = builder.convert_ui_to_simplewx(sample_path, dev_mode=True)
    expected = expected_path.read_text(encoding="utf-8")

    generated_norm = re.sub(r'__date__\s*=\s*"\d{4}/\d{2}/\d{2}"', '__date__ = "<DATE>"', generated)
    expected_norm = re.sub(r'__date__\s*=\s*"\d{4}/\d{2}/\d{2}"', '__date__ = "<DATE>"', expected)

    assert generated_norm == expected_norm
    _unit_passed("static ui conversion matches expected output")


def test_convert_dynamic_ui_fails_on_layout() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_with_layout.ui"

    builder = _load_builder_module()

    with pytest.raises(builder.BuilderError, match="dynamisches Layout-Element"):
        builder.convert_ui_to_simplewx(sample_path)

    _unit_passed("dynamic/layout ui rejected with clear error")


def test_convert_static_ui_default_mode_keeps_scaling_enabled() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_minimal.ui"

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(sample_path)

    assert "Base=0" not in generated
    assert "__author__ = 'swxbuilder'" in generated
    assert '__version__ = "0.1.0"' in generated
    assert re.search(r'__date__\s*=\s*"\d{4}/\d{2}/\d{2}"', generated) is not None
    assert "Signal=wx.EVT_BUTTON" in generated
    _unit_passed("default builder mode keeps scaling enabled")


def test_convert_static_ui_debug_mode_emits_base_zero() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "qt_minimal.ui"

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(sample_path, dev_mode=True)

    assert "Base=0" in generated
    _unit_passed("debug builder mode emits Base=0 in new_window")


def test_build_arg_parser_accepts_date_short_option_and_debug_long_option() -> None:
    builder = _load_builder_module()
    parser = builder.build_arg_parser()

    args = parser.parse_args([
        "-i",
        "form.ui",
        "-d",
        "2026/03/16",
        "--debug",
        "-a",
        "swxbuilder",
        "-v",
        "0.1.0",
    ])

    assert args.input == Path("form.ui")
    assert args.date == "2026/03/16"
    assert args.debug is True
    assert args.author == "swxbuilder"
    assert args.version == "0.1.0"
    _unit_passed("cli parser accepts -d for date and --debug flag")


def test_build_arg_parser_keeps_output_optional() -> None:
    builder = _load_builder_module()
    parser = builder.build_arg_parser()

    args = parser.parse_args(["-i", "form.ui"])

    assert args.input == Path("form.ui")
    assert args.output is None
    assert args.date is None
    assert args.debug is False
    _unit_passed("cli parser keeps output and metadata flags optional")


def test_convert_static_ui_qaction_triggered_maps_to_menu_signal(tmp_path: Path) -> None:
    ui_path = tmp_path / "menu_action_signal.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>200</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\"/>
  <widget class=\"QMenuBar\" name=\"menubar\">
   <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>24</height></rect></property>
   <widget class=\"QMenu\" name=\"menuFile\">
    <property name=\"title\"><string>File</string></property>
    <addaction name=\"actionNew\"/>
   </widget>
  </widget>
  <action name=\"actionNew\">
   <property name=\"text\"><string>New</string></property>
  </action>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>actionNew</sender>
   <signal>triggered()</signal>
   <receiver>MainWindow</receiver>
   <slot>dummy()</slot>
  </connection>
 </connections>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "import wx" in generated
    assert "Function=on_actionNew_triggered" in generated
    assert "Signal=wx.EVT_MENU" in generated
    _unit_passed("qaction triggered signal maps to menu event")


def test_convert_static_ui_priority1_widgets_are_rendered(tmp_path: Path) -> None:
    ui_path = tmp_path / "prio1_widgets.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>480</width><height>260</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QComboBox\" name=\"comboProfiles\">
    <property name=\"geometry\"><rect><x>20</x><y>20</y><width>120</width><height>29</height></rect></property>
    <property name=\"currentIndex\"><number>1</number></property>
    <item><property name=\"text\"><string>Default</string></property></item>
    <item><property name=\"text\"><string>Gaming</string></property></item>
   </widget>
   <widget class=\"QSlider\" name=\"horizontalSlider\">
    <property name=\"geometry\"><rect><x>170</x><y>28</y><width>160</width><height>16</height></rect></property>
    <property name=\"orientation\"><enum>Qt::Orientation::Horizontal</enum></property>
    <property name=\"minimum\"><number>10</number></property>
    <property name=\"maximum\"><number>90</number></property>
    <property name=\"value\"><number>24</number></property>
   </widget>
   <widget class=\"QFrame\" name=\"frame_Sound\">
    <property name=\"geometry\"><rect><x>20</x><y>70</y><width>80</width><height>170</height></rect></property>
    <widget class=\"QSlider\" name=\"verticalSlider\">
     <property name=\"geometry\"><rect><x>25</x><y>10</y><width>16</width><height>140</height></rect></property>
     <property name=\"orientation\"><enum>Qt::Orientation::Vertical</enum></property>
     <property name=\"value\"><number>55</number></property>
    </widget>
   </widget>
   <widget class=\"QLabel\" name=\"label_frame_Sound\">
    <property name=\"geometry\"><rect><x>28</x><y>60</y><width>48</width><height>16</height></rect></property>
    <property name=\"text\"><string>Sound</string></property>
   </widget>
   <widget class=\"QProgressBar\" name=\"progressBar\">
    <property name=\"geometry\"><rect><x>140</x><y>120</y><width>260</width><height>32</height></rect></property>
    <property name=\"minimum\"><number>0</number></property>
    <property name=\"maximum\"><number>100</number></property>
    <property name=\"value\"><number>24</number></property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>comboProfiles</sender>
   <signal>currentIndexChanged(int)</signal>
   <receiver>MainWindow</receiver>
   <slot>dummy()</slot>
  </connection>
  <connection>
   <sender>horizontalSlider</sender>
   <signal>valueChanged(int)</signal>
   <receiver>MainWindow</receiver>
   <slot>dummy()</slot>
  </connection>
  <connection>
   <sender>verticalSlider</sender>
   <signal>valueChanged(int)</signal>
   <receiver>MainWindow</receiver>
   <slot>dummy()</slot>
  </connection>
 </connections>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "win.add_combo_box(" in generated
    assert "Data=['Default', 'Gaming']" in generated
    assert "Start=1" in generated
    assert "Signal=wx.EVT_COMBOBOX" in generated
    assert "win.add_slider(" in generated
    assert "Orientation='horizontal'" in generated
    assert "Orientation='vertical'" in generated
    assert "Signal=wx.EVT_SLIDER" in generated
    assert "win.add_progress_bar(" in generated
    assert "Steps=100" in generated
    assert "win.set_value('progressBar', 'Value', 24)" in generated
    _unit_passed("priority 1 widgets render with signals and values")


def test_convert_static_ui_menu_separator_and_icons_are_rendered(tmp_path: Path) -> None:
    ui_path = tmp_path / "menu_separator_icons.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>200</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\"/>
  <widget class=\"QMenuBar\" name=\"menubar\">
   <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>24</height></rect></property>
   <widget class=\"QMenu\" name=\"menuFile\">
    <property name=\"title\"><string>File</string></property>
    <addaction name=\"actionNew\"/>
    <addaction name=\"separator\"/>
    <addaction name=\"actionQuit\"/>
   </widget>
  </widget>
  <action name=\"actionNew\">
   <property name=\"icon\"><iconset theme=\"document-new\"/></property>
   <property name=\"text\"><string>New</string></property>
   <property name=\"toolTip\"><string>Create new file</string></property>
  </action>
  <action name=\"actionQuit\">
   <property name=\"icon\"><iconset theme=\"application-exit\"/></property>
   <property name=\"text\"><string>Quit</string></property>
  </action>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "Tooltip='Create new file'" in generated
    assert "Icon='gtk-new'" in generated
    assert "Icon='gtk-quit'" in generated
    assert "Type='separator'" in generated
    _unit_passed("menu separators and icons are rendered")


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


def test_convert_static_ui_groups_frames_with_children_and_comments(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_grouping.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>420</width><height>260</height></rect>
  </property>
  <property name=\"windowTitle\"><string>Demo</string></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Top\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>180</width><height>80</height></rect>
    </property>
   </widget>
   <widget class=\"QLabel\" name=\"label_frame_Top\">
    <property name=\"geometry\">
     <rect><x>20</x><y>3</y><width>80</width><height>16</height></rect>
    </property>
    <property name=\"text\"><string>Top</string></property>
   </widget>
   <widget class=\"QCheckBox\" name=\"checkBox\">
    <property name=\"geometry\">
     <rect><x>20</x><y>30</y><width>80</width><height>19</height></rect>
    </property>
    <property name=\"text\"><string>One</string></property>
   </widget>
   <widget class=\"QLineEdit\" name=\"lineEdit\">
    <property name=\"geometry\">
     <rect><x>90</x><y>55</y><width>60</width><height>24</height></rect>
    </property>
    <property name=\"text\"><string>abc</string></property>
   </widget>
   <widget class=\"QPushButton\" name=\"pushButton\">
    <property name=\"geometry\">
     <rect><x>10</x><y>200</y><width>80</width><height>24</height></rect>
    </property>
    <property name=\"text\"><string>Run</string></property>
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

    assert "# Main Window 'Demo'" in generated
    assert "# Frame 'Top'" in generated
    assert generated.index("# Frame 'Top'") < generated.index("Name='checkBox'")
    assert generated.index("Name='checkBox'") < generated.index("Name='lineEdit'")
    assert "# Buttons at the bottom" in generated
    _unit_passed("frame sections are grouped with visual ordering comments")


def test_convert_static_ui_qgroupbox_radio_offset_and_group(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_groupbox_radio.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>320</width><height>200</height></rect>
  </property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Composite_Manager\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>280</width><height>80</height></rect>
    </property>
    <widget class=\"QGroupBox\" name=\"groupBox_Compositors\">
     <property name=\"geometry\">
      <rect><x>10</x><y>10</y><width>260</width><height>40</height></rect>
     </property>
     <widget class=\"QRadioButton\" name=\"radioButton\">
      <property name=\"geometry\">
       <rect><x>60</x><y>5</y><width>100</width><height>19</height></rect>
      </property>
      <property name=\"text\"><string>Xcompmgr</string></property>
     </widget>
    </widget>
   </widget>
   <widget class=\"QRadioButton\" name=\"radioButton_legacy\">
    <property name=\"geometry\">
     <rect><x>30</x><y>30</y><width>100</width><height>19</height></rect>
    </property>
    <property name=\"text\"><string>Legacy</string></property>
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

    # GroupBox child: absolute(80,25) inside frame(10,10) -> local(70,15)
    assert "Name='radioButton'" in generated
    assert "Position=[70, 15]" in generated
    assert "Group='groupBox_Compositors'" in generated

    # Legacy path without GroupBox must remain unchanged.
    # absolute(30,30) inside frame(10,10) -> local(20,20)
    assert "Name='radioButton_legacy'" in generated
    assert "Position=[20, 20]" in generated
    assert "Group='group_frame_Composite_Manager'" in generated
    _unit_passed("qgroupbox radio offset/group works without changing legacy behavior")


def test_convert_static_ui_qtabwidget_maps_to_notebook_pages(tmp_path: Path) -> None:
    ui_path = tmp_path / "notebook_pages.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\">
   <rect><x>0</x><y>0</y><width>420</width><height>320</height></rect>
  </property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QTabWidget\" name=\"tabWidget\">
    <property name=\"geometry\">
     <rect><x>10</x><y>10</y><width>390</width><height>240</height></rect>
    </property>
    <widget class=\"QWidget\" name=\"tab_one\">
     <attribute name=\"title\"><string>One</string></attribute>
     <widget class=\"QLabel\" name=\"label_one\">
      <property name=\"geometry\"><rect><x>20</x><y>20</y><width>80</width><height>20</height></rect></property>
      <property name=\"text\"><string>Hello</string></property>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_two\">
     <attribute name=\"title\"><string>Two</string></attribute>
     <widget class=\"QTextEdit\" name=\"textEdit\">
      <property name=\"geometry\"><rect><x>15</x><y>10</y><width>120</width><height>90</height></rect></property>
      <property name=\"plainText\"><string>abc</string></property>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_three\">
     <attribute name=\"title\"><string>Three</string></attribute>
     <widget class=\"QSpinBox\" name=\"spinBox_Counter\">
      <property name=\"geometry\"><rect><x>25</x><y>30</y><width>70</width><height>24</height></rect></property>
      <property name=\"value\"><number>7</number></property>
     </widget>
    </widget>
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

    assert "win.add_notebook(" in generated
    assert "Name='tabWidget'" in generated
    assert "win.add_nb_page(Name='tab_one', Notebook='tabWidget', Title='One', PositionNumber=0)" in generated
    assert "win.add_nb_page(Name='tab_two', Notebook='tabWidget', Title='Two', PositionNumber=1)" in generated
    assert "win.add_nb_page(Name='tab_three', Notebook='tabWidget', Title='Three', PositionNumber=2)" in generated
    assert "win.add_label(Name='label_one', Position=[20, 20], Title='Hello', Frame='tab_one')" in generated
    assert "win.add_text_view(" in generated
    assert "Name='textEdit'" in generated
    assert "Frame='tab_two'" in generated
    assert "win.add_spin_button(" in generated
    assert "Name='spinBox_Counter'" in generated
    assert "Start=7" in generated
    assert "Frame='tab_three'" in generated
    _unit_passed("qtabwidget maps to notebook pages with page-contained widgets")


def test_convert_static_ui_frame_label_mapping_is_case_insensitive(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_case_label.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>220</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"frame_Groups\">
    <property name=\"geometry\"><rect><x>10</x><y>20</y><width>180</width><height>100</height></rect></property>
   </widget>
   <widget class=\"QLabel\" name=\"label_frame_groups\">
    <property name=\"geometry\"><rect><x>20</x><y>9</y><width>80</width><height>21</height></rect></property>
    <property name=\"text\"><string>Groups</string></property>
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

    assert "win.add_frame(Name='frame_Groups'" in generated
    assert "Title='Groups'" in generated
    assert "win.add_label(Name='label_frame_groups'" not in generated
    _unit_passed("frame title label mapping handles case differences")


def test_convert_static_ui_spinbox_min_width_shifts_right_label(tmp_path: Path) -> None:
    ui_path = tmp_path / "spin_with_right_label.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>220</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QSpinBox\" name=\"spinBox_Counter\">
    <property name=\"geometry\"><rect><x>30</x><y>30</y><width>61</width><height>29</height></rect></property>
   </widget>
   <widget class=\"QLabel\" name=\"label_counter\">
    <property name=\"geometry\"><rect><x>110</x><y>35</y><width>67</width><height>21</height></rect></property>
    <property name=\"text\"><string>Counter</string></property>
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

    assert "win.add_spin_button(Name='spinBox_Counter', Position=[30, 30], Size=[80, 29])" in generated
    assert "win.add_label(Name='label_counter', Position=[129, 35], Title='Counter')" in generated
    _unit_passed("spinbox minimum width is enforced and right-side label keeps its gap")
