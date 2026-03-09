#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx


def on_date_changed(event):
    picker = event.GetEventObject()
    value = picker.GetValue()
    if value.IsValid():
        print(f"Date changed: {value.GetYear():04d}-{int(value.GetMonth()) + 1:02d}-{value.GetDay():02d}")
    event.Skip()


def on_time_changed(event):
    picker = event.GetEventObject()
    value = picker.GetValue()
    if value.IsValid():
        print(f"Time changed: {value.GetHour():02d}:{value.GetMinute():02d}:{value.GetSecond():02d}")
    event.Skip()


win = simplewx()

win.new_window(
    Name="mainWindow",
    Title="Date/Time Picker Demo",
    Size=[520, 210],
)

win.add_label(
    Name="dateLabel",
    Position=[20, 22],
    Title="Date:",
)

win.add_datepicker_ctrl(
    Name="datePicker",
    Position=[90, 18],
    Size=[170, 30],
    Date="2026-03-09",
    Function=on_date_changed,
)

win.add_label(
    Name="timeLabel",
    Position=[20, 72],
    Title="Time:",
)

win.add_timepicker_ctrl(
    Name="timePicker",
    Position=[90, 68],
    Size=[170, 30],
    Time="14:30:00",
    Function=on_time_changed,
)

win.show_and_run()
