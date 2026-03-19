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


@pytest.mark.parametrize("top_level_class", ["QDialog", "QMessageBox", "QFileDialog"])
def test_convert_static_dialog_like_top_levels_with_button_box(top_level_class: str, tmp_path: Path) -> None:
    ui_path = tmp_path / f"{top_level_class.lower()}_static.ui"
    ui_path.write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>{top_level_class}</class>
 <widget class=\"{top_level_class}\" name=\"DialogRoot\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>420</width><height>220</height></rect></property>
  <property name=\"windowTitle\"><string>{top_level_class} Demo</string></property>
  <widget class=\"QLabel\" name=\"labelInfo\">
   <property name=\"geometry\"><rect><x>24</x><y>24</y><width>180</width><height>22</height></rect></property>
   <property name=\"text\"><string>Status</string></property>
  </widget>
  <widget class=\"QDialogButtonBox\" name=\"buttonBox\">
   <property name=\"geometry\"><rect><x>200</x><y>170</y><width>191</width><height>29</height></rect></property>
   <property name=\"standardButtons\"><set>QDialogButtonBox::StandardButton::Cancel|QDialogButtonBox::StandardButton::Ok</set></property>
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

    assert "win.new_window(Name='DialogRoot', Title='" in generated
    assert f"Title='{top_level_class} Demo'" in generated
    assert "win.add_label(Name='labelInfo'" in generated
    assert "win.add_button(Name='buttonBox_cancel'" in generated
    assert "Title='Cancel'" in generated
    assert "win.add_button(Name='buttonBox_ok'" in generated
    assert "Title='Ok'" in generated
    assert generated.index("Name='buttonBox_cancel'") < generated.index("Name='buttonBox_ok'")
    _unit_passed(f"{top_level_class} top-level ui is converted with dialog buttons")


def test_convert_static_ui_qdialogbuttonbox_connections_map_to_generated_buttons(tmp_path: Path) -> None:
    ui_path = tmp_path / "dialog_buttonbox_signal.ui"
    ui_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Dialog</class>
 <widget class="QDialog" name="Dialog">
  <property name="geometry"><rect><x>0</x><y>0</y><width>320</width><height>160</height></rect></property>
  <property name="windowTitle"><string>Dialog</string></property>
  <widget class="QDialogButtonBox" name="buttonBox">
   <property name="geometry"><rect><x>110</x><y>110</y><width>181</width><height>29</height></rect></property>
   <property name="standardButtons"><set>QDialogButtonBox::StandardButton::Cancel|QDialogButtonBox::StandardButton::Ok</set></property>
  </widget>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>buttonBox</sender>
   <signal>accepted()</signal>
   <receiver>Dialog</receiver>
   <slot>accept()</slot>
  </connection>
    <connection>
     <sender>buttonBox</sender>
     <signal>rejected()</signal>
     <receiver>Dialog</receiver>
     <slot>reject()</slot>
    </connection>
 </connections>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "def on_buttonBox_accepted(_event):" in generated
    assert "def on_buttonBox_rejected(_event):" in generated

    ok_call_start = generated.index("Name='buttonBox_ok'")
    ok_call_end = generated.index("\n)", ok_call_start)
    ok_call = generated[ok_call_start:ok_call_end]
    assert "Signal=wx.EVT_BUTTON" in ok_call
    assert "Function=on_buttonBox_accepted" in ok_call
    assert "Function=on_buttonBox_rejected" not in ok_call

    cancel_call_start = generated.index("Name='buttonBox_cancel'")
    cancel_call_end = generated.index("\n)", cancel_call_start)
    cancel_call = generated[cancel_call_start:cancel_call_end]
    assert "Signal=wx.EVT_BUTTON" in cancel_call
    assert "Function=on_buttonBox_rejected" in cancel_call
    assert "Function=on_buttonBox_accepted" not in cancel_call
    _unit_passed("qdialogbuttonbox accepted/rejected signals are attached to matching generated buttons")


