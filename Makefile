SHELL := /bin/bash

minio.start:
	cd backend \
	&& set -o allexport \
	&& source .env \
	&& set +o allexport \
	&& docker-compose up -d
#	&& echo $$MINIO_ROOT_USER
