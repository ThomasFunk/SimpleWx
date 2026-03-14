#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx

# Main Window 'MainWindow'
win = simplewx()
win.new_window(Name='MainWindow', Title='MainWindow', Size=[470, 415])

# Frame 'Composite Manager'
win.add_frame(Name='frame_Composite_Manager', Position=[10, 10], Size=[450, 50], Title='Composite Manager')
win.add_radio_button(
    Name='radioButton',
    Position=[60, 10],
    Title='Xcompmgr',
    Group='group_frame_Composite_Manager',
    Active=0,
    Frame='frame_Composite_Manager',
)
win.add_radio_button(
    Name='radioButton_2',
    Position=[280, 10],
    Title='Compton',
    Group='group_frame_Composite_Manager',
    Active=0,
    Frame='frame_Composite_Manager',
)

# Frame 'Shadows'
win.add_frame(Name='frame_Shadows', Position=[10, 60], Size=[220, 250], Title='Shadows')
win.add_check_button(
    Name='checkBox',
    Position=[10, 20],
    Title='Enable Shadows',
    Active=0,
    Frame='frame_Shadows',
)
win.add_check_button(
    Name='checkBox_2',
    Position=[10, 40],
    Title='On Dock/Panels',
    Active=0,
    Frame='frame_Shadows',
)
win.add_check_button(
    Name='checkBox_5',
    Position=[10, 60],
    Title="Shadows on drag'n'drop",
    Active=0,
    Frame='frame_Shadows',
)
win.add_label(Name='label_8', Position=[15, 95], Title='Opacity:', Frame='frame_Shadows')
win.add_entry(
    Name='lineEdit_5',
    Position=[150, 90],
    Size=[51, 24],
    Title='0.10',
    Frame='frame_Shadows',
)
win.add_label(Name='label_6', Position=[15, 125], Title='Blur Radius:', Frame='frame_Shadows')
win.add_entry(
    Name='lineEdit_4',
    Position=[150, 120],
    Size=[51, 24],
    Title='1234',
    Frame='frame_Shadows',
)
win.add_label(Name='label_9', Position=[15, 155], Title='Left Offset:', Frame='frame_Shadows')
win.add_entry(
    Name='lineEdit_6',
    Position=[150, 150],
    Size=[51, 24],
    Title='-15',
    Frame='frame_Shadows',
)
win.add_label(Name='label_10', Position=[15, 185], Title='Top Offset:', Frame='frame_Shadows')
win.add_entry(
    Name='lineEdit_7',
    Position=[150, 180],
    Size=[51, 24],
    Title='-15',
    Frame='frame_Shadows',
)
win.add_label(Name='label_17', Position=[15, 215], Title='Shadow color:', Frame='frame_Shadows')
win.add_entry(
    Name='lineEdit_12',
    Position=[150, 210],
    Size=[51, 24],
    Title='FFFFFF',
    Frame='frame_Shadows',
)

# Frame 'Fading'
win.add_frame(Name='frame_Fading', Position=[240, 60], Size=[220, 250], Title='Fading')
win.add_check_button(
    Name='checkBox_6',
    Position=[10, 20],
    Title='Enable Fading',
    Active=0,
    Frame='frame_Fading',
)
win.add_check_button(
    Name='checkBox_3',
    Position=[10, 40],
    Title='Fade on Opacity change',
    Active=0,
    Frame='frame_Fading',
)
win.add_check_button(
    Name='checkBox_4',
    Position=[10, 60],
    Title='Fade on Open/Close',
    Active=0,
    Frame='frame_Fading',
)
win.add_label(Name='label_13', Position=[15, 95], Title='Fade-in Steps:', Frame='frame_Fading')
win.add_entry(
    Name='lineEdit_8',
    Position=[150, 90],
    Size=[51, 24],
    Title='0.028',
    Frame='frame_Fading',
)
win.add_label(Name='label_12', Position=[15, 125], Title='Fade-out Steps:', Frame='frame_Fading')
win.add_entry(
    Name='lineEdit_9',
    Position=[150, 120],
    Size=[51, 24],
    Title='0.03',
    Frame='frame_Fading',
)
win.add_label(Name='label_14', Position=[15, 155], Title='Fade Step Time:', Frame='frame_Fading')
win.add_entry(
    Name='lineEdit_10',
    Position=[150, 150],
    Size=[51, 24],
    Title='10',
    Frame='frame_Fading',
)
win.add_label(Name='label_16', Position=[15, 215], Title='Opacity on menus:', Frame='frame_Fading')
win.add_entry(
    Name='lineEdit_11',
    Position=[150, 210],
    Size=[51, 24],
    Title='0.10',
    Frame='frame_Fading',
)

# Frame 'Additional Options'
win.add_frame(Name='frame_Additional_Options', Position=[10, 320], Size=[450, 55], Title='Additional Options')
win.add_entry(Name='lineEdit_13', Position=[10, 10], Size=[431, 24], Frame='frame_Additional_Options')

# Buttons at the bottom
win.add_button(Name='pushButton_6', Position=[10, 380], Title='Restart', Size=[80, 24])
win.add_button(Name='pushButton_7', Position=[135, 380], Title='Help', Size=[80, 24])
win.add_button(Name='pushButton_4', Position=[260, 380], Title='Save', Size=[80, 24])
win.add_button(Name='pushButton_5', Position=[380, 380], Title='Cancel', Size=[80, 24])

if __name__ == '__main__':
    win.show_and_run()
