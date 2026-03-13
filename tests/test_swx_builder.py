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
    module_path = root / "swx-builder.py"
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
