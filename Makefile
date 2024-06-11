SHELL := /bin/bash

minio.start:
	cd backend \
	&& set -o allexport \
	&& source .env \
	&& set +o allexport \
	&& docker-compose up -d

backend.test:
	cd backend \
	&& pytest -vv -s

backend.start:
	cd backend \
	&& uvicorn src.main:app --reload


celery.start:
	cd backend \
	&& celery -A src.worker.celery worker --loglevel=info


celery.flower:
	cd backend \
	&& celery -A src.worker.celery flower

asyncapi.validate:
	cd backend/ws_schema \
	&& asyncapi validate asyncapi.yaml -w


# schema version 3.0.0. not supported yet, use asyncapi studio to view html docs
# https://github.com/asyncapi/cli/issues/629
asyncapi.generate:
	cd backend/ws_schema \
	&& asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template -o ./docs -i --debug
