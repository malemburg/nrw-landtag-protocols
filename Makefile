all:
	echo "Please check the Makefile for available targets"

### Prepare the virtual env

install:
	install-pyrun --python=3.8 pyenv

packages:
	pip install -r requirements.txt

### OpenSearch Docker Setup

setup-os:
	mkdir -p os-config os-data/node-1 os-data/node-2

start-os:
	docker-compose up -d

stop-os:
	docker-compose down

### Quick targets for the loader and parser

load-all:
	for i in 14 15 16 17; do load_data.py $$i; done

parse-all:
	for i in 14 15 16 17; do parse_data.py $$i; done

feed-all:
	for i in 14 15 16 17; do feed_opensearch.py $$i; done

