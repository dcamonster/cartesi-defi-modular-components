debug:
	ERC20_PORTAL_FILE_PATH="../deployments/localhost/ERC20Portal.json" DB_FILE_PATH=indexer.sqlite python3 -m ptvsd --host localhost --port 5679 main.py
init-db:
	[ -f indexer.sqlite ] && rm indexer.sqlite; DB_FILE_PATH=indexer.sqlite python ../sqlite.py
run:
	ERC20_PORTAL_FILE_PATH="../deployments/localhost/ERC20Portal.json" DB_FILE_PATH=indexer.sqlite python3 main.py
run-sepolia:
	NEWTORK="sepolia" ERC20_PORTAL_FILE_PATH="../deployments/sepolia/ERC20Portal.json" DB_FILE_PATH=indexer.sqlite python3 main.py
debug-sepolia:
	NEWTORK="sepolia" ERC20_PORTAL_FILE_PATH="../deployments/sepolia/ERC20Portal.json" DB_FILE_PATH=indexer.sqlite python3 -m ptvsd --host localhost --port 5679 main.py