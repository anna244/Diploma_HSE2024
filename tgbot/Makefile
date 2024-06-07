build:
	docker stop tgbot || true
	docker rm tgbot || true
	docker build . -t tgbot --progress=plain
	docker create --name tgbot \
		--mount type=bind,source="$(shell pwd)/app",target=/app \
	    -v $(shell pwd)/storage:/storage \
		-u $(shell id -u ${USER}):$(shell id -g ${USER}) \
	    -e API_URL="http://localhost:8000" \
		--network host \
		-it tgbot

start:
	docker start tgbot