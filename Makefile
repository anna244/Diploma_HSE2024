SHELL = /bin/bash

UID := $(shell id -u)
GID := $(shell id -g)

export UID
export GID

build:
	docker-compose stop || true 
	docker-compose build
	docker-compose up

start:
	docker-compose start

stop:
	docker-compose stop