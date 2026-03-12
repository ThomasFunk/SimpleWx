#!/usr/bin/env python3
from simplewx import SimpleWx as simplewx

win = simplewx()
win.new_window(Name='MainFrame', Title='Demo', Fixed=1, Size=[500, 300])

def on_btnOk_click(_event):
    pass

win.add_label(Name='lblHello', Position=[20, 20], Title='Hello')
win.add_button(Name='btnOk', Position=[20, 60], Title='OK', Function=on_btnOk_click, Size=[90, 30])

if __name__ == '__main__':
    win.show_and_run()
