#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx

# Main Window 'MainWindow'
win = simplewx()
win.new_window(Name='MainWindow', Title='MainWindow', Size=[340, 200], Statusbar=1)

def on_pushButton_clicked(_event):
    pass

win.add_menu_bar(Name='menubar')
win.add_menu(Name='menuNew', Menubar='menubar', Title='New')
win.add_menu_item(Name='actionSave', Menu='menuNew', Title='Save')
win.add_menu_item(Name='actionLoad', Menu='menuNew', Title='Load')
win.add_menu_item(Name='actionExit', Menu='menuNew', Title='Exit')

# Buttons at the bottom
win.add_button(
    Name='pushButton',
    Position=[230, 100],
    Title='Press Me',
    Size=[90, 30],
    Tooltip='bla bla bal',
    Function=on_pushButton_clicked,
)

if __name__ == '__main__':
    win.show_and_run()
