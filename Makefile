build:
	docker-compose stop || true 
	docker-compose build
	docker-compose up

start:
	docker-compose start

stop:
	docker-compose stop