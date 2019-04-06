#!/bin/sh

DOCKER=$(which docker)

if [ "$DOCKER" = "" ]; then
	echo "This script requires docker"
	exit
fi

if [ ! -f .env ]; then
	echo "Missing .env file"
	exit
fi

HASIMAGE=$(docker images | egrep 'local\/sip-to-mqtt')
REBUILD=$(find Dockerfile -newer $0)

if [ "$REBUILD" != "" ] || [ "$HASIMAGE" = "" ]; then
	docker build -t local/sip-to-mqtt .
	touch $0
fi

docker run -it --rm --name sip-to-mqtt-test --env-file .env -v $(pwd):/app -p 5060:5060 local/sip-to-mqtt
