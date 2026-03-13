#!/usr/bin/env python3
import wx
from simplewx import SimpleWx as simplewx


win = simplewx()
win.new_window(Name='MainWindow', Title='MainWindow', Size=[340, 200], Base=0, Statusbar=0)
print(f"Scale: {win.scalefactor}")
# win.add_menu_bar(Name='menubar')
# win.add_menu(Name='menuNew', Menubar='menubar', Title='New')
# win.add_menu_item(Name='actionSave', Menu='menuNew', Title='Save')
# win.add_menu_item(Name='actionLoad', Menu='menuNew', Title='Load')
# win.add_menu_item(Name='actionExit', Menu='menuNew', Title='Exit')

win.add_button(
    Name='pushButton',
    Position=[230, 100],
    Title='Press Me',
    Size=[90, 30],
    Tooltip='bla bla bal',
)


def _xy_tuple(value_obj):
    if hasattr(value_obj, 'GetWidth') and hasattr(value_obj, 'GetHeight'):
        return int(value_obj.GetWidth()), int(value_obj.GetHeight())
    if hasattr(value_obj, 'x') and hasattr(value_obj, 'y'):
        return int(value_obj.x), int(value_obj.y)
    if hasattr(value_obj, 'GetX') and hasattr(value_obj, 'GetY'):
        return int(value_obj.GetX()), int(value_obj.GetY())
    raise TypeError(f'Unsupported geometry type: {type(value_obj).__name__}')


def _log_geometry(tag):
    frame = win.main_window
    if frame is None:
        return

    window_obj = win.get_object('MainWindow')
    panel = window_obj.data.get('panel') if isinstance(window_obj.data, dict) else None
    button_ref = win.get_widget('pushButton')

    frame_size = _xy_tuple(frame.GetSize())
    frame_client = _xy_tuple(frame.GetClientSize())
    button_pos = _xy_tuple(button_ref.GetPosition())
    button_size = _xy_tuple(button_ref.GetSize())

    menu_height = 0
    menu_bar = frame.GetMenuBar()
    if menu_bar is not None:
        menu_height = int(menu_bar.GetSize().GetHeight())

    status_height = 0
    status_bar = frame.GetStatusBar()
    if status_bar is not None:
        status_height = int(status_bar.GetSize().GetHeight())

    print(f'[{tag}] frame={frame_size} client={frame_client} menu_h={menu_height} status_h={status_height}')

    if isinstance(panel, wx.ScrolledWindow):
        panel_client = _xy_tuple(panel.GetClientSize())
        panel_virtual = _xy_tuple(panel.GetVirtualSize())
        view_start = panel.GetViewStart()
        print(f'[{tag}] panel_client={panel_client} panel_virtual={panel_virtual} view_start=({view_start[0]}, {view_start[1]})')
    else:
        print(f'[{tag}] panel_type={type(panel).__name__ if panel is not None else "None"}')

    print(f'[{tag}] button_pos={button_pos} button_size={button_size}')


def _on_resize(event):
    _log_geometry('resize')
    event.Skip()


def _on_idle(event):
    if not getattr(win, '_initial_log_done', False):
        _log_geometry('startup')
        win._initial_log_done = True
    event.Skip()


if __name__ == '__main__':
    win.show()
    if win.main_window is not None:
        win.main_window.Bind(wx.EVT_SIZE, _on_resize)
        win.main_window.Bind(wx.EVT_IDLE, _on_idle)
    win.app.MainLoop()
