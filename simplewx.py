#!/usr/bin/env python3
__author__ = 'Thomas Funk'
__coauthors__ = 'Github Copilot & Gemini'
__date__ = "2026/03/09"
__version__ = "0.1.0"

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, Callable
import datetime
import gettext
import os
import re
import wx
import wx.adv
import wx.dataview as wxdataview
import wx.grid as wxgrid
import wx.richtext as wxrichtext

@dataclass
class WidgetEntry:
    """
    Stores metadata and runtime references for a single SimpleWx widget.

    This dataclass acts as the single source of truth for widget state,
    including original unscaled geometry, event handlers, and widget-specific
    auxiliary data.
    """
    type: str                         # e.g. 'Button', 'TextCtrl', 'Frame'
    name: str                         # Unique identifier (key in widgets dict)
    ref: Any                          # The actual wxPython instance (e.g. wx.Button)
    
    # Positioning and size
    pos_x: int = 0
    pos_y: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    
    # Metadata
    title: Optional[str] = None       # Label text or window title
    container: Optional[str] = None     # Parent container name
    tip: Optional[str] = None         # Tooltip text
    
    # Event handling (signal -> handler function)
    handler: Dict[Any, Any] = field(default_factory=dict)
    
    # Widget-specific extra data (e.g. for lists, text areas, etc.)
    data: Any = None                  # Flexible storage for content
    font: Optional[wx.Font] = None    # Specific font instance
    path: Optional[str] = None        # File paths (for images/text)


