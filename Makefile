#/ ============================================================================
#/  Makefile — короткие команды для Docker
#/  Makefile — short Docker commands
#/ ============================================================================

#? .PHONY защищает одноимённые файлы            |  .PHONY guards same-named files
.PHONY: up down logs restart status shell build

build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

status:
	docker compose ps

shell:
	docker compose exec secretchat bash

test:
	docker compose exec secretchat python tests/test_e2e.py
