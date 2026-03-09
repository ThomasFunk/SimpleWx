# Project Role: Expert Python Developer (wxPython)
You are helping to port a Perl library (SimpleGtk2/SimpleWx.pm) to Python 3.13.
Preserve SimpleGtk2 functionality and formatting conventions where practical,
implemented on top of Python and the wx toolkit (wxPython).
The goal is a one-file library named `simplewx.py`.

## Core Architecture Rules
1. **Single Source of Truth:** Always use the `WidgetEntry` dataclass for storing widget data. 
2. **Naming Convention:** Method names must match the Perl original (e.g., `add_button`, `new_window`, `set_tooltip`).
3. **Data Management:** All widgets must be stored in the `self.widgets` dictionary using the widget's `name` as the key.
4. **Absolute Positioning:** We do NOT use Sizers for layout. We use absolute coordinates (`pos=(x, y)`).
5. **Scaling:** Always multiply `pos_x`, `pos_y`, `width`, and `height` by `self.scalefactor` before passing them to wxPython objects.

## Data Structures (STRICT)
Every time a widget is created, a `WidgetEntry` must be instantiated:
- `ref`: Holds the actual wxPython object.
- `handler`: Dictionary mapping native wx-Events (e.g., `wx.EVT_BUTTON`) to callbacks.
- `pos_x`, `pos_y`: Store the ORIGINAL (unscaled) values.

## UI Logic
- **Main Container:** In wxPython, a `wx.Frame` needs a `wx.Panel` as its immediate child to support proper tab navigation and background rendering. 
- **Default Container:** The first panel created in `new_window` should be the default parent for all subsequent widgets unless specified otherwise.

## Event Handling
- Use native wxPython events (e.g., `wx.EVT_BUTTON`, `wx.EVT_TEXT`).
- Do not attempt to map them back to GTK names unless explicitly requested.

## Coding Style
- Python 3.13 syntax.
- Use Type Hints for all method signatures.
- Keep the `SimpleWx` class clean so that the VS Code Outline Tree remains readable.

## Porting Fidelity Rules (STRICT)
- **Parameter Fidelity (`Any` handling):** Do not simplify or generalize public function parameters with catch-all patterns (`**kwargs`, broad `Any`) when the original Perl function lists explicit parameters. Mirror the original function parameter list as closely as possible.
- **Return Fidelity:** Match return behavior exactly to the original Perl function:
	- If original function returns nothing, Python method must return `None` (no functional return value).
	- If original function returns a value/object, keep that return in Python.
- **Docstring Format:** Use NumPy-style docstrings (`Parameters`, `Returns`, `Examples`).
	- `Examples` must be derived from the original Perl comment block examples, converted to Python syntax.
	- Keep examples minimal unless explicitly requested otherwise.
	- Internal helper methods (name starts with `_`) must not include an `Examples` section.
- **Inline Comments:** Add meaningful inline `#` comments that explain what the next block/line does, especially in ported logic sections, similar in spirit to comments in `SimpleGtk2.pm`.

### Quick Do / Don’t Checklist
- **Do:** Copy the original Perl function signature semantics into explicit Python parameters.
- **Do:** Keep `self.widgets` as storage authority and avoid returning widget refs for non-returning original functions.
- **Do:** Add concise NumPy docstrings with a minimal converted example.
- **Do:** Add inline comments before non-trivial logic blocks.
- **Don’t:** Introduce `**kwargs` for public API methods that are explicitly defined in Perl.
- **Don’t:** Add extra return values “for convenience” if the original has none.
- **Don’t:** Write long tutorial examples in docstrings unless explicitly requested.
- **Don’t:** Add `Examples` blocks to internal `_...` helper functions.
- **Don’t:** Skip inline explanation comments in complex ported blocks.

## Porting Guidance
- Preserve existing `simplewx.py` behavior unless an explicit change is requested.
- Keep widget-specific state fields (e.g., `font`, `path`) in `WidgetEntry` when relevant.
- Maintain internal state-tracking behavior (for example, persisted image paths or text-buffer content).
- When implementing or extending functions, follow the architecture and fidelity rules above before introducing new behavior.
