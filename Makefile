.PHONY: dev test lint migrate shell compose-up compose-down

dev:
	uv run python manage.py runserver 0.0.0.0:8000

test:
	uv run pytest

test-cov:
	uv run pytest --cov=. --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

lint-fix:
	uv run ruff check --fix .
	uv run ruff format .

migrate:
	uv run python manage.py makemigrations
	uv run python manage.py migrate

shell:
	uv run python manage.py shell_plus

compose-up:
	docker compose up -d

compose-down:
	docker compose down

migrations:
	uv run python manage.py makemigrations accounts login clients rbac delegation pam lifecycle audit

collectstatic:
	uv run python manage.py collectstatic --noinput

worker:
	uv run celery -A config.celery worker -l info

beat:
	uv run celery -A config.celery beat -l info

zitadel-password:
	docker compose logs zitadel 2>&1 | grep -oP 'zitadel-admin@\S+' | head -5
	@echo "---"
	@echo "Run: docker compose logs zitadel 2>&1 | grep -i 'password'"
	@echo "Grab the password from the setup URL (first run only)"

seed:
	uv run python manage.py seed_iam