class _SimpleTextPrintout(wx.Printout):
    """
    Lightweight printout implementation for plain text content.
    """
    def __init__(
        self,
        title: str,
        text: str,
        lines_per_page: int = 60,
        header_template: str = "",
        footer_template: str = "Page {page}",
        show_date: int = 1,
        date_format: str = "%Y-%m-%d",
    ):
        super().__init__(title)
        self._title = str(title or "Print")
        self._text = str(text or "")
        self._lines = self._text.splitlines() if self._text else [""]
        self._lines_per_page = max(1, int(lines_per_page))
        self._header_template = str(header_template or "")
        self._footer_template = str(footer_template or "")
        self._show_date = 1 if int(show_date) else 0
        self._date_format = str(date_format or "%Y-%m-%d")

    def HasPage(self, page_num: int) -> bool:
        if page_num < 1:
            return False
        return page_num <= ((len(self._lines) - 1) // self._lines_per_page + 1)

    def GetPageInfo(self) -> tuple[int, int, int, int]:
        page_count = max(1, (len(self._lines) - 1) // self._lines_per_page + 1)
        return (1, page_count, 1, page_count)

    def OnPrintPage(self, page_num: int) -> bool:
        dc = self.GetDC()
        if dc is None:
            return False

        dc.SetFont(wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        page_width, page_height = dc.GetSize()
        line_height = max(14, dc.GetCharHeight() + 2)
        left_margin = 40
        top_margin = 40
        bottom_margin = 40

        page_count = max(1, (len(self._lines) - 1) // self._lines_per_page + 1)
        date_text = datetime.datetime.now().strftime(self._date_format) if self._show_date else ""

        def _format_template(template: str) -> str:
            text = str(template or "")
            text = text.replace("{title}", self._title)
            text = text.replace("{date}", date_text)
            text = text.replace("{page}", str(page_num))
            text = text.replace("{pages}", str(page_count))
            return text

        header_text = _format_template(self._header_template)
        footer_text = _format_template(self._footer_template)

        if header_text:
            dc.DrawText(header_text, left_margin, top_margin)
            top_margin += line_height + 6

        start = (page_num - 1) * self._lines_per_page
        end = min(len(self._lines), start + self._lines_per_page)
        for idx in range(start, end):
            y = top_margin + (idx - start) * line_height
            if y > page_height - bottom_margin - line_height:
                break
            dc.DrawText(self._lines[idx], left_margin, y)

        if footer_text:
            dc.DrawText(footer_text, left_margin, page_height - bottom_margin)
        _ = page_width
        return True

class SimpleWx:
    """
    Main API class for the SimpleWx rapid UI library.

    The class ports core behavior from SimpleGtk2/SimpleWx Perl modules and
    keeps absolute positioning with explicit scaling support.
    """
    # Definitions for the VS Code outline tree (attribute visibility)
    widgets: Dict[str, WidgetEntry]
    app: wx.App
    main_window: Optional[wx.Frame]
    scalefactor: float
    default_font_size: int
    ref: Optional[wx.Frame]
    name: str
    base: int
    version: Optional[str]
    fontsize: int
    font: str
    old_font: Optional[str]
    old_fontsize: Optional[int]
    containers: Dict[str, wx.Window]
    groups: Dict[str, list[str]]
    lates: list[str]
    subs: Dict[int, Callable[[], None]]
    handler: Dict[Any, Any]
    default_container_name: str
    allocated_colors: Dict[str, Any]
    container: Optional[wx.Window]

    def __init__(self, font_size: int = 10):
        """
        Initializes base runtime state and wx application context.

        Parameters
        ----------

        font_size : int, optional
            Base font size used as scaling reference. Defaults to 10.
        """
        self.widgets = {}
        self.app = wx.App()
        self.main_window = None
        self.ref = None
        self.name = ""
        self.base = font_size
        self.version = None
        self.default_font_size = 10
        self.fontsize = font_size
        self.font = ""
        self.old_font = None
        self.old_fontsize = None
        self.containers = {}
        self.groups = {}
        self.lates = []
        self.subs = {}
        self.handler = {}
        self.default_container_name = "main"
        self.allocated_colors = {}
        self.container = None
        self.scalefactor = 1.0
        self.gettext_enabled = 0
        self.gettext_appname = ""
        self.gettext_localedir = ""
        self._translator: Callable[[str], str] = lambda text: str(text)

    def init_app(self) -> None:
        """
        Initializes the wx application context if required.

        Returns
        -------

        None.

        Examples
        --------

        win.init_app()
        """
        # reuse an existing global wx app when available
        app = wx.GetApp()
        if isinstance(app, wx.App):
            self.app = app
        elif not isinstance(getattr(self, "app", None), wx.App):
            self.app = wx.App()

        # ensure image handlers are available for bitmap/image widgets
        try:
            wx.InitAllImageHandlers()
        except Exception:
            pass

    def use_gettext(self, AppName: str, Localepaths: str) -> None:
        """
        Activates gettext-based localization.

        Parameters
        ----------

        AppName : str
            Translation domain / `.mo` base filename.

        Localepaths : str
            Colon-separated locale search paths.
            A leading `+` or trailing `+` controls whether default system
            locale paths are appended or prepended (compatibility behavior).

        Returns
        -------

        None.

        Examples
        --------

        win.use_gettext("myapp", "/opt/myapp/locale:+")
        """
        app_name = str(AppName or "").strip()
        locale_paths = str(Localepaths or "").strip()

        self.gettext_enabled = 0
        self.gettext_appname = ""
        self.gettext_localedir = ""
        self._translator = lambda text: str(text)

        if app_name == "":
            return

        add_mode = "end"
        if "+" in locale_paths:
            if locale_paths.endswith("+"):
                add_mode = "begin"
            locale_paths = re.sub(r"^\+:", "", locale_paths)
            locale_paths = re.sub(r":\+$", "", locale_paths)

        custom_paths = [path for path in locale_paths.split(":") if path.strip() != ""]
        default_paths = ["/usr/local/share/locale", "/usr/share/locale"]
        search_paths = (custom_paths + default_paths) if add_mode == "begin" else (default_paths + custom_paths)

        language_env = str(os.environ.get("LANGUAGE") or os.environ.get("LANG") or "")
        language_base = language_env.split(".", 1)[0]
        language_short = language_base.split("_", 1)[0] if language_base else ""

        candidate_languages: list[str] = []
        for lang in (language_base, language_short):
            if lang and lang not in candidate_languages:
                candidate_languages.append(lang)
        if len(candidate_languages) == 0:
            candidate_languages.append("en")

        for base_path in search_paths:
            for lang in candidate_languages:
                mo_file = os.path.join(base_path, lang, "LC_MESSAGES", f"{app_name}.mo")
                if not os.path.isfile(mo_file):
                    continue
                try:
                    translation = gettext.translation(app_name, localedir=base_path, languages=[lang], fallback=False)
                    self._translator = translation.gettext
                    self.gettext_enabled = 1
                    self.gettext_appname = app_name
                    self.gettext_localedir = base_path
                    return
                except Exception:
                    continue

    def translate(self, Text: Any) -> str:
        """
        Translates text using active gettext localization.

        Parameters
        ----------

        Text : Any
            Source text.

        Returns
        -------

        str:
            Translated text if gettext is active, otherwise original text.

        Examples
        --------

        title = win.translate("Menus in") + " " + key
        """
        text = "" if Text is None else str(Text)
        text = re.sub(r"\r?\n[\t ]+", "", text)
        if int(self.gettext_enabled) != 1:
            return text
        try:
            return str(self._translator(text))
        except Exception:
            return text

    def _calc_scalefactor(self, old_font_size: int, current_font_size: int) -> float:
        """
        Computes scaling factor from base and current font sizes.

        Parameters
        ----------

        old_font_size : int
            Reference font size used during layout definition.

        current_font_size : int
            Effective runtime font size from the current theme.

        Returns
        -------

        float:
            Computed scale factor. Returns 1.0 for invalid values.
        """
        if old_font_size <= 0 or current_font_size <= 0:
            return 1.0
        return current_font_size / old_font_size

    def _scale(self, value: int | float) -> int:
        """
        Scales a scalar geometry value with the current scale factor.

        Parameters
        ----------

        value : int | float
            Unscaled geometry value.

        Returns
        -------

        int:
            Scaled integer value rounded to nearest pixel.
        """
        return int(round(value * self.scalefactor))

    def _scale_pair(self, x: int, y: int) -> tuple[int, int]:
        """
        Scales a two-dimensional position or size pair.

        Parameters
        ----------

        x : int
            Unscaled x value.

        y : int
            Unscaled y value.

        Returns
        -------

        tuple[int, int]:
            Scaled `(x, y)` pair.
        """
        return self._scale(x), self._scale(y)

    def _extend(self, key: str) -> str:
        """
        Expands known short parameter aliases to canonical key names.

        Parameters
        ----------

        key : str
            Raw keyword name.

        Returns
        -------

        str:
            Expanded key if alias is known, otherwise the input key.
        """
        mapping = {
            "pos": "position",
            "tip": "tooltip",
            "func": "function",
            "sig": "signal",
            "sens": "sensitive",
            "min": "minimum",
            "max": "maximum",
            "orient": "orientation",
            "valuepos": "valueposition",
            "pixbuf": "pixbuffer",
            "textbuf": "textbuffer",
            "wrap": "wrapped",
            "climb": "climbrate",
            "col": "columns",
            "scroll": "scrollable",
            "current": "currentpage",
            "no2name": "number2name",
            "dtype": "dialogtype",
            "mtype": "messagetype",
            "rfunc": "responsefunction",
            "file": "filename",
            "gname": "groupname",
        }
        return mapping.get(key, key)

    def _normalize(self, **params: Any) -> Dict[str, Any]:
        """
        Normalizes keyword arguments to canonical internal keys.

        Parameters
        ----------

        **params : Any
            Arbitrary API keyword arguments.

        Returns
        -------

        dict[str, Any]:
            Normalized argument mapping.
        """
        normalized: Dict[str, Any] = {}
        for key, value in params.items():
            normalized[self._extend(key.lower())] = value
        return normalized

    def _new_widget(self, **params: Any) -> WidgetEntry:
        """
        Creates a new WidgetEntry with extracted geometry and metadata.

        Parameters
        ----------

        **params : Any
            Normalized widget construction parameters.

        Returns
        -------

        WidgetEntry:
            Prepared widget entry with original unscaled geometry.
        """
        position = params.get("position")
        size = params.get("size")

        pos_x = int(position[0]) if isinstance(position, (list, tuple)) and len(position) >= 2 else 0
        pos_y = int(position[1]) if isinstance(position, (list, tuple)) and len(position) >= 2 else 0
        width = int(size[0]) if isinstance(size, (list, tuple)) and len(size) >= 2 else None
        height = int(size[1]) if isinstance(size, (list, tuple)) and len(size) >= 2 else None

        return WidgetEntry(
            type=str(params.get("type") or ""),
            name=str(params.get("name") or ""),
            ref=None,
            title=params.get("title"),
            pos_x=pos_x,
            pos_y=pos_y,
            width=width,
            height=height,
            container=params.get("frame"),
            tip=params.get("tooltip"),
        )

    def internal_die(self, object_name: str, msg: str) -> None:
        """
        Raises a standardized fatal runtime error.

        Parameters
        ----------

        object_name : str
            Name of the involved object.

        msg : str
            Human-readable error message.
        """
        raise RuntimeError(f"{self.name}->{object_name}: {msg} Exiting.")

    def get_object(self, name: str) -> WidgetEntry:
        """
        Retrieves a widget entry by its unique name.

        Parameters
        ----------

        name : str
            Widget name key.

        Returns
        -------

        WidgetEntry:
            Stored widget entry.

        Examples
        --------

        obj = win.get_object("mainWindow")
        title = obj.title
        """
        obj = self.widgets.get(name)
        if obj is None:
            self.internal_die(name, "No object found!")
        return obj

    def exist_object(self, identifier: Any) -> int:
        """
        Checks whether an object exists by name or widget reference.

        Parameters
        ----------

        identifier : Any
            Object name (str) or native widget reference.

        Returns
        -------

        int:
            `1` if object exists, else `0`.

        Examples
        --------

        exists = win.exist_object("entrySplashPath")
        """
        # lookup by unique object name
        if isinstance(identifier, str):
            return 1 if identifier in self.widgets else 0

        # lookup by direct widget reference (or known internal references)
        for object_entry in self.widgets.values():
            if object_entry.ref is identifier:
                return 1

            # DrawingArea binds and exposes an inner drawing panel
            if object_entry.type == "DrawingArea" and isinstance(object_entry.data, dict):
                if object_entry.data.get("drawing_area") is identifier:
                    return 1

            # Image stores inner static bitmap separately
            if object_entry.type == "Image" and isinstance(object_entry.data, dict):
                if object_entry.data.get("static_bitmap") is identifier:
                    return 1

        return 0

    def get_widget(self, name: str) -> wx.Window:
        """
        Retrieves the native wx widget reference for a named entry.

        Parameters
        ----------

        name : str
            Widget name key.

        Returns
        -------

        wx.Window:
            Native wx widget object. For `DrawingArea`, returns the inner
            drawing panel (not the scroll host container).

        Examples
        --------

        button_ref = win.get_widget("closeButton")
        button_ref.Enable(False)
        """
        obj = self.get_object(name)
        if obj.ref is None:
            self.internal_die(name, "No widget reference available!")

        # for drawing areas return the actual paint/event surface panel
        if obj.type == "DrawingArea" and isinstance(obj.data, dict):
            drawing_area = obj.data.get("drawing_area")
            if isinstance(drawing_area, wx.Window):
                return drawing_area

        return obj.ref

    def show_widget(self, Name: str) -> None:
        """
        Shows a previously hidden widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Returns
        -------

        None.

        Examples
        --------

        win.show_widget("frame1")
        """
        object_entry = self.get_object(Name)
        if object_entry.ref is None:
            self.internal_die(Name, "No widget reference available!")

        unsupported = ("MenuBar", "MenuItem", "Menu", "NotebookPage")
        if object_entry.type in unsupported:
            self.show_error(object_entry, f'For "{object_entry.type}" use set_sensitive() instead.')
            return

        object_entry.ref.Show(True)

    def hide_widget(self, Name: str) -> None:
        """
        Hides a currently visible widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Returns
        -------

        None.

        Examples
        --------

        win.hide_widget("frame1")
        """
        object_entry = self.get_object(Name)
        if object_entry.ref is None:
            self.internal_die(Name, "No widget reference available!")

        unsupported = ("MenuBar", "MenuItem", "Menu", "NotebookPage")
        if object_entry.type in unsupported:
            self.show_error(object_entry, f'For "{object_entry.type}" use set_sensitive() instead.')
            return

        object_entry.ref.Show(False)

    def set_sensitive(self, Name: str, State: int) -> None:
        """
        Sets sensitivity of a widget or a radio group.

        Parameters
        ----------

        Name : str
            Widget name or group name.

        State : int
            New sensitivity state (`0` inactive, `1` active).

        Returns
        -------

        None.

        Examples
        --------

        win.set_sensitive("r_state", 0)
        """
        enabled = bool(State)

        # if Name points to a concrete widget, set it directly
        if Name in self.widgets:
            object_entry = self.get_object(Name)
            if object_entry.ref is None:
                self.internal_die(Name, "No widget reference available!")
            object_entry.ref.Enable(enabled)
            return

        # if Name points to a radio group, set all group members
        if Name in self.groups:
            for widget_name in self.groups[Name]:
                object_entry = self.get_object(widget_name)
                if object_entry.ref is not None:
                    object_entry.ref.Enable(enabled)
            return

        self.internal_die(Name, "Not found - neither in widgets nor in groups list!")

    def is_sensitive(self, Name: str) -> int:
        """
        Returns sensitivity/enabled state of a widget or group.

        Parameters
        ----------

        Name : str
            Widget name or group name.

        Returns
        -------

        int:
            `1` if enabled, else `0`.

        Examples
        --------

        state = win.is_sensitive("checkEnabled")
        """
        # if Name points to a concrete widget, read it directly
        if Name in self.widgets:
            object_entry = self.get_object(Name)

            # menus are represented by menu title entries on the menu bar
            if object_entry.type == "Menu" and isinstance(object_entry.data, dict):
                menubar_name = object_entry.data.get("menubar")
                title_index = object_entry.data.get("title_index")
                if isinstance(menubar_name, str) and isinstance(title_index, int):
                    mbar_obj = self.get_object(menubar_name)
                    if isinstance(mbar_obj.ref, wx.MenuBar) and hasattr(mbar_obj.ref, "IsEnabledTop"):
                        return 1 if bool(mbar_obj.ref.IsEnabledTop(title_index)) else 0

            if object_entry.ref is None:
                self.internal_die(Name, "No widget reference available!")
            if hasattr(object_entry.ref, "IsEnabled"):
                return 1 if bool(object_entry.ref.IsEnabled()) else 0
            return 1

        # if Name points to a group, all members must be enabled
        if Name in self.groups:
            group_members = self.groups[Name]
            if len(group_members) == 0:
                return 0
            for widget_name in group_members:
                object_entry = self.get_object(widget_name)
                if object_entry.ref is None or not hasattr(object_entry.ref, "IsEnabled"):
                    return 0
                if not bool(object_entry.ref.IsEnabled()):
                    return 0
            return 1

        self.internal_die(Name, "Not found - neither in widgets nor in groups list!")

    def is_active(self, Name: str, Value: Optional[Any] = None) -> int:
        """
        Returns active state for supported widgets.

        Parameters
        ----------

        Name : str
            Widget name.

        Value : Any | None, optional
            Optional comparison value for combo-box-like widgets.

        Returns
        -------

        int:
            `1` if active/matching, else `0`.

        Examples
        --------

        state = win.is_active("checkEnabled")
        """
        object_entry = self.get_object(Name)
        widget = object_entry.ref
        if widget is None:
            self.internal_die(Name, "No widget reference available!")

        # check and radio buttons
        if object_entry.type in ("CheckButton", "RadioButton"):
            return 1 if bool(widget.GetValue()) else 0

        # menu items with check/radio behavior
        if object_entry.type == "MenuItem" and isinstance(widget, wx.MenuItem):
            if widget.IsCheckable():
                return 1 if bool(widget.IsChecked()) else 0
            self.show_error(object_entry, '"MenuItem" has no active state (not checkable)!')
            return 0

        # combo-box compatibility (for future/partial implementations)
        if object_entry.type == "ComboBox":
            if hasattr(widget, "GetSelection"):
                current_index = int(widget.GetSelection())
                if current_index < 0:
                    return 0

                # direct query of selected index when no Value was provided
                if Value is None:
                    return 1

                selected_value: Any = None
                if isinstance(object_entry.data, list) and current_index < len(object_entry.data):
                    selected_value = object_entry.data[current_index]
                elif isinstance(object_entry.data, dict) and isinstance(object_entry.data.get("data"), list):
                    data_values = object_entry.data["data"]
                    if current_index < len(data_values):
                        selected_value = data_values[current_index]
                elif hasattr(widget, "GetString"):
                    selected_value = widget.GetString(current_index)

                if selected_value is None:
                    return 0

                # numeric comparisons stay numeric when possible
                if isinstance(Value, (int, float)):
                    try:
                        return 1 if float(selected_value) == float(Value) else 0
                    except Exception:
                        return 0
                return 1 if str(selected_value) == str(Value) else 0

        self.show_error(object_entry, f'"{object_entry.type}" has no active state!')
        return 0

    def get_title(self, Name: str) -> Optional[str]:
        """
        Returns title/label text for a supported widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Returns
        -------

        str | None:
            Current title/label text or None if unsupported.

        Examples
        --------

        title = win.get_title("mainWindow")
        """
        object_entry = self.get_object(Name)
        widget = object_entry.ref
        unsupported = ("Slider", "Scrollbar", "Image", "TextView", "MenuBar", "Notebook")

        if object_entry.type in unsupported:
            self.show_error(object_entry, f'"{object_entry.type}" has no title!')
            return None

        if widget is None:
            return object_entry.title

        if object_entry.type in ("TextEntry", "Entry") and hasattr(widget, "GetValue"):
            object_entry.title = str(widget.GetValue())
        elif hasattr(widget, "GetTitle"):
            object_entry.title = str(widget.GetTitle())
        elif hasattr(widget, "GetLabel"):
            object_entry.title = str(widget.GetLabel())

        return object_entry.title

    def set_title(self, Name: str, NewTitle: str) -> None:
        """
        Sets new title/label text on a supported widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        NewTitle : str
            New title text.

        Returns
        -------

        None.

        Examples
        --------

        win.set_title("labelMaxSizeValue", "1920x1080")
        """
        object_entry = self.get_object(Name)
        widget = object_entry.ref
        if widget is None:
            self.internal_die(Name, "No widget reference available!")

        title_text = str(NewTitle)

        if object_entry.type in ("Window",):
            widget.SetTitle(title_text)
        elif object_entry.type == "Frame":
            frame_data = object_entry.data if isinstance(object_entry.data, dict) else {}
            title_label = frame_data.get("title_label")
            if isinstance(title_label, wx.StaticText):
                title_label.SetLabel(title_text)
            elif title_text:
                title_label = wx.StaticText(widget, wx.ID_ANY, title_text)
                frame_data["title_label"] = title_label
                object_entry.data = frame_data
            self._layout_frame_container(Name)
        elif object_entry.type == "NotebookPage":
            page_data = object_entry.data if isinstance(object_entry.data, dict) else {}
            notebook_name = page_data.get("notebook")
            if isinstance(notebook_name, str):
                notebook_object = self.get_object(notebook_name)
                notebook_ref = notebook_object.ref
                if notebook_ref is not None and object_entry.ref is not None and hasattr(notebook_ref, "FindPage"):
                    page_index = int(notebook_ref.FindPage(object_entry.ref))
                    if page_index >= 0:
                        notebook_ref.SetPageText(page_index, title_text)
        elif object_entry.type in ("TextEntry", "Entry"):
            widget.SetValue(title_text)
        elif hasattr(widget, "SetLabel"):
            widget.SetLabel(title_text)
        elif hasattr(widget, "SetTitle"):
            widget.SetTitle(title_text)
        else:
            self.show_error(object_entry, f'Can\'t set title "{title_text}" - wrong type "{object_entry.type}"!')
            return

        object_entry.title = title_text

    def get_size(self, Name: str) -> Optional[tuple[int, int]]:
        """
        Returns current unscaled width/height of a widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Returns
        -------

        tuple[int, int] | None:
            Unscaled width and height or None if unsupported.

        Examples
        --------

        width, height = win.get_size("image1")
        """
        object_entry = self.get_object(Name)
        if object_entry.type in ("MenuItem", "Menu", "NotebookPage"):
            self.show_error(object_entry, f'For "{object_entry.type}" no size available!')
            return None

        if object_entry.width is None or object_entry.height is None:
            if object_entry.ref is None:
                return None
            size = object_entry.ref.GetSize()
            object_entry.width = int(round(size.GetWidth() / self.scalefactor)) if self.scalefactor != 0 else int(size.GetWidth())
            object_entry.height = int(round(size.GetHeight() / self.scalefactor)) if self.scalefactor != 0 else int(size.GetHeight())

        return int(object_entry.width), int(object_entry.height)

    def set_size(self, Name: str, NewWidth: int, NewHeight: int) -> None:
        """
        Sets new unscaled width/height of a widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        NewWidth : int
            New widget width.

        NewHeight : int
            New widget height.

        Returns
        -------

        None.

        Examples
        --------

        win.set_size("image1", 200, 100)
        """
        object_entry = self.get_object(Name)
        if object_entry.ref is None:
            self.internal_die(Name, "No widget reference available!")

        if object_entry.type in ("CheckButton", "RadioButton", "Label", "MenuItem", "Menu", "NotebookPage"):
            self.show_error(object_entry, f'"{object_entry.type}" is not resizable!')
            return

        object_entry.width = int(NewWidth)
        object_entry.height = int(NewHeight)
        object_entry.ref.SetSize((self._scale(object_entry.width), self._scale(object_entry.height)))

        # keep image bitmap in sync with widget size using original source bitmap
        if object_entry.type == "Image" and isinstance(object_entry.data, dict):
            static_bitmap = object_entry.data.get("static_bitmap")
            source_bitmap = object_entry.data.get("source_bitmap")
            if isinstance(static_bitmap, wx.StaticBitmap) and isinstance(source_bitmap, wx.Bitmap):
                scaled_bitmap = self._scale_bitmap(source_bitmap, object_entry.width, object_entry.height)
                static_bitmap.SetBitmap(scaled_bitmap)
                object_entry.data["bitmap"] = scaled_bitmap

        # keep inner frame container aligned after frame resize
        if object_entry.type == "Frame":
            self._layout_frame_container(Name)

    def get_pos(self, Name: str) -> Optional[tuple[int, int]]:
        """
        Returns current unscaled `(x, y)` position of a widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Returns
        -------

        tuple[int, int] | None:
            Unscaled x and y position or None if unsupported.

        Examples
        --------

        x, y = win.get_pos("cbox1")
        """
        object_entry = self.get_object(Name)
        if object_entry.type in ("MenuItem", "Menu", "NotebookPage"):
            self.show_error(object_entry, f'For "{object_entry.type}" no position available!')
            return None
        return int(object_entry.pos_x), int(object_entry.pos_y)

    def set_pos(self, Name: str, NewX: int, NewY: int) -> None:
        """
        Sets new unscaled `(x, y)` position of a widget.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        NewX : int
            New x-position.

        NewY : int
            New y-position.

        Returns
        -------

        None.

        Examples
        --------

        win.set_pos("check_button", 10, 45)
        """
        object_entry = self.get_object(Name)
        if object_entry.type in ("MenuItem", "Menu", "NotebookPage"):
            self.show_error(object_entry, f'"{object_entry.type}" cannot change the position!')
            return

        object_entry.pos_x = int(NewX)
        object_entry.pos_y = int(NewY)
        self._add_to_container(Name)

    def get_value(self, Name: str, Keyname: str, Value: Optional[Any] = None) -> Any:
        """
        Returns a widget-specific value addressed by key.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Keyname : str
            Value key (e.g. `Active`, `Align`, `Minimum`, `Maximum`).

        Value : Any | None, optional
            Optional compatibility argument used by some key styles.

        Returns
        -------

        Any:
            Value resolved for the given widget/key pair.

        Examples
        --------

        active = win.get_value("checkEnabled", "Active")
        """
        object_entry = self.get_object(Name)
        key = self._extend(str(Keyname).lower())
        widget = object_entry.ref
        data = object_entry.data if isinstance(object_entry.data, dict) else {}

        # check and radio buttons
        if object_entry.type in ("CheckButton", "RadioButton"):
            if key == "active" and widget is not None:
                return 1 if bool(widget.GetValue()) else 0
            if object_entry.type == "RadioButton" and key in ("group", "groupname", "gname"):
                return data.get("group")

        # labels
        if object_entry.type == "Label":
            if key in ("wrap", "wrapped"):
                return data.get("wrapped", 0)
            if key == "justify":
                return data.get("justify", "left")

        # link button
        if object_entry.type == "LinkButton" and widget is not None:
            if key == "uri":
                if hasattr(widget, "GetURL"):
                    return widget.GetURL()
                return data.get("uri")
            if key == "text":
                if hasattr(widget, "GetLabel"):
                    return widget.GetLabel()
                return object_entry.title

        # text entry
        if object_entry.type in ("TextEntry", "Entry") and widget is not None:
            if key == "text":
                return widget.GetValue()
            if key == "align":
                style = widget.GetWindowStyleFlag()
                if style & wx.TE_RIGHT:
                    return "right"
                if style & wx.TE_CENTER:
                    return "center"
                return "left"

        # combo box
        if object_entry.type == "ComboBox" and widget is not None:
            if key in ("start", "active"):
                return int(widget.GetSelection())
            if key == "data":
                return data.get("data", [])
            if key == "columns":
                return data.get("columns")

        # spin button
        if object_entry.type == "SpinButton" and widget is not None:
            if key in ("start", "active"):
                return widget.GetValue()
            if key in ("min", "minimum"):
                return data.get("minimum")
            if key in ("max", "maximum"):
                return data.get("maximum")
            if key == "step":
                return data.get("step")
            if key == "digits":
                if hasattr(widget, "GetDigits"):
                    return widget.GetDigits()
                return data.get("digits", 0)
            if key in ("rate", "climbrate"):
                return data.get("climbrate", 0.0)
            if key == "snap":
                return data.get("snap", 0)
            if key == "align":
                style = widget.GetWindowStyleFlag()
                if style & wx.TE_RIGHT:
                    return "right"
                if style & wx.TE_CENTER:
                    return "center"
                return "left"

        # slider
        if object_entry.type == "Slider" and widget is not None:
            if key in ("start", "active"):
                return widget.GetValue()
            if key in ("min", "minimum"):
                return data.get("minimum")
            if key in ("max", "maximum"):
                return data.get("maximum")
            if key == "step":
                return data.get("step")
            if key == "digits":
                return data.get("digits", 0)
            if key == "drawvalue":
                return data.get("drawvalue", 0)
            if key in ("valuepos", "valueposition"):
                return data.get("valueposition", "top")

        # progress bar
        if object_entry.type == "ProgressBar" and widget is not None:
            if key in ("start", "active", "value"):
                return int(data.get("value", 0))
            if key == "fraction":
                steps = max(1, int(data.get("steps", 100)))
                return float(data.get("value", 0)) / float(steps)
            if key == "mode":
                return str(data.get("mode", "percent"))
            if key == "steps":
                return int(data.get("steps", 100))
            if key in ("orientation", "orient"):
                return str(data.get("orientation", "horizontal"))
            if key == "timer":
                return int(data.get("timer", 100))
            if key == "align":
                return str(data.get("align", "left"))

        # scrollbar
        if object_entry.type == "Scrollbar" and widget is not None:
            minimum = float(data.get("minimum", 0))
            if key in ("start", "active"):
                return minimum + float(widget.GetThumbPosition())
            if key in ("min", "minimum"):
                return data.get("minimum")
            if key in ("max", "maximum"):
                return data.get("maximum")
            if key == "step":
                return data.get("step")
            if key == "digits":
                return data.get("digits", 0)

        # text view
        if object_entry.type == "TextView":
            if key == "leftmargin":
                return data.get("leftmargin", 0)
            if key == "rightmargin":
                return data.get("rightmargin", 0)
            if key in ("wrap", "wrapped"):
                return data.get("wrapped", "none")
            if key == "justify":
                return data.get("justify", "left")
            if key in ("rich", "richtext"):
                return int(data.get("rich", 0))
            if key in ("path", "textbuffer", "textview"):
                self.internal_die(Name, f"'get_value' doesn't support \"{key}\". Use 'get_textview' instead.")

        # image
        if object_entry.type == "Image":
            if key in ("path", "pixbuffer", "image", "bitmap", "staticbitmap"):
                self.internal_die(Name, f"'get_value' doesn't support \"{key}\". Use 'get_image' instead.")

        # menu
        if object_entry.type == "Menu":
            if key == "justify":
                return data.get("justify", "left")

        # toolbar
        if object_entry.type == "ToolBar":
            if key in ("tools", "data"):
                tools = data.get("tools") if isinstance(data.get("tools"), list) else []
                return [dict(tool) if isinstance(tool, dict) else tool for tool in tools]
            if key in ("toolcount", "count"):
                tools = data.get("tools") if isinstance(data.get("tools"), list) else []
                return len(tools)
            if key in ("orientation", "orient"):
                return str(data.get("orientation", "horizontal"))
            if key in ("active", "lasttool"):
                return data.get("lasttool")
            if key == "tool":
                tools = data.get("tools") if isinstance(data.get("tools"), list) else []
                if Value is None:
                    return None
                idx = int(Value)
                if 0 <= idx < len(tools):
                    tool_data = tools[idx]
                    return dict(tool_data) if isinstance(tool_data, dict) else tool_data
                return None

        # menu item
        if object_entry.type == "MenuItem" and widget is not None:
            if key == "active" and isinstance(widget, wx.MenuItem) and widget.IsCheckable():
                return 1 if bool(widget.IsChecked()) else 0
            if key in ("group", "groupname", "gname"):
                return data.get("group")
            if key in ("icon", "iconpath", "iconname", "stockicon"):
                icon = data.get("icon")
                if icon is None:
                    return None
                icon_text = str(icon)
                if key == "stockicon" and not icon_text.startswith("gtk-"):
                    return None
                return icon_text

        # notebook
        if object_entry.type == "Notebook" and widget is not None:
            if key == "currentpage":
                return int(widget.GetSelection())
            if key == "pages":
                return int(widget.GetPageCount())
            if key == "popup":
                return int(data.get("popup", 0))
            if key in ("closetabs", "closepages"):
                return int(data.get("closetabs", 0))
            if key in ("lastclosed", "lastclosedpage"):
                return data.get("lastclosed")
            if key == "tabs":
                return str(data.get("tabs", "top"))
            if key in ("no2name", "number2name", "number2title"):
                if Value is None:
                    return None
                idx = int(Value)
                if 0 <= idx < widget.GetPageCount():
                    return widget.GetPageText(idx)
                return None
            if key in ("title2number", "name2number"):
                if Value is None:
                    return None
                title = str(Value)
                for idx in range(widget.GetPageCount()):
                    if widget.GetPageText(idx) == title:
                        return idx
                return -1

        # notebook page
        if object_entry.type == "NotebookPage":
            if key == "pagenumber":
                notebook_name = data.get("notebook") if isinstance(data, dict) else None
                if isinstance(notebook_name, str):
                    notebook_obj = self.get_object(notebook_name)
                    if notebook_obj.ref is not None and object_entry.ref is not None and hasattr(notebook_obj.ref, "FindPage"):
                        return int(notebook_obj.ref.FindPage(object_entry.ref))
                return int(data.get("page_index", -1))
            if key == "notebook":
                return data.get("notebook")
            if key in ("image", "icon"):
                return data.get("image")

        # splitter window
        if object_entry.type == "SplitterWindow":
            if key in ("orientation", "orient"):
                return str(data.get("orientation", "vertical"))
            if key in ("split", "sashposition", "position"):
                if widget is not None and hasattr(widget, "GetSashPosition"):
                    return int(round(widget.GetSashPosition() / self.scalefactor)) if self.scalefactor != 0 else int(widget.GetSashPosition())
                return int(data.get("sashposition", 200))
            if key in ("minsize", "minimum"):
                return int(data.get("minsize", 60))
            if key in ("unsplit", "issplit"):
                if widget is not None and hasattr(widget, "IsSplit"):
                    return 0 if bool(widget.IsSplit()) else 1
                return int(data.get("unsplit", 0))
            if key in ("collapse", "collapseside"):
                return str(data.get("collapse", "second"))
            if key in ("firstpane", "pane1"):
                return data.get("firstpane")
            if key in ("secondpane", "pane2"):
                return data.get("secondpane")
            if key in ("panes", "count"):
                pane_names = [pane for pane in (data.get("firstpane"), data.get("secondpane")) if isinstance(pane, str) and pane]
                return pane_names if key == "panes" else len(pane_names)

        # splitter pane
        if object_entry.type == "SplitterPane":
            if key == "splitter":
                return data.get("splitter")
            if key in ("side", "pane"):
                return str(data.get("side", "first"))

        # list view
        if object_entry.type in ("ListView", "List"):
            rows = data.get("data") if isinstance(data.get("data"), list) else []
            if key == "editable":
                return 0
            if key == "path":
                if Value is None:
                    return None
                row_index = int(Value)
                if 0 <= row_index < len(rows):
                    return rows[row_index]
                return None
            if key == "cell":
                if not isinstance(Value, (list, tuple)) or len(Value) < 2:
                    return None
                row_index = int(Value[0])
                col_index = int(Value[1])
                if 0 <= row_index < len(rows) and isinstance(rows[row_index], list) and 0 <= col_index < len(rows[row_index]):
                    return rows[row_index][col_index]
                return None

        # grid
        if object_entry.type == "Grid":
            rows = data.get("data") if isinstance(data.get("data"), list) else []
            if key in ("data", "rows"):
                return [list(row) if isinstance(row, list) else row for row in rows]
            if key in ("columns", "headers"):
                headers = data.get("headers") if isinstance(data.get("headers"), list) else []
                return [str(header) for header in headers]
            if key in ("rowcount", "rowscount", "count"):
                return len(rows)
            if key in ("colcount", "columncount"):
                headers = data.get("headers") if isinstance(data.get("headers"), list) else []
                return len(headers)
            if key == "editable":
                return int(data.get("editable", 1))
            if key == "sortable":
                return int(data.get("sortable", 1))
            if key in ("sortcolumn", "sortcol"):
                return int(data.get("sortcolumn", -1))
            if key in ("sortascending", "ascending"):
                return int(data.get("sortascending", 1))
            if key == "cell":
                if not isinstance(Value, (list, tuple)) or len(Value) < 2:
                    return None
                row_index = int(Value[0])
                col_index = int(Value[1])
                if 0 <= row_index < len(rows) and isinstance(rows[row_index], list) and 0 <= col_index < len(rows[row_index]):
                    return rows[row_index][col_index]
                return None

        # dataview
        if object_entry.type == "DataViewCtrl":
            rows = data.get("data") if isinstance(data.get("data"), list) else []
            if key in ("data", "rows"):
                return [list(row) if isinstance(row, list) else row for row in rows]
            if key in ("columns", "headers"):
                headers = data.get("headers") if isinstance(data.get("headers"), list) else []
                return [str(header) for header in headers]
            if key in ("rowcount", "rowscount", "count"):
                return len(rows)
            if key in ("colcount", "columncount"):
                headers = data.get("headers") if isinstance(data.get("headers"), list) else []
                return len(headers)
            if key == "editable":
                return int(data.get("editable", 1))
            if key == "sortable":
                return int(data.get("sortable", 1))
            if key == "cell":
                if not isinstance(Value, (list, tuple)) or len(Value) < 2:
                    return None
                row_index = int(Value[0])
                col_index = int(Value[1])
                if 0 <= row_index < len(rows) and isinstance(rows[row_index], list) and 0 <= col_index < len(rows[row_index]):
                    return rows[row_index][col_index]
                return None

        # tree view
        if object_entry.type == "TreeView" and isinstance(data, dict):
            treeview = data.get("treeview")
            root = data.get("root")
            view_type = str(data.get("view_type") or "Tree").lower()
            if isinstance(treeview, wx.TreeCtrl):
                if view_type == "list":
                    rows = data.get("data") if isinstance(data.get("data"), list) else []
                    if key == "editable":
                        return 0
                    if key == "path":
                        if Value is None:
                            return None
                        row_index = int(Value)
                        if 0 <= row_index < len(rows):
                            return rows[row_index]
                        return None
                    if key == "cell":
                        if not isinstance(Value, (list, tuple)) or len(Value) < 2:
                            return None
                        row_index = int(Value[0])
                        col_index = int(Value[1])
                        if 0 <= row_index < len(rows) and isinstance(rows[row_index], list) and 0 <= col_index < len(rows[row_index]):
                            return rows[row_index][col_index]
                        return None

                selected = treeview.GetSelection()
                if key == "iter":
                    return selected
                if key == "path":
                    if not isinstance(root, wx.TreeItemId) or not root.IsOk() or not selected.IsOk():
                        return []
                    path: list[int] = []
                    current = selected
                    while current.IsOk() and current != root:
                        parent = treeview.GetItemParent(current)
                        if not parent.IsOk():
                            break

                        idx = 0
                        child, cookie = treeview.GetFirstChild(parent)
                        while child.IsOk() and child != current:
                            idx += 1
                            child, cookie = treeview.GetNextChild(parent, cookie)
                        path.insert(0, idx)
                        current = parent
                    return path
                if key == "row":
                    return treeview.GetItemText(selected) if selected.IsOk() else ""

        # statusbar
        if object_entry.type == "Statusbar" and widget is not None:
            if key == "message":
                field = int(Value) if Value is not None else 0
                field_count = max(1, int(widget.GetFieldsCount())) if hasattr(widget, "GetFieldsCount") else 1
                field = max(0, min(field, field_count - 1))
                if hasattr(widget, "GetStatusText"):
                    return widget.GetStatusText(field)
                return ""
            if key == "stackcount":
                stack = data.get("sbar_stack") if isinstance(data.get("sbar_stack"), list) else []
                return len(stack)

        # message dialog
        if object_entry.type == "MessageDialog":
            if key == "modal":
                return int(data.get("modal", 1))
            if key in ("dialogtype", "dtype"):
                return str(data.get("dialogtype", "ok"))
            if key in ("messagetype", "mtype"):
                return str(data.get("messagetype", "info"))
            if key == "icon":
                return data.get("icon")
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # file chooser dialog
        if object_entry.type == "FileChooserDialog":
            if key == "action":
                return str(data.get("action", "open"))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key in ("filename", "file"):
                return str(data.get("filename", ""))
            if key == "folder":
                return str(data.get("folder", ""))
            if key == "filter":
                return data.get("filter", [])
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # file chooser button
        if object_entry.type == "FileChooserButton":
            if key == "action":
                return str(data.get("action", "open"))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key in ("filename", "file"):
                text_ctrl = data.get("text")
                if isinstance(text_ctrl, wx.TextCtrl):
                    return str(text_ctrl.GetValue())
                return str(data.get("filename", ""))
            if key == "folder":
                return str(data.get("folder", ""))
            if key == "filter":
                return data.get("filter", [])
            if key in ("button", "browsebutton"):
                return data.get("button")
            if key in ("text", "entry"):
                return data.get("text")

        # directory picker control
        if object_entry.type == "DirPickerCtrl":
            if key in ("folder", "path", "directory", "dir"):
                if widget is not None and hasattr(widget, "GetPath"):
                    return str(widget.GetPath())
                return str(data.get("folder", ""))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))

        # date picker control
        if object_entry.type == "DatePickerCtrl":
            date_value = data.get("date")
            if widget is not None and hasattr(widget, "GetValue"):
                dt_value = widget.GetValue()
                if isinstance(dt_value, wx.DateTime) and dt_value.IsValid():
                    date_value = f"{dt_value.GetYear():04d}-{int(dt_value.GetMonth()) + 1:02d}-{dt_value.GetDay():02d}"
                    data["date"] = date_value
            if key in ("date", "value"):
                return str(date_value or "")
            if key == "year" and isinstance(date_value, str) and len(date_value) >= 4:
                return int(date_value[0:4])
            if key == "month" and isinstance(date_value, str) and len(date_value) >= 7:
                return int(date_value[5:7])
            if key == "day" and isinstance(date_value, str) and len(date_value) >= 10:
                return int(date_value[8:10])
            if key == "title":
                return str(data.get("title", object_entry.title or ""))

        # time picker control
        if object_entry.type == "TimePickerCtrl":
            time_value = data.get("time")
            if widget is not None and hasattr(widget, "GetValue"):
                dt_value = widget.GetValue()
                if isinstance(dt_value, wx.DateTime) and dt_value.IsValid():
                    time_value = f"{dt_value.GetHour():02d}:{dt_value.GetMinute():02d}:{dt_value.GetSecond():02d}"
                    data["time"] = time_value
            if key in ("time", "value"):
                return str(time_value or "")
            if key in ("hour", "hours") and isinstance(time_value, str) and len(time_value) >= 2:
                return int(time_value[0:2])
            if key in ("minute", "minutes") and isinstance(time_value, str) and len(time_value) >= 5:
                return int(time_value[3:5])
            if key in ("second", "seconds") and isinstance(time_value, str) and len(time_value) >= 8:
                return int(time_value[6:8])
            if key == "title":
                return str(data.get("title", object_entry.title or ""))

        # font button and font selection dialog
        if object_entry.type in ("FontButton", "FontSelectionDialog"):
            font_obj = data.get("font_obj") if isinstance(data, dict) else None
            if key == "fontfamily":
                return font_obj.GetFaceName() if isinstance(font_obj, wx.Font) and font_obj.IsOk() else None
            if key == "fontsize":
                return int(font_obj.GetPointSize()) if isinstance(font_obj, wx.Font) and font_obj.IsOk() else None
            if key == "fontweight":
                if isinstance(font_obj, wx.Font) and font_obj.IsOk():
                    return int(font_obj.GetWeight())
                return None
            if key == "fontstring":
                if isinstance(font_obj, wx.Font) and font_obj.IsOk():
                    return f"{font_obj.GetFaceName()} {font_obj.GetPointSize()}"
                return None
            if key == "previewstring" and object_entry.type == "FontSelectionDialog":
                return str(data.get("preview", "AaBbYyZz"))
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # color selection dialog
        if object_entry.type == "ColorSelectionDialog":
            colour_obj = data.get("color") if isinstance(data, dict) else None
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key == "color":
                if isinstance(colour_obj, wx.Colour) and colour_obj.IsOk():
                    return [int(colour_obj.Red()), int(colour_obj.Green()), int(colour_obj.Blue())]
                return None
            if key == "red":
                return int(colour_obj.Red()) if isinstance(colour_obj, wx.Colour) and colour_obj.IsOk() else None
            if key == "green":
                return int(colour_obj.Green()) if isinstance(colour_obj, wx.Colour) and colour_obj.IsOk() else None
            if key == "blue":
                return int(colour_obj.Blue()) if isinstance(colour_obj, wx.Colour) and colour_obj.IsOk() else None
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # generic dialog
        if object_entry.type == "Dialog":
            if key == "modal":
                return int(data.get("modal", 1))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key in ("width", "w"):
                return object_entry.width
            if key in ("height", "h"):
                return object_entry.height
            if key in ("position", "pos"):
                return [int(object_entry.pos_x), int(object_entry.pos_y)]
            if key == "size":
                if object_entry.width is None or object_entry.height is None:
                    return None
                return [int(object_entry.width), int(object_entry.height)]
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # about dialog
        if object_entry.type == "AboutDialog":
            if key == "modal":
                return int(data.get("modal", 1))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key in ("programname", "name"):
                return str(data.get("programname", ""))
            if key == "version":
                return str(data.get("version", ""))
            if key == "copyright":
                return str(data.get("copyright", ""))
            if key in ("comments", "comment"):
                return str(data.get("comments", ""))
            if key == "website":
                return str(data.get("website", ""))
            if key == "authors":
                return data.get("authors", [])
            if key == "license":
                return str(data.get("license", ""))
            if key == "icon":
                return data.get("icon")
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # print dialog
        if object_entry.type == "PrintDialog":
            if key == "modal":
                return int(data.get("modal", 1))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key == "minpage":
                return int(data.get("minpage", 1))
            if key == "maxpage":
                return int(data.get("maxpage", 1))
            if key == "frompage":
                return int(data.get("frompage", 1))
            if key == "topage":
                return int(data.get("topage", 1))
            if key == "allpages":
                return int(data.get("allpages", 1))
            if key == "selection":
                return int(data.get("selection", 0))
            if key == "printtofile":
                return int(data.get("printtofile", 0))
            if key in ("copies", "nocopies"):
                return int(data.get("copies", 1))
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # printout definition
        if object_entry.type == "Printout":
            if key == "title":
                return str(data.get("title", object_entry.title or "Print"))
            if key == "text":
                return str(data.get("text", ""))
            if key == "path":
                return object_entry.path
            if key in ("linesperpage", "lines"):
                return int(data.get("linesperpage", 60))
            if key == "header":
                return str(data.get("header", ""))
            if key == "footer":
                return str(data.get("footer", "Page {page}"))
            if key == "showdate":
                return int(data.get("showdate", 1))
            if key == "dateformat":
                return str(data.get("dateformat", "%Y-%m-%d"))

        # page setup dialog
        if object_entry.type == "PageSetupDialog":
            if key == "modal":
                return int(data.get("modal", 1))
            if key == "title":
                return str(data.get("title", object_entry.title or ""))
            if key == "paperid":
                return int(data.get("paperid", int(wx.PAPER_A4)))
            if key == "orientation":
                return str(data.get("orientation", "portrait"))
            if key == "margintopleft":
                return list(data.get("margintopleft", [10, 10]))
            if key == "marginbottomright":
                return list(data.get("marginbottomright", [10, 10]))
            if key in ("responsefunction", "rfunc"):
                return data.get("responsefunction")

        # compatibility pass-through for extra value context keys
        if Value is not None and key in ("name2number", "number2name", "title2number", "number2title"):
            self.internal_die(Name, f"Parameter \"{key}\" is not implemented for current widget set.")

        self.internal_die(Name, f"Unknown parameter \"{key}\".")

    def set_value(self, Name: str, Keyname: str, NewValue: Any) -> None:
        """
        Sets one widget-specific value by key.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Keyname : str
            Value key.

        NewValue : Any
            New value for the selected key.

        Returns
        -------

        None.

        Examples
        --------

        win.set_value("checkEnabled", "Active", 1)
        """
        self.set_values(Name, {Keyname: NewValue})

    def set_values(self, Name: str, Values: Dict[str, Any]) -> None:
        """
        Sets multiple widget-specific values in one call.

        Parameters
        ----------

        Name : str
            Name of the widget. Must be unique.

        Values : dict[str, Any]
            Mapping of key names to new values.

        Returns
        -------

        None.

        Examples
        --------

        win.set_values("spin1", {"Start": 5, "Minimum": 0, "Maximum": 10, "Step": 1})
        """
        object_entry = self.get_object(Name)
        widget = object_entry.ref
        dialog_types_without_ref = (
            "MessageDialog",
            "FileChooserDialog",
            "FontSelectionDialog",
            "ColorSelectionDialog",
            "Dialog",
            "AboutDialog",
            "PrintDialog",
            "PageSetupDialog",
            "Printout",
        )
        if widget is None and object_entry.type not in dialog_types_without_ref:
            self.internal_die(Name, "No widget reference available!")

        params = {self._extend(str(key).lower()): value for key, value in Values.items()}
        data = object_entry.data if isinstance(object_entry.data, dict) else {}

        # check and radio buttons
        if object_entry.type in ("CheckButton", "RadioButton") and "active" in params:
            widget.SetValue(bool(params.pop("active")))

        # labels
        if object_entry.type == "Label":
            if "wrapped" in params:
                wrapped = 1 if int(params.pop("wrapped")) else 0
                data["wrapped"] = wrapped
                if wrapped:
                    widget.Wrap(-1)
                else:
                    widget.Wrap(0)
            if "justify" in params:
                justify = str(params.pop("justify")).lower()
                data["justify"] = justify
                justify_map = {
                    "left": wx.ALIGN_LEFT,
                    "center": wx.ALIGN_CENTER_HORIZONTAL,
                    "right": wx.ALIGN_RIGHT,
                    "fill": wx.ALIGN_CENTER_HORIZONTAL,
                }
                if justify in justify_map:
                    widget.SetWindowStyleFlag(justify_map[justify])

        # link button
        if object_entry.type == "LinkButton":
            if "uri" in params:
                uri = str(params.pop("uri"))
                data["uri"] = uri
                if hasattr(widget, "SetURL"):
                    widget.SetURL(uri)
            if "text" in params:
                text_value = str(params.pop("text"))
                if hasattr(widget, "SetLabel"):
                    widget.SetLabel(text_value)
                object_entry.title = text_value

        # text entry alignment
        if object_entry.type in ("TextEntry", "Entry") and "align" in params:
            align = str(params.pop("align")).lower()
            style = widget.GetWindowStyleFlag()
            style &= ~(wx.TE_LEFT | wx.TE_CENTER | wx.TE_RIGHT)
            if align == "right":
                style |= wx.TE_RIGHT
            elif align == "center":
                style |= wx.TE_CENTER
            else:
                style |= wx.TE_LEFT
            widget.SetWindowStyleFlag(style)
        if object_entry.type in ("TextEntry", "Entry") and "text" in params:
            text_value = str(params.pop("text"))
            widget.SetValue(text_value)
            object_entry.title = text_value

        # combo box values
        if object_entry.type == "ComboBox":
            if "data" in params:
                source_data = params.pop("data")
                values = [str(item) for item in source_data] if isinstance(source_data, (list, tuple)) else []
                data["data"] = values
                if hasattr(widget, "Clear"):
                    widget.Clear()
                if hasattr(widget, "AppendItems"):
                    widget.AppendItems(values)

                # keep active index valid after data replacement
                active_index = int(data.get("active", -1))
                if len(values) == 0:
                    active_index = -1
                elif active_index < 0 or active_index >= len(values):
                    active_index = 0
                if active_index >= 0:
                    widget.SetSelection(active_index)
                data["active"] = active_index
                object_entry.title = widget.GetStringSelection() if active_index >= 0 else ""

            if "columns" in params:
                columns_value = params.pop("columns")
                data["columns"] = int(columns_value) if columns_value is not None else None

            if "start" in params:
                params["active"] = params.pop("start")
            if "active" in params:
                value = int(params.pop("active"))
                values = data.get("data", []) if isinstance(data.get("data"), list) else []
                if len(values) == 0:
                    value = -1
                else:
                    value = max(0, min(value, len(values) - 1))
                if value >= 0:
                    widget.SetSelection(value)
                data["active"] = value
                object_entry.title = widget.GetStringSelection() if value >= 0 else ""

        # spin button values
        if object_entry.type == "SpinButton":
            if "minimum" in params or "maximum" in params:
                minimum = float(params.pop("minimum", data.get("minimum", 0)))
                maximum = float(params.pop("maximum", data.get("maximum", 100)))
                if maximum < minimum:
                    minimum, maximum = maximum, minimum
                data["minimum"] = minimum
                data["maximum"] = maximum
                if hasattr(widget, "SetRange"):
                    widget.SetRange(minimum, maximum)

            if "step" in params:
                step = float(params.pop("step"))
                if step <= 0:
                    step = 1.0
                data["step"] = step
                if hasattr(widget, "SetIncrement"):
                    widget.SetIncrement(step)

            if "digits" in params:
                digits = int(params.pop("digits"))
                data["digits"] = digits
                if hasattr(widget, "SetDigits"):
                    widget.SetDigits(max(0, digits))

            if "climbrate" in params:
                data["climbrate"] = float(params.pop("climbrate"))
            if "rate" in params:
                data["climbrate"] = float(params.pop("rate"))

            if "snap" in params:
                data["snap"] = 1 if int(params.pop("snap")) else 0

            if "align" in params:
                align = str(params.pop("align")).lower()
                data["align"] = align
                style = widget.GetWindowStyleFlag()
                style &= ~(wx.TE_LEFT | wx.TE_CENTER | wx.TE_RIGHT)
                if align == "right":
                    style |= wx.TE_RIGHT
                elif align == "center":
                    style |= wx.TE_CENTER
                else:
                    style |= wx.TE_LEFT
                widget.SetWindowStyleFlag(style)

            if "start" in params:
                params["active"] = params.pop("start")
            if "active" in params:
                value = params.pop("active")
                if isinstance(widget, wx.SpinCtrlDouble):
                    widget.SetValue(float(value))
                else:
                    widget.SetValue(int(round(float(value))))
                data["value"] = widget.GetValue()

        # slider values
        if object_entry.type == "Slider":
            if "minimum" in params or "maximum" in params:
                minimum = float(params.pop("minimum", data.get("minimum", 0)))
                maximum = float(params.pop("maximum", data.get("maximum", 100)))
                if maximum < minimum:
                    minimum, maximum = maximum, minimum
                data["minimum"] = minimum
                data["maximum"] = maximum
                widget.SetRange(int(round(minimum)), int(round(maximum)))

            if "step" in params:
                step = float(params.pop("step"))
                if step <= 0:
                    step = 1.0
                data["step"] = step
                widget.SetLineSize(max(1, int(round(step))))
                widget.SetPageSize(max(1, int(round(step * 10))))

            if "drawvalue" in params:
                data["drawvalue"] = 1 if int(params.pop("drawvalue")) else 0
            if "valueposition" in params:
                data["valueposition"] = str(params.pop("valueposition")).lower()
            if "digits" in params:
                data["digits"] = int(params.pop("digits"))

            if "start" in params:
                params["active"] = params.pop("start")
            if "active" in params:
                value = int(round(float(params.pop("active"))))
                widget.SetValue(value)
                data["value"] = widget.GetValue()

        # progressbar values
        if object_entry.type == "ProgressBar":
            if "mode" in params:
                data["mode"] = str(params.pop("mode") or "percent").lower()
            if "steps" in params:
                steps = int(params.pop("steps"))
                if steps <= 0:
                    steps = 100
                data["steps"] = steps
                if hasattr(widget, "SetRange"):
                    widget.SetRange(steps)
                current_value = int(data.get("value", 0))
                current_value = max(0, min(current_value, steps))
                data["value"] = current_value
                widget.SetValue(current_value)
            if "timer" in params:
                data["timer"] = max(1, int(params.pop("timer")))
            if "align" in params:
                data["align"] = str(params.pop("align") or "left").lower()

            if "fraction" in params:
                fraction = float(params.pop("fraction"))
                fraction = max(0.0, min(1.0, fraction))
                steps = max(1, int(data.get("steps", 100)))
                value = int(round(fraction * steps))
                data["value"] = value
                widget.SetValue(value)

            if "start" in params:
                params["active"] = params.pop("start")
            if "value" in params:
                params["active"] = params.pop("value")
            if "active" in params:
                value = int(round(float(params.pop("active"))))
                steps = max(1, int(data.get("steps", 100)))
                value = max(0, min(value, steps))
                if str(data.get("mode", "percent")).lower() == "pulse":
                    widget.Pulse()
                else:
                    widget.SetValue(value)
                data["value"] = value

        # scrollbar values
        if object_entry.type == "Scrollbar":
            if "minimum" in params:
                data["minimum"] = float(params.pop("minimum"))
            if "maximum" in params:
                data["maximum"] = float(params.pop("maximum"))
            if "step" in params:
                step = float(params.pop("step"))
                data["step"] = step if step > 0 else 1.0
            if "digits" in params:
                data["digits"] = int(params.pop("digits"))

            if "start" in params:
                params["active"] = params.pop("start")
            if "active" in params:
                data["value"] = float(params.pop("active"))

            # apply normalized scrollbar model to native widget
            effective = self._configure_scrollbar(
                widget,
                minimum=float(data.get("minimum", 0)),
                maximum=float(data.get("maximum", 100)),
                step=float(data.get("step", 1)),
                active_value=float(data.get("value", data.get("minimum", 0))),
            )
            data["value"] = effective

        # text-view values
        if object_entry.type == "TextView":
            if "text" in params:
                text_value = str(params.pop("text"))
                if hasattr(widget, "SetValue"):
                    widget.SetValue(text_value)
                data["textbuffer"] = text_value
                object_entry.title = text_value
            if "textbuffer" in params:
                textbuffer_value = str(params.pop("textbuffer"))
                if hasattr(widget, "SetValue"):
                    widget.SetValue(textbuffer_value)
                data["textbuffer"] = textbuffer_value
                object_entry.title = textbuffer_value
            if "leftmargin" in params:
                data["leftmargin"] = int(params.pop("leftmargin"))
            if "rightmargin" in params:
                data["rightmargin"] = int(params.pop("rightmargin"))
            try:
                widget.SetMargins(int(data.get("leftmargin", 0)), int(data.get("rightmargin", 0)))
            except Exception:
                pass

            if "wrapped" in params:
                wrapped = str(params.pop("wrapped")).lower()
                data["wrapped"] = wrapped
                style = widget.GetWindowStyleFlag()
                if wrapped in ("none", "off", "0"):
                    style |= wx.TE_DONTWRAP
                else:
                    style &= ~wx.TE_DONTWRAP
                widget.SetWindowStyleFlag(style)

            if "justify" in params:
                justify = str(params.pop("justify")).lower()
                data["justify"] = justify
                style = widget.GetWindowStyleFlag()
                style &= ~(wx.TE_LEFT | wx.TE_CENTER | wx.TE_RIGHT)
                if justify == "right":
                    style |= wx.TE_RIGHT
                elif justify == "center":
                    style |= wx.TE_CENTER
                else:
                    style |= wx.TE_LEFT
                widget.SetWindowStyleFlag(style)

            if "rich" in params:
                data["rich"] = 1 if int(params.pop("rich")) else 0
            if "richtext" in params:
                data["rich"] = 1 if int(params.pop("richtext")) else 0

        # list-view values
        if object_entry.type in ("ListView", "List"):
            listview = data.get("listview") if isinstance(data, dict) else None
            if "data" in params:
                source_data = params.pop("data")
                rows: list[list[Any]] = []
                if isinstance(source_data, (list, tuple)):
                    for row in source_data:
                        if isinstance(row, (list, tuple)):
                            rows.append(list(row))
                data["data"] = rows
                if isinstance(listview, wx.ListCtrl):
                    self._render_listview_rows(listview, rows)

        # grid values
        if object_entry.type == "Grid":
            headers = data.get("headers") if isinstance(data.get("headers"), list) else []
            rows = data.get("data") if isinstance(data.get("data"), list) else []

            if "headers" in params or "columns" in params:
                source_headers = params.pop("headers") if "headers" in params else params.pop("columns")
                new_headers = [str(col) for col in source_headers] if isinstance(source_headers, (list, tuple)) else []
                data["headers"] = new_headers
                headers = new_headers

            if "data" in params or "rows" in params:
                source_data = params.pop("data") if "data" in params else params.pop("rows")
                new_rows: list[list[Any]] = []
                if isinstance(source_data, (list, tuple)):
                    for row in source_data:
                        if isinstance(row, (list, tuple)):
                            new_rows.append(list(row))
                data["data"] = new_rows
                rows = new_rows

            if "editable" in params:
                editable = 1 if int(params.pop("editable")) else 0
                data["editable"] = editable
                if widget is not None and hasattr(widget, "EnableEditing"):
                    widget.EnableEditing(bool(editable))

            if "sortable" in params:
                data["sortable"] = 1 if int(params.pop("sortable")) else 0

            if "cell" in params:
                cell_value = params.pop("cell")
                if isinstance(cell_value, (list, tuple)) and len(cell_value) >= 3:
                    row_index = int(cell_value[0])
                    col_index = int(cell_value[1])
                    value = cell_value[2]
                    if row_index >= 0 and col_index >= 0:
                        while len(rows) <= row_index:
                            rows.append([])
                        while len(rows[row_index]) <= col_index:
                            rows[row_index].append("")
                        rows[row_index][col_index] = value
                        data["data"] = rows

            if "sortcolumn" in params:
                sort_col = int(params.pop("sortcolumn"))
                if "sortascending" in params:
                    sort_asc = 1 if int(params.pop("sortascending")) else 0
                else:
                    sort_asc = int(data.get("sortascending", 1))
                self._sort_grid_rows(object_entry.name, sort_col, sort_asc)
                rows = data.get("data") if isinstance(data.get("data"), list) else rows

            if widget is not None and isinstance(widget, wxgrid.Grid):
                self._render_grid_rows(widget, headers, rows)

        # dataview values
        if object_entry.type == "DataViewCtrl":
            headers = data.get("headers") if isinstance(data.get("headers"), list) else []
            rows = data.get("data") if isinstance(data.get("data"), list) else []

            if "headers" in params or "columns" in params:
                source_headers = params.pop("headers") if "headers" in params else params.pop("columns")
                new_headers = [str(col) for col in source_headers] if isinstance(source_headers, (list, tuple)) else []
                data["headers"] = new_headers
                headers = new_headers

            if "data" in params or "rows" in params:
                source_data = params.pop("data") if "data" in params else params.pop("rows")
                new_rows: list[list[Any]] = []
                if isinstance(source_data, (list, tuple)):
                    for row in source_data:
                        if isinstance(row, (list, tuple)):
                            new_rows.append(list(row))
                data["data"] = new_rows
                rows = new_rows

            if "editable" in params:
                data["editable"] = 1 if int(params.pop("editable")) else 0

            if "sortable" in params:
                data["sortable"] = 1 if int(params.pop("sortable")) else 0

            if "cell" in params:
                cell_value = params.pop("cell")
                if isinstance(cell_value, (list, tuple)) and len(cell_value) >= 3:
                    row_index = int(cell_value[0])
                    col_index = int(cell_value[1])
                    value = cell_value[2]
                    if row_index >= 0 and col_index >= 0:
                        while len(rows) <= row_index:
                            rows.append([])
                        while len(rows[row_index]) <= col_index:
                            rows[row_index].append("")
                        rows[row_index][col_index] = value
                        data["data"] = rows

            if widget is not None and isinstance(widget, wxdataview.DataViewListCtrl):
                self._render_dataview_rows(
                    widget,
                    [str(col) for col in headers],
                    rows,
                    int(data.get("editable", 1)),
                    int(data.get("sortable", 1)),
                )

        # notebook values
        if object_entry.type == "Notebook":
            if "currentpage" in params:
                page_index = int(params.pop("currentpage"))
                max_index = widget.GetPageCount() - 1 if hasattr(widget, "GetPageCount") else -1
                if max_index >= 0:
                    page_index = max(0, min(page_index, max_index))
                    widget.SetSelection(page_index)
            if "popup" in params:
                data["popup"] = 1 if int(params.pop("popup")) else 0
            if "closetabs" in params:
                data["closetabs"] = 1 if int(params.pop("closetabs")) else 0
            if "tabs" in params:
                tabs = str(params.pop("tabs") or "top").lower()
                if tabs not in ("top", "bottom", "left", "right", "none"):
                    tabs = "top"
                data["tabs"] = tabs

        # notebook-page values
        if object_entry.type == "NotebookPage":
            if "reorder" in params:
                new_index = int(params.pop("reorder"))
                notebook_name = data.get("notebook") if isinstance(data, dict) else None
                if isinstance(notebook_name, str) and object_entry.ref is not None:
                    notebook_object = self.get_object(notebook_name)
                    notebook_ref = notebook_object.ref
                    if notebook_ref is not None and hasattr(notebook_ref, "FindPage"):
                        old_index = int(notebook_ref.FindPage(object_entry.ref))
                        page_count = notebook_ref.GetPageCount()
                        if old_index >= 0 and page_count > 0:
                            new_index = max(0, min(new_index, page_count - 1))
                            title = notebook_ref.GetPageText(old_index)
                            selected = notebook_ref.GetSelection() == old_index
                            notebook_ref.RemovePage(old_index)
                            notebook_ref.InsertPage(new_index, object_entry.ref, title, selected)
                            data["page_index"] = new_index
            if "image" in params:
                image_value = params.pop("image")
                self._set_notebook_page_image(object_entry.name, image_value)
            if "icon" in params:
                icon_value = params.pop("icon")
                self._set_notebook_page_image(object_entry.name, icon_value)

        # splitter window values
        if object_entry.type == "SplitterWindow":
            if "orientation" in params:
                orient_value = str(params.pop("orientation") or "vertical").lower()
                data["orientation"] = "horizontal" if orient_value.startswith("h") else "vertical"
            if "split" in params:
                data["sashposition"] = int(params.pop("split"))
            if "sashposition" in params:
                data["sashposition"] = int(params.pop("sashposition"))
            if "position" in params:
                data["sashposition"] = int(params.pop("position"))
            if "minsize" in params:
                data["minsize"] = max(1, int(params.pop("minsize")))
            if "minimum" in params:
                data["minsize"] = max(1, int(params.pop("minimum")))
            if "unsplit" in params:
                data["unsplit"] = 1 if int(params.pop("unsplit")) else 0
            if "collapse" in params:
                collapse_value = str(params.pop("collapse") or "second").lower()
                data["collapse"] = "first" if collapse_value.startswith("fir") else "second"
            if "collapseside" in params:
                collapse_value = str(params.pop("collapseside") or "second").lower()
                data["collapse"] = "first" if collapse_value.startswith("fir") else "second"
            if "firstpane" in params:
                pane_name = str(params.pop("firstpane") or "")
                data["firstpane"] = pane_name if pane_name else None
            if "secondpane" in params:
                pane_name = str(params.pop("secondpane") or "")
                data["secondpane"] = pane_name if pane_name else None

            object_entry.data = data
            self._apply_splitter_layout(object_entry.name)
            data = object_entry.data if isinstance(object_entry.data, dict) else data

        # splitter pane values
        if object_entry.type == "SplitterPane":
            if "side" in params:
                side = str(params.pop("side") or "first").lower()
                side = "second" if side.startswith("sec") else "first"
                data["side"] = side
                splitter_name = data.get("splitter")
                if isinstance(splitter_name, str) and splitter_name in self.widgets:
                    splitter_object = self.get_object(splitter_name)
                    splitter_data = splitter_object.data if isinstance(splitter_object.data, dict) else {}
                    if side == "first":
                        splitter_data["firstpane"] = object_entry.name
                    else:
                        splitter_data["secondpane"] = object_entry.name
                    splitter_object.data = splitter_data
                    self._apply_splitter_layout(splitter_name)

        # tree-view values
        if object_entry.type == "TreeView":
            treeview = data.get("treeview") if isinstance(data, dict) else None
            root = data.get("root") if isinstance(data, dict) else None

            if "mode" in params:
                data["mode"] = str(params.pop("mode")).lower()
            if "sortable" in params:
                data["sortable"] = 1 if int(params.pop("sortable")) else 0
            if "reordable" in params:
                data["reordable"] = 1 if int(params.pop("reordable")) else 0

            if isinstance(treeview, wx.TreeCtrl) and isinstance(root, wx.TreeItemId) and root.IsOk():
                if "iter" in params:
                    iter_item = params.pop("iter")
                    if isinstance(iter_item, wx.TreeItemId) and iter_item.IsOk():
                        treeview.SelectItem(iter_item)

                if "path" in params:
                    path_value = params.pop("path")
                    path_list = self._normalize_tree_path(path_value)
                    target_item = self._tree_find_item_by_path(treeview, root, path_list)
                    if target_item.IsOk():
                        treeview.SelectItem(target_item)

                if "row" in params:
                    row_value = params.pop("row")
                    selected_item = treeview.GetSelection()
                    if selected_item.IsOk():
                        if isinstance(row_value, (list, tuple)) and len(row_value) > 0:
                            treeview.SetItemText(selected_item, str(row_value[0]))
                        else:
                            treeview.SetItemText(selected_item, str(row_value))

                if "select" in params:
                    select_value = params.pop("select")
                    rows_to_select = list(select_value) if isinstance(select_value, (list, tuple)) else [select_value]
                    for row_value in rows_to_select:
                        row_index = int(row_value)
                        target_item = self._tree_find_item_by_path(treeview, root, [row_index])
                        if target_item.IsOk():
                            treeview.SelectItem(target_item)

                if "unselect" in params:
                    unselect_value = params.pop("unselect")
                    rows_to_unselect = list(unselect_value) if isinstance(unselect_value, (list, tuple)) else [unselect_value]
                    for row_value in rows_to_unselect:
                        row_index = int(row_value)
                        target_item = self._tree_find_item_by_path(treeview, root, [row_index])
                        if target_item.IsOk():
                            try:
                                treeview.UnselectItem(target_item)
                            except Exception:
                                pass

        # toolbar values
        if object_entry.type == "ToolBar":
            if "orientation" in params:
                orientation = str(params.pop("orientation") or "horizontal").lower()
                data["orientation"] = "vertical" if orientation == "vertical" else "horizontal"

            source_tools = None
            if "tools" in params:
                source_tools = params.pop("tools")
            elif "data" in params:
                source_tools = params.pop("data")
            if source_tools is not None:
                if not isinstance(source_tools, (list, tuple)):
                    source_tools = []
                self._set_toolbar_tools(object_entry.name, list(source_tools))
                data = object_entry.data if isinstance(object_entry.data, dict) else data

            if "active" in params:
                active_value = int(params.pop("active"))
                tools = data.get("tools") if isinstance(data.get("tools"), list) else []
                selected_tool: Optional[dict[str, Any]] = None
                for idx, tool in enumerate(tools):
                    if not isinstance(tool, dict):
                        continue
                    tool_id = int(tool.get("id", -1))
                    if tool_id == active_value or idx == active_value:
                        selected_tool = tool
                        break

                if selected_tool is not None:
                    data["lasttool"] = int(selected_tool.get("id", -1))
                    tool_id = int(selected_tool.get("id", -1))
                    kind = str(selected_tool.get("kind", "normal"))
                    if widget is not None and hasattr(widget, "ToggleTool") and tool_id >= 0 and kind in ("check", "toggle", "radio"):
                        widget.ToggleTool(tool_id, True)
                        selected_tool["active"] = 1

        # message-dialog values
        if object_entry.type == "MessageDialog":
            if "modal" in params:
                data["modal"] = 1 if int(params.pop("modal")) else 0
            if "dialogtype" in params:
                data["dialogtype"] = str(params.pop("dialogtype") or "ok").lower()
            if "messagetype" in params:
                data["messagetype"] = str(params.pop("messagetype") or "info").lower()
            if "icon" in params:
                data["icon"] = params.pop("icon")
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

        # filechooser-dialog values
        if object_entry.type == "FileChooserDialog":
            if "action" in params:
                data["action"] = str(params.pop("action") or "open").lower()
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "filename" in params:
                data["filename"] = str(params.pop("filename") or "")
            if "folder" in params:
                data["folder"] = str(params.pop("folder") or "")
            if "filter" in params:
                filter_value = params.pop("filter")
                if isinstance(filter_value, str):
                    data["filter"] = [None, filter_value]
                elif isinstance(filter_value, (list, tuple)):
                    data["filter"] = list(filter_value)
                else:
                    data["filter"] = []
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

        # filechooser-button values
        if object_entry.type == "FileChooserButton":
            if "action" in params:
                data["action"] = str(params.pop("action") or "open").lower()
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "filename" in params:
                filename_value = str(params.pop("filename") or "")
                data["filename"] = filename_value
                text_ctrl = data.get("text")
                if isinstance(text_ctrl, wx.TextCtrl):
                    text_ctrl.SetValue(filename_value)
            if "folder" in params:
                data["folder"] = str(params.pop("folder") or "")
            if "filter" in params:
                filter_value = params.pop("filter")
                if isinstance(filter_value, str):
                    data["filter"] = [None, filter_value]
                elif isinstance(filter_value, (list, tuple)):
                    data["filter"] = list(filter_value)
                else:
                    data["filter"] = []

        # dirpicker-control values
        if object_entry.type == "DirPickerCtrl":
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value

            folder_value = None
            if "folder" in params:
                folder_value = str(params.pop("folder") or "")
            elif "path" in params:
                folder_value = str(params.pop("path") or "")
            elif "directory" in params:
                folder_value = str(params.pop("directory") or "")
            elif "dir" in params:
                folder_value = str(params.pop("dir") or "")

            if folder_value is not None:
                data["folder"] = folder_value
                if widget is not None and hasattr(widget, "SetPath"):
                    try:
                        widget.SetPath(folder_value)
                    except Exception:
                        pass

        # datepicker-control values
        if object_entry.type == "DatePickerCtrl":
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value

            date_value: Optional[str] = None
            if "date" in params:
                date_value = str(params.pop("date") or "")
            elif "value" in params:
                date_value = str(params.pop("value") or "")
            elif "year" in params or "month" in params or "day" in params:
                current = str(data.get("date") or "")
                try:
                    if current:
                        current_date = datetime.datetime.strptime(current, "%Y-%m-%d").date()
                    else:
                        current_date = datetime.date.today()
                except Exception:
                    current_date = datetime.date.today()
                year_value = int(params.pop("year")) if "year" in params else current_date.year
                month_value = int(params.pop("month")) if "month" in params else current_date.month
                day_value = int(params.pop("day")) if "day" in params else current_date.day
                try:
                    date_value = datetime.date(year_value, month_value, day_value).strftime("%Y-%m-%d")
                except Exception:
                    date_value = current_date.strftime("%Y-%m-%d")

            if date_value is not None:
                parsed_date: Optional[datetime.date] = None
                value_text = str(date_value).strip()
                if value_text:
                    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                        try:
                            parsed_date = datetime.datetime.strptime(value_text, date_format).date()
                            break
                        except Exception:
                            continue
                if parsed_date is None:
                    parsed_date = datetime.date.today()

                data["date"] = parsed_date.strftime("%Y-%m-%d")
                if widget is not None and hasattr(widget, "SetValue"):
                    wx_date = wx.DateTime.FromDMY(parsed_date.day, parsed_date.month - 1, parsed_date.year)
                    if wx_date.IsValid():
                        try:
                            widget.SetValue(wx_date)
                        except Exception:
                            pass

        # timepicker-control values
        if object_entry.type == "TimePickerCtrl":
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value

            time_value: Optional[str] = None
            if "time" in params:
                time_value = str(params.pop("time") or "")
            elif "value" in params:
                time_value = str(params.pop("value") or "")
            elif "hour" in params or "minute" in params or "second" in params:
                current = str(data.get("time") or "")
                try:
                    if current:
                        current_time = datetime.datetime.strptime(current, "%H:%M:%S").time()
                    else:
                        now = datetime.datetime.now()
                        current_time = datetime.time(now.hour, now.minute, now.second)
                except Exception:
                    now = datetime.datetime.now()
                    current_time = datetime.time(now.hour, now.minute, now.second)

                hour_value = int(params.pop("hour")) if "hour" in params else current_time.hour
                minute_value = int(params.pop("minute")) if "minute" in params else current_time.minute
                second_value = int(params.pop("second")) if "second" in params else current_time.second

                hour_value = max(0, min(23, hour_value))
                minute_value = max(0, min(59, minute_value))
                second_value = max(0, min(59, second_value))
                time_value = f"{hour_value:02d}:{minute_value:02d}:{second_value:02d}"

            if time_value is not None:
                parsed_time: Optional[datetime.time] = None
                value_text = str(time_value).strip()
                if value_text:
                    for time_format in ("%H:%M:%S", "%H:%M"):
                        try:
                            parsed_time = datetime.datetime.strptime(value_text, time_format).time()
                            break
                        except Exception:
                            continue
                if parsed_time is None:
                    now = datetime.datetime.now()
                    parsed_time = datetime.time(now.hour, now.minute, now.second)

                data["time"] = f"{parsed_time.hour:02d}:{parsed_time.minute:02d}:{parsed_time.second:02d}"
                if widget is not None and hasattr(widget, "SetValue") and hasattr(widget, "GetValue"):
                    try:
                        wx_time = widget.GetValue()
                        if isinstance(wx_time, wx.DateTime) and wx_time.IsValid():
                            wx_time.SetHour(parsed_time.hour)
                            wx_time.SetMinute(parsed_time.minute)
                            wx_time.SetSecond(parsed_time.second)
                            widget.SetValue(wx_time)
                    except Exception:
                        pass

        # fontbutton/fontselection-dialog values
        if object_entry.type in ("FontButton", "FontSelectionDialog"):
            if "previewstring" in params:
                if object_entry.type == "FontSelectionDialog":
                    data["preview"] = str(params.pop("previewstring") or "")
                else:
                    params.pop("previewstring")

            if "fontstring" in params:
                font_spec = self.font_string_to_array(str(params.pop("fontstring") or ""))
                family = str(font_spec[0]) if len(font_spec) > 0 else "Sans"
                size = int(font_spec[1]) if len(font_spec) > 1 else 10
                weight_label = str(font_spec[2]).lower() if len(font_spec) > 2 else "normal"
                weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
                font_obj = wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, weight, False, family)
                if font_obj.IsOk():
                    data["font_obj"] = font_obj

            if "fontfamily" in params or "fontsize" in params or "fontweight" in params:
                current_font = data.get("font_obj") if isinstance(data.get("font_obj"), wx.Font) else None
                family = str(params.pop("fontfamily")) if "fontfamily" in params else (current_font.GetFaceName() if isinstance(current_font, wx.Font) and current_font.IsOk() else "Sans")
                size = int(params.pop("fontsize")) if "fontsize" in params else (current_font.GetPointSize() if isinstance(current_font, wx.Font) and current_font.IsOk() else 10)
                weight_value: Any
                if "fontweight" in params:
                    weight_value = params.pop("fontweight")
                else:
                    weight_value = current_font.GetWeight() if isinstance(current_font, wx.Font) and current_font.IsOk() else wx.FONTWEIGHT_NORMAL

                if isinstance(weight_value, str):
                    weight_label = weight_value.lower()
                    wx_weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
                else:
                    wx_weight = int(weight_value)

                font_obj = wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx_weight, False, family)
                if font_obj.IsOk():
                    data["font_obj"] = font_obj

            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
                if object_entry.type == "FontButton" and widget is not None and hasattr(widget, "SetLabel"):
                    widget.SetLabel(title_value)

            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

            if object_entry.type == "FontButton" and isinstance(data.get("font_obj"), wx.Font):
                font_obj = data.get("font_obj")
                if isinstance(font_obj, wx.Font) and font_obj.IsOk() and widget is not None and hasattr(widget, "SetLabel"):
                    widget.SetLabel(f"{font_obj.GetFaceName()} {font_obj.GetPointSize()}")

        # colorselection-dialog values
        if object_entry.type == "ColorSelectionDialog":
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value

            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

            # update color from explicit RGB channel keys
            if "red" in params or "green" in params or "blue" in params:
                current = data.get("color")
                red_value = int(params.pop("red")) if "red" in params else (int(current.Red()) if isinstance(current, wx.Colour) and current.IsOk() else 0)
                green_value = int(params.pop("green")) if "green" in params else (int(current.Green()) if isinstance(current, wx.Colour) and current.IsOk() else 0)
                blue_value = int(params.pop("blue")) if "blue" in params else (int(current.Blue()) if isinstance(current, wx.Colour) and current.IsOk() else 0)
                colour_candidate = wx.Colour(red_value, green_value, blue_value)
                if not colour_candidate.IsOk():
                    self.internal_die(Name, "Invalid RGB color values for ColorSelectionDialog.")
                data["color"] = colour_candidate

            # update color from color string/list/tuple/wx.Colour
            if "color" in params:
                color_value = params.pop("color")
                colour_candidate: Optional[wx.Colour] = None
                if isinstance(color_value, wx.Colour):
                    colour_candidate = color_value
                elif isinstance(color_value, str):
                    colour_candidate = wx.Colour(color_value)
                elif isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
                    colour_candidate = wx.Colour(int(color_value[0]), int(color_value[1]), int(color_value[2]))
                if not isinstance(colour_candidate, wx.Colour) or not colour_candidate.IsOk():
                    self.internal_die(Name, "Invalid color format for ColorSelectionDialog.")
                data["color"] = colour_candidate

        # generic dialog values
        if object_entry.type == "Dialog":
            if "modal" in params:
                data["modal"] = 1 if int(params.pop("modal")) else 0
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")
            if "position" in params:
                position_value = params.pop("position")
                if isinstance(position_value, (list, tuple)) and len(position_value) >= 2:
                    object_entry.pos_x = int(position_value[0])
                    object_entry.pos_y = int(position_value[1])
            if "size" in params:
                size_value = params.pop("size")
                if isinstance(size_value, (list, tuple)) and len(size_value) >= 2:
                    object_entry.width = int(size_value[0])
                    object_entry.height = int(size_value[1])
            if "width" in params:
                object_entry.width = int(params.pop("width"))
            if "height" in params:
                object_entry.height = int(params.pop("height"))

        # about dialog values
        if object_entry.type == "AboutDialog":
            if "modal" in params:
                data["modal"] = 1 if int(params.pop("modal")) else 0
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "programname" in params:
                data["programname"] = str(params.pop("programname") or "")
            if "version" in params:
                data["version"] = str(params.pop("version") or "")
            if "copyright" in params:
                data["copyright"] = str(params.pop("copyright") or "")
            if "comments" in params:
                data["comments"] = str(params.pop("comments") or "")
            if "website" in params:
                data["website"] = str(params.pop("website") or "")
            if "authors" in params:
                authors_value = params.pop("authors")
                if isinstance(authors_value, (list, tuple)):
                    data["authors"] = [str(author) for author in authors_value]
                elif isinstance(authors_value, str):
                    data["authors"] = [authors_value]
                else:
                    data["authors"] = []
            if "license" in params:
                data["license"] = str(params.pop("license") or "")
            if "icon" in params:
                data["icon"] = params.pop("icon")
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

        # print dialog values
        if object_entry.type == "PrintDialog":
            if "modal" in params:
                data["modal"] = 1 if int(params.pop("modal")) else 0
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "minpage" in params:
                data["minpage"] = max(1, int(params.pop("minpage")))
            if "maxpage" in params:
                data["maxpage"] = max(1, int(params.pop("maxpage")))
            if "frompage" in params:
                data["frompage"] = max(1, int(params.pop("frompage")))
            if "topage" in params:
                data["topage"] = max(1, int(params.pop("topage")))
            if "allpages" in params:
                data["allpages"] = 1 if int(params.pop("allpages")) else 0
            if "selection" in params:
                data["selection"] = 1 if int(params.pop("selection")) else 0
            if "printtofile" in params:
                data["printtofile"] = 1 if int(params.pop("printtofile")) else 0
            if "copies" in params:
                data["copies"] = max(1, int(params.pop("copies")))
            if "nocopies" in params:
                data["copies"] = max(1, int(params.pop("nocopies")))
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

        # printout values
        if object_entry.type == "Printout":
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value

            if "path" in params:
                source_path = str(params.pop("path") or "")
                object_entry.path = source_path if source_path else None
                if source_path:
                    try:
                        with open(source_path, "r", encoding="utf-8") as file_handle:
                            data["text"] = file_handle.read()
                    except OSError:
                        self.internal_die(Name, f"Can't find {source_path}. Check path.")

            if "text" in params:
                data["text"] = str(params.pop("text") or "")

            if "linesperpage" in params:
                data["linesperpage"] = max(1, int(params.pop("linesperpage")))
            if "lines" in params:
                data["linesperpage"] = max(1, int(params.pop("lines")))
            if "header" in params:
                data["header"] = str(params.pop("header") or "")
            if "footer" in params:
                data["footer"] = str(params.pop("footer") or "")
            if "showdate" in params:
                data["showdate"] = 1 if int(params.pop("showdate")) else 0
            if "dateformat" in params:
                data["dateformat"] = str(params.pop("dateformat") or "%Y-%m-%d")

        # pagesetup dialog values
        if object_entry.type == "PageSetupDialog":
            if "modal" in params:
                data["modal"] = 1 if int(params.pop("modal")) else 0
            if "title" in params:
                title_value = str(params.pop("title") or "")
                data["title"] = title_value
                object_entry.title = title_value
            if "paperid" in params:
                data["paperid"] = int(params.pop("paperid"))
            if "orientation" in params:
                orientation = str(params.pop("orientation") or "portrait").lower()
                data["orientation"] = "landscape" if orientation.startswith("land") else "portrait"
            if "margintopleft" in params:
                margin = params.pop("margintopleft")
                if isinstance(margin, (list, tuple)) and len(margin) >= 2:
                    data["margintopleft"] = [int(margin[0]), int(margin[1])]
            if "marginbottomright" in params:
                margin = params.pop("marginbottomright")
                if isinstance(margin, (list, tuple)) and len(margin) >= 2:
                    data["marginbottomright"] = [int(margin[0]), int(margin[1])]
            if "responsefunction" in params:
                data["responsefunction"] = params.pop("responsefunction")

        # reject textview-content keys here (dedicated API)
        if object_entry.type == "TextView":
            for forbidden in ("path", "textbuffer", "textview"):
                if forbidden in params:
                    self.internal_die(Name, f"'set_value' doesn't support \"{forbidden}\". Use 'set_textview' instead.")

        # reject image-content keys here (dedicated API)
        if object_entry.type == "Image":
            for forbidden in ("path", "pixbuffer", "image", "stock", "bitmap"):
                if forbidden in params:
                    self.internal_die(Name, f"'set_value' doesn't support \"{forbidden}\". Use 'set_image' instead.")

        # persist updated data map
        object_entry.data = data

        # all keys must be consumed
        if len(params) > 0:
            rest = ", ".join(params.keys())
            self.internal_die(Name, f"Unknown parameter(s): \"{rest}\".")

    def _get_container(self, name: str) -> wx.Window:
        """
        Resolves a registered container by name.

        Parameters
        ----------

        name : str
            Container key.

        Returns
        -------

        wx.Window:
            Container window used as parent for child widgets.
        """
        container = self.containers.get(name)
        if container is None:
            self.internal_die(name, "No container found!")
        return container

    def _get_pos_in_frame(self, name: str, src_x: int, src_y: int) -> tuple[int, int]:
        """
        Adjusts child position when placed inside a frame-like container.

        Parameters
        ----------

        name : str
            Name of the frame container.

        src_x : int
            Original x coordinate.

        src_y : int
            Original y coordinate.

        Returns
        -------

        tuple[int, int]:
            Adjusted unscaled `(x, y)` position.
        """
        frame = self.get_object(name)

        # wx-native frames use an inner content panel, so child coords are already local
        if frame.type == "Frame" and isinstance(frame.data, dict) and frame.data.get("content_panel") is not None:
            return src_x, src_y

        label_height = 0
        if frame.title and frame.ref and hasattr(frame.ref, "GetLabel"):
            try:
                label_height = int(frame.ref.GetTextExtent(frame.title).GetHeight())
            except Exception:
                label_height = 0
        return src_x, int(src_y - (label_height / 2))

    def _layout_frame_container(self, name: str) -> None:
        """
        Recomputes title and inner container layout for a frame widget.

        Parameters
        ----------

        name : str
            Name of the frame object.
        """
        frame_object = self.get_object(name)
        if frame_object.type != "Frame" or frame_object.ref is None:
            return
        if not isinstance(frame_object.data, dict):
            return

        outer_panel = frame_object.ref
        content_panel = frame_object.data.get("content_panel")
        title_label = frame_object.data.get("title_label")
        if not isinstance(content_panel, wx.Window):
            return

        # place title label at the upper edge if present
        title_height_unscaled = 0
        if isinstance(title_label, wx.StaticText):
            title_label.SetPosition((self._scale(10), 0))
            label_height = title_label.GetBestSize().GetHeight()
            title_height_unscaled = int(round(label_height / self.scalefactor)) if self.scalefactor != 0 else int(label_height)

        # calculate inner content offset to keep children away from frame title border
        content_offset_y = max(6, (title_height_unscaled // 2) + 4)
        frame_object.data["content_offset_y"] = content_offset_y

        # use logical (unscaled) frame size as source of truth
        frame_width = frame_object.width if frame_object.width is not None else int(round(outer_panel.GetSize().GetWidth() / self.scalefactor))
        frame_height = frame_object.height if frame_object.height is not None else int(round(outer_panel.GetSize().GetHeight() / self.scalefactor))

        # apply scaled geometry to inner absolute-position container
        content_panel.SetPosition((self._scale(5), self._scale(content_offset_y)))
        content_width = max(1, self._scale(max(1, frame_width - 10)))
        content_height = max(1, self._scale(max(1, frame_height - (content_offset_y + 5))))
        content_panel.SetSize((content_width, content_height))

    def _apply_splitter_layout(self, splitter_name: str) -> None:
        """
        Applies stored pane/orientation/sash state to a splitter window.
        """
        splitter_object = self.get_object(splitter_name)
        if splitter_object.type != "SplitterWindow" or not isinstance(splitter_object.ref, wx.SplitterWindow):
            return

        splitter = splitter_object.ref
        data = splitter_object.data if isinstance(splitter_object.data, dict) else {}

        first_name = data.get("firstpane")
        second_name = data.get("secondpane")
        first_ref = self.get_object(first_name).ref if isinstance(first_name, str) and first_name in self.widgets else None
        second_ref = self.get_object(second_name).ref if isinstance(second_name, str) and second_name in self.widgets else None
        if not isinstance(first_ref, wx.Window) or not isinstance(second_ref, wx.Window):
            return

        orientation = str(data.get("orientation", "vertical")).lower()
        sash_unscaled = int(data.get("sashposition", 200))
        sash_scaled = self._scale(sash_unscaled)
        unsplit = 1 if int(data.get("unsplit", 0)) else 0
        min_size = max(1, self._scale(int(data.get("minsize", 60))))
        collapse_side = str(data.get("collapse", "second")).lower()
        collapse_side = "first" if collapse_side.startswith("fir") else "second"

        splitter.SetMinimumPaneSize(min_size)

        if splitter.IsSplit():
            to_remove = first_ref if collapse_side == "first" else second_ref
            try:
                splitter.Unsplit(to_remove)
            except Exception:
                splitter.Unsplit()

        if not unsplit:
            if orientation.startswith("h"):
                splitter.SplitHorizontally(first_ref, second_ref, sash_scaled)
            else:
                splitter.SplitVertically(first_ref, second_ref, sash_scaled)
            splitter.SetSashPosition(sash_scaled)

    def collapse_splitter(self, Name: str, Side: str = "second") -> None:
        """
        Collapses one pane of a splitter window.
        """
        object_entry = self.get_object(Name)
        if object_entry.type != "SplitterWindow" or not isinstance(object_entry.data, dict):
            self.internal_die(Name, "Not a splitter window object.")

        side = str(Side or "second").lower()
        side = "first" if side.startswith("fir") else "second"
        object_entry.data["collapse"] = side
        object_entry.data["unsplit"] = 1
        self._apply_splitter_layout(Name)

    def expand_splitter(self, Name: str) -> None:
        """
        Expands (re-splits) a collapsed splitter window.
        """
        object_entry = self.get_object(Name)
        if object_entry.type != "SplitterWindow" or not isinstance(object_entry.data, dict):
            self.internal_die(Name, "Not a splitter window object.")

        object_entry.data["unsplit"] = 0
        self._apply_splitter_layout(Name)

    def _add_to_container(self, name: str) -> None:
        """
        Parents a widget to its container and applies scaled absolute position.

        Parameters
        ----------

        name : str
            Widget name key.
        """
        # get widget object
        object_entry = self.get_object(name)
        widget = object_entry.ref
        if widget is None:
            self.internal_die(name, "No widget reference available!")

        # start with original (unscaled) source position
        src_x = object_entry.pos_x
        src_y = object_entry.pos_y
        target_container: wx.Window

        # if widget has an explicit container, use it
        if object_entry.container:
            target_container = self._get_container(object_entry.container)
            container_obj = self.get_object(object_entry.container)

            # adjust position if parent is a frame-like container
            if container_obj.type == "Frame":
                src_x, src_y = self._get_pos_in_frame(object_entry.container, src_x, src_y)
        else:
            # otherwise use default main container
            target_container = self.container if self.container is not None else self._get_container(self.default_container_name)

        # ensure widget parent matches target container
        if widget.GetParent() != target_container:
            widget.Reparent(target_container)

        # scale coordinates only when writing to wx widget
        widget.SetPosition((self._scale(src_x), self._scale(src_y)))

    def show_error(self, object_or_msg: Any, msg: Optional[str] = None) -> None:
        """
        Prints a formatted error message to stdout/stderr equivalent output.

        Parameters
        ----------

        object_or_msg : Any
            WidgetEntry or message content depending on usage mode.

        msg : str | None, optional
            Explicit error message. If omitted, `object_or_msg` is treated as
            the message text.

        Examples
        --------

        win.show_error("Something went wrong")
        win.show_error(win.get_object("mainWindow"), "Invalid value")
        """
        if msg is None:
            print(f"[{self.name}][err]: {object_or_msg}")
            return
        if isinstance(object_or_msg, WidgetEntry):
            print(f"[{self.name}->{object_or_msg.name}][err]: {msg}")
        else:
            print(f"[{self.name}][err]: {msg}")

    def is_underlined(self, text: str) -> bool:
        """
        Detects SimpleGtk/SimpleWx mnemonic markers in text.

        Parameters
        ----------

        text : str
            Input label text.

        Returns
        -------

        bool:
            True if text contains a mnemonic underscore, else False.

        Examples
        --------

        has_mnemonic = win.is_underlined("_Close")
        """
        normalized = text.replace("__", "")
        return "_" in normalized

    def add_tooltip(self, name: str, text: Optional[str] = None) -> None:
        """
        Stores and applies tooltip text for a supported widget.

        Parameters
        ----------

        name : str
            Widget name key.

        text : str | None, optional
            Tooltip text to set. If omitted, the stored tooltip is reused.

        Examples
        --------

        win.add_tooltip("closeButton", "Closes the application")
        """
        object_entry = self.get_object(name)
        if text is not None:
            object_entry.tip = " ".join(str(text).split())

        if not object_entry.tip:
            return

        if object_entry.ref is None:
            self.internal_die(name, "No widget reference available!")

        unsupported = ("MenuBar", "Menu", "Dialog", "LinkButton", "List", "Tree", "Notebook", "Statusbar", "Separator", "DrawingArea", "TextView")
        if object_entry.type in unsupported:
            self.show_error(object_entry, f'"{object_entry.type}" supports no tooltips!')
            return

        object_entry.ref.SetToolTip(object_entry.tip)

    def get_tooltip(self, Name: str) -> Optional[str]:
        """
        Returns current tooltip text of a widget.

        Parameters
        ----------

        Name : str
            Name of the widget.

        Returns
        -------

        str | None:
            Tooltip text or None if unsupported.

        Examples
        --------

        text = win.get_tooltip("image1")
        """
        object_entry = self.get_object(Name)
        unsupported = ("MenuBar", "Menu", "Dialog", "LinkButton", "List", "Tree", "Notebook", "Statusbar", "Separator", "DrawingArea", "TextView")
        if object_entry.type in unsupported:
            self.show_error(object_entry, f'"{object_entry.type}" has no tooltip!')
            return None
        return object_entry.tip

    def set_tooltip(self, Name: str, TooltipText: str) -> None:
        """
        Sets a new tooltip text on a widget.

        Parameters
        ----------

        Name : str
            Name of the widget.

        TooltipText : str
            New tooltip text.

        Returns
        -------

        None.

        Examples
        --------

        win.set_tooltip("image1", "Preview image")
        """
        object_entry = self.get_object(Name)
        unsupported = ("MenuBar", "Menu", "Dialog", "LinkButton", "List", "Tree", "Notebook", "Statusbar", "Separator", "DrawingArea", "TextView")
        if object_entry.type in unsupported:
            self.show_error(object_entry, f'"{object_entry.type}" has no tooltip!')
            return

        object_entry.tip = str(TooltipText)
        self.add_tooltip(Name)

    def set_font(self, name: str, font_spec: Any) -> None:
        """
        Applies a font tuple/list specification to a widget.

        Parameters
        ----------

        name : str
            Widget name key.

        font_spec : Any
            Font definition, typically `[family, size, weight]`.

        Examples
        --------

        win.set_font("closeButton", ["Sans", 10, "bold"])
        """
        object_entry = self.get_object(name)
        if object_entry.ref is None or font_spec is None:
            return

        current = object_entry.ref.GetFont()
        if isinstance(font_spec, (list, tuple)) and len(font_spec) >= 2:
            family = str(font_spec[0])
            size = int(font_spec[1])
            weight_label = str(font_spec[2]).lower() if len(font_spec) > 2 and font_spec[2] is not None else "normal"
            weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
            font = wx.Font(size, current.GetFamily(), current.GetStyle(), weight, faceName=family)
            if font.IsOk():
                object_entry.ref.SetFont(font)
                object_entry.font = font

    def set_font_color(self, name: str, color: str, _state: Optional[str] = None) -> None:
        """
        Applies foreground color to a widget.

        Parameters
        ----------

        name : str
            Widget name key.

        color : str
            Color name or color code accepted by wx.Colour.

        _state : str | None, optional
            Reserved compatibility argument for state-specific coloring.

        Examples
        --------

        win.set_font_color("closeButton", "red")
        """
        object_entry = self.get_object(name)
        if object_entry.ref is None:
            return
        object_entry.ref.SetForegroundColour(wx.Colour(color))

    def get_color(self, Name: str) -> Any:
        """
        Returns a color object by name or widget context.

        Parameters
        ----------

        Name : str
            Color name/code or widget name.

        Returns
        -------

        Any:
            Cached `wx.Colour` for color strings, or `(r, g, b)` tuple for
            drawing-area widgets.

        Examples
        --------

        red = win.get_color("red")
        rgb = win.get_color("draw_area")
        """
        # drawing-area compatibility path: get widget background as RGB tuple
        if Name in self.widgets:
            object_entry = self.get_object(Name)
            if object_entry.type == "DrawingArea" and isinstance(object_entry.data, dict):
                drawing_area = object_entry.data.get("drawing_area")
                if isinstance(drawing_area, wx.Window):
                    colour = drawing_area.GetBackgroundColour()
                    return (int(colour.Red()), int(colour.Green()), int(colour.Blue()))

        # generic color allocation/cache path
        cached = self.allocated_colors.get(Name)
        if isinstance(cached, wx.Colour):
            return cached

        colour = wx.Colour(Name)
        if not colour.IsOk():
            self.internal_die(Name, f"Unknown color \"{Name}\".")

        self.allocated_colors[Name] = colour
        return colour

    def _set_commons(self, widget_name: str, **params: Any) -> None:
        """
        Applies common widget behaviors (tooltip, handler, size, sensitivity).

        Parameters
        ----------

        widget_name : str
            Widget name key.

        **params : Any
            Normalized widget parameters.
        """
        # get object and native widget reference
        object_entry = self.get_object(widget_name)
        widget = object_entry.ref
        if widget is None:
            self.internal_die(widget_name, "No widget reference available!")

        # unpack optional callback/function parameter
        function = params.get("function")
        callback: Optional[Callable[[wx.Event], None]] = None
        if function is not None:
            if isinstance(function, (list, tuple)) and len(function) > 0 and callable(function[0]):
                base_cb = function[0]
                data = function[1] if len(function) > 1 else None

                # wrap callback to pass optional payload data
                def callback(event: wx.Event, cb: Callable[..., Any] = base_cb, payload: Any = data) -> None:
                    cb(event, payload)
            elif callable(function):
                callback = function

        # add tooltip if one is stored in object metadata
        if object_entry.tip is not None:
            self.add_tooltip(widget_name)

        # bind callback if function is defined
        if callback is not None:
            signal = params.get("signal")
            event_type = signal if callable(signal) else None

            # for buttons use EVT_BUTTON as default when no event was provided
            if event_type is None and object_entry.type == "Button":
                event_type = wx.EVT_BUTTON
            # for check buttons use EVT_CHECKBOX as default when no event was provided
            if event_type is None and object_entry.type == "CheckButton":
                event_type = wx.EVT_CHECKBOX
            # for radio buttons use EVT_RADIOBUTTON as default when no event was provided
            if event_type is None and object_entry.type == "RadioButton":
                event_type = wx.EVT_RADIOBUTTON
            # for text entries use EVT_TEXT as default when no event was provided
            if event_type is None and object_entry.type == "TextEntry":
                event_type = wx.EVT_TEXT
            # for combo boxes use EVT_COMBOBOX as default when no event was provided
            if event_type is None and object_entry.type == "ComboBox":
                event_type = wx.EVT_COMBOBOX
            # for sliders use EVT_SLIDER as default when no event was provided
            if event_type is None and object_entry.type == "Slider":
                event_type = wx.EVT_SLIDER
            # for link buttons use EVT_HYPERLINK as default when no event was provided
            if event_type is None and object_entry.type == "LinkButton":
                event_type = wx.EVT_HYPERLINK
            # for toolbars use EVT_TOOL as default when no event was provided
            if event_type is None and object_entry.type == "ToolBar":
                event_type = wx.EVT_TOOL
            # for notebooks use EVT_NOTEBOOK_PAGE_CHANGED as default when no event was provided
            if event_type is None and object_entry.type == "Notebook":
                event_type = wx.EVT_NOTEBOOK_PAGE_CHANGED
            # for font buttons use EVT_BUTTON as default when no event was provided
            if event_type is None and object_entry.type == "FontButton":
                event_type = wx.EVT_BUTTON
            # for file chooser buttons use EVT_BUTTON as default when no event was provided
            if event_type is None and object_entry.type == "FileChooserButton":
                event_type = wx.EVT_BUTTON
            # for dir picker controls use EVT_DIRPICKER_CHANGED as default when no event was provided
            if event_type is None and object_entry.type == "DirPickerCtrl":
                event_type = wx.EVT_DIRPICKER_CHANGED
            # for date picker controls use EVT_DATE_CHANGED as default when no event was provided
            if event_type is None and object_entry.type == "DatePickerCtrl":
                event_type = wx.adv.EVT_DATE_CHANGED
            # for time picker controls use EVT_TIME_CHANGED as default when no event was provided
            if event_type is None and object_entry.type == "TimePickerCtrl":
                event_type = wx.adv.EVT_TIME_CHANGED
            # for scrollbars use EVT_SCROLL as default when no event was provided
            if event_type is None and object_entry.type == "Scrollbar":
                event_type = wx.EVT_SCROLL
            # for spin buttons choose default event by concrete control type
            if event_type is None and object_entry.type == "SpinButton":
                if isinstance(widget, wx.SpinCtrlDouble):
                    event_type = wx.EVT_SPINCTRLDOUBLE
                else:
                    event_type = wx.EVT_SPINCTRL
            # for list views use row-selection event as default callback trigger
            if event_type is None and object_entry.type == "ListView":
                event_type = wx.EVT_LIST_ITEM_SELECTED
            # for grids use cell-changed event as default callback trigger
            if event_type is None and object_entry.type == "Grid":
                event_type = wxgrid.EVT_GRID_CELL_CHANGED
            # for data views use item-value-changed as default callback trigger
            if event_type is None and object_entry.type == "DataViewCtrl":
                event_type = wxdataview.EVT_DATAVIEW_ITEM_VALUE_CHANGED
            # for splitters use sash-position-changed as default callback trigger
            if event_type is None and object_entry.type == "SplitterWindow":
                event_type = wx.EVT_SPLITTER_SASH_POS_CHANGED
            # for tree views use selection-changed event as default callback trigger
            if event_type is None and object_entry.type == "TreeView":
                event_type = wx.EVT_TREE_SEL_CHANGED
            if event_type is not None:
                self.add_signal_handler(widget_name, event_type, callback)

        # set sensitive/enabled state (default: enabled)
        sensitive = params.get("sensitive", 1)
        widget.Enable(bool(sensitive))

        # configure widget size
        if object_entry.type not in ("Statusbar", "Menu"):
            # explicit size from object metadata
            if object_entry.width is not None and object_entry.height is not None:
                widget.SetSize((self._scale(object_entry.width), self._scale(object_entry.height)))

            # default button size (stored unscaled, applied scaled)
            elif object_entry.type == "Button":
                object_entry.width = 80
                object_entry.height = 25
                widget.SetSize((self._scale(object_entry.width), self._scale(object_entry.height)))

            # fallback to widget best size and store it as unscaled values
            else:
                best = widget.GetBestSize()
                object_entry.width = int(round(best.GetWidth() / self.scalefactor)) if self.scalefactor != 0 else best.GetWidth()
                object_entry.height = int(round(best.GetHeight() / self.scalefactor)) if self.scalefactor != 0 else best.GetHeight()

    def get_fontsize(self, name_or_widget: Optional[str | wx.Window] = None) -> int:
        """
        Returns effective font point size for a widget.

        Parameters
        ----------

        name_or_widget : str | wx.Window | None, optional
            Widget name, widget reference, or None for main window.

        Returns
        -------

        int:
            Font point size.

        Examples
        --------

        size = win.get_fontsize("mainWindow")
        """
        # resolve target widget: main window, named widget, or direct reference
        if name_or_widget is None:
            widget: wx.Window = self.ref
        elif isinstance(name_or_widget, str):
            widget = self.get_widget(name_or_widget)
        else:
            widget = name_or_widget

        # read point size from current widget font
        font = widget.GetFont()
        size = font.GetPointSize()

        # fallback to default size if wx returns invalid/non-positive value
        return size if size > 0 else self.default_font_size

    def get_fontfamily(self, name_or_widget: Optional[str | wx.Window] = None) -> str:
        """
        Returns font family name for a widget.

        Parameters
        ----------

        name_or_widget : str | wx.Window | None, optional
            Widget name, widget reference, or None for main window.

        Returns
        -------

        str:
            Font face name.

        Examples
        --------

        family = win.get_fontfamily("mainWindow")
        """
        # resolve target widget: main window, named widget, or direct reference
        if name_or_widget is None:
            widget: wx.Window = self.ref
        elif isinstance(name_or_widget, str):
            widget = self.get_widget(name_or_widget)
        else:
            widget = name_or_widget

        # return font face/family name
        return widget.GetFont().GetFaceName()

    def get_fontweight(self, name_or_widget: Optional[str | wx.Window] = None) -> str:
        """
        Returns normalized font weight label for a widget.

        Parameters
        ----------

        name_or_widget : str | wx.Window | None, optional
            Widget name, widget reference, or None for main window.

        Returns
        -------

        str:
            Weight label (`normal`, `bold`, or `light`).

        Examples
        --------

        weight = win.get_fontweight("mainWindow")
        """
        # resolve target widget: main window, named widget, or direct reference
        if name_or_widget is None:
            widget: wx.Window = self.ref
        elif isinstance(name_or_widget, str):
            widget = self.get_widget(name_or_widget)
        else:
            widget = name_or_widget

        # map wx font weight constants to normalized strings
        weight = widget.GetFont().GetWeight()
        if weight == wx.FONTWEIGHT_BOLD:
            return "bold"
        if weight == wx.FONTWEIGHT_LIGHT:
            return "light"
        return "normal"

    def get_font_array(self, name: str) -> list[str | int]:
        """
        Returns widget font as `[family, size, weight]` list.

        Parameters
        ----------

        name : str
            Widget name key.

        Returns
        -------

        list[str | int]:
            Font family, size and weight tuple-like list.

        Examples
        --------

        font_data = win.get_font_array("labelTitle")
        """
        # get native widget and read its current font
        widget = self.get_widget(name)
        font = widget.GetFont()

        # return [family, size, weight] as in SimpleGtk2 conventions
        return [font.GetFaceName(), font.GetPointSize(), self.get_fontweight(widget)]

    def font_array_to_string(self, family: str, size: int, weight: str = "") -> str:
        """
        Converts a font array-like tuple to a canonical string.

        Parameters
        ----------

        family : str
            Font family name.

        size : int
            Font size in points.

        weight : str, optional
            Optional weight label.

        Returns
        -------

        str:
            Concatenated font string.

        Examples
        --------

        font_str = win.font_array_to_string("Sans", 10, "bold")
        """
        # include weight part only when set
        if weight:
            return f"{family} {weight} {size}"
        return f"{family} {size}"

    def font_string_to_array(self, font_string: str) -> list[Any]:
        """
        Converts a font string into a normalized font array.

        Parameters
        ----------

        font_string : str
            Font string containing family and size, optionally weight/style.

        Returns
        -------

        list[Any]:
            Parsed `[family, size, weight, style, under]` values.

        Examples
        --------

        font_array = win.font_string_to_array("Arial Bold Italic 12")
        """
        text = str(font_string or "").strip()
        if not text:
            return ["Sans", 10, "normal", "normal", 0]

        parts = text.split()
        family_tokens: list[str] = []
        weight = "normal"
        style = "normal"
        under = 0
        size = 10

        # parse trailing numeric size if available
        if len(parts) > 0:
            tail = parts[-1]
            try:
                size = int(float(tail))
                parts = parts[:-1]
            except Exception:
                size = 10

        for token in parts:
            lower = token.lower()
            if lower in ("bold", "light", "thin", "heavy"):
                weight = lower
            elif lower in ("italic", "slant", "oblique"):
                style = lower
            elif lower == "underline":
                under = 1
            else:
                family_tokens.append(token)

        family = " ".join(family_tokens).strip()
        if not family:
            family = "Sans"

        return [family, size, weight, style, under]

    def get_font_string(self, name: str) -> str:
        """
        Returns widget font in serialized string format.

        Parameters
        ----------

        name : str
            Widget name key.

        Returns
        -------

        str:
            Serialized font description.

        Examples
        --------

        font_str = win.get_font_string("mainWindow")
        """
        # build serialized font string from normalized font array
        family, size, weight = self.get_font_array(name)
        return self.font_array_to_string(str(family), int(size), str(weight))

    def _on_font_changed(self, _event: wx.Event) -> None:
        """
        Handles runtime theme/font updates for scaling state.

        Parameters
        ----------

        _event : wx.Event
            Triggering wx event instance.
        """
        # abort if main frame is not available
        if not self.ref:
            return

        # detect whether current window font changed
        new_font = self.get_font_string(self.name)
        if new_font != self.font:
            # update stored old/new font values
            self.old_font = self.font
            self.font = new_font

            # get updated font size and recalculate scale factor if needed
            new_fontsize = self.get_fontsize(self.ref)
            if new_fontsize != self.fontsize:
                self.old_fontsize = self.fontsize
                self.fontsize = new_fontsize
                self.scalefactor = self._calc_scalefactor(self.base, self.fontsize)

    def add_signal_handler(self, name: str, event_type: Any, callback: Callable[[wx.Event], None]) -> None:
        """
        Binds a native wx event handler and stores callback metadata.

        Parameters
        ----------

        name : str
            Widget name key.

        event_type : Any
            Native wx event binder (e.g. `wx.EVT_BUTTON`).

        callback : Callable[[wx.Event], None]
            Event callback function.

        Examples
        --------

        win.add_signal_handler("closeButton", wx.EVT_BUTTON, lambda event: win.main_quit())
        """
        obj = self.get_object(name)
        if obj and obj.ref:
            target_widget: wx.Window = obj.ref

            # for drawing areas bind interactive/paint events on inner drawing panel
            if obj.type == "DrawingArea" and isinstance(obj.data, dict):
                drawing_area = obj.data.get("drawing_area")
                if isinstance(drawing_area, wx.Window):
                    target_widget = drawing_area

            # for list views bind list events on inner wx.ListCtrl
            if obj.type == "ListView" and isinstance(obj.data, dict):
                listview = obj.data.get("listview")
                if isinstance(listview, wx.Window):
                    target_widget = listview

            # for tree views bind events on inner wx.TreeCtrl
            if obj.type == "TreeView" and isinstance(obj.data, dict):
                treeview = obj.data.get("treeview")
                if isinstance(treeview, wx.Window):
                    target_widget = treeview

            # for file chooser buttons bind events on inner browse button
            if obj.type == "FileChooserButton" and isinstance(obj.data, dict):
                chooser_button = obj.data.get("button")
                if isinstance(chooser_button, wx.Window):
                    target_widget = chooser_button

            target_widget.Bind(event_type, callback)
            obj.handler[event_type] = callback

    def remove_signal_handler(self, name: str, signal: Any) -> None:
        """
        Removes a previously bound signal handler from a widget.

        Parameters
        ----------

        name : str
            Widget name key.

        signal : Any
            Signal/event key used on registration.

        Returns
        -------

        None.

        Examples
        --------

        win.remove_signal_handler("closeButton", wx.EVT_BUTTON)
        """
        object_entry = self.get_object(name)
        if object_entry.ref is None:
            self.internal_die(name, "No widget reference available!")

        callback = object_entry.handler.get(signal)
        event_type = signal

        # menu item callbacks are stored under EVT_MENU and bound to main frame with id
        if callback is None and object_entry.type == "MenuItem":
            callback = object_entry.handler.get(wx.EVT_MENU)
            event_type = wx.EVT_MENU

        if callback is None:
            self.show_error(object_entry, f'No signal handler found for "{signal}".')
            return

        if object_entry.type == "MenuItem":
            if self.ref is None:
                self.internal_die(name, "No main window available for menu handler removal.")
            data = object_entry.data if isinstance(object_entry.data, dict) else {}
            item_id = int(data.get("id", -1))
            if item_id >= 0:
                self.ref.Unbind(wx.EVT_MENU, handler=callback, id=item_id)
            else:
                self.ref.Unbind(wx.EVT_MENU, handler=callback)
            object_entry.handler.pop(wx.EVT_MENU, None)
            object_entry.handler.pop(signal, None)
            return

        target_widget: wx.Window = object_entry.ref
        if object_entry.type == "ListView" and isinstance(object_entry.data, dict):
            listview = object_entry.data.get("listview")
            if isinstance(listview, wx.Window):
                target_widget = listview
        if object_entry.type == "TreeView" and isinstance(object_entry.data, dict):
            treeview = object_entry.data.get("treeview")
            if isinstance(treeview, wx.Window):
                target_widget = treeview
        if object_entry.type == "FileChooserButton" and isinstance(object_entry.data, dict):
            chooser_button = object_entry.data.get("button")
            if isinstance(chooser_button, wx.Window):
                target_widget = chooser_button

        target_widget.Unbind(event_type, handler=callback)
        object_entry.handler.pop(signal, None)
        if event_type != signal:
            object_entry.handler.pop(event_type, None)

    def main_quit(self) -> None:
        """
        Closes and destroys the main application window.

        Examples
        --------

        win.main_quit()
        """
        if self.main_window is not None:
            self.main_window.Destroy()

    def add_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        Position: Optional[list[int] | tuple[int, int]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Modal: int = 1,
        Frame: Optional[str] = None,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a generic dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the dialog object. Must be unique.

        Title : str | None, optional
            Dialog title text.

        Position : list[int] | tuple[int, int] | None, optional
            Optional unscaled dialog position `[x, y]`.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled dialog size `[width, height]`.

        Modal : int, optional
            Modal flag (`1` modal, `0` modeless).

        Frame : str | None, optional
            Optional parent frame name.

        RFunc : Callable | None, optional
            Optional response callback in modeless mode.

        Returns
        -------

        None.

        Examples
        --------

        win.add_dialog(Name="dialog1", Title="Optionen", Modal=1)
        """
        # normalize dialog parameters and create object entry
        params = self._normalize(
            Name=Name,
            Title=Title,
            Position=Position,
            Size=Size,
            Modal=Modal,
            Frame=Frame,
            RFunc=RFunc,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "Dialog"
        object_entry.title = str(params.get("title") or "Dialog")
        object_entry.ref = None
        object_entry.data = {
            "modal": 1 if int(params.get("modal", 1)) else 0,
            "title": object_entry.title,
            "frame": params.get("frame"),
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_dialog(self, Name: str) -> Optional[int]:
        """
        Shows a predefined generic dialog.

        Parameters
        ----------

        Name : str
            Name of the dialog object. Must be unique.

        Returns
        -------

        int | None:
            Modal response id, or `None` in modeless mode.

        Examples
        --------

        response = win.show_dialog("dialog1")
        """
        # read predefined dialog metadata
        object_entry = self.get_object(Name)
        if object_entry.type != "Dialog":
            self.internal_die(Name, "Not a dialog object.")

        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        title = str(data.get("title") or object_entry.title or "Dialog")
        modal = 1 if int(data.get("modal", 1)) else 0
        response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None

        # resolve dialog parent from frame name or fall back to main frame
        parent: Optional[wx.Window] = None
        frame_name = data.get("frame")
        if isinstance(frame_name, str) and frame_name:
            if frame_name in self.widgets:
                frame_object = self.get_object(frame_name)
                parent = frame_object.ref if isinstance(frame_object.ref, wx.Window) else None
        if parent is None:
            parent = self.ref if isinstance(self.ref, wx.Window) else None

        # create and configure native dialog from stored geometry
        dialog = wx.Dialog(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        if object_entry.width is not None and object_entry.height is not None:
            dialog.SetSize((self._scale(int(object_entry.width)), self._scale(int(object_entry.height))))
        if object_entry.pos_x is not None and object_entry.pos_y is not None:
            dialog.SetPosition((self._scale(int(object_entry.pos_x)), self._scale(int(object_entry.pos_y))))

        # build a minimal content layout with OK/Cancel buttons
        vbox = wx.BoxSizer(wx.VERTICAL)
        info = wx.StaticText(dialog, wx.ID_ANY, title)
        vbox.Add(info, 1, wx.EXPAND | wx.ALL, 12)
        button_sizer = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if button_sizer is not None:
            vbox.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        dialog.SetSizer(vbox)
        dialog.Layout()

        # modal and modeless behavior follow existing dialog patterns
        if modal:
            response = int(dialog.ShowModal())
            dialog.Destroy()
            return response

        if callable(response_function):
            def _on_dialog_response(event: wx.CommandEvent) -> None:
                try:
                    response_function(dialog, event.GetId())
                finally:
                    dialog.Destroy()

            dialog.Bind(wx.EVT_BUTTON, _on_dialog_response)
        dialog.Show()
        return None

    def add_about_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        ProgramName: Optional[str] = None,
        Version: Optional[str] = None,
        Copyright: Optional[str] = None,
        Comments: Optional[str] = None,
        Website: Optional[str] = None,
        Authors: Optional[list[Any] | tuple[Any, ...]] = None,
        License: Optional[str] = None,
        Icon: Optional[Any] = None,
        Modal: int = 1,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers an about-dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the about-dialog object. Must be unique.

        Title : str | None, optional
            Optional dialog title.

        ProgramName : str | None, optional
            Program/application name.

        Version : str | None, optional
            Program version text.

        Copyright : str | None, optional
            Copyright information.

        Comments : str | None, optional
            Additional about text.

        Website : str | None, optional
            Project website URL.

        Authors : list[Any] | tuple[Any, ...] | None, optional
            Author names.

        License : str | None, optional
            License text.

        Icon : Any | None, optional
            Optional icon path, `wx.Icon`, or `wx.Bitmap`.

        Modal : int, optional
            Modal metadata flag (`1` modal, `0` modeless compatibility).

        RFunc : Callable | None, optional
            Optional callback executed after dialog closes.

        Returns
        -------

        None.

        Examples
        --------

        win.add_about_dialog(Name="about1", ProgramName="SimpleWx", Version="0.1.0")
        """
        # normalize about-dialog parameters
        params = self._normalize(
            Name=Name,
            Title=Title,
            ProgramName=ProgramName,
            Version=Version,
            Copyright=Copyright,
            Comments=Comments,
            Website=Website,
            Authors=Authors,
            License=License,
            Icon=Icon,
            Modal=Modal,
            RFunc=RFunc,
        )

        # create and store object metadata for deferred display
        object_entry = self._new_widget(**params)
        object_entry.type = "AboutDialog"
        object_entry.title = str(params.get("title") or params.get("programname") or "About")
        object_entry.ref = None
        object_entry.data = {
            "title": object_entry.title,
            "programname": str(params.get("programname") or ""),
            "version": str(params.get("version") or ""),
            "copyright": str(params.get("copyright") or ""),
            "comments": str(params.get("comments") or ""),
            "website": str(params.get("website") or ""),
            "authors": [str(author) for author in params.get("authors", [])] if isinstance(params.get("authors"), (list, tuple)) else [],
            "license": str(params.get("license") or ""),
            "icon": params.get("icon"),
            "modal": 1 if int(params.get("modal", 1)) else 0,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_about_dialog(self, Name: str) -> None:
        """
        Shows a predefined about dialog.

        Parameters
        ----------

        Name : str
            Name of the about-dialog object. Must be unique.

        Returns
        -------

        None.

        Examples
        --------

        win.show_about_dialog("about1")
        """
        # read predefined about-dialog metadata
        object_entry = self.get_object(Name)
        if object_entry.type != "AboutDialog":
            self.internal_die(Name, "Not an about-dialog object.")
        data = object_entry.data if isinstance(object_entry.data, dict) else {}

        # build wx AboutDialogInfo from stored values
        info = wx.adv.AboutDialogInfo()
        program_name = str(data.get("programname") or "")
        title = str(data.get("title") or object_entry.title or "About")
        info.SetName(program_name if program_name else title)

        version = str(data.get("version") or "")
        if version:
            info.SetVersion(version)
        copyright_text = str(data.get("copyright") or "")
        if copyright_text:
            info.SetCopyright(copyright_text)
        comments = str(data.get("comments") or "")
        if comments:
            info.SetDescription(comments)
        website = str(data.get("website") or "")
        if website:
            info.SetWebSite(website)
        license_text = str(data.get("license") or "")
        if license_text:
            info.SetLicence(license_text)

        authors = data.get("authors")
        if isinstance(authors, list):
            for author in authors:
                info.AddDeveloper(str(author))

        # apply optional icon in supported formats
        icon_value = data.get("icon")
        if isinstance(icon_value, wx.Icon) and icon_value.IsOk():
            info.SetIcon(icon_value)
        elif isinstance(icon_value, wx.Bitmap) and icon_value.IsOk():
            icon = wx.Icon()
            icon.CopyFromBitmap(icon_value)
            if icon.IsOk():
                info.SetIcon(icon)
        elif isinstance(icon_value, str) and icon_value:
            try:
                icon = wx.Icon(icon_value, wx.BITMAP_TYPE_ANY)
                if icon.IsOk():
                    info.SetIcon(icon)
            except Exception:
                pass

        # show the native about dialog
        parent = self.ref if isinstance(self.ref, wx.Window) else None
        wx.adv.AboutBox(info, parent)

        # execute optional callback after closing the about dialog
        response_function = data.get("responsefunction")
        if callable(response_function):
            response_function(None)

    def add_msg_dialog(
        self,
        Name: str,
        Modal: int = 1,
        DType: str = "ok",
        MType: str = "info",
        Icon: Optional[str] = None,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a message-dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the message-dialog object. Must be unique.

        Modal : int, optional
            Modal flag (`1` modal, `0` modeless).

        DType : str, optional
            Dialog button type (`ok`, `yesno`, `okcancel`, `yesnocancel`).

        MType : str, optional
            Message type (`info`, `warning`, `error`, `question`).

        Icon : str | None, optional
            Optional icon path or stock/icon name.

        RFunc : Callable | None, optional
            Optional response callback (primarily for modeless mode).
        """
        params = self._normalize(
            Name=Name,
            Modal=Modal,
            DType=DType,
            MType=MType,
            Icon=Icon,
            RFunc=RFunc,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "MessageDialog"
        object_entry.ref = None
        object_entry.data = {
            "modal": 1 if int(params.get("modal", 1)) else 0,
            "dialogtype": str(params.get("dialogtype") or "ok").lower(),
            "messagetype": str(params.get("messagetype") or "info").lower(),
            "icon": params.get("icon"),
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def add_printout(
        self,
        Name: str,
        Title: Optional[str] = None,
        Text: Optional[str] = None,
        Path: Optional[str] = None,
        LinesPerPage: int = 60,
        Header: Optional[str] = None,
        Footer: Optional[str] = None,
        ShowDate: int = 1,
        DateFormat: str = "%Y-%m-%d",
    ) -> None:
        """
        Registers a printout definition used by preview/printing pipeline.
        """
        params = self._normalize(
            Name=Name,
            Title=Title,
            Text=Text,
            Path=Path,
            LinesPerPage=LinesPerPage,
            Header=Header,
            Footer=Footer,
            ShowDate=ShowDate,
            DateFormat=DateFormat,
        )

        content = str(params.get("text") or "")
        source_path = str(params.get("path") or "")
        if source_path:
            try:
                with open(source_path, "r", encoding="utf-8") as file_handle:
                    content = file_handle.read()
            except OSError:
                self.internal_die(Name, f"Can't find {source_path}. Check path.")

        object_entry = self._new_widget(**params)
        object_entry.type = "Printout"
        object_entry.title = str(params.get("title") or "Print")
        object_entry.path = source_path if source_path else None
        object_entry.ref = None
        object_entry.data = {
            "title": object_entry.title,
            "text": content,
            "linesperpage": max(1, int(params.get("linesperpage", 60))),
            "header": str(params.get("header") or ""),
            "footer": str(params.get("footer") or "Page {page}"),
            "showdate": 1 if int(params.get("showdate", 1)) else 0,
            "dateformat": str(params.get("dateformat") or "%Y-%m-%d"),
        }
        self.widgets[object_entry.name] = object_entry

    def _build_print_dialog_data(self, print_dialog_name: Optional[str] = None) -> wx.PrintDialogData:
        """
        Builds wx.PrintDialogData from optional predefined PrintDialog metadata.
        """
        payload: dict[str, Any] = {
            "minpage": 1,
            "maxpage": 1,
            "frompage": 1,
            "topage": 1,
            "allpages": 1,
            "selection": 0,
            "printtofile": 0,
            "copies": 1,
        }
        if isinstance(print_dialog_name, str) and print_dialog_name in self.widgets:
            dialog_object = self.get_object(print_dialog_name)
            if dialog_object.type == "PrintDialog" and isinstance(dialog_object.data, dict):
                payload.update(dialog_object.data)

        print_data = wx.PrintDialogData()
        if hasattr(print_data, "SetMinPage"):
            print_data.SetMinPage(max(1, int(payload.get("minpage", 1))))
        if hasattr(print_data, "SetMaxPage"):
            print_data.SetMaxPage(max(1, int(payload.get("maxpage", 1))))
        if hasattr(print_data, "SetFromPage"):
            print_data.SetFromPage(max(1, int(payload.get("frompage", 1))))
        if hasattr(print_data, "SetToPage"):
            print_data.SetToPage(max(1, int(payload.get("topage", 1))))
        if hasattr(print_data, "SetAllPages"):
            print_data.SetAllPages(bool(int(payload.get("allpages", 1))))
        if hasattr(print_data, "SetSelection"):
            print_data.SetSelection(bool(int(payload.get("selection", 0))))
        if hasattr(print_data, "SetPrintToFile"):
            print_data.SetPrintToFile(bool(int(payload.get("printtofile", 0))))
        if hasattr(print_data, "SetNoCopies"):
            print_data.SetNoCopies(max(1, int(payload.get("copies", 1))))
        return print_data

    def _apply_pagesetup_to_print_dialog_data(self, print_data: wx.PrintDialogData, page_setup_name: Optional[str] = None) -> None:
        """
        Applies paper/orientation values from optional PageSetupDialog metadata.
        """
        if not isinstance(page_setup_name, str) or page_setup_name not in self.widgets:
            return
        page_object = self.get_object(page_setup_name)
        if page_object.type != "PageSetupDialog" or not isinstance(page_object.data, dict):
            return

        data = page_object.data
        native = print_data.GetPrintData()
        if hasattr(native, "SetPaperId"):
            native.SetPaperId(int(data.get("paperid", int(wx.PAPER_A4))))
        if hasattr(native, "SetOrientation"):
            orientation_flag = wx.LANDSCAPE if str(data.get("orientation", "portrait")).lower().startswith("land") else wx.PORTRAIT
            native.SetOrientation(orientation_flag)

    def _build_printout(self, printout_name: str) -> _SimpleTextPrintout:
        """
        Creates runtime wx.Printout from a predefined Printout object.
        """
        object_entry = self.get_object(printout_name)
        if object_entry.type != "Printout":
            self.internal_die(printout_name, "Not a printout object.")
        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        title = str(data.get("title") or object_entry.title or "Print")
        text = str(data.get("text") or "")
        lines_per_page = max(1, int(data.get("linesperpage", 60)))
        header = str(data.get("header") or "")
        footer = str(data.get("footer") or "Page {page}")
        show_date = 1 if int(data.get("showdate", 1)) else 0
        date_format = str(data.get("dateformat") or "%Y-%m-%d")
        return _SimpleTextPrintout(title, text, lines_per_page, header, footer, show_date, date_format)

    def show_print_preview(
        self,
        Printout: str,
        PrintDialog: Optional[str] = None,
        PageSetup: Optional[str] = None,
        Title: Optional[str] = None,
    ) -> Optional[wx.Frame]:
        """
        Opens print preview for a predefined printout.
        """
        print_dialog_data = self._build_print_dialog_data(PrintDialog)
        self._apply_pagesetup_to_print_dialog_data(print_dialog_data, PageSetup)

        preview = wx.PrintPreview(
            self._build_printout(Printout),
            self._build_printout(Printout),
            print_dialog_data,
        )
        if not preview.IsOk():
            self.show_error(Printout, "Print preview creation failed.")
            return None

        frame_title = str(Title or f"Print Preview - {Printout}")
        frame = wx.PreviewFrame(preview, self.ref if isinstance(self.ref, wx.Window) else None, frame_title)
        frame.Initialize()
        frame.Centre(wx.BOTH)
        frame.Show(True)
        return frame

    def print_document(
        self,
        Printout: str,
        PrintDialog: Optional[str] = None,
        PageSetup: Optional[str] = None,
        Prompt: int = 1,
    ) -> int:
        """
        Prints a predefined printout through wx.Printer.
        """
        print_dialog_data = self._build_print_dialog_data(PrintDialog)
        self._apply_pagesetup_to_print_dialog_data(print_dialog_data, PageSetup)

        printer = wx.Printer(print_dialog_data)
        ok = printer.Print(
            self.ref if isinstance(self.ref, wx.Window) else None,
            self._build_printout(Printout),
            bool(int(Prompt)),
        )
        if not ok:
            return 0

        if isinstance(PrintDialog, str) and PrintDialog in self.widgets:
            dialog_object = self.get_object(PrintDialog)
            if dialog_object.type == "PrintDialog" and isinstance(dialog_object.data, dict):
                selected_data = printer.GetPrintDialogData()
                dialog_object.data.update(
                    {
                        "minpage": selected_data.GetMinPage() if hasattr(selected_data, "GetMinPage") else 1,
                        "maxpage": selected_data.GetMaxPage() if hasattr(selected_data, "GetMaxPage") else 1,
                        "frompage": selected_data.GetFromPage() if hasattr(selected_data, "GetFromPage") else 1,
                        "topage": selected_data.GetToPage() if hasattr(selected_data, "GetToPage") else 1,
                        "allpages": 1 if bool(selected_data.GetAllPages()) else 0,
                        "selection": 1 if bool(selected_data.GetSelection()) else 0,
                        "printtofile": 1 if bool(selected_data.GetPrintToFile()) else 0,
                        "copies": selected_data.GetNoCopies() if hasattr(selected_data, "GetNoCopies") else 1,
                    }
                )
        return 1

    def add_print_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        MinPage: int = 1,
        MaxPage: int = 1,
        FromPage: int = 1,
        ToPage: int = 1,
        AllPages: int = 1,
        Selection: int = 0,
        PrintToFile: int = 0,
        Copies: int = 1,
        Modal: int = 1,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a print-dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the print-dialog object. Must be unique.

        Title : str | None, optional
            Optional dialog title.

        MinPage : int, optional
            Minimum page number.

        MaxPage : int, optional
            Maximum page number.

        FromPage : int, optional
            Start page number.

        ToPage : int, optional
            End page number.

        AllPages : int, optional
            All-pages selection flag (`0`/`1`).

        Selection : int, optional
            Selection-only flag (`0`/`1`).

        PrintToFile : int, optional
            Print-to-file flag (`0`/`1`).

        Copies : int, optional
            Number of copies.

        Modal : int, optional
            Modal metadata flag (`1` modal, `0` modeless compatibility).

        RFunc : Callable | None, optional
            Optional response callback.

        Returns
        -------

        None.

        Examples
        --------

        win.add_print_dialog(Name="print1", MinPage=1, MaxPage=10, FromPage=1, ToPage=2)
        """
        # normalize print-dialog parameters
        params = self._normalize(
            Name=Name,
            Title=Title,
            MinPage=MinPage,
            MaxPage=MaxPage,
            FromPage=FromPage,
            ToPage=ToPage,
            AllPages=AllPages,
            Selection=Selection,
            PrintToFile=PrintToFile,
            Copies=Copies,
            Modal=Modal,
            RFunc=RFunc,
        )

        # create and store print-dialog metadata
        object_entry = self._new_widget(**params)
        object_entry.type = "PrintDialog"
        object_entry.title = str(params.get("title") or "Print")
        object_entry.ref = None
        object_entry.data = {
            "title": object_entry.title,
            "minpage": max(1, int(params.get("minpage", 1))),
            "maxpage": max(1, int(params.get("maxpage", 1))),
            "frompage": max(1, int(params.get("frompage", 1))),
            "topage": max(1, int(params.get("topage", 1))),
            "allpages": 1 if int(params.get("allpages", 1)) else 0,
            "selection": 1 if int(params.get("selection", 0)) else 0,
            "printtofile": 1 if int(params.get("printtofile", 0)) else 0,
            "copies": max(1, int(params.get("copies", 1))),
            "modal": 1 if int(params.get("modal", 1)) else 0,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_print_dialog(self, Name: str) -> Optional[dict[str, Any]]:
        """
        Shows a predefined print dialog or a one-shot print dialog.

        Parameters
        ----------

        Name : str
            Predefined print-dialog name or one-shot title string.

        Returns
        -------

        dict[str, Any] | None:
            Selected print settings in modal mode, else `None`.

        Examples
        --------

        settings = win.show_print_dialog("print1")
        """
        # detect predefined or one-shot mode
        is_predefined = Name in self.widgets and self.widgets[Name].type == "PrintDialog"
        if is_predefined:
            object_entry = self.get_object(Name)
            data = object_entry.data if isinstance(object_entry.data, dict) else {}
            title = str(data.get("title") or object_entry.title or "Print")
            modal = 1 if int(data.get("modal", 1)) else 0
            response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None
        else:
            object_entry = None
            data = {
                "minpage": 1,
                "maxpage": 1,
                "frompage": 1,
                "topage": 1,
                "allpages": 1,
                "selection": 0,
                "printtofile": 0,
                "copies": 1,
            }
            title = str(Name or "Print")
            modal = 1
            response_function = None

        # build wx print dialog data from stored metadata
        print_data = wx.PrintDialogData()
        if hasattr(print_data, "SetMinPage"):
            print_data.SetMinPage(max(1, int(data.get("minpage", 1))))
        if hasattr(print_data, "SetMaxPage"):
            print_data.SetMaxPage(max(1, int(data.get("maxpage", 1))))
        if hasattr(print_data, "SetFromPage"):
            print_data.SetFromPage(max(1, int(data.get("frompage", 1))))
        if hasattr(print_data, "SetToPage"):
            print_data.SetToPage(max(1, int(data.get("topage", 1))))
        if hasattr(print_data, "SetAllPages"):
            print_data.SetAllPages(bool(int(data.get("allpages", 1))))
        if hasattr(print_data, "SetSelection"):
            print_data.SetSelection(bool(int(data.get("selection", 0))))
        if hasattr(print_data, "SetPrintToFile"):
            print_data.SetPrintToFile(bool(int(data.get("printtofile", 0))))
        if hasattr(print_data, "SetNoCopies"):
            print_data.SetNoCopies(max(1, int(data.get("copies", 1))))

        # create native print dialog
        dialog = wx.PrintDialog(self.ref if isinstance(self.ref, wx.Window) else None, print_data)
        if hasattr(dialog, "SetTitle"):
            dialog.SetTitle(title)

        # execute as modal (wx print dialogs are modal in common usage)
        result_payload: Optional[dict[str, Any]] = None
        if dialog.ShowModal() == wx.ID_OK:
            selected_data = dialog.GetPrintDialogData()
            all_pages = bool(selected_data.GetAllPages()) if hasattr(selected_data, "GetAllPages") else False
            selection_only = bool(selected_data.GetSelection()) if hasattr(selected_data, "GetSelection") else False
            print_to_file = bool(selected_data.GetPrintToFile()) if hasattr(selected_data, "GetPrintToFile") else False
            result_payload = {
                "minpage": selected_data.GetMinPage() if hasattr(selected_data, "GetMinPage") else 1,
                "maxpage": selected_data.GetMaxPage() if hasattr(selected_data, "GetMaxPage") else 1,
                "frompage": selected_data.GetFromPage() if hasattr(selected_data, "GetFromPage") else 1,
                "topage": selected_data.GetToPage() if hasattr(selected_data, "GetToPage") else 1,
                "allpages": 1 if all_pages else 0,
                "selection": 1 if selection_only else 0,
                "printtofile": 1 if print_to_file else 0,
                "copies": selected_data.GetNoCopies() if hasattr(selected_data, "GetNoCopies") else 1,
            }

            # persist resulting settings for predefined dialogs
            if is_predefined and object_entry is not None and isinstance(object_entry.data, dict):
                object_entry.data.update(result_payload)
        dialog.Destroy()

        # callback support follows existing dialog behavior
        if callable(response_function):
            response_function(None, result_payload)
            return None
        return result_payload if modal else None

    def add_pagesetup_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        PaperId: int = int(wx.PAPER_A4),
        Orientation: str = "portrait",
        MarginTopLeft: Optional[list[int] | tuple[int, int]] = None,
        MarginBottomRight: Optional[list[int] | tuple[int, int]] = None,
        Modal: int = 1,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a page-setup dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the page-setup dialog object. Must be unique.

        Title : str | None, optional
            Optional dialog title.

        PaperId : int, optional
            wx paper id value.

        Orientation : str, optional
            Page orientation (`portrait` or `landscape`).

        MarginTopLeft : list[int] | tuple[int, int] | None, optional
            Top-left page margin `[x, y]`.

        MarginBottomRight : list[int] | tuple[int, int] | None, optional
            Bottom-right page margin `[x, y]`.

        Modal : int, optional
            Modal metadata flag (`1` modal, `0` modeless compatibility).

        RFunc : Callable | None, optional
            Optional response callback.

        Returns
        -------

        None.

        Examples
        --------

        win.add_pagesetup_dialog(Name="pset1", Orientation="landscape")
        """
        # normalize page-setup parameters
        params = self._normalize(
            Name=Name,
            Title=Title,
            PaperId=PaperId,
            Orientation=Orientation,
            MarginTopLeft=MarginTopLeft,
            MarginBottomRight=MarginBottomRight,
            Modal=Modal,
            RFunc=RFunc,
        )

        # sanitize margins and orientation
        margin_top_left = params.get("margintopleft")
        if isinstance(margin_top_left, (list, tuple)) and len(margin_top_left) >= 2:
            top_left = [int(margin_top_left[0]), int(margin_top_left[1])]
        else:
            top_left = [10, 10]

        margin_bottom_right = params.get("marginbottomright")
        if isinstance(margin_bottom_right, (list, tuple)) and len(margin_bottom_right) >= 2:
            bottom_right = [int(margin_bottom_right[0]), int(margin_bottom_right[1])]
        else:
            bottom_right = [10, 10]

        orientation = str(params.get("orientation") or "portrait").lower()
        orientation = "landscape" if orientation.startswith("land") else "portrait"

        # create and store page-setup metadata
        object_entry = self._new_widget(**params)
        object_entry.type = "PageSetupDialog"
        object_entry.title = str(params.get("title") or "Page Setup")
        object_entry.ref = None
        object_entry.data = {
            "title": object_entry.title,
            "paperid": int(params.get("paperid", int(wx.PAPER_A4))),
            "orientation": orientation,
            "margintopleft": top_left,
            "marginbottomright": bottom_right,
            "modal": 1 if int(params.get("modal", 1)) else 0,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_pagesetup_dialog(self, Name: str) -> Optional[dict[str, Any]]:
        """
        Shows a predefined page-setup dialog or a one-shot page-setup dialog.

        Parameters
        ----------

        Name : str
            Predefined page-setup dialog name or one-shot title string.

        Returns
        -------

        dict[str, Any] | None:
            Selected page setup in modal mode, else `None`.

        Examples
        --------

        setup = win.show_pagesetup_dialog("pset1")
        """
        # detect predefined or one-shot mode
        is_predefined = Name in self.widgets and self.widgets[Name].type == "PageSetupDialog"
        if is_predefined:
            object_entry = self.get_object(Name)
            data = object_entry.data if isinstance(object_entry.data, dict) else {}
            title = str(data.get("title") or object_entry.title or "Page Setup")
            modal = 1 if int(data.get("modal", 1)) else 0
            response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None
        else:
            object_entry = None
            data = {
                "paperid": int(wx.PAPER_A4),
                "orientation": "portrait",
                "margintopleft": [10, 10],
                "marginbottomright": [10, 10],
            }
            title = str(Name or "Page Setup")
            modal = 1
            response_function = None

        # build page setup data object from stored metadata
        page_setup_data = wx.PageSetupDialogData()
        print_data = page_setup_data.GetPrintData()
        if hasattr(print_data, "SetPaperId"):
            print_data.SetPaperId(int(data.get("paperid", int(wx.PAPER_A4))))
        if hasattr(print_data, "SetOrientation"):
            orientation_flag = wx.LANDSCAPE if str(data.get("orientation", "portrait")).lower().startswith("land") else wx.PORTRAIT
            print_data.SetOrientation(orientation_flag)

        top_left = data.get("margintopleft", [10, 10])
        if isinstance(top_left, (list, tuple)) and len(top_left) >= 2:
            page_setup_data.SetMarginTopLeft(wx.Point(int(top_left[0]), int(top_left[1])))
        bottom_right = data.get("marginbottomright", [10, 10])
        if isinstance(bottom_right, (list, tuple)) and len(bottom_right) >= 2:
            page_setup_data.SetMarginBottomRight(wx.Point(int(bottom_right[0]), int(bottom_right[1])))

        # create native page setup dialog
        dialog = wx.PageSetupDialog(self.ref if isinstance(self.ref, wx.Window) else None, page_setup_data)
        if hasattr(dialog, "SetTitle"):
            dialog.SetTitle(title)

        # show dialog modally and collect resulting values
        result_payload: Optional[dict[str, Any]] = None
        if dialog.ShowModal() == wx.ID_OK:
            selected_data = dialog.GetPageSetupData()
            selected_print_data = selected_data.GetPrintData()
            margin_top_left = selected_data.GetMarginTopLeft()
            margin_bottom_right = selected_data.GetMarginBottomRight()
            orientation_value = "landscape" if selected_print_data.GetOrientation() == wx.LANDSCAPE else "portrait"

            result_payload = {
                "paperid": selected_print_data.GetPaperId(),
                "orientation": orientation_value,
                "margintopleft": [int(margin_top_left.x), int(margin_top_left.y)],
                "marginbottomright": [int(margin_bottom_right.x), int(margin_bottom_right.y)],
            }

            # persist resulting setup for predefined dialogs
            if is_predefined and object_entry is not None and isinstance(object_entry.data, dict):
                object_entry.data.update(result_payload)
        dialog.Destroy()

        # callback support follows existing dialog behavior
        if callable(response_function):
            response_function(None, result_payload)
            return None
        return result_payload if modal else None

    def show_msg_dialog(
        self,
        Name: str,
        MessageText1: Optional[str] = None,
        MessageText2: Optional[str] = None,
    ) -> Optional[int]:
        """
        Shows a predefined message dialog or a one-shot dialog.

        Modes
        -----
        - Predefined: `show_msg_dialog(name, msg1, [msg2])`
        - One-shot: `show_msg_dialog(dtype, mtype, message)`

        Returns
        -------

        int | None:
            Modal return code, or `None` for modeless mode.
        """
        is_predefined = Name in self.widgets and self.widgets[Name].type == "MessageDialog"

        if is_predefined:
            dialog_object = self.get_object(Name)
            data = dialog_object.data if isinstance(dialog_object.data, dict) else {}
            modal = 1 if int(data.get("modal", 1)) else 0
            dialog_type = str(data.get("dialogtype") or "ok").lower()
            message_type = str(data.get("messagetype") or "info").lower()
            icon = data.get("icon")
            response_function = data.get("responsefunction")
            message_primary = str(MessageText1 or "")
            message_secondary = str(MessageText2 or "")
        else:
            modal = 1
            dialog_type = str(Name or "ok").lower()
            message_type = str(MessageText1 or "info").lower()
            icon = None
            response_function = None
            message_primary = str(MessageText2 or "")
            message_secondary = ""

        message_primary = re.sub(r"<[^>]+>", "", message_primary)
        message_secondary = re.sub(r"<[^>]+>", "", message_secondary)

        dialog_type_map = {
            "ok": wx.OK,
            "yesno": wx.YES_NO,
            "okcancel": wx.OK | wx.CANCEL,
            "yesnocancel": wx.YES_NO | wx.CANCEL,
        }
        message_type_map = {
            "info": wx.ICON_INFORMATION,
            "warning": wx.ICON_WARNING,
            "error": wx.ICON_ERROR,
            "question": wx.ICON_QUESTION,
        }

        style = dialog_type_map.get(dialog_type, wx.OK)
        style |= message_type_map.get(message_type, wx.ICON_INFORMATION)
        style |= wx.CENTRE

        title = message_type.capitalize()
        parent = self.ref if isinstance(self.ref, wx.Window) else None

        dialog = wx.MessageDialog(parent, message_primary, title, style)
        if message_secondary and hasattr(dialog, "SetExtendedMessage"):
            dialog.SetExtendedMessage(message_secondary)

        if isinstance(icon, str) and icon:
            try:
                if wx.FileExists(icon):
                    custom_icon = wx.Icon(icon, wx.BITMAP_TYPE_ANY)
                    if custom_icon.IsOk():
                        dialog.SetIcon(custom_icon)
            except Exception:
                pass

        if modal:
            result = int(dialog.ShowModal())
            dialog.Destroy()
            return result

        if callable(response_function):
            def _on_dialog_response(event: wx.CommandEvent) -> None:
                try:
                    response_function(dialog, event.GetId())
                finally:
                    dialog.Destroy()

            dialog.Bind(wx.EVT_BUTTON, _on_dialog_response)

        dialog.Show()
        return None

    def show_message(self, ObjectOrMsg: Any, Msg: Optional[str] = None, Dialog: int = 0) -> None:
        """
        Prints an informational message and optionally shows it in a dialog.

        Parameters
        ----------

        ObjectOrMsg : Any
            Either a widget object/context or the message text.

        Msg : str | None, optional
            Message text when context is passed in `ObjectOrMsg`.

        Dialog : int, optional
            If non-zero, opens an information message dialog.
        """
        if Msg is None:
            context = None
            message_text = str(ObjectOrMsg)
        else:
            context = ObjectOrMsg
            message_text = str(Msg)

        if isinstance(context, WidgetEntry):
            print(f"[{self.name}->{context.name}][msg]: {message_text}")
        else:
            print(f"[{self.name}][msg]: {message_text}")

        if not int(Dialog):
            return

        parent: Optional[wx.Window] = self.ref if isinstance(self.ref, wx.Window) else None
        dialog = wx.MessageDialog(parent, message_text, "Information", wx.CENTRE | wx.OK | wx.ICON_INFORMATION)
        dialog.ShowModal()
        dialog.Destroy()

    def _build_wx_filter(self, filter_value: Any) -> str:
        """
        Converts a filter definition to a wx wildcard string.
        """
        if filter_value is None:
            return "*.*"

        if isinstance(filter_value, str):
            pattern = filter_value.strip()
            return pattern if pattern else "*.*"

        if isinstance(filter_value, (list, tuple)):
            if len(filter_value) >= 2:
                name = "" if filter_value[0] is None else str(filter_value[0]).strip()
                pattern = str(filter_value[1]).strip() if filter_value[1] is not None else ""
                if not pattern:
                    return "*.*"
                label = name if name else f"Files ({pattern})"
                return f"{label}|{pattern}"
            if len(filter_value) == 1 and filter_value[0] is not None:
                pattern = str(filter_value[0]).strip()
                return pattern if pattern else "*.*"

        return "*.*"

    def add_filechooser_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Action: str = "open",
        Frame: Optional[str] = None,
        File: Optional[str] = None,
        Filter: Optional[Any] = None,
        Folder: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a file chooser button widget with path display and browse action.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Action=Action,
            Frame=Frame,
            File=File,
            Filter=Filter,
            Folder=Folder,
            Size=Size,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "FileChooserButton"
        self.widgets[object_entry.name] = object_entry

        action = str(params.get("action") or "open").lower()
        title = str(params.get("title") or "Select file")
        filename = str(params.get("filename") or "")

        try:
            default_folder = wx.StandardPaths.Get().GetDocumentsDir()
        except Exception:
            default_folder = ""
        folder = str(params.get("folder") or default_folder)

        filter_value = params.get("filter")
        if isinstance(filter_value, str):
            normalized_filter: Any = [None, filter_value]
        elif isinstance(filter_value, (list, tuple)):
            normalized_filter = list(filter_value)
        else:
            normalized_filter = []

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        panel = wx.Panel(provisional_parent, wx.ID_ANY, pos=(0, 0), size=wx.DefaultSize)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        text_ctrl = wx.TextCtrl(panel, wx.ID_ANY, filename, style=wx.TE_READONLY)
        browse_button = wx.Button(panel, wx.ID_ANY, "...", size=(self._scale(30), wx.DefaultCoord))
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(browse_button, 0, wx.ALIGN_CENTER_VERTICAL)
        panel.SetSizer(sizer)

        object_entry.title = title
        object_entry.ref = panel
        object_entry.data = {
            "text": text_ctrl,
            "button": browse_button,
            "action": action,
            "title": title,
            "filename": filename,
            "folder": folder,
            "filter": normalized_filter,
        }

        def _invoke_user_callback(path: Optional[str]) -> None:
            callback_spec = params.get("function")
            if isinstance(callback_spec, (list, tuple)) and len(callback_spec) > 0 and callable(callback_spec[0]):
                callback = callback_spec[0]
                payload = callback_spec[1] if len(callback_spec) > 1 else None
                try:
                    callback(panel, path, payload)
                except TypeError:
                    callback(panel, path)
            elif callable(callback_spec):
                try:
                    callback_spec(panel, path)
                except TypeError:
                    callback_spec(path)

        def _on_browse_click(_event: wx.Event) -> None:
            current_text = text_ctrl.GetValue()
            default_path = current_text if current_text else folder
            selected_path = self.show_filechooser_dialog(action, default_path, normalized_filter)
            if isinstance(selected_path, str) and selected_path:
                text_ctrl.SetValue(selected_path)
                if isinstance(object_entry.data, dict):
                    object_entry.data["filename"] = selected_path
            _invoke_user_callback(selected_path)

        browse_button.Bind(wx.EVT_BUTTON, _on_browse_click)

        custom_signal = params.get("signal")
        callback_spec = params.get("function")
        if callable(custom_signal) and callback_spec is not None:
            def _signal_wrapper(event: wx.Event) -> None:
                _invoke_user_callback(text_ctrl.GetValue())
                event.Skip()

            browse_button.Bind(custom_signal, _signal_wrapper)

        common_params = dict(params)
        common_params.pop("function", None)
        common_params.pop("signal", None)
        self._set_commons(object_entry.name, **common_params)
        self._add_to_container(object_entry.name)

    def add_filechooser_dialog(
        self,
        Name: str,
        Action: str = "open",
        Title: Optional[str] = None,
        FName: Optional[str] = None,
        Filter: Optional[Any] = None,
        Folder: Optional[str] = None,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a file chooser dialog definition for later display.
        """
        params = self._normalize(
            Name=Name,
            Action=Action,
            Title=Title,
            Filename=FName,
            Filter=Filter,
            Folder=Folder,
            RFunc=RFunc,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "FileChooserDialog"
        action = str(params.get("action") or "open").lower()
        default_title = "Save file" if action == "save" else "Open file"

        try:
            default_folder = wx.StandardPaths.Get().GetDocumentsDir()
        except Exception:
            default_folder = ""

        filter_value = params.get("filter")
        if isinstance(filter_value, str):
            normalized_filter: Any = [None, filter_value]
        elif isinstance(filter_value, (list, tuple)):
            normalized_filter = list(filter_value)
        else:
            normalized_filter = []

        object_entry.title = str(params.get("title") or default_title)
        object_entry.ref = None
        object_entry.data = {
            "action": action,
            "title": object_entry.title,
            "filename": str(params.get("filename") or ""),
            "folder": str(params.get("folder") or default_folder),
            "filter": normalized_filter,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def add_dirpicker_ctrl(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Folder: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a directory picker control (DirPickerCtrl).
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Folder=Folder,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "DirPickerCtrl"
        self.widgets[object_entry.name] = object_entry

        try:
            default_folder = wx.StandardPaths.Get().GetDocumentsDir()
        except Exception:
            default_folder = ""

        title = str(params.get("title") or "Select folder")
        folder = str(params.get("folder") or default_folder)

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        picker = wx.DirPickerCtrl(
            provisional_parent,
            wx.ID_ANY,
            path=folder,
            message=title,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.DIRP_DEFAULT_STYLE | wx.DIRP_USE_TEXTCTRL,
        )

        object_entry.title = title
        object_entry.ref = picker
        object_entry.data = {
            "title": title,
            "folder": folder,
        }

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_dir_picker(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Folder: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for add_dirpicker_ctrl.
        """
        self.add_dirpicker_ctrl(
            Name=Name,
            Position=Position,
            Title=Title,
            Folder=Folder,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def add_datepicker_ctrl(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Date: Optional[str] = None,
        Title: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a date picker control (DatePickerCtrl).
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Date=Date,
            Title=Title,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "DatePickerCtrl"
        self.widgets[object_entry.name] = object_entry

        initial_date = datetime.date.today()
        raw_date = str(params.get("date") or "").strip()
        if raw_date:
            for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                try:
                    initial_date = datetime.datetime.strptime(raw_date, date_format).date()
                    break
                except Exception:
                    continue

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        picker = wx.adv.DatePickerCtrl(
            provisional_parent,
            wx.ID_ANY,
            dt=wx.DateTime.FromDMY(initial_date.day, initial_date.month - 1, initial_date.year),
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY,
        )

        object_entry.title = str(params.get("title") or "Select date")
        object_entry.ref = picker
        object_entry.data = {
            "title": object_entry.title,
            "date": initial_date.strftime("%Y-%m-%d"),
        }

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_date_picker(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Date: Optional[str] = None,
        Title: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for add_datepicker_ctrl.
        """
        self.add_datepicker_ctrl(
            Name=Name,
            Position=Position,
            Date=Date,
            Title=Title,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def add_timepicker_ctrl(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Time: Optional[str] = None,
        Title: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a time picker control (TimePickerCtrl).
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Time=Time,
            Title=Title,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "TimePickerCtrl"
        self.widgets[object_entry.name] = object_entry

        now = datetime.datetime.now()
        initial_time = datetime.time(now.hour, now.minute, now.second)
        raw_time = str(params.get("time") or "").strip()
        if raw_time:
            for time_format in ("%H:%M:%S", "%H:%M"):
                try:
                    initial_time = datetime.datetime.strptime(raw_time, time_format).time()
                    break
                except Exception:
                    continue

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        base_dt = wx.DateTime.Now()
        base_dt.SetHour(initial_time.hour)
        base_dt.SetMinute(initial_time.minute)
        base_dt.SetSecond(initial_time.second)
        picker = wx.adv.TimePickerCtrl(
            provisional_parent,
            wx.ID_ANY,
            dt=base_dt,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.adv.TP_DEFAULT,
        )

        object_entry.title = str(params.get("title") or "Select time")
        object_entry.ref = picker
        object_entry.data = {
            "title": object_entry.title,
            "time": f"{initial_time.hour:02d}:{initial_time.minute:02d}:{initial_time.second:02d}",
        }

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_time_picker(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Time: Optional[str] = None,
        Title: Optional[str] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for add_timepicker_ctrl.
        """
        self.add_timepicker_ctrl(
            Name=Name,
            Position=Position,
            Time=Time,
            Title=Title,
            Size=Size,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def show_filechooser_dialog(
        self,
        Name: str,
        FileFolder: Optional[str] = None,
        Filter: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Shows a predefined file chooser dialog or a one-shot chooser.
        """
        is_predefined = Name in self.widgets and self.widgets[Name].type == "FileChooserDialog"

        response_function: Optional[Callable[..., Any]] = None
        if is_predefined:
            obj = self.get_object(Name)
            data = obj.data if isinstance(obj.data, dict) else {}
            action = str(data.get("action") or "open").lower()
            title = str(data.get("title") or ("Save file" if action == "save" else "Open file"))
            filter_value = data.get("filter") if Filter is None else Filter
            response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None
            default_path = str(FileFolder) if isinstance(FileFolder, str) and FileFolder else str(data.get("filename") or data.get("folder") or "")
        else:
            action = str(Name or "open").lower()
            title = "Save file" if action == "save" else "Open file"
            filter_value = Filter
            default_path = str(FileFolder) if isinstance(FileFolder, str) else ""

        if action in ("select-folder", "select_folder", "folder"):
            dialog = wx.DirDialog(
                self.ref if isinstance(self.ref, wx.Window) else None,
                title,
                defaultPath=default_path,
                style=wx.DD_DEFAULT_STYLE,
            )
            selected_path: Optional[str] = None
            if dialog.ShowModal() == wx.ID_OK:
                selected_path = dialog.GetPath()
            dialog.Destroy()
            if callable(response_function):
                response_function(None, selected_path)
                return None
            return selected_path

        style = wx.FD_DEFAULT_STYLE
        if action == "save":
            style |= wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        else:
            style |= wx.FD_OPEN

        dialog = wx.FileDialog(
            self.ref if isinstance(self.ref, wx.Window) else None,
            title,
            wildcard=self._build_wx_filter(filter_value),
            style=style,
        )

        if default_path:
            try:
                if wx.DirExists(default_path):
                    dialog.SetDirectory(default_path)
                elif wx.FileExists(default_path):
                    dialog.SetPath(default_path)
                else:
                    dialog.SetDirectory(default_path)
            except Exception:
                pass

        selected_path: Optional[str] = None
        if dialog.ShowModal() == wx.ID_OK:
            selected_path = dialog.GetPath()
        dialog.Destroy()

        if callable(response_function):
            response_function(None, selected_path)
            return None
        return selected_path

    def add_font_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Action: Optional[str] = None,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a button that opens a font chooser dialog.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Action=Action,
            Frame=Frame,
            Font=Font,
            Size=Size,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "FontButton"
        self.widgets[object_entry.name] = object_entry

        title = str(params.get("title") or "Choose font")
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        button = wx.Button(provisional_parent, wx.ID_ANY, title, pos=(0, 0), size=wx.DefaultSize)

        font_obj: Optional[wx.Font] = None
        font_spec = params.get("font")
        if isinstance(font_spec, (list, tuple)) and len(font_spec) >= 2:
            family = str(font_spec[0])
            size_value = int(font_spec[1])
            weight_label = str(font_spec[2]).lower() if len(font_spec) > 2 and font_spec[2] is not None else "normal"
            weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
            candidate = wx.Font(size_value, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, weight, False, family)
            if candidate.IsOk():
                font_obj = candidate
                button.SetLabel(f"{candidate.GetFaceName()} {candidate.GetPointSize()}")

        object_entry.ref = button
        object_entry.title = title
        object_entry.data = {
            "font_obj": font_obj,
            "action": params.get("action"),
        }

        def _invoke_user_callback(selected_font: Optional[wx.Font]) -> None:
            callback_spec = params.get("function")
            if isinstance(callback_spec, (list, tuple)) and len(callback_spec) > 0 and callable(callback_spec[0]):
                callback = callback_spec[0]
                payload = callback_spec[1] if len(callback_spec) > 1 else None
                try:
                    callback(button, selected_font, payload)
                except TypeError:
                    callback(button, selected_font)
            elif callable(callback_spec):
                try:
                    callback_spec(button, selected_font)
                except TypeError:
                    callback_spec(selected_font)

        def _on_font_pick(_event: wx.Event) -> None:
            font_data = wx.FontData()
            current_font = object_entry.data.get("font_obj") if isinstance(object_entry.data, dict) else None
            if isinstance(current_font, wx.Font) and current_font.IsOk():
                font_data.SetInitialFont(current_font)

            dialog = wx.FontDialog(button, font_data)
            if dialog.ShowModal() == wx.ID_OK:
                result_data = dialog.GetFontData()
                selected_font = result_data.GetChosenFont() if result_data is not None else None
                if isinstance(selected_font, wx.Font) and selected_font.IsOk() and isinstance(object_entry.data, dict):
                    object_entry.data["font_obj"] = selected_font
                    button.SetLabel(f"{selected_font.GetFaceName()} {selected_font.GetPointSize()}")
                _invoke_user_callback(selected_font)
            dialog.Destroy()

        button.Bind(wx.EVT_BUTTON, _on_font_pick)

        custom_signal = params.get("signal")
        callback_spec = params.get("function")
        if callable(custom_signal) and callback_spec is not None:
            def _signal_wrapper(event: wx.Event) -> None:
                current_font = object_entry.data.get("font_obj") if isinstance(object_entry.data, dict) else None
                _invoke_user_callback(current_font if isinstance(current_font, wx.Font) else None)
                event.Skip()

            button.Bind(custom_signal, _signal_wrapper)

        common_params = dict(params)
        common_params.pop("function", None)
        common_params.pop("signal", None)
        self._set_commons(object_entry.name, **common_params)
        self._add_to_container(object_entry.name)

    def add_fontselection_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Preview: Optional[str] = None,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a font-selection dialog definition for later display.
        """
        params = self._normalize(
            Name=Name,
            Title=Title,
            Font=Font,
            Preview=Preview,
            RFunc=RFunc,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "FontSelectionDialog"

        title_value = str(params.get("title") or "Choose font")
        preview_value = str(params.get("preview") or "AaBbYyZz")

        font_obj: Optional[wx.Font] = None
        font_spec = params.get("font")
        if isinstance(font_spec, (list, tuple)) and len(font_spec) >= 2:
            family = str(font_spec[0])
            size = int(font_spec[1])
            weight_label = str(font_spec[2]).lower() if len(font_spec) > 2 and font_spec[2] is not None else "normal"
            weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
            candidate = wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, weight, False, family)
            if candidate.IsOk():
                font_obj = candidate

        object_entry.title = title_value
        object_entry.ref = None
        object_entry.data = {
            "title": title_value,
            "preview": preview_value,
            "font_obj": font_obj,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_fontselection_dialog(
        self,
        Name: str,
        Size: Optional[int] = None,
        Weight: Optional[Any] = None,
    ) -> Optional[wx.Font]:
        """
        Shows a predefined font-selection dialog or a one-shot font chooser.

        Modes
        -----
        - Predefined: `show_fontselection_dialog(name)`
        - One-shot: `show_fontselection_dialog(family, size, weight)`
        """
        is_predefined = Name in self.widgets and self.widgets[Name].type == "FontSelectionDialog"

        response_function: Optional[Callable[..., Any]] = None
        if is_predefined:
            obj = self.get_object(Name)
            data = obj.data if isinstance(obj.data, dict) else {}
            title = str(data.get("title") or "Choose font")
            response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None
            current_font = data.get("font_obj") if isinstance(data.get("font_obj"), wx.Font) and data.get("font_obj").IsOk() else None
        else:
            title = "Choose font"
            family = str(Name or "Sans")
            point_size = int(Size) if Size is not None else 10
            if isinstance(Weight, str):
                weight_label = Weight.lower()
                wx_weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
            elif Weight is None:
                wx_weight = wx.FONTWEIGHT_NORMAL
            else:
                wx_weight = int(Weight)
            candidate = wx.Font(point_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx_weight, False, family)
            current_font = candidate if candidate.IsOk() else None

        font_data = wx.FontData()
        if isinstance(current_font, wx.Font) and current_font.IsOk():
            font_data.SetInitialFont(current_font)

        dialog = wx.FontDialog(self.ref if isinstance(self.ref, wx.Window) else None, font_data)
        dialog.SetTitle(title)

        selected_font: Optional[wx.Font] = None
        if dialog.ShowModal() == wx.ID_OK:
            result_data = dialog.GetFontData()
            selected_font = result_data.GetChosenFont() if result_data is not None else None
            if is_predefined and selected_font is not None and selected_font.IsOk():
                obj = self.get_object(Name)
                if not isinstance(obj.data, dict):
                    obj.data = {}
                obj.data["font_obj"] = selected_font
        dialog.Destroy()

        if callable(response_function):
            response_function(selected_font)
            return None
        return selected_font

    def add_colorselection_dialog(
        self,
        Name: str,
        Title: Optional[str] = None,
        Color: Optional[Any] = None,
        RFunc: Optional[Callable[..., Any]] = None,
    ) -> None:
        """
        Registers a color-selection dialog definition for later display.

        Parameters
        ----------

        Name : str
            Name of the color-selection dialog object. Must be unique.

        Title : str | None, optional
            Dialog title.

        Color : Any | None, optional
            Initial color as color name, `wx.Colour`, or `[r, g, b]` tuple/list.

        RFunc : Callable | None, optional
            Optional response callback.

        Returns
        -------

        None.

        Examples
        --------

        win.add_colorselection_dialog(Name="colorDialog", Title="Choose color")
        """
        # normalize API parameters and create a new object entry
        params = self._normalize(
            Name=Name,
            Title=Title,
            Color=Color,
            RFunc=RFunc,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "ColorSelectionDialog"

        # resolve optional initial color in supported formats
        color_value = params.get("color")
        initial_color: Optional[wx.Colour] = None
        if isinstance(color_value, wx.Colour):
            initial_color = color_value if color_value.IsOk() else None
        elif isinstance(color_value, str):
            candidate = wx.Colour(color_value)
            initial_color = candidate if candidate.IsOk() else None
        elif isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
            candidate = wx.Colour(int(color_value[0]), int(color_value[1]), int(color_value[2]))
            initial_color = candidate if candidate.IsOk() else None

        # store object metadata for deferred dialog creation
        title_value = str(params.get("title") or "Choose color")
        object_entry.title = title_value
        object_entry.ref = None
        object_entry.data = {
            "title": title_value,
            "color": initial_color,
            "responsefunction": params.get("responsefunction"),
        }
        self.widgets[object_entry.name] = object_entry

    def show_colorselection_dialog(
        self,
        Name: Any,
        Green: Optional[int] = None,
        Blue: Optional[int] = None,
    ) -> Optional[wx.Colour]:
        """
        Shows a predefined color-selection dialog or a one-shot color chooser.

        Parameters
        ----------

        Name : Any
            Predefined dialog name or one-shot red channel / color string.

        Green : int | None, optional
            One-shot green channel value.

        Blue : int | None, optional
            One-shot blue channel value.

        Returns
        -------

        wx.Colour | None:
            Selected color or `None` when cancelled / callback mode.

        Examples
        --------

        color = win.show_colorselection_dialog("colorDialog")
        """
        # detect whether a predefined dialog object exists
        is_predefined = isinstance(Name, str) and Name in self.widgets and self.widgets[Name].type == "ColorSelectionDialog"

        response_function: Optional[Callable[..., Any]] = None
        if is_predefined:
            # read predefined dialog metadata
            obj = self.get_object(str(Name))
            data = obj.data if isinstance(obj.data, dict) else {}
            title = str(data.get("title") or "Choose color")
            response_function = data.get("responsefunction") if callable(data.get("responsefunction")) else None
            current_color = data.get("color") if isinstance(data.get("color"), wx.Colour) and data.get("color").IsOk() else None
        else:
            # parse one-shot color arguments: string name, wx.Colour, or RGB triplet
            title = "Choose color"
            current_color: Optional[wx.Colour] = None
            if isinstance(Name, wx.Colour) and Name.IsOk():
                current_color = Name
            elif isinstance(Name, str):
                candidate = wx.Colour(Name)
                current_color = candidate if candidate.IsOk() else None
            elif Green is not None and Blue is not None:
                candidate = wx.Colour(int(Name), int(Green), int(Blue))
                current_color = candidate if candidate.IsOk() else None

        # initialize wx color data and optional current color
        colour_data = wx.ColourData()
        colour_data.SetChooseFull(True)
        if isinstance(current_color, wx.Colour) and current_color.IsOk():
            colour_data.SetColour(current_color)

        # create and run native color dialog
        dialog = wx.ColourDialog(self.ref if isinstance(self.ref, wx.Window) else None, colour_data)
        dialog.SetTitle(title)

        selected_color: Optional[wx.Colour] = None
        if dialog.ShowModal() == wx.ID_OK:
            result_data = dialog.GetColourData()
            selected_color = result_data.GetColour() if result_data is not None else None

            # persist selected color in predefined dialog object state
            if is_predefined and isinstance(selected_color, wx.Colour) and selected_color.IsOk():
                obj = self.get_object(str(Name))
                if not isinstance(obj.data, dict):
                    obj.data = {}
                obj.data["color"] = selected_color
        dialog.Destroy()

        # callback mode behaves like other selector dialogs
        if callable(response_function):
            response_function(selected_color)
            return None
        return selected_color

    def add_statusbar(
        self,
        Name: str,
        Position: Optional[list[int] | tuple[int, int]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Timeout: int = 0,
        Fields: int = 1,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates or configures a status bar attached to the main window.

        Parameters
        ----------

        Name : str
            Name of the statusbar object. Must be unique.

        Position : list[int] | tuple[int, int] | None, optional
            Optional position placeholder for API compatibility.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Frame : str | None, optional
            Optional frame name. Currently only main window is supported.

        Timeout : int, optional
            Default auto-remove timeout in seconds.

        Fields : int, optional
            Number of status fields. Defaults to 1.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_statusbar(Name="win_sbar", Fields=2, Timeout=5)
        """
        if self.ref is None:
            self.internal_die(Name, "No main window available!")

        if Frame is not None and Frame != self.name:
            self.internal_die(Name, "Statusbar is only supported on main window.")

        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Frame=Frame,
            Timeout=Timeout,
            Fields=Fields,
            Sensitive=Sensitive,
        )

        fields = max(1, int(params.get("fields", 1)))
        default_timeout = max(0, int(params.get("timeout", 0)))

        # wx allows one statusbar per frame; reuse existing one if present
        statusbar = self.ref.GetStatusBar()
        if not isinstance(statusbar, wx.StatusBar):
            statusbar = self.ref.CreateStatusBar(fields)

        statusbar.SetFieldsCount(fields)
        statusbar.SetStatusWidths([-1] * fields)

        object_entry = self.widgets.get(Name)
        if object_entry is None:
            object_entry = self._new_widget(**params)
            object_entry.type = "Statusbar"
            self.widgets[object_entry.name] = object_entry
        elif object_entry.type != "Statusbar":
            self.internal_die(Name, "Object exists and is not a statusbar.")

        object_entry.ref = statusbar
        if object_entry.width is None or object_entry.height is None:
            size_obj = statusbar.GetSize()
            object_entry.width = int(round(size_obj.GetWidth() / self.scalefactor)) if self.scalefactor != 0 else int(size_obj.GetWidth())
            object_entry.height = int(round(size_obj.GetHeight() / self.scalefactor)) if self.scalefactor != 0 else int(size_obj.GetHeight())

        object_entry.data = {
            "sbar_timeout": default_timeout,
            "sbar_stack": [],
            "fields": fields,
            "timers": {},
        }
        statusbar.Enable(bool(int(params.get("sensitive", 1))))

    def set_sb_text(
        self,
        Name: Optional[str] = None,
        Text: Optional[str] = None,
        Field: int = 0,
        Timeout: Optional[int] = None,
        MsgId: Optional[Any] = None,
    ) -> Any:
        """
        Sets/displays a status bar message and returns its message id.

        Parameters
        ----------

        Name : str | None, optional
            Statusbar name. Defaults to `win_sbar`.

        Text : str | None, optional
            New message text. If omitted, Name is treated as text.

        Field : int, optional
            Statusbar field index. Defaults to 0.

        Timeout : int | None, optional
            Auto-remove timeout in seconds. Uses statusbar default if None.

        MsgId : Any | None, optional
            Optional explicit message id.

        Returns
        -------

        Any:
            Message id of the inserted message.

        Examples
        --------

        msg_id = win.set_sb_text("win_sbar", "Ready", 0, 3)
        """
        # Perl compatibility: set_sb_text(text) uses default statusbar
        if Text is None and Name is not None:
            Text = str(Name)
            Name = "win_sbar"

        sb_name = Name if isinstance(Name, str) and Name else "win_sbar"
        if Text is None:
            self.internal_die(sb_name, "No status text defined!")

        object_entry = self.get_object(sb_name)
        if object_entry.type != "Statusbar" or object_entry.ref is None:
            self.internal_die(sb_name, "Not a valid statusbar object.")

        statusbar = object_entry.ref
        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        stack = data.get("sbar_stack") if isinstance(data.get("sbar_stack"), list) else []
        timers = data.get("timers") if isinstance(data.get("timers"), dict) else {}
        fields = int(data.get("fields", max(1, statusbar.GetFieldsCount())))

        field = int(Field)
        if field < 0:
            field = 0
        if field >= fields:
            field = fields - 1

        message = str(Text)
        message_id = MsgId if MsgId is not None else int(wx.NewIdRef())
        statusbar.SetStatusText(message, field)

        stack.append({
            "msg_id": message_id,
            "text": message,
            "field": field,
        })

        timeout_s = int(Timeout) if Timeout is not None else int(data.get("sbar_timeout", 0))
        if timeout_s > 0:
            timer = wx.CallLater(timeout_s * 1000, lambda: self.remove_sb_text(sb_name, field, message_id))
            timers[message_id] = timer

        data["sbar_stack"] = stack
        data["timers"] = timers
        data["fields"] = fields
        object_entry.data = data
        return message_id

    def remove_sb_text(
        self,
        Name: Optional[str] = None,
        Field: Optional[int] = None,
        MsgId: Optional[Any] = None,
    ) -> None:
        """
        Removes a status bar message by id or removes the last one.

        Parameters
        ----------

        Name : str | None, optional
            Statusbar name. Defaults to `win_sbar`.

        Field : int | None, optional
            Target field index. Defaults to 0.

        MsgId : Any | None, optional
            Message id to remove. If omitted, removes the last message.

        Returns
        -------

        None.

        Examples
        --------

        win.remove_sb_text("win_sbar", 0, msg_id)
        """
        sb_name = Name if isinstance(Name, str) and Name else "win_sbar"
        object_entry = self.get_object(sb_name)
        if object_entry.type != "Statusbar" or object_entry.ref is None:
            self.internal_die(sb_name, "Not a valid statusbar object.")

        statusbar = object_entry.ref
        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        stack = data.get("sbar_stack") if isinstance(data.get("sbar_stack"), list) else []
        timers = data.get("timers") if isinstance(data.get("timers"), dict) else {}
        fields = int(data.get("fields", max(1, statusbar.GetFieldsCount())))

        target_field = int(Field) if Field is not None else 0
        if target_field < 0:
            target_field = 0
        if target_field >= fields:
            target_field = fields - 1

        affected_fields: set[int] = set()

        if MsgId is not None:
            new_stack = []
            for item in stack:
                if item.get("msg_id") == MsgId:
                    item_field = int(item.get("field", target_field))
                    affected_fields.add(item_field)
                    timer = timers.pop(MsgId, None)
                    if isinstance(timer, wx.CallLater) and timer.IsRunning():
                        timer.Stop()
                else:
                    new_stack.append(item)
            stack = new_stack
        else:
            # remove latest message in requested field; fallback to global last
            index_to_remove: Optional[int] = None
            for idx in range(len(stack) - 1, -1, -1):
                item_field = int(stack[idx].get("field", 0))
                if item_field == target_field:
                    index_to_remove = idx
                    break
            if index_to_remove is None and len(stack) > 0:
                index_to_remove = len(stack) - 1

            if index_to_remove is not None:
                removed = stack.pop(index_to_remove)
                removed_id = removed.get("msg_id")
                removed_field = int(removed.get("field", target_field))
                affected_fields.add(removed_field)
                timer = timers.pop(removed_id, None)
                if isinstance(timer, wx.CallLater) and timer.IsRunning():
                    timer.Stop()

        if len(affected_fields) == 0:
            affected_fields.add(target_field)

        # redraw affected fields with latest stack message for each field
        for field_index in affected_fields:
            latest_text = ""
            for item in reversed(stack):
                if int(item.get("field", 0)) == field_index:
                    latest_text = str(item.get("text", ""))
                    break
            statusbar.SetStatusText(latest_text, field_index)

        data["sbar_stack"] = stack
        data["timers"] = timers
        data["fields"] = fields
        object_entry.data = data

    def clear_sb_stack(self, Name: Optional[str] = None) -> None:
        """
        Clears the complete message stack of a status bar.

        Parameters
        ----------

        Name : str | None, optional
            Statusbar name. Defaults to `win_sbar`.

        Returns
        -------

        None.

        Examples
        --------

        win.clear_sb_stack("win_sbar")
        """
        sb_name = Name if isinstance(Name, str) and Name else "win_sbar"
        object_entry = self.get_object(sb_name)
        if object_entry.type != "Statusbar" or object_entry.ref is None:
            self.internal_die(sb_name, "Not a valid statusbar object.")

        statusbar = object_entry.ref
        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        timers = data.get("timers") if isinstance(data.get("timers"), dict) else {}

        for timer in timers.values():
            if isinstance(timer, wx.CallLater) and timer.IsRunning():
                timer.Stop()

        field_count = max(1, statusbar.GetFieldsCount())
        for field in range(field_count):
            statusbar.SetStatusText("", field)

        data["sbar_stack"] = []
        data["timers"] = {}
        data["fields"] = field_count
        object_entry.data = data

    def _set_toolbar_tools(self, name: str, tools_data: list[Any]) -> None:
        """
        Rebuilds toolbar tools from compatibility list data.

        Parameters
        ----------

        name : str
            Toolbar object name.

        tools_data : list[Any]
            Tool descriptor list.
        """
        # resolve toolbar object and native reference
        object_entry = self.get_object(name)
        if object_entry.type != "ToolBar" or object_entry.ref is None:
            self.internal_die(name, "Not a toolbar object.")
        toolbar = object_entry.ref

        # clear existing tools before rebuilding toolbar content
        if hasattr(toolbar, "GetToolsCount") and hasattr(toolbar, "DeleteToolByPos"):
            while toolbar.GetToolsCount() > 0:
                toolbar.DeleteToolByPos(0)

        # normalize incoming descriptors to a consistent internal structure
        normalized_tools: list[dict[str, Any]] = []
        for item in tools_data:
            if isinstance(item, str) and item.strip().lower() in ("separator", "---"):
                toolbar.AddSeparator()
                normalized_tools.append({"kind": "separator"})
                continue

            label = ""
            icon_ref: Optional[str] = None
            kind = "normal"
            active = 0
            tooltip = ""

            if isinstance(item, dict):
                label = str(item.get("label") or item.get("title") or item.get("text") or "")
                icon_ref = str(item.get("icon")) if item.get("icon") is not None else None
                kind = str(item.get("kind") or item.get("type") or "normal").lower()
                active = 1 if int(item.get("active", 0)) else 0
                tooltip = str(item.get("tooltip") or "")
            elif isinstance(item, (list, tuple)):
                if len(item) > 0 and item[0] is not None:
                    label = str(item[0])
                if len(item) > 1 and item[1] is not None:
                    icon_ref = str(item[1])
                if len(item) > 2 and item[2] is not None:
                    kind = str(item[2]).lower()
                if len(item) > 3 and item[3] is not None:
                    active = 1 if int(item[3]) else 0
                if len(item) > 4 and item[4] is not None:
                    tooltip = str(item[4])
            else:
                label = str(item)

            if kind in ("separator", "sep"):
                toolbar.AddSeparator()
                normalized_tools.append({"kind": "separator"})
                continue

            # resolve bitmap from path or stock art-id compatible name
            bitmap = wx.ArtProvider.GetBitmap(wx.ART_MISSING_IMAGE, wx.ART_TOOLBAR, wx.Size(16, 16))
            if isinstance(icon_ref, str) and icon_ref:
                if wx.FileExists(icon_ref):
                    icon_bitmap = wx.Bitmap(icon_ref, wx.BITMAP_TYPE_ANY)
                    if icon_bitmap.IsOk():
                        bitmap = icon_bitmap
                else:
                    art_id = self._resolve_art_id(icon_ref)
                    icon_bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_TOOLBAR, wx.Size(16, 16))
                    if icon_bitmap.IsOk():
                        bitmap = icon_bitmap

            # map generic kind value to wx toolbar item kind
            if kind in ("check", "toggle"):
                wx_kind = wx.ITEM_CHECK
                normalized_kind = "check"
            elif kind == "radio":
                wx_kind = wx.ITEM_RADIO
                normalized_kind = "radio"
            else:
                wx_kind = wx.ITEM_NORMAL
                normalized_kind = "normal"

            # add the tool and keep normalized metadata in object data map
            tool_id = int(wx.NewIdRef())
            toolbar.AddTool(tool_id, label, bitmap, shortHelp=tooltip, kind=wx_kind)
            if wx_kind in (wx.ITEM_CHECK, wx.ITEM_RADIO):
                toolbar.ToggleTool(tool_id, bool(active))
            normalized_tools.append(
                {
                    "id": tool_id,
                    "label": label,
                    "icon": icon_ref,
                    "kind": normalized_kind,
                    "active": active,
                    "tooltip": tooltip,
                }
            )

        # finalize toolbar rendering and update object metadata
        toolbar.Realize()
        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        data["tools"] = normalized_tools
        if data.get("lasttool") is None and len(normalized_tools) > 0:
            first_tool = next((tool for tool in normalized_tools if isinstance(tool, dict) and "id" in tool), None)
            data["lasttool"] = first_tool.get("id") if isinstance(first_tool, dict) else None
        object_entry.data = data

    def add_toolbar(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Orient: str = "horizontal",
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a toolbar widget and optional initial tool set.

        Parameters
        ----------

        Name : str
            Name of the toolbar object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Data : list[Any] | tuple[Any, ...] | None, optional
            Optional initial tool descriptors.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Orient : str, optional
            Toolbar orientation (`horizontal` or `vertical`).

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_toolbar(Name="tb1", Position=[0, 0], Data=[["Open", "gtk-open"], ["Save", "gtk-save"]])
        """
        # normalize toolbar parameters and create object entry
        params = self._normalize(
            Name=Name,
            Position=Position,
            Data=Data,
            Size=Size,
            Orient=Orient,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "ToolBar"
        self.widgets[object_entry.name] = object_entry

        # map orientation to native toolbar style
        orientation = str(params.get("orientation") or "horizontal").lower()
        orientation = "vertical" if orientation == "vertical" else "horizontal"
        style = wx.TB_VERTICAL if orientation == "vertical" else wx.TB_HORIZONTAL
        style |= wx.TB_FLAT | wx.TB_NODIVIDER

        # create native toolbar with provisional parent and deferred placement
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        toolbar = wx.ToolBar(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        # store reference and toolbar metadata
        object_entry.ref = toolbar
        object_entry.data = {
            "orientation": orientation,
            "tools": [],
            "lasttool": None,
        }

        # initialize toolbar content from optional data list
        source_tools = params.get("data")
        if isinstance(source_tools, (list, tuple)):
            self._set_toolbar_tools(object_entry.name, list(source_tools))
        else:
            toolbar.Realize()

        # keep active tool metadata in sync on toolbar events
        def _on_toolbar_tool(event: wx.CommandEvent, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            if not isinstance(entry.data, dict):
                return
            tool_id = int(event.GetId())
            entry.data["lasttool"] = tool_id
            tools = entry.data.get("tools") if isinstance(entry.data.get("tools"), list) else []
            for tool in tools:
                if isinstance(tool, dict) and int(tool.get("id", -1)) == tool_id and entry.ref is not None and hasattr(entry.ref, "GetToolState"):
                    kind = str(tool.get("kind", "normal"))
                    if kind in ("check", "toggle", "radio"):
                        tool["active"] = 1 if bool(entry.ref.GetToolState(tool_id)) else 0
                    break
            event.Skip()

        toolbar.Bind(wx.EVT_TOOL, _on_toolbar_tool)

        # apply shared setup and place toolbar in target container
        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_menu_bar(
        self,
        Name: str,
        Position: Optional[list[int] | tuple[int, int]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
    ) -> None:
        """
        Creates and attaches a menu bar to the main window.

        Parameters
        ----------

        Name : str
            Name of the menubar object. Must be unique.

        Position : list[int] | tuple[int, int] | None, optional
            Optional position placeholder for API compatibility.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled size placeholder for API compatibility.

        Returns
        -------

        None.

        Examples
        --------

        win.add_menu_bar(Name="menubar1")
        """
        if self.ref is None:
            self.internal_die(Name, "No main window available!")

        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
        )

        object_entry = self.widgets.get(Name)
        if object_entry is not None and object_entry.type != "MenuBar":
            self.internal_die(Name, "Object exists and is not a menubar.")

        menubar = wx.MenuBar()
        self.ref.SetMenuBar(menubar)

        if object_entry is None:
            object_entry = self._new_widget(**params)
            object_entry.type = "MenuBar"
            self.widgets[object_entry.name] = object_entry

        object_entry.ref = menubar
        object_entry.data = {
            "menus": [],
        }

    def add_menu(
        self,
        Name: str,
        Menubar: str,
        Title: str,
        Justify: str = "left",
        Sensitive: int = 1,
    ) -> None:
        """
        Creates and registers a dropdown menu on a menu bar.

        Parameters
        ----------

        Name : str
            Name of the menu object. Must be unique.

        Menubar : str
            Name of the menu bar object.

        Title : str
            Menu title text.

        Justify : str, optional
            Menu alignment hint (`left` or `right`).

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_menu(Name="menu_file", Menubar="menubar1", Title="_File")
        """
        mbar_object = self.get_object(Menubar)
        if mbar_object.type != "MenuBar" or mbar_object.ref is None:
            self.internal_die(Name, f"Menubar \"{Menubar}\" not found.")

        params = self._normalize(
            Name=Name,
            Menubar=Menubar,
            Title=Title,
            Justify=Justify,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "Menu"
        self.widgets[object_entry.name] = object_entry

        menu = wx.Menu()
        menubar = mbar_object.ref

        # convert underscore mnemonic markers to wx style (&)
        raw_title = str(object_entry.title or "")
        if self.is_underlined(raw_title):
            menu_label = raw_title.replace("__", "\0")
            menu_label = menu_label.replace("_", "&")
            menu_label = menu_label.replace("\0", "_")
        else:
            menu_label = raw_title

        menu_index = menubar.GetMenuCount()
        menubar.Append(menu, menu_label)
        menubar.EnableTop(menu_index, bool(Sensitive))

        object_entry.ref = menu
        object_entry.data = {
            "menubar": Menubar,
            "title_index": menu_index,
            "justify": str(Justify).lower(),
        }

        mbar_data = mbar_object.data if isinstance(mbar_object.data, dict) else {}
        menus = mbar_data.get("menus") if isinstance(mbar_data.get("menus"), list) else []
        menus.append(object_entry.name)
        mbar_data["menus"] = menus
        mbar_object.data = mbar_data

    def add_menu_item(
        self,
        Name: str,
        Menu: str,
        Type: str = "item",
        Title: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Icon: Optional[str] = None,
        Group: Optional[str] = None,
        Active: int = 0,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates and appends a menu item to an existing menu.

        Parameters
        ----------

        Name : str
            Name of the menu item object. Must be unique.

        Menu : str
            Parent menu object name.

        Type : str, optional
            Menu item type (`item`, `separator`, `check`, `radio`, `tearoff`).

        Title : str | None, optional
            Menu item label.

        Tooltip : str | None, optional
            Optional help/tooltip text.

        Icon : str | None, optional
            Optional icon path or stock/icon name.

        Group : str | None, optional
            Optional radio group name.

        Active : int, optional
            Initial active state for check/radio items.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional event binder hint.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_menu_item(Name="menu_item_quit", Menu="menu_file", Title="_Quit")
        """
        menu_object = self.get_object(Menu)
        if menu_object.type != "Menu" or menu_object.ref is None:
            self.internal_die(Name, f"Menu \"{Menu}\" not found.")
        if self.ref is None:
            self.internal_die(Name, "No main window available for menu item binding.")

        params = self._normalize(
            Name=Name,
            Menu=Menu,
            Type=Type,
            Title=Title,
            Tooltip=Tooltip,
            Icon=Icon,
            Group=Group,
            Active=Active,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        item_type = str(params.get("type") or "item").lower()
        if item_type == "tearoff":
            item_type = "separator"

        object_entry = self._new_widget(**params)
        object_entry.type = "MenuItem"
        object_entry.title = str(params.get("title") or "")
        self.widgets[object_entry.name] = object_entry

        parent_menu: wx.Menu = menu_object.ref
        item_id = wx.NewIdRef()

        if item_type == "separator":
            menu_item = wx.MenuItem(parent_menu, item_id, "", "", wx.ITEM_SEPARATOR)
        else:
            if item_type == "check":
                kind = wx.ITEM_CHECK
            elif item_type == "radio":
                kind = wx.ITEM_RADIO
            else:
                kind = wx.ITEM_NORMAL

            label = str(object_entry.title or "")
            if self.is_underlined(label):
                label = label.replace("__", "\0")
                label = label.replace("_", "&")
                label = label.replace("\0", "_")

            help_text = str(params.get("tooltip") or "")
            menu_item = wx.MenuItem(parent_menu, item_id, label, help_text, kind)

            icon = params.get("icon")
            if isinstance(icon, str) and icon:
                bitmap: Optional[wx.Bitmap] = None
                if wx.FileExists(icon):
                    bitmap = wx.Bitmap(icon, wx.BITMAP_TYPE_ANY)
                else:
                    art_id = self._resolve_art_id(icon)
                    bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_MENU, wx.Size(16, 16))
                if isinstance(bitmap, wx.Bitmap) and bitmap.IsOk():
                    menu_item.SetBitmap(bitmap)

        parent_menu.Append(menu_item)
        menu_item.Enable(bool(int(Sensitive)))

        if item_type in ("check", "radio"):
            menu_item.Check(bool(int(Active)))

        # radio menu groups are tracked in self.groups for group-wide APIs
        group_name: Optional[str] = None
        if item_type == "radio" and isinstance(params.get("group"), str) and str(params.get("group")).strip():
            group_name = str(params.get("group")).strip()
            if group_name not in self.groups:
                self.groups[group_name] = []

            # activate exactly one element when this item is marked active
            if bool(int(Active)):
                for entry_name in self.groups[group_name]:
                    group_entry = self.get_object(entry_name)
                    if group_entry.type == "MenuItem" and isinstance(group_entry.ref, wx.MenuItem) and group_entry.ref.IsCheckable():
                        group_entry.ref.Check(False)
                        if isinstance(group_entry.data, dict):
                            group_entry.data["active"] = 0

            self.groups[group_name].append(object_entry.name)

        callback: Optional[Callable[..., Any]] = None
        if Function is not None:
            if isinstance(Function, (list, tuple)) and len(Function) > 0 and callable(Function[0]):
                base_cb = Function[0]
                payload = Function[1] if len(Function) > 1 else None

                def callback(event: wx.Event, cb: Callable[..., Any] = base_cb, data: Any = payload) -> None:
                    cb(event, data)
            elif callable(Function):
                callback = Function

        # menu items are dispatched through EVT_MENU on the main frame
        if callback is not None:
            self.ref.Bind(wx.EVT_MENU, callback, id=int(item_id))
            object_entry.handler[wx.EVT_MENU] = callback

        object_entry.ref = menu_item
        object_entry.data = {
            "menu": Menu,
            "type": item_type,
            "group": group_name,
            "active": 1 if menu_item.IsCheckable() and menu_item.IsChecked() else 0,
            "icon": params.get("icon"),
            "signal": Signal,
            "id": int(item_id),
        }

    def new_window(
        self,
        Name: str,
        Title: str,
        Version: Optional[str] = None,
        Base: int = 10,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Fixed: int = 0,
        Iconpath: Optional[str] = None,
        ThemeIcon: Optional[str] = None,
        Statusbar: Optional[int] = None,
    ) -> "SimpleWx":
        """
        Creates a new top-level window and default content container.

        Parameters
        ----------

        Name : str
            Name of the window object. Must be unique.

        Title : str
            Window title.

        Version : str | None, optional
            Version string appended to the title.

        Base : int, optional
            Base font size used during layout creation.

        Size : list[int] | tuple[int, int] | None, optional
            Initial window width and height.

        Fixed : int, optional
            If non-zero, window is non-resizable.

        Iconpath : str | None, optional
            Path to icon file.

        ThemeIcon : str | None, optional
            Theme icon name (reserved for later mapping in wx).

        Statusbar : int | None, optional
            Statusbar mode or timeout value.

        Returns
        -------

        SimpleWx:
            Current instance for fluent API usage.

        Examples
        --------

        win = SimpleWx().new_window(
            Name="mainWindow",
            Title="testem-all",
            Size=[400, 400],
            ThemeIcon="emblem-dropbox-syncing",
        )
        """
        # normalize incoming parameters (short keys -> long keys)
        params = self._normalize(
            Name=Name,
            Title=Title,
            Version=Version,
            Base=Base,
            Size=Size,
            Fixed=Fixed,
            Iconpath=Iconpath,
            ThemeIcon=ThemeIcon,
            Statusbar=Statusbar,
        )

        # initialize wx app context before creating any window/widgets
        self.init_app()

        # initialize/reset internal object registries for this toplevel window
        self.widgets = {}
        self.groups = {}
        self.containers = {}
        self.lates = []
        self.subs = {}
        self.handler = {}
        self.allocated_colors = {}
        self.scalefactor = 1.0

        # set core window metadata
        self.name = str(params["name"])
        self.base = int(params.get("base", 10))
        self.version = params.get("version")

        # create the internal window object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Window"

        # evaluate optional window flags
        fixed = bool(params.get("fixed", 0))
        statusbar = params.get("statusbar")
        sbar_timeout = int(statusbar) if isinstance(statusbar, int) and statusbar > 1 else 0
        object_entry.data = {
            "fixed": fixed,
            "statusbar": statusbar,
            "sbar_timeout": sbar_timeout,
            "sbar_stack": [],
        }

        # create the actual wx top-level frame
        frame = wx.Frame(parent=None, id=wx.ID_ANY, title="", pos=wx.DefaultPosition, size=wx.DefaultSize)

        # compose title from title + optional version suffix
        title = str(object_entry.title or "")
        if self.version is not None:
            title = f"{title} {self.version}"
        frame.SetTitle(title)

        # store frame references in object and class state
        object_entry.ref = frame
        self.ref = frame
        self.main_window = frame

        # create default parent panel (wx needs a panel as immediate child for proper behavior)
        root_panel = wx.Panel(frame, wx.ID_ANY)
        root_panel.SetSizer(None)
        self.containers[self.default_container_name] = root_panel
        self.container = root_panel

        content_container: wx.Window
        if fixed:
            # fixed window uses panel directly as content area
            content_container = root_panel
        else:
            # non-fixed window uses a scrolled content area
            scrolled = wx.ScrolledWindow(root_panel, wx.ID_ANY, style=wx.HSCROLL | wx.VSCROLL)
            scrolled.SetScrollRate(10, 10)

            # set initial virtual size (scaled) for scroll area
            initial_width = object_entry.width if object_entry.width is not None else 400
            initial_height = object_entry.height if object_entry.height is not None else 300
            scaled_initial_width, scaled_initial_height = self._scale_pair(initial_width, initial_height)
            scrolled.SetVirtualSize((scaled_initial_width, scaled_initial_height))

            # anchor scrolled container into the root panel and track resize
            scrolled.SetPosition((0, 0))
            scrolled.SetSize(root_panel.GetClientSize())
            root_panel.Bind(
                wx.EVT_SIZE,
                lambda event: (scrolled.SetSize(root_panel.GetClientSize()), event.Skip()),
            )
            content_container = scrolled
            self.containers["content"] = scrolled

        # keep content container reference in the main window object
        object_entry.data["panel"] = content_container

        # register window object in widget registry
        self.widgets[object_entry.name] = object_entry

        # get font size in current theme
        self.fontsize = self.get_fontsize(frame)
        # get SCALE_FACTOR
        self.scalefactor = self._calc_scalefactor(self.base, self.fontsize)

        # set it fixed if wanted (disable resize border)
        if fixed:
            frame.SetWindowStyle(frame.GetWindowStyle() & ~wx.RESIZE_BORDER)

        # add an identifier icon if defined
        iconpath = params.get("iconpath")
        if isinstance(iconpath, str) and iconpath:
            icon = wx.Icon(iconpath, wx.BITMAP_TYPE_ANY)
            if icon.IsOk():
                frame.SetIcon(icon)

        # if statusbar is requested, create and register it as internal object
        if statusbar is not None:
            bar = frame.CreateStatusBar()
            sb_entry = self._new_widget(type="Statusbar", name="win_sbar")
            sb_entry.ref = bar
            sb_entry.width = bar.GetSize().GetWidth()
            sb_entry.height = bar.GetSize().GetHeight()
            sb_entry.data = {
                "sbar_timeout": sbar_timeout,
                "statusbar": bar,
                "contextid": 0,
                "sbar_stack": [],
            }
            self.widgets[sb_entry.name] = sb_entry

        # add geometry if defined (scale at wx boundary only)
        if object_entry.width is not None and object_entry.height is not None:
            scaled_width, scaled_height = self._scale_pair(object_entry.width, object_entry.height)
            frame.SetSize(scaled_width, scaled_height)

        # add default signal handlers: close + theme/font changes
        self.add_signal_handler(object_entry.name, wx.EVT_CLOSE, lambda event: self.main_quit())
        frame.Bind(wx.EVT_SYS_COLOUR_CHANGED, self._on_font_changed)

        # remember current font on window level
        self.font = self.get_font_string(self.name)

        # keep frame hidden until show()/show_and_run() is called
        frame.Show(False)
        return self

    def add_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: str,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Color: Optional[list[Any] | tuple[Any, ...]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates and registers a button with absolute positioning.

        Parameters
        ----------

        Name : str
            Name of the button object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Title : str
            Button label.

        Frame : str | None, optional
            Optional parent container name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Color : list[Any] | tuple[Any, ...] | None, optional
            Optional foreground color definition.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_button(
            Name="closeButton",
            Position=[10, 45],
            Title="_Close",
            Tooltip="Closes the application",
        )
        win.add_signal_handler("closeButton", wx.EVT_BUTTON, lambda event: win.main_quit())
        """
        # normalize incoming button parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Frame=Frame,
            Font=Font,
            Color=Color,
            Size=Size,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register button object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Button"
        self.widgets[object_entry.name] = object_entry

        # create with provisional parent; final placement is done in _add_to_container()
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)

        # convert underscore mnemonic markers to wx style (&)
        raw_title = str(object_entry.title or "")
        if self.is_underlined(raw_title):
            label = raw_title.replace("__", "\0")
            label = label.replace("_", "&")
            label = label.replace("\0", "_")
        else:
            label = raw_title

        # create native button with placeholder position/size (set later in commons)
        button = wx.Button(
            provisional_parent,
            wx.ID_ANY,
            label,
            pos=(0, 0),
            size=wx.DefaultSize,
        )
        object_entry.ref = button

        # apply optional font settings
        font = params.get("font")
        if font is not None:
            self.set_font(object_entry.name, font)

        # apply optional font color settings
        color = params.get("color")
        if isinstance(color, (list, tuple)) and len(color) > 0 and color[0]:
            state = color[1] if len(color) > 1 else None
            self.set_font_color(object_entry.name, str(color[0]), state)

        # apply shared defaults (tooltip, size, sensitivity, callback)
        self._set_commons(object_entry.name, **params)

        # place widget into target container using absolute coordinates
        self._add_to_container(object_entry.name)

    def add_link_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: str,
        Uri: str,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Color: Optional[list[Any] | tuple[Any, ...]] = None,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new hyperlink button widget.

        Parameters
        ----------

        Name : str
            Name of the link button object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Title : str
            Hyperlink label text.

        Uri : str
            Hyperlink target URI.

        Frame : str | None, optional
            Optional parent container name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Color : list[Any] | tuple[Any, ...] | None, optional
            Optional color definition (`[color, state]`).

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_link_button(
            Name="linkButton",
            Position=[15, 30],
            Title="simplewx repository",
            Uri="https://github.com/ThomasFunk/SimpleWx",
        )
        """
        # normalize incoming link-button parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Uri=Uri,
            Frame=Frame,
            Font=Font,
            Color=Color,
            Size=Size,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # validate required uri
        uri = str(params.get("uri") or "").strip()
        if not uri:
            self.internal_die(Name, "No Uri defined!")

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "LinkButton"
        self.widgets[object_entry.name] = object_entry

        # create hyperlink control with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        link_button = wx.adv.HyperlinkCtrl(
            provisional_parent,
            wx.ID_ANY,
            str(object_entry.title or ""),
            uri,
            pos=(0, 0),
            size=wx.DefaultSize,
        )

        # add widget reference and uri metadata
        object_entry.ref = link_button
        object_entry.data = {
            "uri": uri,
        }

        # hover underline behavior (normal state without underline)
        if hasattr(link_button, "SetUnderlines"):
            link_button.SetUnderlines(False, True, True)

        # apply optional font settings
        font = params.get("font")
        if font is not None:
            self.set_font(object_entry.name, font)

        # apply optional color settings
        color = params.get("color")
        if isinstance(color, (list, tuple)) and len(color) > 0 and color[0]:
            link_button.SetNormalColour(wx.Colour(str(color[0])))

        # apply shared defaults (size, sensitive, callback)
        self._set_commons(object_entry.name, **params)

        # place link button into target container
        self._add_to_container(object_entry.name)

    def _scale_bitmap(self, bitmap: wx.Bitmap, width: int, height: int) -> wx.Bitmap:
        """
        Scales a bitmap to a target logical size using current scale factor.

        Parameters
        ----------

        bitmap : wx.Bitmap
            Source bitmap.

        width : int
            Target logical width.

        height : int
            Target logical height.

        Returns
        -------

        wx.Bitmap:
            Scaled bitmap (or original if invalid input).
        """
        if not isinstance(bitmap, wx.Bitmap) or not bitmap.IsOk():
            return bitmap

        target_w = max(1, self._scale(int(width)))
        target_h = max(1, self._scale(int(height)))
        image = bitmap.ConvertToImage()
        image = image.Scale(target_w, target_h, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(image)

    def _resolve_art_id(self, icon_name: str) -> str:
        """
        Maps common stock/icon names to wx art IDs.

        Parameters
        ----------

        icon_name : str
            Stock/icon name from API input.

        Returns
        -------

        str:
            wx art ID constant value.
        """
        name = icon_name.strip().lower()
        stock_map: Dict[str, str] = {
            "gtk-open": wx.ART_FILE_OPEN,
            "gtk-save": wx.ART_FILE_SAVE,
            "gtk-save-as": wx.ART_FILE_SAVE_AS,
            "gtk-new": wx.ART_NEW,
            "gtk-copy": wx.ART_COPY,
            "gtk-cut": wx.ART_CUT,
            "gtk-paste": wx.ART_PASTE,
            "gtk-delete": wx.ART_DELETE,
            "gtk-quit": wx.ART_QUIT,
            "gtk-help": wx.ART_HELP,
            "gtk-find": wx.ART_FIND,
            "gtk-home": wx.ART_GO_HOME,
            "gtk-go-back": wx.ART_GO_BACK,
            "gtk-go-forward": wx.ART_GO_FORWARD,
            "gtk-refresh": wx.ART_REDO,
            "gtk-undo": wx.ART_UNDO,
            "gtk-info": wx.ART_INFORMATION,
            "gtk-warning": wx.ART_WARNING,
            "gtk-error": wx.ART_ERROR,
        }
        if name in stock_map:
            return stock_map[name]
        return wx.ART_MISSING_IMAGE

    def add_image(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Path: Optional[str] = None,
        Pixbuffer: Optional[Any] = None,
        Stock: Optional[list[Any] | tuple[Any, ...]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new image widget.

        Parameters
        ----------

        Name : str
            Name of the image object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled image size `[width, height]`.

        Path : str | None, optional
            Optional image file path source.

        Pixbuffer : Any | None, optional
            Optional wx bitmap/image source.

        Stock : list[Any] | tuple[Any, ...] | None, optional
            Optional stock/art source (`[stock_name, stock_size]`).

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_image(
            Name="image1",
            Path="./icon.png",
            Size=[64, 64],
            Position=[10, 10],
        )
        """
        params = self._normalize(
            Name=Name,
            Path=Path,
            Pixbuffer=Pixbuffer,
            Stock=Stock,
            Size=Size,
            Position=Position,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "Image"
        self.widgets[object_entry.name] = object_entry
        object_entry.path = str(params.get("path")) if isinstance(params.get("path"), str) else None

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        panel = wx.Panel(provisional_parent, wx.ID_ANY, pos=(0, 0), size=wx.DefaultSize)

        source_bitmap: Optional[wx.Bitmap] = None
        pixbuffer = params.get("pixbuffer")
        stock = params.get("stock")

        if isinstance(pixbuffer, wx.Bitmap):
            source_bitmap = pixbuffer
        elif isinstance(pixbuffer, wx.Image):
            source_bitmap = wx.Bitmap(pixbuffer)
        elif object_entry.path:
            source_bitmap = wx.Bitmap(object_entry.path, wx.BITMAP_TYPE_ANY)
        elif isinstance(stock, (list, tuple)) and len(stock) > 0 and stock[0]:
            art_id = self._resolve_art_id(str(stock[0]))
            source_bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_OTHER)

        if source_bitmap is None or not source_bitmap.IsOk():
            self.internal_die(object_entry.name, "No valid image source defined!")

        if object_entry.width is None or object_entry.height is None:
            self.internal_die(object_entry.name, "No image size defined!")

        bitmap = self._scale_bitmap(source_bitmap, int(object_entry.width), int(object_entry.height))
        static_bitmap = wx.StaticBitmap(panel, wx.ID_ANY, bitmap, pos=(0, 0), size=bitmap.GetSize())
        panel.SetSize(bitmap.GetSize())

        object_entry.ref = panel
        object_entry.data = {
            "static_bitmap": static_bitmap,
            "bitmap": bitmap,
            "source_bitmap": source_bitmap,
            "pixbuffer": source_bitmap,
            "stock": stock,
        }

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def get_image(self, Name: str, Keyname: Optional[str] = None) -> Any:
        """
        Returns image reference, bitmap/pixbuffer, or file path.

        Parameters
        ----------

        Name : str
            Name of the image object. Must be unique.

        Keyname : str | None, optional
            Optional selector (`Path`, `Image`, `Pixbuf`/`Pixbuffer`).

        Returns
        -------

        Any:
            Selected image data/reference.
        """
        object_entry = self.get_object(Name)
        if object_entry.type != "Image":
            self.internal_die(Name, "Not an image object.")
        data = object_entry.data if isinstance(object_entry.data, dict) else {}

        key = self._extend(str(Keyname).lower()) if Keyname is not None else None
        if key is None or key == "image":
            return data.get("static_bitmap")
        if key == "pixbuffer":
            return data.get("pixbuffer")
        if key == "path":
            return object_entry.path
        if key == "bitmap":
            return data.get("bitmap")
        if key == "staticbitmap":
            return data.get("static_bitmap")
        self.internal_die(Name, f"Unknown parameter \"{key}\".")

    def set_image(
        self,
        Name: str,
        Path: Optional[str] = None,
        Pixbuffer: Optional[Any] = None,
        Image: Optional[Any] = None,
        Stock: Optional[list[Any] | tuple[Any, ...]] = None,
    ) -> None:
        """
        Sets a new image source by path, pixbuffer, image object, or stock.

        Parameters
        ----------

        Name : str
            Name of the image object. Must be unique.

        Path : str | None, optional
            New image file path.

        Pixbuffer : Any | None, optional
            New bitmap/image source.

        Image : Any | None, optional
            New image object (`wx.Image`, `wx.Bitmap`, or `wx.StaticBitmap`).

        Stock : list[Any] | tuple[Any, ...] | None, optional
            New stock/art source (`[stock_name, stock_size]`).

        Returns
        -------

        None.
        """
        object_entry = self.get_object(Name)
        if object_entry.type != "Image":
            self.internal_die(Name, "Not an image object.")

        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        static_bitmap = data.get("static_bitmap")
        if not isinstance(static_bitmap, wx.StaticBitmap):
            self.internal_die(Name, "No static bitmap reference available.")

        source_bitmap: Optional[wx.Bitmap] = None

        if isinstance(Path, str) and Path:
            object_entry.path = Path
            source_bitmap = wx.Bitmap(Path, wx.BITMAP_TYPE_ANY)
        elif isinstance(Pixbuffer, wx.Bitmap):
            source_bitmap = Pixbuffer
        elif isinstance(Pixbuffer, wx.Image):
            source_bitmap = wx.Bitmap(Pixbuffer)
        elif isinstance(Image, wx.StaticBitmap):
            source_bitmap = Image.GetBitmap()
        elif isinstance(Image, wx.Bitmap):
            source_bitmap = Image
        elif isinstance(Image, wx.Image):
            source_bitmap = wx.Bitmap(Image)
        elif isinstance(Stock, (list, tuple)) and len(Stock) > 0 and Stock[0]:
            art_id = self._resolve_art_id(str(Stock[0]))
            source_bitmap = wx.ArtProvider.GetBitmap(art_id, wx.ART_OTHER)
            data["stock"] = Stock
        else:
            self.internal_die(Name, "Unknown parameter(s): no valid image source provided.")

        if source_bitmap is None or not source_bitmap.IsOk():
            self.internal_die(Name, "No valid image source defined!")

        width = int(object_entry.width) if object_entry.width is not None else source_bitmap.GetWidth()
        height = int(object_entry.height) if object_entry.height is not None else source_bitmap.GetHeight()
        scaled_bitmap = self._scale_bitmap(source_bitmap, width, height)

        data["source_bitmap"] = source_bitmap
        data["pixbuffer"] = source_bitmap
        data["bitmap"] = scaled_bitmap
        object_entry.data = data

        static_bitmap.SetBitmap(scaled_bitmap)
        if object_entry.ref is not None:
            object_entry.ref.Refresh()

    def _create_check_widget(self, widget_name: str, **params: Any) -> wx.CheckBox:
        """
        Creates and configures a wx.CheckBox for a stored check-button object.

        Parameters
        ----------

        widget_name : str
            Widget name key.

        **params : Any
            Normalized check-button parameters.

        Returns
        -------

        wx.CheckBox:
            Created check widget reference.
        """
        # get object
        object_entry = self.get_object(widget_name)

        # check button specific fields
        active = 1 if params.get("active") else 0
        font = params.get("font")
        color = params.get("color")
        label = str(object_entry.title or "")

        # if underline in text should be used, convert to wx mnemonic style
        if self.is_underlined(label):
            label = label.replace("__", "\0")
            label = label.replace("_", "&")
            label = label.replace("\0", "_")

        # create check button with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        check_widget = wx.CheckBox(provisional_parent, wx.ID_ANY, label, pos=(0, 0), size=wx.DefaultSize)
        check_widget.SetValue(bool(active))

        # add widget reference to object
        object_entry.ref = check_widget

        # change font if set
        if font is not None:
            self.set_font(widget_name, font)

        # set font color if defined
        if isinstance(color, (list, tuple)) and len(color) > 0 and color[0]:
            cstate = color[1] if len(color) > 1 else None
            self.set_font_color(widget_name, str(color[0]), cstate)

        # apply common setup (tooltip, callbacks, sensitive, size)
        self._set_commons(widget_name, **params)

        return check_widget

    def add_check_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: str,
        Frame: Optional[str] = None,
        Active: int = 0,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Color: Optional[list[Any] | tuple[Any, ...]] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new check button widget.

        Parameters
        ----------

        Name : str
            Name of the check button object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Title : str
            Check button label.

        Frame : str | None, optional
            Optional parent container name.

        Active : int, optional
            Initial active state (`0` or `1`).

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Color : list[Any] | tuple[Any, ...] | None, optional
            Optional foreground color definition.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_check_button(
            Name="checkEnabled",
            Position=[10, 20],
            Title="_Enabled",
            Active=1,
        )
        """
        # normalize incoming check button parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Frame=Frame,
            Active=Active,
            Font=Font,
            Color=Color,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "CheckButton"
        self.widgets[object_entry.name] = object_entry

        # create native check button
        self._create_check_widget(object_entry.name, **params)

        # position the check button
        self._add_to_container(object_entry.name)

    def _create_radio_widget(self, widget_name: str, **params: Any) -> wx.RadioButton:
        """
        Creates and configures a wx.RadioButton for a stored radio-button object.

        Parameters
        ----------

        widget_name : str
            Widget name key.

        **params : Any
            Normalized radio-button parameters.

        Returns
        -------

        wx.RadioButton:
            Created radio widget reference.
        """
        # get object
        object_entry = self.get_object(widget_name)

        # radio button specific fields
        group_name = str(params.get("group") or "default")
        active = 1 if params.get("active") else 0
        font = params.get("font")
        color = params.get("color")
        label = str(object_entry.title or "")

        # persist group metadata on object
        if object_entry.data is None or not isinstance(object_entry.data, dict):
            object_entry.data = {}
        object_entry.data["group"] = group_name

        # if underline in text should be used, convert to wx mnemonic style
        if self.is_underlined(label):
            label = label.replace("__", "\0")
            label = label.replace("_", "&")
            label = label.replace("\0", "_")

        # get group state to decide style for first/next member
        if group_name not in self.groups:
            self.groups[group_name] = []
        is_first_in_group = len(self.groups[group_name]) == 0
        style = wx.RB_GROUP if is_first_in_group else 0

        # create radio button with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        radio_widget = wx.RadioButton(
            provisional_parent,
            wx.ID_ANY,
            label,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        # add widget reference to object
        object_entry.ref = radio_widget

        # change font if set
        if font is not None:
            self.set_font(widget_name, font)

        # set font color if defined
        if isinstance(color, (list, tuple)) and len(color) > 0 and color[0]:
            cstate = color[1] if len(color) > 1 else None
            self.set_font_color(widget_name, str(color[0]), cstate)

        # apply common setup (tooltip, callbacks, sensitive, size)
        self._set_commons(widget_name, **params)

        # register button name in groups list
        self.groups[group_name].append(object_entry.name)

        # set active state
        radio_widget.SetValue(bool(active))

        return radio_widget

    def _extract_mnemonic_char(self, text: str) -> Optional[str]:
        """
        Extracts mnemonic character from underscore-based label markup.

        Parameters
        ----------

        text : str
            Source label text.

        Returns
        -------

        str | None:
            Lowercase mnemonic character or None.
        """
        escaped = text.replace("__", "")
        for index, char in enumerate(escaped[:-1]):
            if char == "_":
                return escaped[index + 1].lower()
        return None

    def _bind_label_mnemonic(self, mnemonic_char: str, widget_name: str) -> None:
        """
        Binds Alt+<char> to focus the linked widget.

        Parameters
        ----------

        mnemonic_char : str
            Mnemonic character to react on.

        widget_name : str
            Name of target widget to focus.

        Returns
        -------

        None.
        """
        if not self.ref:
            return
        if not self.widgets.get(widget_name):
            return

        def _on_char_hook(event: wx.KeyEvent) -> None:
            code = event.GetUnicodeKey()
            key = chr(code).lower() if code not in (wx.WXK_NONE, wx.WXK_INVALID) and code >= 0 else ""
            if event.AltDown() and key == mnemonic_char:
                linked = self.get_object(widget_name)
                if linked.ref is not None:
                    linked.ref.SetFocus()
                event.Skip(False)
                return
            event.Skip(True)

        self.ref.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)

    def add_radio_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: str,
        Group: str,
        Frame: Optional[str] = None,
        Active: int = 0,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Color: Optional[list[Any] | tuple[Any, ...]] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new radio button widget.

        Parameters
        ----------

        Name : str
            Name of the radio button object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Title : str
            Radio button label.

        Group : str
            Name of the radio group. Must be unique in scope.

        Frame : str | None, optional
            Optional parent container name.

        Active : int, optional
            Initial active state (`0` or `1`).

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Color : list[Any] | tuple[Any, ...] | None, optional
            Optional foreground color definition.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_radio_button(
            Name="radioLow",
            Position=[10, 50],
            Title="_Low",
            Group="priority",
            Active=1,
        )
        """
        # normalize incoming radio button parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Group=Group,
            Frame=Frame,
            Active=Active,
            Font=Font,
            Color=Color,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "RadioButton"
        self.widgets[object_entry.name] = object_entry

        # create native radio button
        self._create_radio_widget(object_entry.name, **params)

        # position the radio button
        self._add_to_container(object_entry.name)

    def add_splitter_window(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Orient: str = "vertical",
        Split: int = 200,
        MinSize: int = 60,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a splitter-window container with two configurable panes.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Orient=Orient,
            Split=Split,
            MinSize=MinSize,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "SplitterWindow"
        self.widgets[object_entry.name] = object_entry

        orientation = str(params.get("orientation") or "vertical").lower()
        orientation = "horizontal" if orientation.startswith("h") else "vertical"
        sash_position = int(params.get("split") or 200)
        min_size = max(1, int(params.get("minsize") or 60))

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        splitter = wx.SplitterWindow(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.SP_LIVE_UPDATE | wx.SP_3D,
        )
        splitter.SetMinimumPaneSize(self._scale(min_size))

        object_entry.ref = splitter
        object_entry.data = {
            "orientation": orientation,
            "sashposition": sash_position,
            "minsize": min_size,
            "firstpane": None,
            "secondpane": None,
            "unsplit": 0,
            "collapse": "second",
        }

        def _on_sash_changed(event: wx.SplitterEvent, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            if isinstance(entry.data, dict):
                sash_scaled = int(event.GetSashPosition())
                entry.data["sashposition"] = int(round(sash_scaled / self.scalefactor)) if self.scalefactor != 0 else sash_scaled
            event.Skip()

        splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, _on_sash_changed)

        self.containers[object_entry.name] = splitter
        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_splitter_pane(
        self,
        Name: str,
        Splitter: str,
        Side: str = "first",
        Tooltip: Optional[str] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates one pane panel inside a splitter window.
        """
        splitter_object = self.get_object(Splitter)
        if splitter_object.type != "SplitterWindow" or not isinstance(splitter_object.ref, wx.SplitterWindow):
            self.internal_die(Name, f'SplitterWindow "{Splitter}" not found.')

        params = self._normalize(
            Name=Name,
            Position=[0, 0],
            Splitter=Splitter,
            Side=Side,
            Frame=Splitter,
            Tooltip=Tooltip,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "SplitterPane"
        self.widgets[object_entry.name] = object_entry

        side = str(params.get("side") or "first").lower()
        side = "second" if side.startswith("sec") else "first"

        pane_panel = wx.Panel(splitter_object.ref, wx.ID_ANY)
        pane_panel.SetSizer(None)

        object_entry.ref = pane_panel
        object_entry.data = {
            "splitter": Splitter,
            "side": side,
        }

        self.containers[object_entry.name] = pane_panel

        splitter_data = splitter_object.data if isinstance(splitter_object.data, dict) else {}
        if side == "first":
            splitter_data["firstpane"] = object_entry.name
        else:
            splitter_data["secondpane"] = object_entry.name
        splitter_object.data = splitter_data

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)
        self._apply_splitter_layout(Splitter)

    def add_splitter(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Orient: str = "vertical",
        Split: int = 200,
        MinSize: int = 60,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for add_splitter_window.
        """
        self.add_splitter_window(
            Name=Name,
            Position=Position,
            Size=Size,
            Orient=Orient,
            Split=Split,
            MinSize=MinSize,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def add_frame(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Tooltip: Optional[str] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new frame-like container widget.

        Parameters
        ----------

        Name : str
            Name of the frame. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled frame size `[width, height]`.

        Title : str | None, optional
            Optional frame title.

        Frame : str | None, optional
            Optional parent container name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition for title text.

        Tooltip : str | None, optional
            Optional tooltip text.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_frame(
            Name="frame1",
            Position=[5, 5],
            Size=[390, 190],
            Title=" A Frame around ",
        )
        """
        # normalize incoming frame parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Title=Title,
            Frame=Frame,
            Font=Font,
            Tooltip=Tooltip,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Frame"
        self.widgets[object_entry.name] = object_entry

        # create frame host panel (wx has no direct GtkFrame equivalent)
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        frame_panel = wx.Panel(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.BORDER_SIMPLE,
        )
        object_entry.ref = frame_panel

        # add optional title label on frame border area
        title_label: Optional[wx.StaticText] = None
        if object_entry.title:
            title_label = wx.StaticText(frame_panel, wx.ID_ANY, str(object_entry.title))

        # create inner absolute-position container for frame children
        content_panel = wx.Panel(frame_panel, wx.ID_ANY)
        content_panel.SetSizer(None)
        self.containers[object_entry.name] = content_panel

        # persist frame internals for later layout/title updates
        object_entry.data = {
            "title_label": title_label,
            "content_panel": content_panel,
            "content_offset_y": 6,
        }

        # apply common defaults (size, tooltip, sensitive)
        self._set_commons(object_entry.name, **params)

        # apply optional font to frame/title
        frame_font = params.get("font")
        if frame_font is not None:
            self.set_font(object_entry.name, frame_font)
            if title_label is not None:
                current = title_label.GetFont()
                if isinstance(frame_font, (list, tuple)) and len(frame_font) >= 2:
                    family = str(frame_font[0])
                    size = int(frame_font[1])
                    weight_label = str(frame_font[2]).lower() if len(frame_font) > 2 and frame_font[2] is not None else "normal"
                    weight = wx.FONTWEIGHT_BOLD if "bold" in weight_label else wx.FONTWEIGHT_LIGHT if "light" in weight_label else wx.FONTWEIGHT_NORMAL
                    font = wx.Font(size, current.GetFamily(), current.GetStyle(), weight, faceName=family)
                    if font.IsOk():
                        title_label.SetFont(font)

        # place frame and then layout its inner content area
        self._add_to_container(object_entry.name)
        self._layout_frame_container(object_entry.name)

    def _get_notebook_style(self, tabs: str, scrollable: int) -> int:
        """
        Builds wx notebook style flags from tab position and scroll mode.

        Parameters
        ----------

        tabs : str
            Tab position (`top`, `bottom`, `left`, `right`, `none`).

        scrollable : int
            If non-zero, enables multiline tab layout.

        Returns
        -------

        int:
            Combined wx style flags for `wx.Notebook`.
        """
        tabs_norm = str(tabs or "top").lower()
        tab_positions = {
            "top": wx.NB_TOP,
            "bottom": wx.NB_BOTTOM,
            "left": wx.NB_LEFT,
            "right": wx.NB_RIGHT,
            "none": wx.NB_TOP,
        }

        if tabs_norm not in tab_positions:
            tabs_norm = "top"

        style = tab_positions[tabs_norm]
        if tabs_norm == "none":
            style |= int(getattr(wx, "NB_NOPAGETHEME", 0))
        if int(scrollable):
            style |= wx.NB_MULTILINE
        return style

    def _resolve_notebook_bitmap(self, icon_ref: Any, size: int = 16) -> Optional[wx.Bitmap]:
        """
        Resolves a notebook tab image reference to a bitmap.

        Parameters
        ----------

        icon_ref : Any
            Path or stock icon name.

        size : int, optional
            Target bitmap edge size in pixels.

        Returns
        -------

        wx.Bitmap | None:
            Resolved bitmap or None when unavailable.
        """
        if icon_ref is None:
            return None

        icon_text = str(icon_ref).strip()
        if not icon_text:
            return None

        bitmap: Optional[wx.Bitmap] = None
        if wx.FileExists(icon_text):
            source = wx.Bitmap(icon_text, wx.BITMAP_TYPE_ANY)
            if source.IsOk():
                bitmap = source
        else:
            art_id = self._resolve_art_id(icon_text)
            source = wx.ArtProvider.GetBitmap(art_id, wx.ART_OTHER, wx.Size(size, size))
            if source.IsOk():
                bitmap = source

        if bitmap is None or not bitmap.IsOk():
            return None

        if bitmap.GetWidth() != size or bitmap.GetHeight() != size:
            image = bitmap.ConvertToImage()
            image = image.Scale(size, size, wx.IMAGE_QUALITY_HIGH)
            bitmap = wx.Bitmap(image)
        return bitmap

    def _set_notebook_page_image(self, page_name: str, image_ref: Any) -> int:
        """
        Sets or clears a tab image for a notebook page.

        Parameters
        ----------

        page_name : str
            Notebook page object name.

        image_ref : Any
            Path/stock icon reference. Empty value clears image.

        Returns
        -------

        int:
            `1` on success, else `0`.
        """
        page_object = self.get_object(page_name)
        if page_object.type != "NotebookPage" or page_object.ref is None:
            self.internal_die(page_name, f'NotebookPage "{page_name}" not found.')

        page_data = page_object.data if isinstance(page_object.data, dict) else {}
        notebook_name = page_data.get("notebook")
        if not isinstance(notebook_name, str):
            self.internal_die(page_name, "Notebook page has no parent notebook metadata.")

        notebook_object = self.get_object(notebook_name)
        notebook_ref = notebook_object.ref
        if notebook_object.type != "Notebook" or notebook_ref is None:
            self.internal_die(page_name, f'Notebook "{notebook_name}" not found.')

        page_index = int(notebook_ref.FindPage(page_object.ref)) if hasattr(notebook_ref, "FindPage") else -1
        if page_index < 0:
            self.show_error(page_object, "Notebook page index not found.")
            return 0

        notebook_data = notebook_object.data if isinstance(notebook_object.data, dict) else {}
        image_size = int(notebook_data.get("imagesize", 16))

        # clear page image when empty input is provided
        if image_ref is None or str(image_ref).strip() == "":
            if hasattr(notebook_ref, "SetPageImage"):
                try:
                    notebook_ref.SetPageImage(page_index, -1)
                except Exception:
                    pass
            page_data["image"] = None
            page_object.data = page_data
            return 1

        bitmap = self._resolve_notebook_bitmap(image_ref, image_size)
        if bitmap is None or not bitmap.IsOk():
            self.show_error(page_object, f'Notebook tab image "{image_ref}" not found.')
            return 0

        image_list = notebook_data.get("imagelist")
        if not isinstance(image_list, wx.ImageList):
            image_list = wx.ImageList(image_size, image_size, mask=True)
            notebook_data["imagelist"] = image_list
            notebook_data["image_index_map"] = {}
            if hasattr(notebook_ref, "SetImageList"):
                notebook_ref.SetImageList(image_list)

        image_map = notebook_data.get("image_index_map") if isinstance(notebook_data.get("image_index_map"), dict) else {}
        image_key = str(image_ref).strip()
        image_index = image_map.get(image_key)

        if not isinstance(image_index, int):
            image_index = int(image_list.Add(bitmap))
            image_map[image_key] = image_index
            notebook_data["image_index_map"] = image_map

        if hasattr(notebook_ref, "SetPageImage"):
            notebook_ref.SetPageImage(page_index, image_index)

        page_data["image"] = image_key
        page_object.data = page_data
        notebook_object.data = notebook_data
        return 1

    def add_notebook(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Tabs: str = "top",
        Scrollable: int = 1,
        Popup: int = 0,
        CloseTabs: int = 0,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new notebook widget.

        Parameters
        ----------

        Name : str
            Name of the notebook object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled notebook size `[width, height]`.

        Tabs : str, optional
            Tab position (`top`, `bottom`, `left`, `right`, `none`).

        Scrollable : int, optional
            If non-zero, enables multiline tab layout.

        Popup : int, optional
            Compatibility metadata for tab popup support.

        CloseTabs : int, optional
            If non-zero, middle-click on a tab closes that page.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Tabs=Tabs,
            Scrollable=Scrollable,
            Popup=Popup,
            CloseTabs=CloseTabs,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "Notebook"
        self.widgets[object_entry.name] = object_entry

        scrollable = 1 if int(params.get("scrollable") or 0) else 0
        popup = 1 if int(params.get("popup") or 0) else 0
        closetabs = 1 if int(params.get("closetabs") or 0) else 0
        tabs = str(params.get("tabs") or "top").lower()
        style = self._get_notebook_style(tabs, scrollable)

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        notebook = wx.Notebook(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        object_entry.ref = notebook
        object_entry.data = {
            "tabs": tabs,
            "scrollable": scrollable,
            "popup": popup,
            "closetabs": closetabs,
            "pages": [],
            "lastclosed": None,
            "imagesize": 16,
            "image_index_map": {},
            "imagelist": None,
        }

        def _on_notebook_page_changed(event: wx.BookCtrlEvent, notebook_name: str = object_entry.name) -> None:
            notebook_obj = self.get_object(notebook_name)
            if isinstance(notebook_obj.data, dict) and notebook_obj.ref is not None:
                notebook_obj.data["currentpage"] = int(notebook_obj.ref.GetSelection())
            event.Skip()

        def _on_notebook_middle_click(event: wx.MouseEvent, notebook_name: str = object_entry.name) -> None:
            notebook_obj = self.get_object(notebook_name)
            notebook_data = notebook_obj.data if isinstance(notebook_obj.data, dict) else {}
            if int(notebook_data.get("closetabs", 0)) == 0:
                event.Skip()
                return

            notebook_ref = notebook_obj.ref
            if notebook_ref is None or not hasattr(notebook_ref, "HitTest"):
                event.Skip()
                return

            page_idx, _flags = notebook_ref.HitTest(event.GetPosition())
            if int(page_idx) < 0:
                event.Skip()
                return

            pages = notebook_data.get("pages") if isinstance(notebook_data.get("pages"), list) else []
            target_name = pages[int(page_idx)] if int(page_idx) < len(pages) else None

            removed = 0
            if isinstance(target_name, str) and target_name in self.widgets:
                removed = self.remove_nb_page(target_name)
            else:
                removed = self.remove_nb_page(notebook_name, int(page_idx))

            if int(removed) == 1:
                notebook_data = notebook_obj.data if isinstance(notebook_obj.data, dict) else {}
                notebook_data["lastclosed"] = int(page_idx)
                notebook_obj.data = notebook_data
            else:
                event.Skip()

        notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_notebook_page_changed)
        notebook.Bind(wx.EVT_MIDDLE_DOWN, _on_notebook_middle_click)

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_nb_page(
        self,
        Name: str,
        Notebook: str,
        Title: Optional[str] = None,
        Image: Optional[Any] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Color: Optional[list[Any] | tuple[Any, ...]] = None,
        PositionNumber: Optional[int] = None,
        Tooltip: Optional[str] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates and inserts a notebook page.

        Parameters
        ----------

        Name : str
            Name of the notebook page object. Must be unique.

        Notebook : str
            Parent notebook object name.

        Title : str | None, optional
            Page tab title.

        Image : Any | None, optional
            Optional tab image path or stock icon name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition for the page container.

        Color : list[Any] | tuple[Any, ...] | None, optional
            Optional font color definition `[color, state]`.

        PositionNumber : int | None, optional
            Optional target page index for insertion.

        Tooltip : str | None, optional
            Optional tooltip text.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.
        """
        notebook_object = self.get_object(Notebook)
        if notebook_object.type != "Notebook" or notebook_object.ref is None:
            self.internal_die(Name, f'Notebook "{Notebook}" not found.')

        params = self._normalize(
            Name=Name,
            Notebook=Notebook,
            Title=Title,
            Image=Image,
            Font=Font,
            Color=Color,
            PositionNumber=PositionNumber,
            Tooltip=Tooltip,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "NotebookPage"
        self.widgets[object_entry.name] = object_entry

        notebook_ref = notebook_object.ref
        page_panel = wx.ScrolledWindow(notebook_ref, wx.ID_ANY, style=wx.HSCROLL | wx.VSCROLL)
        page_panel.SetScrollRate(10, 10)

        object_entry.ref = page_panel
        object_entry.data = {
            "notebook": Notebook,
            "image": str(Image).strip() if Image is not None and str(Image).strip() else None,
        }
        self.containers[object_entry.name] = page_panel

        page_title = str(object_entry.title or "")
        page_count = notebook_ref.GetPageCount()
        insert_index = PositionNumber if PositionNumber is not None else params.get("positionnumber")
        if isinstance(insert_index, int) and 0 <= insert_index <= page_count:
            notebook_ref.InsertPage(int(insert_index), page_panel, page_title, select=True)
            page_index = int(insert_index)
        else:
            notebook_ref.AddPage(page_panel, page_title, select=True)
            page_index = int(page_count)

        object_entry.data["page_index"] = page_index

        if Image is not None:
            self._set_notebook_page_image(object_entry.name, Image)

        if isinstance(Tooltip, str) and Tooltip and hasattr(notebook_ref, "SetPageToolTip"):
            try:
                notebook_ref.SetPageToolTip(page_index, Tooltip)
            except Exception:
                pass

        notebook_data = notebook_object.data if isinstance(notebook_object.data, dict) else {}
        pages = notebook_data.get("pages") if isinstance(notebook_data.get("pages"), list) else []
        if page_index < 0 or page_index > len(pages):
            pages.append(object_entry.name)
        else:
            pages.insert(page_index, object_entry.name)
        notebook_data["pages"] = pages
        notebook_object.data = notebook_data

        self._set_commons(object_entry.name, **params)

        if Font is not None:
            self.set_font(object_entry.name, Font)

        if isinstance(Color, (list, tuple)) and len(Color) > 0:
            color_name = Color[0]
            color_state = Color[1] if len(Color) > 1 else None
            if color_name is not None:
                self.set_font_color(object_entry.name, str(color_name), color_state)

    def remove_nb_page(self, Name: str, Number: Optional[int] = None) -> int:
        """
        Removes a notebook page by notebook/index or by page name.

        Parameters
        ----------

        Name : str
            Notebook name (when `Number` is set) or notebook-page name.

        Number : int | None, optional
            Optional 0-based page index in the notebook.

        Returns
        -------

        int:
            `1` if a page was removed, else `0`.
        """
        notebook_object: Optional[WidgetEntry] = None
        page_object: Optional[WidgetEntry] = None
        page_index = -1

        if Number is not None:
            notebook_object = self.get_object(Name)
            if notebook_object.type != "Notebook" or notebook_object.ref is None:
                self.internal_die(Name, f'Notebook "{Name}" not found.')

            page_index = int(Number)
            if page_index < 0 or page_index >= notebook_object.ref.GetPageCount():
                self.show_error(notebook_object, f'No notebook page with number "{Number}" found.')
                return 0

            page_ref = notebook_object.ref.GetPage(page_index)
            for entry in self.widgets.values():
                if entry.type == "NotebookPage" and entry.ref is page_ref:
                    page_object = entry
                    break
        else:
            page_object = self.get_object(Name)
            if page_object.type != "NotebookPage" or page_object.ref is None:
                self.internal_die(Name, f'NotebookPage "{Name}" not found.')

            page_data = page_object.data if isinstance(page_object.data, dict) else {}
            notebook_name = page_data.get("notebook")
            if not isinstance(notebook_name, str):
                self.internal_die(Name, "Notebook page has no parent notebook metadata.")

            notebook_object = self.get_object(notebook_name)
            if notebook_object.type != "Notebook" or notebook_object.ref is None:
                self.internal_die(Name, f'Notebook "{notebook_name}" not found.')

            if hasattr(notebook_object.ref, "FindPage"):
                page_index = int(notebook_object.ref.FindPage(page_object.ref))
            else:
                for idx in range(notebook_object.ref.GetPageCount()):
                    if notebook_object.ref.GetPage(idx) is page_object.ref:
                        page_index = idx
                        break

        if page_index < 0:
            self.show_error(notebook_object, "No notebook page found.")
            return 0

        notebook_ref = notebook_object.ref
        if not notebook_ref.DeletePage(page_index):
            self.show_error(notebook_object, "Removing notebook page failed.")
            return 0

        if page_object is not None:
            self.widgets.pop(page_object.name, None)
            self.containers.pop(page_object.name, None)

        notebook_data = notebook_object.data if isinstance(notebook_object.data, dict) else {}
        pages = notebook_data.get("pages") if isinstance(notebook_data.get("pages"), list) else []
        if page_object is not None and page_object.name in pages:
            pages = [entry_name for entry_name in pages if entry_name != page_object.name]
        elif 0 <= page_index < len(pages):
            pages.pop(page_index)
        notebook_data["pages"] = pages
        notebook_object.data = notebook_data

        return 1

    def _render_listview_rows(self, listview: wx.ListCtrl, rows: list[list[Any]]) -> None:
        """
        Rebuilds all rows of a wx.ListCtrl from the provided row data.

        Parameters
        ----------

        listview : wx.ListCtrl
            Target list control.

        rows : list[list[Any]]
            Row data matrix.
        """
        listview.DeleteAllItems()
        for row in rows:
            if not isinstance(row, list):
                continue
            first_value = str(row[0]) if len(row) > 0 else ""
            row_index = listview.InsertItem(listview.GetItemCount(), first_value)
            for col_idx in range(1, len(row)):
                listview.SetItem(row_index, col_idx, str(row[col_idx]))

    def _render_grid_rows(self, grid: wxgrid.Grid, headers: list[str], rows: list[list[Any]]) -> None:
        """
        Rebuilds a wx.grid.Grid from header and row matrix data.
        """
        col_count = max(1, len(headers))
        row_count = max(1, len(rows))

        current_rows = grid.GetNumberRows()
        if current_rows < row_count:
            grid.AppendRows(row_count - current_rows)
        elif current_rows > row_count:
            grid.DeleteRows(0, current_rows - row_count)

        current_cols = grid.GetNumberCols()
        if current_cols < col_count:
            grid.AppendCols(col_count - current_cols)
        elif current_cols > col_count:
            grid.DeleteCols(0, current_cols - col_count)

        for col_idx in range(col_count):
            label = headers[col_idx] if col_idx < len(headers) else ""
            grid.SetColLabelValue(col_idx, str(label))

        for row_idx in range(row_count):
            row = rows[row_idx] if row_idx < len(rows) and isinstance(rows[row_idx], list) else []
            for col_idx in range(col_count):
                value = row[col_idx] if col_idx < len(row) else ""
                grid.SetCellValue(row_idx, col_idx, str(value))

        for col_idx in range(col_count):
            try:
                grid.AutoSizeColumn(col_idx, setAsMin=False)
            except Exception:
                pass

    def _render_dataview_rows(
        self,
        dataview: wxdataview.DataViewListCtrl,
        headers: list[str],
        rows: list[list[Any]],
        editable: int = 1,
        sortable: int = 1,
    ) -> None:
        """
        Rebuilds a DataViewListCtrl from header and row data.
        """
        if hasattr(dataview, "DeleteAllItems"):
            dataview.DeleteAllItems()

        if hasattr(dataview, "ClearColumns"):
            dataview.ClearColumns()

        column_flags = wxdataview.DATAVIEW_COL_RESIZABLE
        if int(sortable):
            column_flags |= wxdataview.DATAVIEW_COL_SORTABLE

        cell_mode = wxdataview.DATAVIEW_CELL_EDITABLE if int(editable) else wxdataview.DATAVIEW_CELL_INERT

        normalized_headers = [str(col) for col in headers] if len(headers) > 0 else ["Column 1"]
        for header in normalized_headers:
            dataview.AppendTextColumn(str(header), mode=cell_mode, flags=column_flags)

        col_count = len(normalized_headers)
        for row in rows:
            if not isinstance(row, list):
                continue
            prepared = [str(row[col_idx]) if col_idx < len(row) else "" for col_idx in range(col_count)]
            dataview.AppendItem(prepared)

    def _sort_grid_rows(self, name: str, column_index: int, ascending: int = 1) -> None:
        """
        Sorts stored grid row data by a column and re-renders widget.
        """
        object_entry = self.get_object(name)
        if object_entry.type != "Grid":
            self.internal_die(name, "Not a grid object.")

        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        rows = data.get("data") if isinstance(data.get("data"), list) else []
        headers = data.get("headers") if isinstance(data.get("headers"), list) else []
        col_count = max(len(headers), max((len(row) for row in rows if isinstance(row, list)), default=0))
        if column_index < 0 or column_index >= max(1, col_count):
            return

        def _sort_key(row: Any) -> tuple[int, Any]:
            if not isinstance(row, list) or column_index >= len(row):
                return (1, "")
            value = row[column_index]
            text = str(value).strip()
            try:
                return (0, float(text))
            except Exception:
                return (0, text.lower())

        reverse = not bool(int(ascending))
        rows.sort(key=_sort_key, reverse=reverse)
        data["data"] = rows
        data["sortcolumn"] = int(column_index)
        data["sortascending"] = 1 if int(ascending) else 0
        object_entry.data = data

        if isinstance(object_entry.ref, wxgrid.Grid):
            header_names = [str(col) for col in headers]
            self._render_grid_rows(object_entry.ref, header_names, rows)

    def _normalize_tree_path(self, path: Any) -> list[int]:
        """
        Normalizes tree-path input into a list of child indices.

        Parameters
        ----------

        path : Any
            Path value as int, list/tuple, or string (e.g. "0:1:2").

        Returns
        -------

        list[int]:
            Normalized index path.
        """
        if path is None:
            return []
        if isinstance(path, int):
            return [path] if path >= 0 else []
        if isinstance(path, (list, tuple)):
            result: list[int] = []
            for part in path:
                value = int(part)
                if value < 0:
                    self.internal_die("treepath", f"Negative path index '{value}' is invalid.")
                result.append(value)
            return result
        if isinstance(path, str):
            text = path.strip().replace("/", ":")
            if text == "":
                return []
            parts = [item for item in text.split(":") if item != ""]
            result = []
            for part in parts:
                value = int(part)
                if value < 0:
                    self.internal_die("treepath", f"Negative path index '{value}' is invalid.")
                result.append(value)
            return result
        self.internal_die("treepath", f"Unsupported tree path type '{type(path).__name__}'.")

    def _tree_find_item_by_path(self, tree: wx.TreeCtrl, root: wx.TreeItemId, path: list[int]) -> wx.TreeItemId:
        """
        Resolves a tree item id from a root-relative path.

        Parameters
        ----------

        tree : wx.TreeCtrl
            Target tree control.

        root : wx.TreeItemId
            Root item id.

        path : list[int]
            Root-relative child-index path.

        Returns
        -------

        wx.TreeItemId:
            Resolved item id, or invalid id if not found.
        """
        current = root
        for index in path:
            if not current.IsOk():
                return wx.TreeItemId()

            child, cookie = tree.GetFirstChild(current)
            current_index = 0
            while child.IsOk() and current_index < index:
                child, cookie = tree.GetNextChild(current, cookie)
                current_index += 1

            if not child.IsOk() or current_index != index:
                return wx.TreeItemId()
            current = child
        return current

    def _tree_append_from_node(self, tree: wx.TreeCtrl, parent: wx.TreeItemId, node: Any) -> wx.TreeItemId:
        """
        Appends one node (and optional descendants) from nested data.

        Parameters
        ----------

        tree : wx.TreeCtrl
            Target tree control.

        parent : wx.TreeItemId
            Parent item id.

        node : Any
            Node data (`label` or `[label, children]`).

        Returns
        -------

        wx.TreeItemId:
            Appended item id.
        """
        label = ""
        children: list[Any] = []

        if isinstance(node, (list, tuple)) and len(node) > 0:
            label = str(node[0])
            if len(node) > 1 and isinstance(node[1], (list, tuple)):
                children = list(node[1])
        else:
            label = str(node)

        item = tree.AppendItem(parent, label)
        for child in children:
            self._tree_append_from_node(tree, item, child)
        return item

    def add_treeview(
        self,
        Name: str,
        Type: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Headers: list[Any] | tuple[Any, ...],
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Treeview: Optional[wx.TreeCtrl] = None,
        Mode: Optional[str] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new tree-view widget.

        Parameters
        ----------

        Name : str
            Name of the tree-view object. Must be unique.

        Type : str
            Tree-view mode (`List` or `Tree`).

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled tree-view size `[width, height]`.

        Headers : list[Any] | tuple[Any, ...]
            Header/column definitions. First entry is used as root label.

        Data : list[Any] | tuple[Any, ...] | None, optional
            Optional nested tree data.

        Treeview : wx.TreeCtrl | None, optional
            Optional existing tree control to reuse.

        Mode : str | None, optional
            Selection mode compatibility hint (`single`, `multiple`, ...).

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.
        """
        tview_type = str(Type or "").strip().lower()
        if tview_type not in ("list", "tree"):
            self.internal_die(Name, "Wrong treeview type defined! Possible values are: 'List' or 'Tree'.")

        params = self._normalize(
            Name=Name,
            Type=Type,
            Position=Position,
            Size=Size,
            Headers=Headers,
            Data=Data,
            Treeview=Treeview,
            Mode=Mode,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "TreeView"
        self.widgets[object_entry.name] = object_entry

        headers_raw = params.get("headers")
        if not isinstance(headers_raw, (list, tuple)) or len(headers_raw) == 0:
            self.internal_die(Name, "No column header(s) defined!")
        headers = list(headers_raw)

        rows_raw = params.get("data")
        rows: list[Any] = list(rows_raw) if isinstance(rows_raw, (list, tuple)) else []

        mode = str(params.get("mode") or "single").lower()
        style = wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_DEFAULT_STYLE
        if mode == "multiple":
            style |= wx.TR_MULTIPLE
        if tview_type == "list":
            style |= wx.TR_HIDE_ROOT

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        scrolled_window = wx.ScrolledWindow(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.HSCROLL | wx.VSCROLL,
        )
        scrolled_window.SetScrollRate(10, 10)

        if isinstance(Treeview, wx.TreeCtrl):
            treeview = Treeview
            if treeview.GetParent() != scrolled_window:
                treeview.Reparent(scrolled_window)
        else:
            treeview = wx.TreeCtrl(
                scrolled_window,
                wx.ID_ANY,
                pos=(0, 0),
                size=wx.DefaultSize,
                style=style,
            )

        first_header = headers[0]
        if isinstance(first_header, (list, tuple)) and len(first_header) > 0:
            root_label = str(first_header[0])
        else:
            root_label = str(first_header)
        if root_label.strip() == "":
            root_label = "Root"

        root = treeview.AddRoot(root_label)
        for node in rows:
            self._tree_append_from_node(treeview, root, node)

        object_entry.ref = scrolled_window
        object_entry.data = {
            "treeview": treeview,
            "root": root,
            "headers": headers,
            "data": rows,
            "mode": mode,
            "view_type": "List" if tview_type == "list" else "Tree",
        }

        def _on_treeview_size(event: wx.Event, host: wx.ScrolledWindow = scrolled_window, ctrl: wx.TreeCtrl = treeview) -> None:
            ctrl.SetSize(host.GetClientSize())
            event.Skip()

        scrolled_window.Bind(wx.EVT_SIZE, _on_treeview_size)

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)
        treeview.SetSize(scrolled_window.GetClientSize())
        treeview.Expand(root)

    def get_treeview(self, Name: str, Keyname: Optional[str] = None) -> wx.TreeCtrl:
        """
        Returns the underlying wx.TreeCtrl of a TreeView object.

        Parameters
        ----------

        Name : str
            Name of the tree-view widget. Must be unique.

        Keyname : str | None, optional
            Optional compatibility key. Accepted values: `list`, `tree`.

        Returns
        -------

        wx.TreeCtrl:
            Native tree-control reference.
        """
        object_entry = self.get_object(Name)
        if object_entry.type not in ("TreeView", "List", "Tree"):
            self.internal_die(Name, "Not a treeview object.")

        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        treeview = data.get("treeview")
        if not isinstance(treeview, wx.TreeCtrl):
            self.internal_die(Name, "No treeview reference available.")

        if Keyname is None:
            return treeview

        key = self._extend(str(Keyname).lower())
        if key in ("list", "tree"):
            return treeview

        self.internal_die(Name, f'"get_treeview" returns TreeView reference only. Use "get_value" for "{key}" instead.')

    def modify_tree_data(self, Name: str, **commands: Any) -> Any:
        """
        Modifies tree-view data (`add`, `change`, `delete`).

        Parameters
        ----------

        Name : str
            Name of the tree-view widget. Must be unique.

        **commands : Any
            Exactly one command mapping.

        Returns
        -------

        Any:
            Added tree item id for `add`, else `0`.
        """
        if len(commands) != 1:
            self.internal_die(Name, "Exactly one command must be provided.")

        object_entry = self.get_object(Name)
        if object_entry.type not in ("TreeView", "List", "Tree"):
            self.internal_die(Name, "Not a treeview object.")

        data_map = object_entry.data if isinstance(object_entry.data, dict) else {}
        treeview = data_map.get("treeview")
        root = data_map.get("root")
        rows = data_map.get("data") if isinstance(data_map.get("data"), list) else []

        if not isinstance(treeview, wx.TreeCtrl) or not isinstance(root, wx.TreeItemId) or not root.IsOk():
            self.internal_die(Name, "No treeview/root reference available.")

        command_raw = next(iter(commands.keys()))
        payload = commands[command_raw]
        command = self._extend(str(command_raw).lower())

        if command == "add":
            if not isinstance(payload, (list, tuple)) or len(payload) < 2:
                self.internal_die(Name, '"add" expects [path, node].')

            path = self._normalize_tree_path(payload[0])
            node = payload[1]
            parent_item = root if len(path) == 0 else self._tree_find_item_by_path(treeview, root, path)
            if not parent_item.IsOk():
                self.internal_die(Name, f"Tree path '{path}' not found.")

            new_item = self._tree_append_from_node(treeview, parent_item, node)

            target_rows = rows
            for depth, idx in enumerate(path):
                if idx < 0 or idx >= len(target_rows):
                    self.internal_die(Name, f"Tree path '{path}' not found.")
                current_node = target_rows[idx]
                if not isinstance(current_node, list):
                    current_node = [str(current_node), []]
                    target_rows[idx] = current_node
                if len(current_node) < 2 or not isinstance(current_node[1], list):
                    if len(current_node) < 2:
                        current_node.append([])
                    else:
                        current_node[1] = []
                target_rows = current_node[1]

            if isinstance(node, tuple):
                node = list(node)
            elif not isinstance(node, list):
                node = [str(node), []]
            target_rows.append(node)

            data_map["data"] = rows
            object_entry.data = data_map
            return new_item

        if command == "change":
            if not isinstance(payload, (list, tuple)) or len(payload) < 3:
                self.internal_die(Name, '"change" expects [path, index, value].')

            path = self._normalize_tree_path(payload[0])
            value = payload[2]
            target_item = self._tree_find_item_by_path(treeview, root, path)
            if not target_item.IsOk():
                self.internal_die(Name, f"Tree path '{path}' not found.")

            treeview.SetItemText(target_item, str(value))

            target_rows = rows
            for depth, idx in enumerate(path):
                if idx < 0 or idx >= len(target_rows):
                    target_rows = []
                    break
                if depth == len(path) - 1:
                    node = target_rows[idx]
                    if isinstance(node, list) and len(node) > 0:
                        node[0] = value
                        target_rows[idx] = node
                    else:
                        target_rows[idx] = [value, []]
                    break
                node = target_rows[idx]
                if not isinstance(node, list):
                    break
                if len(node) < 2 or not isinstance(node[1], list):
                    node_children: list[Any] = []
                    if len(node) < 2:
                        node.append(node_children)
                    else:
                        node[1] = node_children
                target_rows = node[1]

            data_map["data"] = rows
            object_entry.data = data_map
            return 0

        if command == "delete":
            path = self._normalize_tree_path(payload)
            if len(path) == 0:
                self.internal_die(Name, "Deleting the root node is not supported.")

            target_item = self._tree_find_item_by_path(treeview, root, path)
            if not target_item.IsOk():
                self.internal_die(Name, f"Tree path '{path}' not found.")
            treeview.Delete(target_item)

            parent_rows = rows
            for idx in path[:-1]:
                if idx < 0 or idx >= len(parent_rows):
                    parent_rows = []
                    break
                node = parent_rows[idx]
                if not isinstance(node, list) or len(node) < 2 or not isinstance(node[1], list):
                    parent_rows = []
                    break
                parent_rows = node[1]
            delete_index = path[-1]
            if 0 <= delete_index < len(parent_rows):
                parent_rows.pop(delete_index)

            data_map["data"] = rows
            object_entry.data = data_map
            return 0

        self.internal_die(Name, f"Unknown command '{command}' for modify_tree_data. Use 'add', 'change' or 'delete'.")

    def add_listview(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Headers: list[Any] | tuple[Any, ...],
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new list-view widget.

        Parameters
        ----------

        Name : str
            Name of the list view object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled list-view size `[width, height]`.

        Headers : list[Any] | tuple[Any, ...]
            Sequence of column titles.

        Data : list[Any] | tuple[Any, ...] | None, optional
            Optional initial row matrix.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Headers=Headers,
            Data=Data,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "ListView"
        self.widgets[object_entry.name] = object_entry

        headers_raw = params.get("headers")
        headers = [str(col) for col in headers_raw] if isinstance(headers_raw, (list, tuple)) else []

        rows_raw = params.get("data")
        rows: list[list[Any]] = []
        if isinstance(rows_raw, (list, tuple)):
            for row in rows_raw:
                if isinstance(row, (list, tuple)):
                    rows.append(list(row))

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        scrolled_window = wx.ScrolledWindow(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.HSCROLL | wx.VSCROLL,
        )
        scrolled_window.SetScrollRate(10, 10)

        listview = wx.ListCtrl(
            scrolled_window,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
        )

        for col_index, header in enumerate(headers):
            listview.InsertColumn(col_index, header)

        self._render_listview_rows(listview, rows)
        for col_index in range(max(1, len(headers))):
            listview.SetColumnWidth(col_index, wx.LIST_AUTOSIZE_USEHEADER)

        object_entry.ref = scrolled_window
        object_entry.data = {
            "listview": listview,
            "headers": headers,
            "data": rows,
        }

        def _on_listview_size(event: wx.Event, host: wx.ScrolledWindow = scrolled_window, ctrl: wx.ListCtrl = listview) -> None:
            ctrl.SetSize(host.GetClientSize())
            event.Skip()

        scrolled_window.Bind(wx.EVT_SIZE, _on_listview_size)

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)
        listview.SetSize(scrolled_window.GetClientSize())

    def add_grid(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Headers: Optional[list[Any] | tuple[Any, ...]] = None,
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Editable: int = 1,
        Sortable: int = 1,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a grid widget with optional editing and column sorting.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Headers=Headers,
            Data=Data,
            Editable=Editable,
            Sortable=Sortable,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "Grid"
        self.widgets[object_entry.name] = object_entry

        headers_raw = params.get("headers")
        headers = [str(col) for col in headers_raw] if isinstance(headers_raw, (list, tuple)) else []

        rows_raw = params.get("data")
        rows: list[list[Any]] = []
        if isinstance(rows_raw, (list, tuple)):
            for row in rows_raw:
                if isinstance(row, (list, tuple)):
                    rows.append(list(row))

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        grid = wxgrid.Grid(provisional_parent, wx.ID_ANY, pos=(0, 0), size=wx.DefaultSize)
        grid.CreateGrid(1, 1)

        editable = 1 if int(params.get("editable") or 0) else 0
        sortable = 1 if int(params.get("sortable") or 0) else 0

        object_entry.ref = grid
        object_entry.data = {
            "headers": headers,
            "data": rows,
            "editable": editable,
            "sortable": sortable,
            "sortcolumn": -1,
            "sortascending": 1,
        }

        self._render_grid_rows(grid, headers, rows)
        grid.EnableEditing(bool(editable))

        def _on_grid_cell_changed(event: wxgrid.GridEvent, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            grid_data = entry.data if isinstance(entry.data, dict) else {}
            matrix = grid_data.get("data") if isinstance(grid_data.get("data"), list) else []
            row_idx = int(event.GetRow())
            col_idx = int(event.GetCol())
            if row_idx >= 0 and col_idx >= 0:
                while len(matrix) <= row_idx:
                    matrix.append([])
                while len(matrix[row_idx]) <= col_idx:
                    matrix[row_idx].append("")
                if isinstance(entry.ref, wxgrid.Grid):
                    matrix[row_idx][col_idx] = entry.ref.GetCellValue(row_idx, col_idx)
                grid_data["data"] = matrix
                entry.data = grid_data
            event.Skip()

        def _on_grid_label_click(event: wxgrid.GridEvent, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            grid_data = entry.data if isinstance(entry.data, dict) else {}
            if int(grid_data.get("sortable", 0)) == 0:
                event.Skip()
                return
            if int(event.GetRow()) != -1:
                event.Skip()
                return

            col_idx = int(event.GetCol())
            previous_col = int(grid_data.get("sortcolumn", -1))
            previous_asc = int(grid_data.get("sortascending", 1))
            new_asc = 0 if previous_col == col_idx and previous_asc == 1 else 1
            self._sort_grid_rows(name, col_idx, new_asc)
            event.Skip()

        grid.Bind(wxgrid.EVT_GRID_CELL_CHANGED, _on_grid_cell_changed)
        grid.Bind(wxgrid.EVT_GRID_LABEL_LEFT_CLICK, _on_grid_label_click)

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_dataview(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Headers: Optional[list[Any] | tuple[Any, ...]] = None,
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Editable: int = 1,
        Sortable: int = 1,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a DataViewCtrl widget for tabular data.
        """
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Headers=Headers,
            Data=Data,
            Editable=Editable,
            Sortable=Sortable,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        object_entry = self._new_widget(**params)
        object_entry.type = "DataViewCtrl"
        self.widgets[object_entry.name] = object_entry

        headers_raw = params.get("headers")
        headers = [str(col) for col in headers_raw] if isinstance(headers_raw, (list, tuple)) else []

        rows_raw = params.get("data")
        rows: list[list[Any]] = []
        if isinstance(rows_raw, (list, tuple)):
            for row in rows_raw:
                if isinstance(row, (list, tuple)):
                    rows.append(list(row))

        editable = 1 if int(params.get("editable") or 0) else 0
        sortable = 1 if int(params.get("sortable") or 0) else 0

        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        dataview = wxdataview.DataViewListCtrl(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.BORDER_THEME,
        )

        object_entry.ref = dataview
        object_entry.data = {
            "headers": headers,
            "data": rows,
            "editable": editable,
            "sortable": sortable,
        }

        self._render_dataview_rows(dataview, headers, rows, editable, sortable)

        def _on_dataview_changed(event: wxdataview.DataViewEvent, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            if not isinstance(entry.ref, wxdataview.DataViewListCtrl):
                event.Skip()
                return
            data_map = entry.data if isinstance(entry.data, dict) else {}
            matrix = data_map.get("data") if isinstance(data_map.get("data"), list) else []

            row_index = int(entry.ref.ItemToRow(event.GetItem())) if event.GetItem().IsOk() else -1
            col_index = int(event.GetColumn())
            if row_index >= 0 and col_index >= 0:
                while len(matrix) <= row_index:
                    matrix.append([])
                while len(matrix[row_index]) <= col_index:
                    matrix[row_index].append("")
                try:
                    matrix[row_index][col_index] = entry.ref.GetTextValue(row_index, col_index)
                except Exception:
                    pass
                data_map["data"] = matrix
                entry.data = data_map
            event.Skip()

        dataview.Bind(wxdataview.EVT_DATAVIEW_ITEM_VALUE_CHANGED, _on_dataview_changed)

        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_dataview_ctrl(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Headers: Optional[list[Any] | tuple[Any, ...]] = None,
        Data: Optional[list[Any] | tuple[Any, ...]] = None,
        Editable: int = 1,
        Sortable: int = 1,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for add_dataview.
        """
        self.add_dataview(
            Name=Name,
            Position=Position,
            Size=Size,
            Headers=Headers,
            Data=Data,
            Editable=Editable,
            Sortable=Sortable,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def get_listview(self, Name: str, Keyname: Optional[str] = None) -> wx.ListCtrl:
        """
        Returns the underlying wx.ListCtrl of a ListView object.

        Parameters
        ----------

        Name : str
            Name of the list-view widget. Must be unique.

        Keyname : str | None, optional
            Optional compatibility key. Accepted values: `list`.

        Returns
        -------

        wx.ListCtrl:
            Native list-control reference.
        """
        object_entry = self.get_object(Name)
        if object_entry.type not in ("ListView", "List"):
            self.internal_die(Name, "Not a listview object.")

        data = object_entry.data if isinstance(object_entry.data, dict) else {}
        listview = data.get("listview")
        if not isinstance(listview, wx.ListCtrl):
            self.internal_die(Name, "No listview reference available.")

        if Keyname is None:
            return listview

        key = self._extend(str(Keyname).lower())
        if key == "list":
            return listview

        self.internal_die(Name, f'"get_listview" returns ListView reference only. Use "get_value" for "{key}" instead.')

    def modify_list_data(self, Name: str, **commands: Any) -> int:
        """
        Modifies list-view row or cell data.

        Parameters
        ----------

        Name : str
            Name of the list-view widget. Must be unique.

        **commands : Any
            Exactly one command mapping, e.g. `push=[...]`, `delete=2`,
            `set=[row, col, value]`, `clear=None`.

        Returns
        -------

        int:
            `0` on success.
        """
        if len(commands) != 1:
            self.internal_die(Name, "Exactly one command must be provided.")

        object_entry = self.get_object(Name)
        if object_entry.type not in ("ListView", "List"):
            self.internal_die(Name, "Not a listview object.")

        data_map = object_entry.data if isinstance(object_entry.data, dict) else {}
        listview = data_map.get("listview")
        if not isinstance(listview, wx.ListCtrl):
            self.internal_die(Name, "No listview reference available.")

        rows_value = data_map.get("data")
        rows: list[list[Any]] = []
        if isinstance(rows_value, list):
            for row in rows_value:
                if isinstance(row, list):
                    rows.append(row)
                elif isinstance(row, tuple):
                    rows.append(list(row))
        data_map["data"] = rows

        command_raw = next(iter(commands.keys()))
        modification = commands[command_raw]
        command = self._extend(str(command_raw).lower())

        if command == "set":
            if not isinstance(modification, (list, tuple)) or len(modification) < 3:
                self.internal_die(Name, '"set" expects [row, column, value].')
            row_index = int(modification[0])
            col_index = int(modification[1])
            value = modification[2]
            if row_index < 0 or row_index >= len(rows):
                self.internal_die(Name, f'Row index "{row_index}" out of range.')
            if col_index < 0:
                self.internal_die(Name, f'Column index "{col_index}" out of range.')

            row = rows[row_index]
            while len(row) <= col_index:
                row.append("")
            row[col_index] = value
            rows[row_index] = row
            listview.SetItem(row_index, col_index, str(value))

        elif command == "push":
            row = list(modification) if isinstance(modification, (list, tuple)) else [modification]
            rows.append(row)
            row_index = listview.InsertItem(listview.GetItemCount(), str(row[0]) if len(row) > 0 else "")
            for col_index in range(1, len(row)):
                listview.SetItem(row_index, col_index, str(row[col_index]))

        elif command == "unshift":
            row = list(modification) if isinstance(modification, (list, tuple)) else [modification]
            rows.insert(0, row)
            self._render_listview_rows(listview, rows)

        elif command == "pop":
            if len(rows) > 0:
                rows.pop()
            if listview.GetItemCount() > 0:
                listview.DeleteItem(listview.GetItemCount() - 1)

        elif command == "shift":
            if len(rows) > 0:
                rows.pop(0)
            if listview.GetItemCount() > 0:
                listview.DeleteItem(0)

        elif command == "delete":
            if modification is None:
                self.internal_die(Name, '"delete" expects a row index.')
            row_index = int(modification)
            if row_index < 0 or row_index >= len(rows):
                self.internal_die(Name, f'Row index "{row_index}" out of range.')
            rows.pop(row_index)
            listview.DeleteItem(row_index)

        elif command == "clear":
            rows.clear()
            listview.DeleteAllItems()

        else:
            self.internal_die(
                Name,
                f"Unknown parameter \"{command}\". Possible values are: 'push' 'pop', 'unshift', 'shift', 'delete' or 'clear'.",
            )

        data_map["data"] = rows
        object_entry.data = data_map
        return 0

    def add_separator(
        self,
        Name: str,
        Orientation: str,
        Position: list[int] | tuple[int, int],
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a horizontal or vertical separator widget.

        Parameters
        ----------

        Name : str
            Name of the separator. Must be unique.

        Orientation : str
            Orientation (`horizontal` or `vertical`).

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Frame : str | None, optional
            Optional parent container name.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_separator(
            Name="sepMain",
            Orientation="horizontal",
            Position=[10, 120],
            Size=[220, 2],
        )

        Notes
        -----

        Menu separators are not created with this function; in Gtk/SimpleGtk2
        they are created via `add_menu_item(..., Type="separator")`.
        """
        # normalize incoming separator parameters
        params = self._normalize(
            Name=Name,
            Orientation=Orientation,
            Position=Position,
            Size=Size,
            Frame=Frame,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Separator"
        self.widgets[object_entry.name] = object_entry

        # check orientation and map it to wx static line style
        orientation = str(params.get("orientation") or "").lower()
        if orientation == "horizontal":
            wx_orientation = wx.LI_HORIZONTAL
        elif orientation == "vertical":
            wx_orientation = wx.LI_VERTICAL
        else:
            self.internal_die(object_entry.name, f"Wrong orientation '{orientation}' defined!")
            return

        # create separator with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        separator = wx.StaticLine(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx_orientation,
        )

        # store native reference and separator metadata
        object_entry.ref = separator
        object_entry.data = {
            "orientation": orientation,
            "separator": separator,
        }

        # apply common setup and position separator
        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_label(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Title: str,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Widget: Optional[str] = None,
        Justify: Optional[str] = None,
        Wrapped: int = 0,
        Tooltip: Optional[str] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new label widget.

        Parameters
        ----------

        Name : str
            Name of the label object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Title : str
            Label text.

        Frame : str | None, optional
            Optional parent container name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Widget : str | None, optional
            Optional linked target widget for mnemonic focus.

        Justify : str | None, optional
            Text justification (`left`, `center`, `right`, `fill`).

        Wrapped : int, optional
            Wrap mode (`0` disabled, `1` enabled).

        Tooltip : str | None, optional
            Optional tooltip text.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_label(
            Name="label1",
            Position=[10, 20],
            Title="A Label",
            Justify="left",
        )
        """
        # normalize incoming label parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Title=Title,
            Frame=Frame,
            Font=Font,
            Widget=Widget,
            Justify=Justify,
            Wrapped=Wrapped,
            Tooltip=Tooltip,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Label"
        self.widgets[object_entry.name] = object_entry

        # label-specific fields
        object_entry.data = {
            "widget": params.get("widget"),
            "wrapped": int(params.get("wrapped") or 0),
            "justify": params.get("justify"),
        }

        # remove wrapped indentation from multiline strings
        object_entry.title = "\n".join(line.strip() for line in str(object_entry.title or "").splitlines())

        # create label text and convert mnemonic markers if needed
        label_text = str(object_entry.title or "")
        mnemonic_char = None
        if self.is_underlined(label_text):
            mnemonic_char = self._extract_mnemonic_char(label_text)
            label_text = label_text.replace("__", "\0")
            label_text = label_text.replace("_", "&")
            label_text = label_text.replace("\0", "_")

        # create native label with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        label = wx.StaticText(provisional_parent, wx.ID_ANY, label_text, pos=(0, 0), size=wx.DefaultSize)
        object_entry.ref = label

        # apply common setup (tooltip, size, sensitive)
        self._set_commons(object_entry.name, **params)

        # set wrapping behavior (wx uses wrap width)
        if object_entry.data["wrapped"]:
            label.Wrap(-1)

        # set justification if defined
        justify = object_entry.data.get("justify")
        justify_map = {
            "left": wx.ALIGN_LEFT,
            "center": wx.ALIGN_CENTER_HORIZONTAL,
            "right": wx.ALIGN_RIGHT,
            "fill": wx.ALIGN_CENTER_HORIZONTAL,
        }
        if isinstance(justify, str) and justify in justify_map:
            label.SetWindowStyleFlag(justify_map[justify])

        # apply optional font settings
        font = params.get("font")
        if font is not None:
            self.set_font(object_entry.name, font)

        # bind mnemonic to linked widget if requested
        linked_name = params.get("widget")
        if mnemonic_char and isinstance(linked_name, str):
            self._bind_label_mnemonic(mnemonic_char, linked_name)

        # place label in container
        self._add_to_container(object_entry.name)

    def add_entry(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Title: Optional[str] = None,
        Frame: Optional[str] = None,
        Font: Optional[list[Any] | tuple[Any, ...]] = None,
        Align: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new single-line text entry widget.

        Parameters
        ----------

        Name : str
            Name of the text entry object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled entry size `[width, height]`.

        Title : str | None, optional
            Initial text value.

        Frame : str | None, optional
            Optional parent container name.

        Font : list[Any] | tuple[Any, ...] | None, optional
            Optional font definition.

        Align : str | None, optional
            Text alignment (`left`, `center`, `right`).

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_entry(
            Name="entry1",
            Position=[200, 20],
            Size=[100, 20],
            Title="A text entry field",
            Align="right",
        )
        """
        # normalize incoming entry parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Title=Title,
            Frame=Frame,
            Font=Font,
            Align=Align,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "TextEntry"
        self.widgets[object_entry.name] = object_entry

        # entry-specific defaults
        align = str(params.get("align") or "left").lower()
        font = params.get("font")
        text = str(params.get("title") or "")

        # map textual alignment to wx text-control flags
        align_map = {
            "left": wx.TE_LEFT,
            "center": wx.TE_CENTER,
            "right": wx.TE_RIGHT,
        }
        style = align_map.get(align, wx.TE_LEFT)

        # create native text control with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        entry = wx.TextCtrl(
            provisional_parent,
            wx.ID_ANY,
            text,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        # add widget reference to object metadata
        object_entry.ref = entry

        # apply font if one was provided
        if font is not None:
            self.set_font(object_entry.name, font)

        # keep object title synchronized with current entry text
        def _on_entry_changed(event: wx.Event, name: str = object_entry.name) -> None:
            self.get_object(name).title = entry.GetValue()
            event.Skip()

        entry.Bind(wx.EVT_TEXT, _on_entry_changed)

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position entry in target container
        self._add_to_container(object_entry.name)

    def add_combo_box(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Data: list[Any] | tuple[Any, ...],
        Start: int = 0,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Frame: Optional[str] = None,
        Columns: Optional[int] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new combo box widget.

        Parameters
        ----------

        Name : str
            Name of the combo box object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Data : list[Any] | tuple[Any, ...]
            Sequence of combo entries.

        Start : int, optional
            Initial selected index, default is 0.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Frame : str | None, optional
            Optional parent container name.

        Columns : int | None, optional
            Optional wrap column count (compatibility metadata).

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_combo_box(
            Name="combo_res",
            Position=[10, 70],
            Data=["800x600", "1280x720", "1920x1080"],
            Start=1,
        )
        """
        # normalize incoming combo-box parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Data=Data,
            Start=Start,
            Size=Size,
            Frame=Frame,
            Columns=Columns,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "ComboBox"
        self.widgets[object_entry.name] = object_entry

        # normalize and persist combo data values as strings
        raw_data = params.get("data")
        if isinstance(raw_data, (list, tuple)):
            values = [str(item) for item in raw_data]
        else:
            values = []

        start_index = int(params.get("start") or 0)
        if len(values) == 0:
            start_index = -1
        else:
            start_index = max(0, min(start_index, len(values) - 1))

        # create readonly combo box with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        combo_box = wx.ComboBox(
            provisional_parent,
            wx.ID_ANY,
            value="",
            pos=(0, 0),
            size=wx.DefaultSize,
            choices=values,
            style=wx.CB_READONLY,
        )

        if start_index >= 0:
            combo_box.SetSelection(start_index)

        # add widget reference and combo-specific metadata
        object_entry.ref = combo_box
        object_entry.title = combo_box.GetStringSelection() if start_index >= 0 else ""
        object_entry.data = {
            "data": values,
            "start": start_index,
            "columns": int(params.get("columns")) if params.get("columns") is not None else None,
            "active": start_index,
        }

        # keep metadata synchronized on selection changes
        def _on_combo_changed(event: wx.Event, name: str = object_entry.name) -> None:
            entry = self.get_object(name)
            if entry.ref is None:
                return
            index = int(entry.ref.GetSelection())
            if isinstance(entry.data, dict):
                entry.data["active"] = index
            entry.title = entry.ref.GetStringSelection() if index >= 0 else ""
            event.Skip()

        combo_box.Bind(wx.EVT_COMBOBOX, _on_combo_changed)

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position combo box in target container
        self._add_to_container(object_entry.name)

    def add_slider(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Orientation: str,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Start: float = 0,
        Minimum: float = 0,
        Maximum: float = 100,
        Step: float = 1,
        DrawValue: int = 1,
        ValuePosition: str = "top",
        Digits: int = 0,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new horizontal or vertical slider widget.

        Parameters
        ----------

        Name : str
            Name of the slider object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Orientation : str
            Slider orientation (`horizontal` or `vertical`).

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Start : float, optional
            Initial slider value.

        Minimum : float, optional
            Minimum allowed value.

        Maximum : float, optional
            Maximum allowed value.

        Step : float, optional
            Step increment.

        DrawValue : int, optional
            Value-display flag for compatibility metadata.

        ValuePosition : str, optional
            Value-display position metadata (`top`, `left`, `right`, `bottom`).

        Digits : int, optional
            Decimal precision metadata for value formatting.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_slider(
            Name="hslider",
            Position=[10, 220],
            Size=[200, -1],
            Orientation="horizontal",
            Start=5,
            Minimum=0,
            Maximum=100,
            Step=1,
            Digits=1,
            Tooltip="Round and round we go",
        )
        """
        # normalize incoming slider parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Orientation=Orientation,
            Size=Size,
            Start=Start,
            Minimum=Minimum,
            Maximum=Maximum,
            Step=Step,
            DrawValue=DrawValue,
            ValuePosition=ValuePosition,
            Digits=Digits,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Slider"
        self.widgets[object_entry.name] = object_entry

        # read and validate slider-specific values
        orientation = str(params.get("orientation") or "horizontal").lower()
        start = float(params.get("start") or 0)
        minimum = float(params.get("minimum") or 0)
        maximum = float(params.get("maximum") or 100)
        step = float(params.get("step") or 1)
        digits = int(params.get("digits") or 0)
        draw_value = 1 if int(params.get("drawvalue") or 0) else 0
        value_position = str(params.get("valueposition") or "top").lower()

        # reject unsupported orientation values
        if orientation not in ("horizontal", "vertical"):
            self.show_error(object_entry, f"Invalid orientation: '{orientation}'")
            return

        # wx.Slider is integer-based, so keep a safe integer range
        min_int = int(round(minimum))
        max_int = int(round(maximum))
        if max_int < min_int:
            min_int, max_int = max_int, min_int
        value_int = int(round(start))
        value_int = max(min_int, min(value_int, max_int))
        line_step = max(1, int(round(abs(step))))

        # map orientation to wx slider style flags
        style = wx.SL_HORIZONTAL if orientation == "horizontal" else wx.SL_VERTICAL
        style |= wx.SL_AUTOTICKS

        # create native slider with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        slider = wx.Slider(
            provisional_parent,
            wx.ID_ANY,
            value_int,
            min_int,
            max_int,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )
        slider.SetLineSize(line_step)
        slider.SetPageSize(max(1, line_step * 10))

        # add widget reference and range metadata to object state
        object_entry.ref = slider
        object_entry.data = {
            "start": start,
            "value": value_int,
            "minimum": minimum,
            "maximum": maximum,
            "step": step,
            "orientation": orientation,
            "drawvalue": draw_value,
            "valueposition": value_position,
            "digits": digits,
        }

        # keep value metadata synchronized whenever slider changes
        def _on_slider_value_changed(event: wx.Event, name: str = object_entry.name) -> None:
            value = slider.GetValue()
            self.get_object(name).data["value"] = value
            event.Skip()

        slider.Bind(wx.EVT_SLIDER, _on_slider_value_changed)

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position the slider in its target container
        self._add_to_container(object_entry.name)

    def add_progress_bar(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: Optional[list[int] | tuple[int, int]] = None,
        Mode: str = "percent",
        Steps: int = 100,
        Orient: str = "horizontal",
        Timer: int = 100,
        Align: str = "left",
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new progress bar widget.

        Parameters
        ----------

        Name : str
            Name of the progress-bar object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Mode : str, optional
            Progress mode (`percent` or `pulse`).

        Steps : int, optional
            Logical progress range maximum.

        Orient : str, optional
            Orientation (`horizontal` or `vertical`).

        Timer : int, optional
            Compatibility timer metadata in milliseconds.

        Align : str, optional
            Compatibility alignment metadata (`left` or `right`).

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_progress_bar(Name="prog1", Position=[20, 20], Size=[200, 18], Mode="percent", Steps=100)
        """
        # normalize incoming progress-bar parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Mode=Mode,
            Steps=Steps,
            Orient=Orient,
            Timer=Timer,
            Align=Align,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "ProgressBar"
        self.widgets[object_entry.name] = object_entry

        # read and validate progress-bar specific values
        mode = str(params.get("mode") or "percent").lower()
        if mode not in ("percent", "pulse"):
            mode = "percent"

        steps = int(params.get("steps") or 100)
        if steps <= 0:
            steps = 100

        orientation = str(params.get("orientation") or "horizontal").lower()
        if orientation not in ("horizontal", "vertical"):
            orientation = "horizontal"

        align = str(params.get("align") or "left").lower()
        if align not in ("left", "right"):
            align = "left"

        timer = max(1, int(params.get("timer") or 100))

        # map orientation into wx.Gauge style and create native widget
        style = wx.GA_HORIZONTAL if orientation == "horizontal" else wx.GA_VERTICAL
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        gauge = wx.Gauge(
            provisional_parent,
            wx.ID_ANY,
            range=steps,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        # initialize widget value based on selected mode
        value = 0
        if mode == "pulse":
            gauge.Pulse()
        else:
            gauge.SetValue(value)

        # store native reference and metadata in WidgetEntry
        object_entry.ref = gauge
        object_entry.data = {
            "mode": mode,
            "steps": steps,
            "orientation": orientation,
            "timer": timer,
            "align": align,
            "value": value,
        }

        # apply common setup and place widget in target container
        self._set_commons(object_entry.name, **params)
        self._add_to_container(object_entry.name)

    def add_progressbar(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: Optional[list[int] | tuple[int, int]] = None,
        Mode: str = "percent",
        Steps: int = 100,
        Orient: str = "horizontal",
        Timer: int = 100,
        Align: str = "left",
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Compatibility alias for `add_progress_bar`.

        Parameters
        ----------

        Name : str
            Name of the progress-bar object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Mode : str, optional
            Progress mode (`percent` or `pulse`).

        Steps : int, optional
            Logical progress range maximum.

        Orient : str, optional
            Orientation (`horizontal` or `vertical`).

        Timer : int, optional
            Compatibility timer metadata in milliseconds.

        Align : str, optional
            Compatibility alignment metadata (`left` or `right`).

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_progressbar(Name="prog1", Position=[20, 20], Size=[200, 18], Mode="percent", Steps=100)
        """
        # forward compatibility call to the canonical method name
        self.add_progress_bar(
            Name=Name,
            Position=Position,
            Size=Size,
            Mode=Mode,
            Steps=Steps,
            Orient=Orient,
            Timer=Timer,
            Align=Align,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

    def _configure_scrollbar(
        self,
        widget: wx.ScrollBar,
        minimum: float,
        maximum: float,
        step: float,
        active_value: float,
    ) -> float:
        """
        Normalizes and applies scrollbar range/thumb settings.

        Parameters
        ----------

        widget : wx.ScrollBar
            Native scrollbar widget reference.

        minimum : float
            Logical minimum value.

        maximum : float
            Logical maximum value.

        step : float
            Logical step size.

        active_value : float
            Logical active value.

        Returns
        -------

        float:
            Effective logical value after clamping.
        """
        min_int = int(round(minimum))
        max_int = int(round(maximum))
        if max_int < min_int:
            min_int, max_int = max_int, min_int

        step_int = max(1, int(round(abs(step))))
        page_size = max(1, step_int * 10)

        # wx.ScrollBar uses thumb-position in a [0..range-thumb] model
        span = max(1, max_int - min_int)
        thumb_size = max(1, step_int)
        range_total = max(thumb_size + 1, span + thumb_size)

        requested_position = int(round(active_value)) - min_int
        max_position = max(0, range_total - thumb_size)
        position = max(0, min(requested_position, max_position))

        widget.SetScrollbar(position, thumb_size, range_total, page_size)
        return float(min_int + position)

    def add_scrollbar(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Orientation: str,
        Size: Optional[list[int] | tuple[int, int]] = None,
        Start: float = 0,
        Minimum: float = 0,
        Maximum: float = 100,
        Step: float = 1,
        Digits: int = 0,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new horizontal or vertical scrollbar widget.

        Parameters
        ----------

        Name : str
            Name of the scrollbar object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Orientation : str
            Scrollbar orientation (`horizontal` or `vertical`).

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Start : float, optional
            Initial active value.

        Minimum : float, optional
            Minimum allowed value.

        Maximum : float, optional
            Maximum allowed value.

        Step : float, optional
            Step increment.

        Digits : int, optional
            Decimal precision metadata for compatibility.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_scrollbar(
            Name="hscroll",
            Position=[10, 220],
            Size=[200, -1],
            Orientation="horizontal",
            Start=5,
            Minimum=0,
            Maximum=100,
            Step=1,
            Digits=1,
            Tooltip="From left to right",
            Frame="frame2",
        )
        """
        # normalize incoming scrollbar parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Orientation=Orientation,
            Size=Size,
            Start=Start,
            Minimum=Minimum,
            Maximum=Maximum,
            Step=Step,
            Digits=Digits,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "Scrollbar"
        self.widgets[object_entry.name] = object_entry

        # read and validate scrollbar-specific values
        orientation = str(params.get("orientation") or "horizontal").lower()
        minimum = float(params.get("minimum") or 0)
        maximum = float(params.get("maximum") or 100)
        step = float(params.get("step") or 1)
        start = float(params.get("start") or 0)
        digits = int(params.get("digits") or 0)

        if orientation == "horizontal":
            style = wx.SB_HORIZONTAL
        elif orientation == "vertical":
            style = wx.SB_VERTICAL
        else:
            self.internal_die(object_entry.name, f"Wrong orientation '{orientation}' defined!")
            return

        # create native scrollbar with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        scrollbar = wx.ScrollBar(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=style,
        )

        # apply normalized scrollbar model and store metadata
        effective_value = self._configure_scrollbar(scrollbar, minimum, maximum, step, start)
        object_entry.ref = scrollbar
        object_entry.data = {
            "value": effective_value,
            "start": start,
            "minimum": minimum,
            "maximum": maximum,
            "step": step,
            "digits": digits,
            "orientation": orientation,
        }

        # keep value metadata synchronized whenever scrollbar moves
        def _on_scroll_changed(event: wx.Event, name: str = object_entry.name) -> None:
            current_object = self.get_object(name)
            current_data = current_object.data if isinstance(current_object.data, dict) else {}
            base_min = float(current_data.get("minimum", 0))
            current_data["value"] = base_min + float(scrollbar.GetThumbPosition())
            current_object.data = current_data
            event.Skip()

        scrollbar.Bind(wx.EVT_SCROLL, _on_scroll_changed)

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position scrollbar in target container
        self._add_to_container(object_entry.name)

    def add_drawing_area(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Frame: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new drawing area widget.

        Parameters
        ----------

        Name : str
            Name of the drawing area. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled drawing area size `[width, height]`.

        Frame : str | None, optional
            Optional parent container name.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional event callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_drawing_area(
            Name="drawArea",
            Position=[20, 20],
            Size=[400, 250],
        )
        win.add_signal_handler("drawArea", wx.EVT_LEFT_DOWN, lambda event: print("click"))
        """
        # normalize incoming drawing-area parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Frame=Frame,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "DrawingArea"
        self.widgets[object_entry.name] = object_entry

        # create scrolled host window as top-level drawing-area widget reference
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        scrolled_window = wx.ScrolledWindow(
            provisional_parent,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
            style=wx.HSCROLL | wx.VSCROLL,
        )
        scrolled_window.SetScrollRate(10, 10)

        # create inner drawing panel for paint/mouse event handling
        drawing_panel = wx.Panel(
            scrolled_window,
            wx.ID_ANY,
            pos=(0, 0),
            size=wx.DefaultSize,
        )
        drawing_panel.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        # keep inner panel at least as large as logical requested drawing size
        requested_w = object_entry.width if object_entry.width is not None else 200
        requested_h = object_entry.height if object_entry.height is not None else 120
        drawing_panel.SetSize((self._scale(requested_w), self._scale(requested_h)))
        scrolled_window.SetVirtualSize((self._scale(requested_w), self._scale(requested_h)))

        # store references and drawing-specific metadata
        object_entry.ref = scrolled_window
        object_entry.data = {
            "drawing_area": drawing_panel,
            "pixmap": None,
            "draw_function": None,
            "draw_data": None,
        }

        # paint hook delegates drawing to stored draw_function, if set
        def _on_drawing_paint(event: wx.PaintEvent, name: str = object_entry.name) -> None:
            obj = self.get_object(name)
            data = obj.data if isinstance(obj.data, dict) else {}
            draw_function = data.get("draw_function")
            draw_data = data.get("draw_data")

            dc = wx.PaintDC(drawing_panel)
            if callable(draw_function):
                try:
                    draw_function(dc, draw_data)
                except TypeError:
                    try:
                        draw_function(dc)
                    except TypeError:
                        draw_function(event)
            else:
                event.Skip()

        drawing_panel.Bind(wx.EVT_PAINT, _on_drawing_paint)

        # apply common setup (size/sensitive/callback on optional signal)
        self._set_commons(object_entry.name, **params)

        # position drawing area host widget in target container
        self._add_to_container(object_entry.name)

    def initial_draw(self, Name: str, Function: Callable[..., Any], Data: Optional[Any] = None) -> None:
        """
        Registers a base draw function for a drawing area and triggers refresh.

        Parameters
        ----------

        Name : str
            Name of the drawing area. Must be unique.

        Function : Callable[..., Any]
            Drawing callback function.

        Data : Any | None, optional
            Optional payload passed to the draw function.

        Returns
        -------

        None.

        Examples
        --------

        win.initial_draw("drawArea", lambda dc, data: dc.Clear())
        """
        object_entry = self.get_object(Name)
        if object_entry.type != "DrawingArea":
            self.internal_die(Name, "Not a drawing area object.")
        if object_entry.data is None or not isinstance(object_entry.data, dict):
            self.internal_die(Name, "No drawing area data available.")

        # store draw callback and optional payload
        object_entry.data["draw_function"] = Function
        object_entry.data["draw_data"] = Data

        # trigger redraw on inner drawing panel
        drawing_panel = object_entry.data.get("drawing_area")
        if isinstance(drawing_panel, wx.Window):
            drawing_panel.Refresh()

    def add_spin_button(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: Optional[list[int] | tuple[int, int]] = None,
        Start: float = 0,
        Minimum: float = 0,
        Maximum: float = 0,
        Step: float = 0,
        Page: float = 0,
        Snap: int = 0,
        Align: Optional[str] = None,
        Rate: float = 0.0,
        Digits: int = 0,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a new spin button for integer or floating-point input.

        Parameters
        ----------

        Name : str
            Name of the spin button object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int] | None, optional
            Optional unscaled width/height.

        Start : float, optional
            Initial value.

        Minimum : float, optional
            Minimum allowed value.

        Maximum : float, optional
            Maximum allowed value.

        Step : float, optional
            Step increment.

        Page : float, optional
            Page increment used for PageUp/PageDown emulation.

        Snap : int, optional
            Snap-to-step flag (`0` or `1`).

        Align : str | None, optional
            Content alignment (`left`, `center`, `right`).

        Rate : float, optional
            Compatibility metadata for climb-rate style behavior.

        Digits : int, optional
            Number of decimal places. Values `> 0` use a floating spin control.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_spin_button(
            Name="spin1",
            Position=[10, 60],
            Start=5,
            Minimum=0,
            Maximum=10,
            Step=1,
            Tooltip="That's a spin button",
            Align="right",
            Frame="frame1",
        )
        """
        # normalize incoming spin-button parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Start=Start,
            Minimum=Minimum,
            Maximum=Maximum,
            Step=Step,
            Page=Page,
            Snap=Snap,
            Align=Align,
            Rate=Rate,
            Digits=Digits,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "SpinButton"
        self.widgets[object_entry.name] = object_entry

        # read spin-button specific values
        start = float(params.get("start") or 0)
        minimum = float(params.get("minimum") or 0)
        maximum = float(params.get("maximum") or 0)
        step = float(params.get("step") or 0)
        page = float(params.get("page") or 0)
        snap = 1 if int(params.get("snap") or 0) else 0
        align = str(params.get("align") or "").lower()
        climbrate = float(params.get("rate") or params.get("climbrate") or 0.0)
        digits = int(params.get("digits") or 0)

        # normalize numeric bounds and defaults
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        if minimum == maximum:
            maximum = minimum + 100
        if step <= 0:
            step = 1.0
        start = max(minimum, min(start, maximum))

        # build alignment style flag for wx controls
        align_style = 0
        if align == "right":
            align_style = wx.TE_RIGHT
        elif align == "center":
            align_style = wx.TE_CENTER

        # create native spin control with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        if digits > 0:
            spin: wx.Window = wx.SpinCtrlDouble(
                provisional_parent,
                wx.ID_ANY,
                value="",
                pos=(0, 0),
                size=wx.DefaultSize,
                style=wx.SP_ARROW_KEYS | align_style,
                min=minimum,
                max=maximum,
                initial=start,
                inc=step,
            )
            spin.SetDigits(digits)
            if params.get("signal") is None:
                params["signal"] = wx.EVT_SPINCTRLDOUBLE
        else:
            spin = wx.SpinCtrl(
                provisional_parent,
                wx.ID_ANY,
                value="",
                pos=(0, 0),
                size=wx.DefaultSize,
                style=wx.SP_ARROW_KEYS | align_style,
                min=int(round(minimum)),
                max=int(round(maximum)),
                initial=int(round(start)),
            )
            if params.get("signal") is None:
                params["signal"] = wx.EVT_SPINCTRL

        # add native reference and metadata
        object_entry.ref = spin
        object_entry.data = {
            "value": spin.GetValue(),
            "start": start,
            "minimum": minimum,
            "maximum": maximum,
            "step": step,
            "page": page,
            "snap": snap,
            "align": align,
            "climbrate": climbrate,
            "digits": digits,
        }

        # keep current value synchronized in object metadata
        def _on_spin_changed(event: wx.Event, name: str = object_entry.name) -> None:
            self.get_object(name).data["value"] = spin.GetValue()
            event.Skip()

        if digits > 0:
            spin.Bind(wx.EVT_SPINCTRLDOUBLE, _on_spin_changed)
        else:
            spin.Bind(wx.EVT_SPINCTRL, _on_spin_changed)

        # emulate snap-to-step when focus leaves the control
        if snap:
            def _on_spin_kill_focus(event: wx.FocusEvent, name: str = object_entry.name) -> None:
                current = float(spin.GetValue())
                snapped = round(current / step) * step
                snapped = max(minimum, min(snapped, maximum))
                spin.SetValue(snapped if digits > 0 else int(round(snapped)))
                self.get_object(name).data["value"] = spin.GetValue()
                event.Skip()

            spin.Bind(wx.EVT_KILL_FOCUS, _on_spin_kill_focus)

        # emulate page increment/decrement with keyboard page keys
        if page > 0:
            def _on_spin_key_down(event: wx.KeyEvent, name: str = object_entry.name) -> None:
                key = event.GetKeyCode()
                current = float(spin.GetValue())
                if key == wx.WXK_PAGEUP:
                    next_value = min(maximum, current + page)
                    spin.SetValue(next_value if digits > 0 else int(round(next_value)))
                    self.get_object(name).data["value"] = spin.GetValue()
                    return
                if key == wx.WXK_PAGEDOWN:
                    next_value = max(minimum, current - page)
                    spin.SetValue(next_value if digits > 0 else int(round(next_value)))
                    self.get_object(name).data["value"] = spin.GetValue()
                    return
                event.Skip()

            spin.Bind(wx.EVT_KEY_DOWN, _on_spin_key_down)

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position the spin button in target container
        self._add_to_container(object_entry.name)

    def add_text_view(
        self,
        Name: str,
        Position: list[int] | tuple[int, int],
        Size: list[int] | tuple[int, int],
        Path: Optional[str] = None,
        Textbuffer: Optional[str] = None,
        Text: Optional[str] = None,
        LeftMargin: int = 0,
        RightMargin: int = 0,
        Wrapped: str = "none",
        Justify: str = "left",
        Rich: int = 0,
        Frame: Optional[str] = None,
        Tooltip: Optional[str] = None,
        Function: Optional[Callable[..., Any] | list[Any] | tuple[Any, ...]] = None,
        Signal: Optional[Any] = None,
        Sensitive: int = 1,
    ) -> None:
        """
        Creates a multiline text-view widget.

        Parameters
        ----------

        Name : str
            Name of the text-view object. Must be unique.

        Position : list[int] | tuple[int, int]
            Unscaled absolute position `[x, y]`.

        Size : list[int] | tuple[int, int]
            Unscaled widget size `[width, height]`.

        Path : str | None, optional
            Optional file path used as text source.

        Textbuffer : str | None, optional
            Optional text-buffer content.

        Text : str | None, optional
            Optional direct text content.

        LeftMargin : int, optional
            Left inner margin in pixels.

        RightMargin : int, optional
            Right inner margin in pixels.

        Wrapped : str, optional
            Wrap mode (`none`, `char`, `word`, `word-char`).

        Justify : str, optional
            Text justification (`left`, `center`, `right`, `fill`).

        Rich : int, optional
            If non-zero, uses `wx.richtext.RichTextCtrl` instead of plain
            `wx.TextCtrl`.

        Frame : str | None, optional
            Optional parent container name.

        Tooltip : str | None, optional
            Optional tooltip text.

        Function : Callable | list[Any] | tuple[Any, ...] | None, optional
            Optional callback or callback/data pair.

        Signal : Any | None, optional
            Optional native wx event binder.

        Sensitive : int, optional
            Sensitivity state (0/1), default is 1.

        Returns
        -------

        None.

        Examples
        --------

        win.add_text_view(
            Name="tview1",
            Position=[40, 260],
            Size=[200, 120],
            Tooltip="A text",
            Frame="frame2",
            Path="./testem.txt",
            Wrapped="char",
            LeftMargin=10,
            RightMargin=10,
        )
        """
        # normalize incoming text-view parameters
        params = self._normalize(
            Name=Name,
            Position=Position,
            Size=Size,
            Path=Path,
            Textbuffer=Textbuffer,
            Text=Text,
            LeftMargin=LeftMargin,
            RightMargin=RightMargin,
            Wrapped=Wrapped,
            Justify=Justify,
            Rich=Rich,
            Frame=Frame,
            Tooltip=Tooltip,
            Function=Function,
            Signal=Signal,
            Sensitive=Sensitive,
        )

        # create and register object entry
        object_entry = self._new_widget(**params)
        object_entry.type = "TextView"
        self.widgets[object_entry.name] = object_entry

        # read text-view specific values
        source_path = params.get("path")
        textbuffer = params.get("textbuffer")
        text = params.get("text")
        left_margin = int(params.get("leftmargin") or 0)
        right_margin = int(params.get("rightmargin") or 0)
        wrapped = str(params.get("wrapped") or "none").lower()
        justify = str(params.get("justify") or "left").lower()
        rich_mode = 1 if int(params.get("rich") or 0) else 0

        # map justification to wx text-control style
        justify_style = 0
        if justify == "center":
            justify_style = wx.TE_CENTER
        elif justify == "right":
            justify_style = wx.TE_RIGHT

        # map wrap modes to wx text-control styles
        style = wx.TE_MULTILINE | wx.TE_RICH2 | justify_style
        if wrapped in ("none", "off", "0"):
            style |= wx.TE_DONTWRAP

        # create text control with provisional parent
        provisional_parent = self.container if self.container is not None else self._get_container(self.default_container_name)
        if rich_mode:
            text_view: wx.Window = wxrichtext.RichTextCtrl(
                provisional_parent,
                wx.ID_ANY,
                "",
                pos=(0, 0),
                size=wx.DefaultSize,
                style=style,
            )
        else:
            text_view = wx.TextCtrl(
                provisional_parent,
                wx.ID_ANY,
                "",
                pos=(0, 0),
                size=wx.DefaultSize,
                style=style,
            )

        # resolve initial content source (Path > Text > Textbuffer)
        content = ""
        if isinstance(source_path, str) and source_path:
            try:
                with open(source_path, "r", encoding="utf-8") as file_handle:
                    content = file_handle.read()
            except OSError:
                self.internal_die(object_entry.name, f"Can't find {source_path}. Check path.")
        elif text is not None:
            content = str(text)
        elif textbuffer is not None:
            content = str(textbuffer)

        # apply content and keep default as read-only like original Gtk2 behavior
        text_view.SetValue(content)
        text_view.SetEditable(False)

        # store references and metadata for later set/get operations
        object_entry.ref = text_view
        object_entry.path = str(source_path) if isinstance(source_path, str) else None
        object_entry.data = {
            "textview": text_view,
            "textbuffer": content,
            "leftmargin": left_margin,
            "rightmargin": right_margin,
            "wrapped": wrapped,
            "justify": justify,
            "rich": rich_mode,
        }

        # apply margins when platform/backend supports this operation
        try:
            text_view.SetMargins(left_margin, right_margin)
        except Exception:
            pass

        # apply common setup (tooltip, callback, sensitive, size)
        self._set_commons(object_entry.name, **params)

        # position the text view in target container
        self._add_to_container(object_entry.name)

    def get_textview(self, Name: str, Keyname: Optional[str] = None) -> Any:
        """
        Returns text-view reference, text buffer content, or source path.

        Parameters
        ----------

        Name : str
            Name of the text-view object. Must be unique.

        Keyname : str | None, optional
            Optional selector (`Path`, `Textview`, `Textbuf`/`Textbuffer`).

        Returns
        -------

        Any:
            Text view reference, text buffer string, or path string.

        Examples
        --------

        text_widget = win.get_textview("tview1")
        current_text = win.get_textview("tview1", "Textbuffer")
        source_path = win.get_textview("tview1", "Path")
        """
        # get object and verify type
        object_entry = self.get_object(Name)
        if object_entry.type != "TextView":
            self.internal_die(Name, "Not a textview object.")

        # normalize optional key selector
        key = self._extend(str(Keyname).lower()) if Keyname is not None else None

        # no key means return the textview reference
        if key is None:
            return object_entry.ref

        # return file path if requested
        if key == "path":
            return object_entry.path

        # return textview reference
        if key == "textview":
            return object_entry.ref

        # return current text buffer content
        if key == "textbuffer":
            data = object_entry.data if isinstance(object_entry.data, dict) else {}
            return data.get("textbuffer", "")

        # return rich mode flag (0/1)
        if key in ("rich", "richtext"):
            data = object_entry.data if isinstance(object_entry.data, dict) else {}
            return int(data.get("rich", 0))

        # unsupported key for get_textview
        if key in ("leftmargin", "rightmargin", "wrapped", "justify"):
            self.internal_die(Name, f"'get_textview' returns textbuffer/textview reference only. Use 'get_value' for \"{key}\" instead.")

        # unknown selector
        self.internal_die(Name, f"Unknown parameter \"{key}\".")

    def set_textview(
        self,
        Name: str,
        Path: Optional[str] = None,
        Textbuffer: Optional[str] = None,
        Text: Optional[str] = None,
    ) -> None:
        """
        Sets text-view content from path, text buffer, or direct text.

        Parameters
        ----------

        Name : str
            Name of the text-view object. Must be unique.

        Path : str | None, optional
            File path used as new text source.

        Textbuffer : str | None, optional
            New text-buffer content.

        Text : str | None, optional
            New direct text content.

        Returns
        -------

        None.

        Examples
        --------

        win.set_textview(Name="tview1", Text="Updated text")
        win.set_textview(Name="tview1", Path="./notes.txt")
        """
        # get object and verify type
        object_entry = self.get_object(Name)
        if object_entry.type != "TextView":
            self.internal_die(Name, "Not a textview object.")
        if object_entry.ref is None:
            self.internal_die(Name, "No textview reference available.")

        # normalize incoming setter parameters
        params = self._normalize(Path=Path, Textbuffer=Textbuffer, Text=Text)
        text_view = object_entry.ref
        data = object_entry.data if isinstance(object_entry.data, dict) else {}

        # set content from path when provided
        if isinstance(params.get("path"), str) and params.get("path"):
            source_path = str(params["path"])
            try:
                with open(source_path, "r", encoding="utf-8") as file_handle:
                    content = file_handle.read()
            except OSError:
                self.internal_die(Name, f"Can't find {source_path}. Check path.")
            text_view.SetValue(content)
            object_entry.path = source_path
            data["textbuffer"] = content

        # set content from direct text
        elif params.get("text") is not None:
            content = str(params.get("text") or "")
            text_view.SetValue(content)
            data["textbuffer"] = content

        # set content from textbuffer value
        elif params.get("textbuffer") is not None:
            content = str(params.get("textbuffer") or "")
            text_view.SetValue(content)
            data["textbuffer"] = content

        # unsupported/empty parameter set
        else:
            self.internal_die(Name, "Unknown parameter(s): no Path, Textbuffer, or Text provided.")

        # persist updated data map back to object
        object_entry.data = data

    def show(self) -> None:
        """
        Shows the main window without entering the event loop.

        Examples
        --------

        win.show()
        """
        if self.main_window is not None:
            self.main_window.Show(True)

    def show_and_run(self) -> None:
        """
        Shows the main window and starts the wx main event loop.

        Examples
        --------

        win.show_and_run()
        """
        self.show()
        self.app.MainLoop()

    # --- Copilot can continue here with add_... methods ---