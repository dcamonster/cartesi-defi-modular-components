import json
from os import environ

import requests

from dapp.util import (
    logger,
    rollup_server,
)
from dapp.request_handler import handle

network = environ.get("NETWORK", "localhost")
ERC20PortalFile = open(f"./deployments/{network}/ERC20Portal.json")
erc20Portal = json.load(ERC20PortalFile)

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        finish["status"] = handle(rollup_request)