def test_convert_static_ui_qdialogbuttonbox_click_slot_generates_toggle_body(tmp_path: Path) -> None:
    """Receiver widget + click() slot → handler body toggles the widget instead of 'pass'."""
    ui_path = tmp_path / "dialog_click_slot.ui"
    ui_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Dialog</class>
 <widget class="QDialog" name="Dialog">
  <property name="geometry"><rect><x>0</x><y>0</y><width>320</width><height>200</height></rect></property>
  <property name="windowTitle"><string>Dialog</string></property>
  <widget class="QCheckBox" name="checkBox">
   <property name="geometry"><rect><x>40</x><y>100</y><width>94</width><height>27</height></rect></property>
   <property name="text"><string>All</string></property>
  </widget>
  <widget class="QCheckBox" name="checkBox_2">
   <property name="geometry"><rect><x>40</x><y>130</y><width>94</width><height>27</height></rect></property>
   <property name="text"><string>Nothing</string></property>
  </widget>
  <widget class="QDialogButtonBox" name="buttonBox">
   <property name="geometry"><rect><x>110</x><y>160</y><width>181</width><height>29</height></rect></property>
   <property name="standardButtons"><set>QDialogButtonBox::StandardButton::Cancel|QDialogButtonBox::StandardButton::Ok</set></property>
  </widget>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>buttonBox</sender>
   <signal>accepted()</signal>
   <receiver>checkBox</receiver>
   <slot>click()</slot>
  </connection>
  <connection>
   <sender>buttonBox</sender>
   <signal>rejected()</signal>
   <receiver>checkBox_2</receiver>
   <slot>click()</slot>
  </connection>
 </connections>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    # accepted → toggles checkBox
    accepted_def_pos = generated.index("def on_buttonBox_accepted(_event):")
    accepted_body = generated[accepted_def_pos: generated.index("\n\n", accepted_def_pos)]
    assert "win.get_widget('checkBox')" in accepted_body
    assert "checkBox.SetValue(not" in accepted_body
    assert "pass" not in accepted_body

    # rejected → toggles checkBox_2
    rejected_def_pos = generated.index("def on_buttonBox_rejected(_event):")
    rejected_body = generated[rejected_def_pos: generated.index("\n\n", rejected_def_pos)]
    assert "win.get_widget('checkBox_2')" in rejected_body
    assert "checkBox_2.SetValue(not" in rejected_body
    assert "pass" not in rejected_body

    _unit_passed("QDialogButtonBox click() slot generates toggle body for receiver widget")


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


def test_build_arg_parser_accepts_no_debug_option() -> None:
    builder = _load_builder_module()
    parser = builder.build_arg_parser()

    args = parser.parse_args(["-i", "form.ui", "--no-debug"])

    assert args.input == Path("form.ui")
    assert args.debug is False
    _unit_passed("cli parser accepts --no-debug as scaling opt-out")


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


def test_convert_static_ui_priority3_view_widgets_are_rendered(tmp_path: Path) -> None:
    ui_path = tmp_path / "prio3_views.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>620</width><height>420</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QTabWidget\" name=\"tabWidget\">
    <property name=\"geometry\"><rect><x>20</x><y>20</y><width>560</width><height>320</height></rect></property>
    <widget class=\"QWidget\" name=\"tab_tree\">
     <attribute name=\"title\"><string>Tree</string></attribute>
     <widget class=\"QTreeWidget\" name=\"treeWidget\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
      <column><property name=\"text\"><string>Name</string></property></column>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_table\">
     <attribute name=\"title\"><string>Table</string></attribute>
     <widget class=\"QTableWidget\" name=\"tableWidget\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
      <property name=\"rowCount\"><number>2</number></property>
      <property name=\"columnCount\"><number>2</number></property>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_list_widget\">
     <attribute name=\"title\"><string>ListWidget</string></attribute>
     <widget class=\"QListWidget\" name=\"listWidget\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
      <item><property name=\"text\"><string>Alpha</string></property></item>
      <item><property name=\"text\"><string>Beta</string></property></item>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_list_view\">
     <attribute name=\"title\"><string>ListView</string></attribute>
     <widget class=\"QListView\" name=\"listView\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_tableview\">
     <attribute name=\"title\"><string>TableView</string></attribute>
     <widget class=\"QTableView\" name=\"tableView\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
     </widget>
    </widget>
    <widget class=\"QWidget\" name=\"tab_treeview\">
     <attribute name=\"title\"><string>TreeView</string></attribute>
     <widget class=\"QTreeView\" name=\"treeView\">
      <property name=\"geometry\"><rect><x>10</x><y>10</y><width>500</width><height>240</height></rect></property>
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

    assert "win.add_treeview(" in generated
    assert "Name='treeWidget'" in generated
    assert "Headers=['Name']" in generated
    assert "win.add_grid(" in generated
    assert "Name='tableWidget'" in generated
    assert "Headers=['Column 1', 'Column 2']" in generated
    assert "Data=[['', ''], ['', '']]" in generated
    assert "win.add_listview(" in generated
    assert "Name='listWidget'" in generated
    assert "Data=[['Alpha'], ['Beta']]" in generated
    assert "Name='listView'" in generated
    assert "win.add_dataview(" in generated
    assert "Name='tableView'" in generated
    assert "Name='treeView'" in generated
    _unit_passed("priority 3 views map to simplewx data widgets")


