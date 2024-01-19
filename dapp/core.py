import json
import traceback
from os import environ

import requests
from dapp.amm import AMM
from eth_abi.abi import encode

from dapp.db import get_connection, stream_test
from dapp.streamabletoken import StreamableToken
from dapp.util import (
    decode_packed,
    get_portal_address,
    hex_to_str,
    logger,
    rollup_server,
    str_to_hex,
)


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
    binary = bytes.fromhex(data["payload"][2:])

    decoded = decode_packed(["bool", "address", "address", "uint256"], binary)

    erc20 = decoded[1]
    depositor = decoded[2]
    amount = decoded[3]

    StreamableToken(connection, erc20).mint(amount, depositor)

    return "accept"


def handle_action(data, connection):
    if data["metadata"]["msg_sender"].lower() == get_portal_address().lower():
        return handle_deposit(data, connection)

    str_payload = hex_to_str(data["payload"])
    payload = json.loads(str_payload)

    sender = data["metadata"]["msg_sender"]
    timestamp = data["metadata"]["timestamp"]

    if payload["method"] == "stream":
        StreamableToken(connection, payload["args"]["token"]).transfer(
            receiver=payload["args"]["receiver"],
            amount=int(payload["args"]["amount"]),
            duration=int(payload["args"]["duration"]),
            start_timestamp=int(payload["args"]["start"]),
            sender=sender,
            current_timestamp=timestamp,
        )
    elif payload["method"] == "stream_test":  # Just for testing purposes
        stream_test(payload, sender, timestamp, connection)
    elif payload["method"] == "withdraw":
        token_address = payload["args"]["token"]
        token = StreamableToken(connection, payload["args"]["token"])
        amount = int(payload["args"]["amount"])
        token.burn(
            amount=amount,
            sender=sender,
            current_timestamp=timestamp,
        )
        # Encode a transfer function call that returns the amount back to the depositor
        TRANSFER_FUNCTION_SELECTOR = b"\xa9\x05\x9c\xbb"
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
        token = StreamableToken(connection, payload["args"]["token"]).cancel_stream(
            stream_id=int(payload["args"]["stream_id"]),
            sender=sender,
            current_timestamp=timestamp,
        )
    elif payload["method"] == "add_liquidity":
        AMM(connection).add_liquidity(
            token_a=payload["args"]["token_a"],
            token_b=payload["args"]["token_b"],
            token_a_desired=int(payload["args"]["token_a_desired"]),
            token_b_desired=int(payload["args"]["token_b_desired"]),
            token_a_min=int(payload["args"]["token_a_min"]),
            token_b_min=int(payload["args"]["token_b_min"]),
            to=payload["args"]["to"],
            msg_sender=data["metadata"]["msg_sender"],
            current_timestamp=int(data["metadata"]["timestamp"]),
        )
    elif payload["method"] == "remove_liquidity":
        AMM(connection).remove_liquidity(
            token_a=payload["args"]["token_a"],
            token_b=payload["args"]["token_b"],
            liquidity=int(payload["args"]["liquidity"]),
            amount_a_min=int(payload["args"]["amount_a_min"]),
            amount_b_min=int(payload["args"]["amount_b_min"]),
            to=payload["args"]["to"],
            msg_sender=data["metadata"]["msg_sender"],
            current_timestamp=int(data["metadata"]["timestamp"]),
        )
    elif payload["method"] == "swap":
        AMM(connection).swap_exact_tokens_for_tokens(
            amount_in=int(payload["args"]["amount_in"]),
            amount_out_min=int(payload["args"]["amount_out_min"]),
            path=payload["args"]["path"],
            start=int(payload["args"]["start"]),
            duration=int(payload["args"]["duration"]),
            to=payload["args"]["to"],
            msg_sender=data["metadata"]["msg_sender"],
            current_timestamp=int(data["metadata"]["timestamp"]),
        )
    else:
        raise Exception(f"Unknown method {payload['method']}")

    return "accept"


def handle_advance(data):
    logger.info(f"Received advance request data {data}")
    connection = get_connection()
    status = "accept"
    try:
        status = handle_action(data, connection)
        report_success("Success", str_to_hex(json.dumps(data)))
        connection.commit()
        connection.close()
    except Exception as e:
        connection.rollback()
        status = "reject"
        report_error(str(e), data["payload"])

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
        response = report_error(str(e), data["payload"])
    return response


def handle(rollup_request):
    handlers = {
        "advance_state": handle_advance,
        "inspect_state": handle_inspect,
    }
    handler = handlers[rollup_request["request_type"]]
    return handler(rollup_request["data"])
