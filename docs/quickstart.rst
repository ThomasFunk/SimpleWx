Quickstart
==========

Installation
------------

Create a virtual environment and install dependencies:

.. code-block:: bash

   python3 -m venv venv
   source venv/bin/activate
   pip install -U pip
   pip install -r requirements-dev.txt

Run an example
--------------

.. code-block:: bash

   ./venv/bin/python examples/samples/windows_basic.py

Build documentation
-------------------

HTML output:

.. code-block:: bash

   make docs-html

Manpage output:

.. code-block:: bash

   make docs-man

Generated files are written to:

- ``docs/_build/html``
- ``docs/_build/man``
