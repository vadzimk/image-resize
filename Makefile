demo.up:
	make -C backend mongo.keyfile
	set -o allexport \
	&& source ./backend/.env.demo \
	&& set +o allexport && \
	docker-compose -f ./backend/docker-compose.yml -f docker-compose.demo.override.yml -p image-resize-demo up -d

demo.down:
	docker-compose -p image-resize-demo down

demo.clean:
	docker-compose \
	-f ./backend/docker-compose.yml \
	-f docker-compose.demo.override.yml \
	-p image-resize-demo down --volumes --remove-orphans --rmi all