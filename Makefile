.PHONY: test lint pytest check

test: lint pytest

lint:
	python -m ruff check . --select E9,F63,F7,F82

pytest:
	python -m pytest -q

check:
	python manage.py check
