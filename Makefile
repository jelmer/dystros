PYTHON ?= python3

check:
	$(PYTHON) -m unittest dystros.tests.test_suite

check-all: check