def test_convert_static_ui_qframe_hline_vline_map_to_separators(tmp_path: Path) -> None:
    ui_path = tmp_path / "frame_line_separators.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>360</width><height>220</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFrame\" name=\"lineHorizontal\">
    <property name=\"geometry\"><rect><x>20</x><y>40</y><width>200</width><height>3</height></rect></property>
    <property name=\"frameShape\"><enum>QFrame::HLine</enum></property>
   </widget>
   <widget class=\"QFrame\" name=\"lineVertical\">
    <property name=\"geometry\"><rect><x>260</x><y>20</y><width>3</width><height>120</height></rect></property>
    <property name=\"frameShape\"><enum>QFrame::VLine</enum></property>
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

    assert "win.add_separator(" in generated
    assert "Name='lineHorizontal'" in generated
    assert "Orientation='horizontal'" in generated
    assert "Name='lineVertical'" in generated
    assert "Orientation='vertical'" in generated
    assert "win.add_frame(Name='lineHorizontal'" not in generated
    assert "win.add_frame(Name='lineVertical'" not in generated
    _unit_passed("qframe hline/vline map to add_separator")


def test_convert_static_ui_notebook_page_qframe_line_uses_page_frame(tmp_path: Path) -> None:
    ui_path = tmp_path / "notebook_line_separator.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>420</width><height>320</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QTabWidget\" name=\"tabWidget\">
    <property name=\"geometry\"><rect><x>10</x><y>10</y><width>390</width><height>240</height></rect></property>
    <widget class=\"QWidget\" name=\"tab_one\">
     <attribute name=\"title\"><string>One</string></attribute>
     <widget class=\"QFrame\" name=\"linePage\">
      <property name=\"geometry\"><rect><x>20</x><y>30</y><width>180</width><height>3</height></rect></property>
      <property name=\"frameShape\"><enum>QFrame::HLine</enum></property>
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

    assert "win.add_separator(" in generated
    assert "Name='linePage'" in generated
    assert "Orientation='horizontal'" in generated
    assert "Frame='tab_one'" in generated
    _unit_passed("notebook page qframe line uses add_separator with page frame")


def test_convert_static_ui_line_widgets_map_to_separators(tmp_path: Path) -> None:
    ui_path = tmp_path / "line_widgets.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>420</width><height>260</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"Line\" name=\"line_h\">
    <property name=\"geometry\"><rect><x>20</x><y>40</y><width>200</width><height>3</height></rect></property>
    <property name=\"orientation\"><enum>Qt::Orientation::Horizontal</enum></property>
   </widget>
   <widget class=\"Line\" name=\"line_v\">
    <property name=\"geometry\"><rect><x>260</x><y>20</y><width>3</width><height>120</height></rect></property>
    <property name=\"orientation\"><enum>Qt::Orientation::Vertical</enum></property>
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

    assert "win.add_separator(" in generated
    assert "Name='line_h'" in generated
    assert "Orientation='horizontal'" in generated
    assert "Name='line_v'" in generated
    assert "Orientation='vertical'" in generated
    _unit_passed("line widgets map to add_separator")


def test_convert_static_ui_qrc_icon_is_resolved_to_real_file(tmp_path: Path) -> None:
    icons_dir = tmp_path / "assets"
    icons_dir.mkdir()
    icon_path = icons_dir / "rename.png"
    icon_path.write_bytes(b"fake-png")

    qrc_path = tmp_path / "images.qrc"
    qrc_path.write_text(
        """<RCC>
  <qresource>
    <file>assets/rename.png</file>
  </qresource>
</RCC>
""",
        encoding="utf-8",
    )

    ui_path = tmp_path / "resource_icon.ui"
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
    <addaction name=\"actionRename\"/>
   </widget>
  </widget>
  <action name=\"actionRename\">
   <property name=\"icon\"><iconset><selectedon>:/assets/rename.png</selectedon></iconset></property>
   <property name=\"text\"><string>Rename</string></property>
  </action>
 </widget>
 <resources>
  <include location=\"images.qrc\"/>
 </resources>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert f"Icon='{icon_path.resolve()}'" in generated
    _unit_passed("qrc icon paths are resolved to real files")


