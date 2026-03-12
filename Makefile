VENV ?= venv
PYTHON ?= python3

VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: help venv install install-dev test test-headless run-example clean

help:
	@echo "Available targets:"
	@echo "  make venv           - Create local virtual environment ($(VENV))"
	@echo "  make install        - Install runtime dependencies"
	@echo "  make install-dev    - Install runtime + development dependencies"
	@echo "  make test           - Run pytest test suite"
	@echo "  make test-headless  - Run pytest test suite under Xvfb"
	@echo "  make run-example EXAMPLE=examples/windows_basic.py"
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
		echo "Please provide EXAMPLE=<path>, e.g. EXAMPLE=examples/windows_basic.py"; \
		exit 1; \
	fi
	$(VENV_PYTHON) $(EXAMPLE)

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
