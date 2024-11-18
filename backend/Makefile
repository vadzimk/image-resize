SHELL := /bin/bash

.PHONY: docker.up
docker.up: mongo.keyfile
	set -o allexport \
	&& source .env.dev \
	&& set +o allexport \
	&& docker-compose -p image-resize-dev up -d

.PHONY: docker.down
docker.down:
	docker-compose -p image-resize-dev down

.PHONY: docker.downup
docker.downup: docker.down docker.up

.PHONY: backend.test
backend.test:
	pipenv run python -m pytest -vv -s

.PHONY: backend.start
backend.start:
	uvicorn src.main:app --reload

.PHONY: celery.start
celery.start:
	celery -A src.celery_app.worker.celery worker

.PHONY: celery.flower
celery.flower:
	celery -A src.worker.celery flower

.PHONY: asyncapi.validate
asyncapi.validate:
	@cd ws_schema \
	&& asyncapi validate asyncapi.yaml -w

# schema version 3.0.0. not supported yet, use asyncapi studio to view html docs
# https://github.com/asyncapi/cli/issues/629
.PHONY: asyncapi.generate
asyncapi.generate:
	@cd ws_schema \
	&& asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template -o ./docs -i --debug


.PHONY: mongo.keyfile
mongo.keyfile:
	@cd mongo && \
	if [ ! -f mongo-keyfile ]; then \
		openssl rand -base64 756 > mongo-keyfile; \
		chmod 400 mongo-keyfile; \
	else \
		echo "mongo-keyfile exists, skipped creation"; \
	fi

.PHONY: backend.build
backend.build:
	docker build -t image_resize:latest .