def test_convert_static_ui_relative_icon_path_is_resolved_from_ui_dir(tmp_path: Path) -> None:
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    icon_path = icons_dir / "rename.png"
    icon_path.write_bytes(b"fake-png")

    ui_path = tmp_path / "relative_icon.ui"
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
    <addaction name=\"actionRename\"/>
   </widget>
  </widget>
  <action name=\"actionRename\">
   <property name=\"icon\"><iconset><selectedon>icons/rename.png</selectedon></iconset></property>
   <property name=\"text\"><string>Rename</string></property>
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

    assert f"Icon='{icon_path.resolve()}'" in generated
    _unit_passed("relative icon paths are resolved from ui directory")


def test_convert_static_ui_colon_absolute_icon_path_resolves_via_qrc_basename(tmp_path: Path) -> None:
        icons_dir = tmp_path / "assets"
        icons_dir.mkdir()
        icon_path = icons_dir / "rename.png"
        icon_path.write_bytes(b"fake-png")

        qrc_path = tmp_path / "images.qrc"
        qrc_path.write_text(
                """<RCC>
    <qresource>
        <file>assets/rename.png</file>
    </qresource>
</RCC>
""",
                encoding="utf-8",
        )

        ui_path = tmp_path / "resource_icon_abs_in_colon.ui"
        ui_path.write_text(
                f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
    <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>200</height></rect></property>
    <widget class=\"QWidget\" name=\"centralwidget\"/>
    <widget class=\"QMenuBar\" name=\"menubar\">
     <property name=\"geometry\"><rect><x>0</x><y>0</y><width>320</width><height>24</height></rect></property>
     <widget class=\"QMenu\" name=\"menuFile\">
        <property name=\"title\"><string>File</string></property>
        <addaction name=\"actionRename\"/>
     </widget>
    </widget>
    <action name=\"actionRename\">
     <property name=\"icon\"><iconset><selectedon>:{icon_path.as_posix()}</selectedon></iconset></property>
     <property name=\"text\"><string>Rename</string></property>
    </action>
 </widget>
 <resources>
    <include location=\"images.qrc\"/>
 </resources>
 <connections/>
</ui>
""",
                encoding="utf-8",
        )

        builder = _load_builder_module()
        generated = builder.convert_ui_to_simplewx(ui_path)

        assert f"Icon='{icon_path.resolve()}'" in generated
        _unit_passed("colon absolute selectedon icon resolves via qrc basename fallback")


def test_convert_static_ui_missing_icon_path_fails_with_clear_error(tmp_path: Path) -> None:
    ui_path = tmp_path / "missing_icon.ui"
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
    <addaction name=\"actionRename\"/>
   </widget>
  </widget>
  <action name=\"actionRename\">
   <property name=\"icon\"><iconset><selectedon>icons/does-not-exist.png</selectedon></iconset></property>
   <property name=\"text\"><string>Rename</string></property>
  </action>
 </widget>
 <resources/>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()

    with pytest.raises(builder.BuilderError, match="Icon-Datei.*actionRename.*nicht gefunden"):
        builder.convert_ui_to_simplewx(ui_path)

    _unit_passed("missing icon path fails with clear error")


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


def test_convert_static_ui_priority4_toolbar_and_splitter_are_rendered(tmp_path: Path) -> None:
    ui_path = tmp_path / "prio4_toolbar_splitter.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>544</width><height>324</height></rect></property>
  <property name=\"windowTitle\"><string>MainWindow</string></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QSplitter\" name=\"splitter\">
    <property name=\"geometry\"><rect><x>10</x><y>10</y><width>512</width><height>192</height></rect></property>
    <property name=\"orientation\"><enum>Qt::Orientation::Horizontal</enum></property>
    <widget class=\"QTreeView\" name=\"treeView\"/>
    <widget class=\"QListWidget\" name=\"listWidget\"/>
   </widget>
  </widget>
  <widget class=\"QMenuBar\" name=\"menubar\">
   <property name=\"geometry\"><rect><x>0</x><y>0</y><width>544</width><height>26</height></rect></property>
   <widget class=\"QMenu\" name=\"menuFile\">
    <property name=\"title\"><string>File</string></property>
    <addaction name=\"actionOpen\"/>
   </widget>
   <addaction name=\"menuFile\"/>
  </widget>
  <widget class=\"QToolBar\" name=\"toolBar\">
   <property name=\"windowTitle\"><string>toolBar</string></property>
   <attribute name=\"toolBarArea\"><enum>TopToolBarArea</enum></attribute>
   <addaction name=\"actionNew\"/>
   <addaction name=\"actionSave\"/>
   <addaction name=\"separator\"/>
   <addaction name=\"actionQuit\"/>
  </widget>
  <action name=\"actionNew\">
   <property name=\"icon\"><iconset theme=\"QIcon::ThemeIcon::DocumentNew\"/></property>
   <property name=\"text\"><string>New</string></property>
   <property name=\"toolTip\"><string>Create new thing</string></property>
  </action>
  <action name=\"actionSave\">
   <property name=\"icon\"><iconset theme=\"document-save\"/></property>
   <property name=\"text\"><string>Save</string></property>
   <property name=\"toolTip\"><string>Save em all</string></property>
  </action>
  <action name=\"actionQuit\">
   <property name=\"icon\"><iconset theme=\"application-exit\"/></property>
   <property name=\"text\"><string>Quit</string></property>
  </action>
  <action name=\"actionOpen\">
   <property name=\"icon\"><iconset theme=\"document-open\"/></property>
   <property name=\"text\"><string>Open</string></property>
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

    assert "win.add_toolbar(" in generated
    assert "Name='toolBar'" in generated
    assert "'label': 'New'" in generated
    assert "'icon': 'gtk-new'" in generated
    assert "'kind': 'separator'" in generated
    assert "win.add_splitter(" in generated
    assert "Name='splitter'" in generated
    assert "Orient='vertical'" in generated
    assert "win.add_splitter_pane(" in generated
    assert "Splitter='splitter'" in generated
    assert "Frame='splitter_firstpane'" in generated
    assert "Frame='splitter_secondpane'" in generated
    assert "win.add_treeview(" in generated
    assert "win.add_listview(" in generated
    assert "win.add_splitter(Name='splitter'" not in generated
    assert (
        "win.add_splitter(\n"
        "    Name='splitter',\n"
        "    Position=[10, 10],\n"
        "    Size=[512, 192],\n"
        "    Orient='vertical',\n"
        "    Split=256,\n"
        ")"
    ) in generated
    assert "win.add_splitter_pane(Name='splitter_firstpane', Splitter='splitter', Side='first')" in generated
    _unit_passed("priority 4 toolbar and splitter render with pane content")


def test_convert_static_ui_priority6_datetimeedit_maps_to_date_and_time_pickers(tmp_path: Path) -> None:
    ui_path = tmp_path / "prio6_datetimeedit.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>400</width><height>200</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QDateTimeEdit\" name=\"scheduleEdit\">
    <property name=\"geometry\"><rect><x>20</x><y>30</y><width>200</width><height>29</height></rect></property>
    <property name=\"dateTime\">
     <datetime>
      <hour>14</hour>
      <minute>30</minute>
      <second>0</second>
      <year>2025</year>
      <month>6</month>
      <day>15</day>
     </datetime>
    </property>
   </widget>
  </widget>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>scheduleEdit</sender>
   <signal>dateTimeChanged(QDateTime)</signal>
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

    # Date picker: primary widget using the original name.
    assert "win.add_datepicker_ctrl(" in generated
    assert "Name='scheduleEdit'" in generated
    assert "Date='2025-06-15'" in generated
    assert "Signal=wx.EVT_DATE_CHANGED" in generated
    # Time picker: secondary widget with '_time' suffix, same row, shifted x.
    assert "win.add_timepicker_ctrl(" in generated
    assert "Name='scheduleEdit_time'" in generated
    assert "Time='14:30:00'" in generated
    # Both must appear in the same generated block (time after date).
    date_pos = generated.index("win.add_datepicker_ctrl(")
    time_pos = generated.index("win.add_timepicker_ctrl(")
    assert date_pos < time_pos, "date picker must precede time picker"
    # Inline comment.
    assert "# DateTime edit" in generated
    _unit_passed("priority 6: QDateTimeEdit maps to date + time picker pair")


def test_convert_static_ui_priority6_fontcombobox_maps_to_font_button(tmp_path: Path) -> None:
    ui_path = tmp_path / "prio6_fontcombobox.ui"
    ui_path.write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>400</width><height>200</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QFontComboBox\" name=\"fontPicker\">
    <property name=\"geometry\"><rect><x>20</x><y>40</y><width>280</width><height>29</height></rect></property>
    <property name=\"currentFont\">
     <font>
      <family>Arial</family>
      <pointsize>12</pointsize>
      <bold>false</bold>
     </font>
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

    assert "win.add_font_button(" in generated
    assert "Name='fontPicker'" in generated
    assert "Font=['Arial', 12]" in generated
    assert "# Font combo" in generated
    _unit_passed("priority 6: QFontComboBox maps to add_font_button with font spec")


def test_convert_static_ui_priority7_graphicsview_stylesheet_image_maps_to_add_image(tmp_path: Path) -> None:
    # Create a minimal PNG-like file so the QRC resolution can verify file existence.
    png_file = tmp_path / "scene.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes

    qrc_path = tmp_path / "images.qrc"
    qrc_path.write_text(
        "<RCC><qresource><file>scene.png</file></qresource></RCC>",
        encoding="utf-8",
    )

    ui_path = tmp_path / "prio7_graphicsview.ui"
    ui_path.write_text(
        f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<ui version=\"4.0\">
 <class>MainWindow</class>
 <widget class=\"QMainWindow\" name=\"MainWindow\">
  <property name=\"geometry\"><rect><x>0</x><y>0</y><width>600</width><height>400</height></rect></property>
  <widget class=\"QWidget\" name=\"centralwidget\">
   <widget class=\"QGraphicsView\" name=\"sceneView\">
    <property name=\"geometry\"><rect><x>10</x><y>10</y><width>320</width><height>280</height></rect></property>
    <property name=\"styleSheet\">
     <string notr=\"true\">background-image: url(:/scene.png); background-position: center;</string>
    </property>
   </widget>
  </widget>
 </widget>
 <resources>
  <include location=\"images.qrc\"/>
 </resources>
 <connections/>
</ui>
""",
        encoding="utf-8",
    )

    builder = _load_builder_module()
    generated = builder.convert_ui_to_simplewx(ui_path)

    assert "win.add_image(" in generated
    assert "Name='sceneView'" in generated
    assert "scene.png" in generated
    assert "# Graphics view" in generated
    _unit_passed("priority 7: QGraphicsView with stylesheet background-image maps to add_image")


