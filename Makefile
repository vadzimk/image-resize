SHELL := /bin/bash

minio.start:
	cd backend \
	&& set -o allexport \
	&& source .env \
	&& set +o allexport \
	&& docker-compose up -d

test.backend:
	cd backend \
	&& pytest
