docker_build:
	docker stop api || true 
	docker rm api || true 
	docker build -t fastapi . 
	docker create --name api \
	    -v $(shell pwd)/app:/app \
	    -v $(shell pwd)/storage:/storage \
	    -p 8000:80 \
	    -e HF_HOME="/storage/cache" \
	    --gpus all \
	    -it fastapi

start:
	docker start api
	docker exec -it api sh -c "uvicorn main:app --host 0.0.0.0 --port 80 --reload"