def test_convert_static_ui_widget_call_format_rule_applies_globally(tmp_path: Path) -> None:
    ui_path = tmp_path / "format_rule_widgets.ui"
    ui_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="geometry"><rect><x>0</x><y>0</y><width>520</width><height>240</height></rect></property>
  <widget class="QWidget" name="centralwidget">
   <widget class="QPushButton" name="buttonFourArgs">
    <property name="geometry"><rect><x>20</x><y>20</y><width>140</width><height>30</height></rect></property>
    <property name="text"><string>Four</string></property>
   </widget>
   <widget class="QPushButton" name="buttonFiveArgs">
    <property name="geometry"><rect><x>20</x><y>70</y><width>160</width><height>30</height></rect></property>
    <property name="text"><string>Five</string></property>
    <property name="toolTip"><string>forces multiline</string></property>
   </widget>
   <widget class="QComboBox" name="comboFiveArgs">
    <property name="geometry"><rect><x>220</x><y>20</y><width>180</width><height>29</height></rect></property>
    <property name="toolTip"><string>combo multiline</string></property>
    <item><property name="text"><string>A</string></property></item>
    <item><property name="text"><string>B</string></property></item>
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

    # 4 parameters -> single line.
    assert "win.add_button(Name='buttonFourArgs', Position=[20, 20], Title='Four', Size=[140, 30])" in generated

    # 5+ parameters -> multiline with one argument per line.
    assert "win.add_button(Name='buttonFiveArgs'" not in generated
    assert (
        "win.add_button(\n"
        "    Name='buttonFiveArgs',\n"
        "    Position=[20, 70],\n"
        "    Title='Five',\n"
        "    Size=[160, 30],\n"
        "    Tooltip='forces multiline',\n"
        ")"
    ) in generated

    assert "win.add_combo_box(Name='comboFiveArgs'" not in generated
    assert (
        "win.add_combo_box(\n"
        "    Name='comboFiveArgs',\n"
        "    Position=[220, 20],\n"
        "    Data=['A', 'B'],\n"
        "    Size=[180, 29],\n"
        "    Tooltip='combo multiline',\n"
        ")"
    ) in generated
    _unit_passed("global format rule: <5 args single-line, >=5 args multiline for widget calls")
