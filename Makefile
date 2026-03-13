VENV ?= venv
PYTHON ?= python3

VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
SPHINXBUILD := $(VENV)/bin/sphinx-build
DOCS_DIR := docs

.PHONY: help venv install install-dev test test-headless run-example docs-html docs-man docs-deploy-html docs-deploy-man docs-clean clean

help:
	@echo "Available targets:"
	@echo "  make venv           - Create local virtual environment ($(VENV))"
	@echo "  make install        - Install runtime dependencies"
	@echo "  make install-dev    - Install runtime + development dependencies"
	@echo "  make test           - Run pytest test suite"
	@echo "  make test-headless  - Run pytest test suite under Xvfb"
	@echo "  make run-example EXAMPLE=examples/samples/windows_basic.py"
	@echo "  make docs-html         - Build HTML documentation via Sphinx"
	@echo "  make docs-man          - Build manpage documentation via Sphinx"
	@echo "  make docs-deploy-html  - Copy built HTML docs to docs/html/"
	@echo "  make docs-deploy-man   - Copy built manpage to doc/simplewx.1"
	@echo "  make docs-clean        - Remove generated Sphinx build output"
	@echo "  make clean          - Remove Python cache files"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV_PIP) install -U pip
	$(VENV_PIP) install -r requirements.txt

install-dev: venv
	$(VENV_PIP) install -U pip
	$(VENV_PIP) install -r requirements-dev.txt

test: install-dev
	$(VENV_PYTHON) -m pytest -q

test-headless: install-dev
	xvfb-run -a $(VENV_PYTHON) -m pytest -q

run-example: install
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Please provide EXAMPLE=<path>, e.g. EXAMPLE=examples/samples/windows_basic.py"; \
		exit 1; \
	fi
	$(VENV_PYTHON) $(EXAMPLE)

docs-html: install-dev
	$(SPHINXBUILD) -b html $(DOCS_DIR) $(DOCS_DIR)/_build/html

docs-man: install-dev
	$(SPHINXBUILD) -b man $(DOCS_DIR) $(DOCS_DIR)/_build/man

docs-deploy-html:
	rm -rf $(DOCS_DIR)/html
	cp -r $(DOCS_DIR)/_build/html $(DOCS_DIR)/html

docs-deploy-man:
	mkdir -p doc
	cp $(DOCS_DIR)/_build/man/simplewx.1 doc/simplewx.1

docs-clean:
	rm -rf $(DOCS_DIR)/_build

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
