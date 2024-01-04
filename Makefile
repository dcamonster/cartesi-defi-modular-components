test:
	DB_FILE_PATH="test-dapp.sqlite" python -m unittest discover -s tests
test-watch:
	find . -name '*.py' | entr -c make test
build:
	docker buildx bake -f docker-bake.hcl -f docker-bake.override.hcl --load
dev:
	docker compose up
dev-down:
	docker compose down -v
host:
	docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose-host.yml up
host-python:
	ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 -m dapp.listener
host-python-debug:
	ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 -m ptvsd --host localhost --port 5678 -m dapp.listener
host-python-profile-line:
	ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" PYTHONPATH=. kernprof -u 1e-03 -r -l -v dapp/listener.py
notebook:
	docker run -p 8888:8888 -v $$(pwd):/home/jovyan/work jupyter/scipy-notebook start.sh bash -c "cd /home/jovyan/work && pip install -r requirements.txt &&  python ./sqlite.py && start-notebook.sh"
