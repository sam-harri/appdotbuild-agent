SHELL := /bin/bash

.DEFAULT_GOAL := dev

.PHONY: dev-server dev-client dev \
        db-migrate db-revision db-push \
        check-py-syntax check-py-health check-ts check \
        sync-client sync-server sync \
        client-build client-lint

dev-server:
	@cd server && uv run uvicorn --factory app.main:create_app --reload --port 2022

dev-client:
	@cd client2 && bun run dev

dev:
		@set -m; \
	$(MAKE) -s dev-server & SRV=$$!; \
	$(MAKE) -s dev-client & CLI=$$!; \
	trap 'kill -TERM $$SRV $$CLI 2>/dev/null' INT TERM EXIT; \
	wait $$SRV $$CLI

db-migrate:
	@cd server && uv run alembic upgrade head

db-revision:
	@cd server && uv run alembic revision --autogenerate -m "update"

db-push: db-revision db-migrate

check-py-syntax:
	@cd server && uv run python -m compileall -q app

check-py-health:
	@curl -f http://localhost:2022/healthcheck

check-ts:
	@cd client2 && bun x tsc -p tsconfig.json --noEmit

check: check-py-syntax check-ts

sync-client:
	@cd client2 && bun install

sync-server:
	@cd server && uv sync

sync: sync-client sync-server


client-build:
	@cd client2 && bun run build

client-lint:
	@cd client2 && bun run lint
