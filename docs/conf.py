import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'SimpleWx'
author = 'Thomas Funk'
release = '0.4.1'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
html_static_path = ['_static']
html_css_files = ['custom.css']

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

autosummary_generate = False

suppress_warnings = [
    'docutils',
]
