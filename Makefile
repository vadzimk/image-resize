SHELL := /bin/bash

.PHONY: docker.up
docker.up: mongo.make.keyfile
	@cd backend \
	&& set -o allexport \
	&& source .env \
	&& set +o allexport \
	&& docker-compose up -d

.PHONY: docker.down
docker.down:
	@cd backend \
	&& docker-compose down -v


.PHONY: docker.downup
docker.downup: docker.down docker.up


.PHONY: backend.test
backend.test:
	@cd backend \
	&& pytest -vv -s

.PHONY: backend.test.unit
backend.test.unit:
	@cd backend \
	&& pytest tests/unit -vv -s

.PHONY: backend.start
backend.start:
	@cd backend \
	&& uvicorn src.main:app --reload

.PHONY: celery.start
celery.start:
	@cd backend \
	&& celery -A src.celery_app.worker.celery worker --loglevel=info

.PHONY: celery.flower
celery.flower:
	@cd backend \
	&& celery -A src.worker.celery flower

.PHONY: asyncapi.validate
asyncapi.validate:
	@cd backend/ws_schema \
	&& asyncapi validate asyncapi.yaml -w

# schema version 3.0.0. not supported yet, use asyncapi studio to view html docs
# https://github.com/asyncapi/cli/issues/629
.PHONY: asyncapi.generate
asyncapi.generate:
	@cd backend/ws_schema \
	&& asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template -o ./docs -i --debug


.PHONY: mongo.make.keyfile
mongo.make.keyfile:
	@cd backend/mongo && \
	if [ ! -f mongo-keyfile ]; then \
		openssl rand -base64 756 > mongo-keyfile; \
		chmod 400 mongo-keyfile; \
	else \
		echo "mongo-keyfile exists, skipped creation"; \
	fi