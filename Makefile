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
