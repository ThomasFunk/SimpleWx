import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'SimpleWx'
author = 'Thomas Funk'
release = '0.4.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'

autodoc_mock_imports = [
    'wx',
    'wx.adv',
    'wx.dataview',
    'wx.grid',
    'wx.richtext',
]

man_pages = [
    ('index', 'simplewx', 'SimpleWx Documentation', [author], 1),
]

suppress_warnings = [
    'docutils',
]
