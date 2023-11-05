test:
	python -m unittest discover -s tests
build:
	docker buildx bake -f docker-bake.hcl -f docker-bake.override.hcl --load
dev:
	docker compose up
dev-down:
	docker compose down -v
host:
	docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose-host.yml up
host-python:
	ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" -m dapp.dca
host-python-debug:
	ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 -m ptvsd --host localhost --port 5678 -m dapp.dca
notebook:
	docker run -p 8888:8888 -v $$(pwd):/home/jovyan/work jupyter/scipy-notebook start.sh bash -c "cd /home/jovyan/work && pip install -r requirements.txt && start-notebook.sh"
