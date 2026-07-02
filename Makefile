# AI Employee — common commands (macOS / Linux).
# Windows: use Docker Desktop + scripts in README, or WSL2 with these targets.

.PHONY: setup dev dev-scheduler test migrate prod prod-bundled prod-logs backup restore frontend

setup:
	@chmod +x scripts/*.sh
	@./scripts/setup.sh

dev:
	@./scripts/dev.sh

dev-scheduler:
	@./scripts/dev.sh --scheduler

test:
	docker compose exec api python -m unittest discover -s tests -v

migrate:
	docker compose exec api alembic upgrade head

frontend:
	cd frontend && npm install && npm run dev

prod:
	@./scripts/prod-up.sh

prod-bundled:
	@./scripts/prod-up.sh --bundled-db

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f api caddy scheduler

backup:
	@./scripts/backup-db.sh

restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/your.sql.gz" && exit 1)
	@./scripts/restore-db.sh "$(FILE)"
