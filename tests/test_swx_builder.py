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


def test_convert_static_fbp_matches_expected_reference() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "static_minimal.fbp"
    expected_path = root / "examples" / "formbuilder" / "static_minimal_expected.py"

    builder = _load_builder_module()
    generated = builder.convert_fbp_to_simplewx(sample_path)
    expected = expected_path.read_text(encoding="utf-8")

    assert generated == expected
    _unit_passed("static fbp conversion matches expected output")


def test_convert_dynamic_fbp_fails_on_sizer() -> None:
    root = Path(__file__).resolve().parent.parent
    sample_path = root / "examples" / "formbuilder" / "dynamic_with_sizer.fbp"

    builder = _load_builder_module()

    with pytest.raises(builder.BuilderError, match="dynamisches Layout-Element"):
        builder.convert_fbp_to_simplewx(sample_path)

    _unit_passed("dynamic/sizer layout rejected with clear error")
