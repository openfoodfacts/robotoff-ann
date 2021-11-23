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
	${DOCKER_COMPOSE} up -d --build 2>&1

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

livecheck:
	@echo "🥫 Running livecheck …"
	docker/docker-livecheck.sh

log:
	@echo "🥫 Reading logs (docker-compose) …"
	${DOCKER_COMPOSE} logs -f

#---------#
# Quality #
#---------#

up_tests:
	@echo "🥫 Run a test docker"
	docker rm -f robotoff-ann-tests
	${DOCKER_COMPOSE} run --rm -d --name robotoff-ann-tests ann  tail -f /dev/null
	docker exec -u root robotoff-ann-tests pip install -r requirements_test.txt

down_tests:
	@echo "🥫 shutdown test docker"
	docker rm -f robotoff-ann-tests

_lint:
	@echo "🥫 Linting"
	docker exec robotoff-ann-tests isort .
	docker exec robotoff-ann-tests black .

lint: up_tests _lint down_tests

_checks:
	@echo "🥫 Run checks"
	docker exec robotoff-ann-tests isort --check .
	docker exec robotoff-ann-tests black --check .
	docker exec robotoff-ann-tests flake8

checks: up_tests _checks down_tests

_tests:
	@echo "🥫 Run ctests"
	docker exec robotoff-ann-tests pytest tests

tests: up_tests _tests down_tests

quality: up_tests _lint _checks _tests down_tests


#------------#
# Production #
#------------#
create_external_volumes:
	@echo "🥫 Creating external volumes (production only) …"
	docker volume create ann_data

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
