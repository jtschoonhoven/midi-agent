.PHONY: api app up fmt lint mypy check types test eval reset-db

api:
	uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8246

app:
	cd app && npm run dev

up:
	@make api 2>&1 | sed 's/^/[API] /' & \
	make app 2>&1 | sed 's/^/[APP] /' & \
	wait

fmt:
	uv run ruff format .
	uv run ruff check --fix .
	cd app && npm run format

lint:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy .

mypy:
	uv run mypy .

check: lint mypy

# Generate typescript bindings for the API
types:
	cd app && npm run generate:types


build: types
	cd app && npm run build

test:
	uv run pytest api/tests/ -v

# Run the evaluation suite
eval:
	uv run python api/midi/midi_evals.py

# Reset the database by removing all records
reset-db:
	@echo "Resetting database..."
	@for db in midi_agent.db api/midi_agent.db app/midi_agent.db; do \
		if [ -f "$$db" ]; then \
			echo "Removing $$db and auxiliary files"; \
			rm -f "$$db" "$$db-shm" "$$db-wal" "$$db-journal"; \
		fi \
	done
	@echo "Database reset complete. It will be recreated on next API startup."