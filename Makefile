.PHONY: install test analyse all

install:
	python3 -m pip install -e .

test:
	python3 -m pytest

analyse:
	PYTHONPATH=src python3 -m aicapitalgraph.cli analyse

all: test analyse

