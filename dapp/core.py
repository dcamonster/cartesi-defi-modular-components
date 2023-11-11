import json
import traceback
from os import environ

import requests
from eth_abi.abi import encode

from dapp.db import get_connection
from dapp.stream import Stream
from dapp.streamabletoken import StreamableToken
from dapp.util import (
    decode_packed,
    hex_to_str,
    logger,
    rollup_server,
    str_to_hex,
    to_checksum_address,
)

network = environ.get("NETWORK", "localhost")
ERC20PortalFile = open(f"./deployments/{network}/ERC20Portal.json")
erc20Portal = json.load(ERC20PortalFile)

TRANSFER_FUNCTION_SELECTOR = b"\xa9\x05\x9c\xbb"


def send_post_request(endpoint, payload):
    url = rollup_server + endpoint
    json_payload = {"payload": str_to_hex(json.dumps(payload))}

    logger.info(f"Sending POST request to {url} with payload {json_payload}")
    response = requests.post(url, json=json_payload)

    if response.status_code not in (200, 202):
        logger.error(
            f"Failed POST request to {url}. Status: {response.status_code}. Response: {response.text}"
        )
    else:
        logger.info(
            f"Successful POST request to {url}. Status: {response.status_code}. Response: {response.text}"
        )

    return response


def report_error(msg, payload):
    error_log = {
        "error": True,
        "message": msg,
        "payload": payload,
    }
    logger.error(error_log)
    send_post_request("/report", error_log)
    return "reject"


def report_success(msg, payload):
    success_log = {
        "error": False,
        "message": msg,
        "payload": payload,
    }
    """Function to report successful operations."""
    send_post_request("/report", success_log)
    return "accept"


def handle_deposit(data, connection):
    try:
        # Attempt to decode input as an ABI-packed-encoded ERC20 deposit
        binary = bytes.fromhex(data["payload"][2:])
        try:
            decoded = decode_packed(["bool", "address", "address", "uint256"], binary)
        except Exception as e:
            msg = "Payload does not conform to ERC20 deposit ABI"
            logger.error(f"{msg}\n{traceback.format_exc()}")
            return report_error(msg, data["payload"])

        success = decoded[0]
        erc20 = decoded[1]
        depositor = decoded[2]
        amount = decoded[3]

        StreamableToken(connection, erc20).mint(amount, depositor)

        # Post report about the deposit and minting
        report_success("Success", str_to_hex(json.dumps(data)))
        return "accept"

    except Exception as e:
        return report_error(
            f"Error processing data {data}\n{traceback.format_exc()}", data["payload"]
        )


def handle_action(data, connection):
    try:
        str_payload = hex_to_str(data["payload"])
        payload = json.loads(str_payload)

        sender = data["metadata"]["msg_sender"]
        block_number = data["metadata"]["block_number"]

        if payload["method"] == "stream":
            StreamableToken(connection, payload["args"]["token"]).transfer(
                receiver=payload["args"]["receiver"],
                amount=int(payload["args"]["amount"]),
                duration=int(payload["args"]["duration"]),
                block_start=int(payload["args"]["start"]),
                sender=sender,
                current_block=block_number,
            )
        elif payload["method"] == "stream_test":  # Just for testing purposes
            split_number = int(payload["args"]["split_number"])
            split_amount = int(payload["args"]["amount"]) // split_number

            for number in range(split_number):
                StreamableToken(connection, payload["args"]["token"]).add_stream(
                    Stream(
                        "",
                        from_address=to_checksum_address(sender),
                        to_address=to_checksum_address(payload["args"]["receiver"]),
                        start_block=int(block_number),
                        block_duration=int(payload["args"]["duration"]) + number,
                        amount=split_amount,
                        token_address=to_checksum_address(payload["args"]["token"]),
                        pair_address=None,
                    )
                )
        elif payload["method"] == "withdraw":
            token_address = payload["args"]["token"]
            token = StreamableToken(connection, payload["args"]["token"])
            amount = int(payload["args"]["amount"])
            token.burn(
                amount=amount,
                sender=sender,
                current_block=block_number,
            )
            # Encode a transfer function call that returns the amount back to the depositor
            transfer_payload = TRANSFER_FUNCTION_SELECTOR + encode(
                ["address", "uint256"], [sender, amount]
            )
            voucher = {
                "destination": token_address,
                "payload": "0x" + transfer_payload.hex(),
            }
            logger.info(f"Issuing voucher {voucher}")
            response = requests.post(rollup_server + "/voucher", json=voucher)
            logger.info(
                f"Received voucher status {response.status_code} body {response.content}"
            )
        elif payload["method"] == "cancel_stream":
            token = StreamableToken(connection, payload["args"]["token"])
        else:
            return report_error(f"Unknown method {payload['method']}", data["payload"])

        report_success("Success", str_to_hex(json.dumps(data)))
    except Exception as error:
        connection.rollback()
        error_msg = f"{error}"
        return report_error(error_msg, data["payload"])

    return "accept"


def handle_advance(data):
    logger.info(f"Received advance request data {data}")
    connection = get_connection()
    status = "accept"
    try:
        if data["metadata"]["msg_sender"].lower() == erc20Portal["address"].lower():
            status = handle_deposit(data, connection)
        else:
            status = handle_action(data, connection)

        connection.commit()
        connection.close()
    except Exception as e:
        connection.rollback()
        status = "reject"
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        report_error(msg, data["payload"])

    return status


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")

    response = "accept"
    try:
        # retrieves SQL statement from input payload
        statement = hex_to_str(data["payload"])
        logger.info(f"Processing statement: '{statement}'")

        connection = get_connection()
        cursor = connection.cursor()

        try:
            # attempts to execute the statement and fetch any results
            cursor.execute(statement)
            result = cursor.fetchall()
        except Exception as e:
            msg = f"Error executing statement '{statement}': {e}"
            response = report_error(msg, data["payload"])

        if result:
            # if there is a result, converts it to JSON and posts it as a notice or report
            payloadJson = json.dumps(result)
            response = report_success(payloadJson, data["payload"])
    except Exception as e:
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        response = report_error(msg, data["payload"])
    return response


def handle(rollup_request):
    handlers = {
        "advance_state": handle_advance,
        "inspect_state": handle_inspect,
    }
    handler = handlers[rollup_request["request_type"]]
    return handler(rollup_request["data"])
