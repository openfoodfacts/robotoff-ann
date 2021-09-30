#!/usr/bin/make

NAME = "robotoff-ann"
ENV_FILE ?= .env
DOCKER_COMPOSE=docker-compose --env-file=${ENV_FILE}

.DEFAULT_GOAL := dev

#------#
# Info #
#------#
hello:
	@echo "🥫 Welcome to the Robotoff-ANN dev environment setup!"
	@echo "🥫 Thanks for contributing to Robotoff!"
	@echo ""

goodbye:
	@echo "🥫 Cleaning up dev environment (remove containers, remove local folder binds, prune Docker system) …"

#----------------#
# Docker Compose #
#----------------#
up:
	@echo "🥫 Building and starting containers …"
	${DOCKER_COMPOSE} up -d --remove-orphans --build 2>&1

down:
	@echo "🥫 Bringing down containers …"
	${DOCKER_COMPOSE} down

hdown:
	@echo "🥫 Bringing down containers and associated volumes …"
	${DOCKER_COMPOSE} down -v

restart:
	@echo "🥫 Restarting frontend & backend containers …"
	${DOCKER_COMPOSE} restart backend frontend

status:
	@echo "🥫 Getting container status …"
	${DOCKER_COMPOSE} ps

log:
	@echo "🥫 Reading logs (docker-compose) …"
	${DOCKER_COMPOSE} logs -f

#------------#
# Production #
#------------#
create_external_volumes:
	@echo "🥫 Creating external volumes (production only) …"
	for volume in ann_data; do \
		docker volume create $$volume || echo "Docker volume '$$volume' already exist. Skipping."; \
	done

#---------#
# Cleanup #
#---------#
prune:
	@echo "🥫 Pruning unused Docker artifacts (save space) …"
	docker system prune -af

prune_cache:
	@echo "🥫 Pruning Docker builder cache …"
	docker builder prune -f

clean: goodbye hdown prune prune_cache
