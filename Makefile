build:
	docker-compose build
	docker-compose up

start:
	docker start api
	docker exec -it api sh -c "uvicorn main:app --host 0.0.0.0 --port 80 --reload"