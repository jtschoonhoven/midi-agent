.PHONY: notebook api app up fmt lint mypy check types

notebook:
	uv run marimo edit notebook.py

api:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

app:
	cd app && npm run dev

up:
	@make api 2>&1 | sed 's/^/[API] /' & \
	make app 2>&1 | sed 's/^/[APP] /' & \
	wait

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy .

mypy:
	uv run mypy .

check: lint mypy

types:
	cd app && npm run generate:types