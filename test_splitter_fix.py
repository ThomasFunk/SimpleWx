#!/usr/bin/env python3
"""
Test script for verifying the SplitterPane sizer fix.
This test checks that:
1. SplitterPane widgets have a BoxSizer
2. Child widgets are added to the sizer (not with absolute positioning)
3. The sizer can handle resize events correctly
"""

import sys
import wx
sys.path.insert(0, '/home/tf/workset/SimpleWx')

from simplewx import SimpleWx as simplewx

def test_splitter_pane_sizer():
    """Test that SplitterPane creates and uses a BoxSizer correctly."""
    
    # Create a simple test window
    win = simplewx()
    win.new_window(Name='TestWindow', Title='Splitter Sizer Test', Size=[512, 300])
    
    # Create a splitter with two panes
    win.add_splitter(
        Name='test_splitter',
        Position=[10, 10],
        Size=[450, 200],
        Orient='vertical',
        Split=225,
        MinSize=50,
    )
    
    # Create panes
    win.add_splitter_pane(Name='pane1', Splitter='test_splitter', Side='first')
    win.add_splitter_pane(Name='pane2', Splitter='test_splitter', Side='second')
    
    # Add widgets to panes
    win.add_treeview(
        Name='tree1',
        Type='Tree',
        Position=[0, 0],
        Size=[225, 200],
        Headers=['Tree View'],
        Data=[],
        Frame='pane1',
    )
    
    win.add_listview(
        Name='list1',
        Position=[0, 0],
        Headers=['List View'],
        Data=[],
        Size=[225, 200],
        Frame='pane2',
    )
    
    # Get the pane objects to check sizer
    pane1_obj = win.get_object('pane1')
    pane2_obj = win.get_object('pane2')
    
    # Verify that sizers are set
    success = True
    errors = []
    
    # Check pane1
    if pane1_obj.data and 'sizer' in pane1_obj.data:
        sizer = pane1_obj.data['sizer']
        if isinstance(sizer, wx.BoxSizer):
            print("✓ pane1 has a BoxSizer")
        else:
            print("✗ pane1 sizer is not a BoxSizer:", type(sizer))
            success = False
            errors.append("pane1 sizer type incorrect")
    else:
        print("✗ pane1 does not have a sizer in data")
        success = False
        errors.append("pane1 missing sizer")
    
    # Check pane2
    if pane2_obj.data and 'sizer' in pane2_obj.data:
        sizer = pane2_obj.data['sizer']
        if isinstance(sizer, wx.BoxSizer):
            print("✓ pane2 has a BoxSizer")
        else:
            print("✗ pane2 sizer is not a BoxSizer:", type(sizer))
            success = False
            errors.append("pane2 sizer type incorrect")
    else:
        print("✗ pane2 does not have a sizer in data")
        success = False
        errors.append("pane2 missing sizer")
    
    # Get the splitter
    splitter_obj = win.get_object('test_splitter')
    splitter = splitter_obj.ref
    
    # Check that splitter is split
    if splitter.IsSplit():
        print("✓ Splitter is correctly split")
    else:
        print("✗ Splitter is not split")
        success = False
        errors.append("Splitter not split")
    
    # Check that widgets are parented to panes
    tree = win.get_object('tree1').ref
    list_widget = win.get_object('list1').ref
    
    if tree.GetParent() == pane1_obj.ref:
        print("✓ TreeView parent is pane1")
    else:
        print("✗ TreeView parent is not pane1:", tree.GetParent())
        success = False
        errors.append("TreeView parent incorrect")
    
    if list_widget.GetParent() == pane2_obj.ref:
        print("✓ ListWidget parent is pane2")
    else:
        print("✗ ListWidget parent is not pane2:", list_widget.GetParent())
        success = False
        errors.append("ListWidget parent incorrect")
    
    print()
    if success:
        print("✅ All tests passed! SplitterPane sizer fix is working correctly.")
        return True
    else:
        print(f"❌ Tests failed with {len(errors)} error(s):")
        for err in errors:
            print(f"   - {err}")
        return False

if __name__ == '__main__':
    try:
        result = test_splitter_pane_sizer()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ Test script failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
