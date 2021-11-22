install:
	install-pyrun --python=3.8 pyenv

packages:
	pip install -r requirements.txt

start-os:
	docker-compose up -d

stop-os:
	docker-compose down
