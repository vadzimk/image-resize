SHELL := /bin/bash

.PHONY: docker.up
docker.up: mongo.make.keyfile
	set -o allexport \
	&& source .env \
	&& set +o allexport \
	&& docker-compose up -d

.PHONY: docker.down
docker.down:
	docker-compose down -v


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
	celery -A src.celery_app.worker.celery worker --loglevel=info

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


.PHONY: mongo.make.keyfile
mongo.make.keyfile:
	@cd mongo && \
	if [ ! -f mongo-keyfile ]; then \
		openssl rand -base64 756 > mongo-keyfile; \
		chmod 400 mongo-keyfile; \
	else \
		echo "mongo-keyfile exists, skipped creation"; \
	fi