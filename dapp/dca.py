# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import json
import os
import traceback
from os import environ
from urllib.parse import parse_qs, urlparse

import requests
from dapp.amm import AMM
from dapp.ammlibrary import get_amount_out, get_pair_address
from dapp.constants import ZERO_ADDRESS
from dapp.eth_abi_ext import decode_packed
from dapp.streamabletoken import StreamableToken
from dapp.util import NoticeBuffer, ReportBuffer, hex_to_str, logger, rollup_server
from eth_abi.abi import encode
from eth_utils import to_checksum_address

network = environ.get("NETWORK", "localhost")
ERC20PortalFile = open(f"./deployments/{network}/ERC20Portal.json")
erc20Portal = json.load(ERC20PortalFile)


notice_buffer = NoticeBuffer()
report_buffer = ReportBuffer()


def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")


def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()


# Function selector to be called during the execution of a voucher that transfers funds,
# which corresponds to the first 4 bytes of the Keccak256-encoded result of "transfer(address,uint256)"
TRANSFER_FUNCTION_SELECTOR = b"\xa9\x05\x9c\xbb"


def send_post_request(endpoint, payload):
    """Centralized function to send POST requests."""
    url = rollup_server + endpoint
    json_payload = {"payload": str2hex(json.dumps(payload))}

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
    """Function to handle and report errors."""
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


def send_notice_buffer(message):
    notice_log = {
        "message": message,
    }
    return notice_buffer.add(json.dumps(notice_log))


def send_report_buffer(message):
    report_log = {
        "message": message,
    }
    return report_buffer.add(json.dumps(report_log))


def get_storage():
    if os.path.exists("./storage/amm.json"):
        with open("./storage/amm.json", "r") as f:
            amm = json.load(f)
    else:
        amm = {}

    if os.path.exists("./storage/balances.json"):
        with open("./storage/balances.json", "r") as f:
            balances = json.load(f)
    else:
        balances = {}

    return amm, balances


def restore_storage(amm, balances):
    if not os.path.exists("./storage"):
        os.makedirs("./storage")

    with open("./storage/amm.json", "w") as f:
        json.dump(amm, f, indent=4)

    with open("./storage/balances.json", "w") as f:
        json.dump(balances, f, indent=4)


def handle_deposit(data):
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

        StreamableToken(erc20).mint(amount, depositor)
        StreamableToken(erc20)._persist_storage()

        # Post notice about the deposit and minting
        send_notice_buffer("Success")
        return "accept"

    except Exception as e:
        notice_buffer.clear()
        report_buffer.clear()
        return report_error(
            f"Error processing data {data}\n{traceback.format_exc()}", data["payload"]
        )


def handle_action(data):
    amm, balances = get_storage()
    try:
        str_payload = hex_to_str(data["payload"])
        payload = json.loads(str_payload)

        if payload["method"] == "add_liquidity":
            AMM().add_liquidity(
                token_a=payload["args"]["token_a"],
                token_b=payload["args"]["token_b"],
                token_a_desired=int(payload["args"]["token_a_desired"]),
                token_b_desired=int(payload["args"]["token_b_desired"]),
                token_a_min=int(payload["args"]["token_a_min"]),
                token_b_min=int(payload["args"]["token_b_min"]),
                to=payload["args"]["to"],
                msg_sender=data["metadata"]["msg_sender"],
                timestamp=int(data["metadata"]["timestamp"]),
            )
        elif payload["method"] == "remove_liquidity":
            AMM().remove_liquidity(
                token_a=payload["args"]["token_a"],
                token_b=payload["args"]["token_b"],
                liquidity=int(payload["args"]["liquidity"]),
                amount_a_min=int(payload["args"]["amount_a_min"]),
                amount_b_min=int(payload["args"]["amount_b_min"]),
                to=payload["args"]["to"],
                msg_sender=data["metadata"]["msg_sender"],
                timestamp=int(data["metadata"]["timestamp"]),
            )
        elif payload["method"] == "swap":
            AMM().swap_exact_tokens_for_tokens(
                amount_in=int(payload["args"]["amount_in"]),
                amount_out_min=int(payload["args"]["amount_out_min"]),
                path=payload["args"]["path"],
                start=int(payload["args"]["start"]),
                duration=int(payload["args"]["duration"]),
                to=payload["args"]["to"],
                msg_sender=data["metadata"]["msg_sender"],
                timestamp=int(data["metadata"]["timestamp"]),
            )
        elif payload["method"] == "stream":
            StreamableToken(payload["args"]["token"]).transfer_from(
                sender=data["metadata"]["msg_sender"],
                receiver=payload["args"]["receiver"],
                amount=int(payload["args"]["amount"]),
                duration=int(payload["args"]["duration"]),
                start=int(payload["args"]["start"]),
                timestamp=int(data["metadata"]["timestamp"]),
            )
            StreamableToken(payload["args"]["token"])._persist_storage()
        elif payload["method"] == "stream_test":
            split_number = int(payload["args"]["split_number"])
            split_amount = int(payload["args"]["amount"]) // split_number

            for number in range(split_number):
                StreamableToken(payload["args"]["token"]).transfer_from(
                    sender=data["metadata"]["msg_sender"],
                    receiver=payload["args"]["receiver"],
                    amount=split_amount,
                    duration=int(payload["args"]["duration"]) + number,
                    start=int(payload["args"]["start"]),
                    timestamp=int(data["metadata"]["timestamp"]),
                )
            StreamableToken(payload["args"]["token"])._persist_storage()
        elif payload["method"] == "unwrap":
            token_address = payload["args"]["token"]
            token = StreamableToken(payload["args"]["token"])
            amount = int(payload["args"]["amount"])
            msg_sender = data["metadata"]["msg_sender"]
            token.burn(
                amount=amount,
                wallet=msg_sender,
                timestamp=int(data["metadata"]["timestamp"]),
            )
            # Encode a transfer function call that returns the amount back to the depositor
            transfer_payload = TRANSFER_FUNCTION_SELECTOR + encode(
                ["address", "uint256"], [msg_sender, amount]
            )
            # Post voucher executing the transfer on the ERC-20 contract: "I don't want your money"!
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
            token = StreamableToken(payload["args"]["token"])
            stream_id_to_cancel = payload["args"]["stream_id"]
            parent_id_to_cancel = payload["args"]["parent_id"]

            # TODO move this logic somewhere else
            amm_pairs = AMM().get_storage()["pairs"]
            streams = token.get_storage()["streams"]

            if parent_id_to_cancel is not None:
                related_streams = {
                    stream_id: stream
                    for stream_id, stream in streams.items()
                    if stream.get("parent_id", "") == parent_id_to_cancel
                    and to_checksum_address(stream["from"])
                    == to_checksum_address(data["metadata"]["msg_sender"])
                }
                # Cancel all related streams
                pairs_to_recalculate = set()
                is_completed = True

                for stream_id, stream in related_streams.items():
                    token.cancel_stream(
                        stream_id,
                        data["metadata"]["msg_sender"],
                        int(data["metadata"]["timestamp"]),
                    )
                    if stream.get("start") + stream.get("duration") > int(
                        data["metadata"]["timestamp"]
                    ):
                        is_completed = False

                    # Recalculate AMM pair if needed
                    if amm_pairs.get(stream["to"]) is not None:
                        pairs_to_recalculate.add(stream["to"])

                if is_completed:
                    raise Exception("Stream is already completed")
                # Recalculate AMM pairs
                for pair_address in pairs_to_recalculate:
                    pair = amm_pairs.get(pair_address)
                    AMM().recalculate_pair(
                        pair.get("token_0"),
                        pair.get("token_1"),
                        int(data["metadata"]["timestamp"]),
                    )
            elif streams.get(stream_id_to_cancel) is not None:
                stream = streams.get(stream_id_to_cancel)
                token.cancel_stream(
                    stream_id_to_cancel,
                    data["metadata"]["msg_sender"],
                    int(data["metadata"]["timestamp"]),
                )
                # Recalculate AMM pair if needed
                if amm_pairs.get(stream["to"]) is not None:
                    pair = amm_pairs.get(stream["to"])
                    AMM().recalculate_pair(
                        pair.get("token_0"),
                        pair.get("token_1"),
                        int(data["metadata"]["timestamp"]),
                    )
            else:
                return report_error(
                    f"Stream with id {stream_id_to_cancel} does not exist",
                    data["payload"],
                )
        else:
            return report_error(f"Unknown method {payload['method']}", data["payload"])

        send_notice_buffer("Success")
    except Exception as error:
        restore_storage(amm, balances)
        notice_buffer.clear()
        report_buffer.clear()
        error_msg = f"{error}"
        return report_error(error_msg, data["payload"])

    return "accept"


def handle_advance(data):
    logger.info(f"Received advance request data {data}")

    status = "accept"
    try:
        if data["metadata"]["msg_sender"].lower() == erc20Portal["address"].lower():
            status = handle_deposit(data)
        else:
            status = handle_action(data)

        notice_buffer.send_all_grouped()
        report_buffer.send_all_grouped()
    except Exception as e:
        status = "reject"
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        report_error(msg, data["payload"])

    return status


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    logger.info("Adding report")
    # decode payload as a URL
    url = urlparse(hex2str(data["payload"]))
    amm, balances = get_storage()

    response = None
    try:
        if url.path == "balance":
            # parse query parameters
            query_params = parse_qs(url.query)
            token_address = query_params.get("token", [ZERO_ADDRESS])
            wallet = query_params.get("wallet", [ZERO_ADDRESS])
            timestamp = query_params.get("timestamp", [0])

            if not token_address or not wallet:
                return report_error("Missing query parameters", data["payload"])

            token = StreamableToken(token_address[0])

            response = report_success(
                str(token.balance_of(wallet[0], int(float(timestamp[0])))),
                data["payload"],
            )

        if url.path == "balance_details":
            query_params = parse_qs(url.query)
            token_address = query_params.get("token", [ZERO_ADDRESS])
            wallet = query_params.get("wallet", [ZERO_ADDRESS])
            token = StreamableToken(token_address[0])
            token_storage = token.get_storage()
            streams = token_storage["streams"]

            # Convert amounts to strings in the streams
            converted_streams = {
                stream_id: {
                    key: str(value) if key == "amount" else value
                    for key, value in stream.items()
                }
                for stream_id, stream in streams.items()
            }
            balance_details = {
                "balance": str(token_storage["balances"].get(wallet[0], 0)),
                "streams": {
                    stream_id: stream
                    for stream_id, stream in converted_streams.items()
                    if to_checksum_address(stream["from"]) == wallet[0]
                    or to_checksum_address(stream["to"])
                    == to_checksum_address(wallet[0])
                },
            }
            response = report_success(balance_details, data["payload"])
        if url.path == "tokens":
            unique_tokens = set()
            for key in balances.keys():
                #  if key not in amm.get("pairs", {}) keys then it is a token
                if key not in amm.get("pairs", {}).keys():
                    unique_tokens.add(key)
            response = report_success(list(unique_tokens), data["payload"])
        if url.path == "pairs":
            query_params = parse_qs(url.query)
            token_0 = query_params.get("token0", [ZERO_ADDRESS])
            token_1 = query_params.get("token1", [ZERO_ADDRESS])
            unique_tokens = set()
            if token_0[0] != ZERO_ADDRESS and token_1[0] != ZERO_ADDRESS:
                pair_address = get_pair_address(token_0[0], token_1[0])
                unique_tokens.add(pair_address)
            else:
                for key, pair in amm.get("pairs", {}).items():
                    unique_tokens.add(key)
            response = report_success(list(unique_tokens), data["payload"])
        if url.path == "tokens_from_pair":
            query_params = parse_qs(url.query)
            pair = query_params.get("pair", [ZERO_ADDRESS])
            unique_tokens = set()
            token_0 = amm.get("pairs", {}).get(pair[0], {}).get("token_0", ZERO_ADDRESS)
            token_1 = amm.get("pairs", {}).get(pair[0], {}).get("token_1", ZERO_ADDRESS)
            unique_tokens.add(token_0)
            unique_tokens.add(token_1)
            response = report_success(list(unique_tokens), data["payload"])
        if url.path == "quote":
            query_params = parse_qs(url.query)
            token_in = to_checksum_address(
                query_params.get("token_in", [ZERO_ADDRESS])[0]
            )
            token_out = to_checksum_address(
                query_params.get("token_out", [ZERO_ADDRESS])[0]
            )
            amount_in = int(query_params.get("amount_in", [0])[0])
            timestamp = int(query_params.get("timestamp", [0])[0])
            (reserve_in, reserve_out) = AMM().get_reserves(
                token_in, token_out, timestamp
            )
            amount_out = get_amount_out(amount_in, reserve_in, reserve_out)
            response = report_success(amount_out, data["payload"])
        if url.path == "reserves":
            query_params = parse_qs(url.query)
            token_in = to_checksum_address(
                query_params.get("token_in", [ZERO_ADDRESS])[0]
            )
            token_out = to_checksum_address(
                query_params.get("token_out", [ZERO_ADDRESS])[0]
            )
            timestamp = int(query_params.get("timestamp", [0])[0])
            (reserve_in, reserve_out) = AMM().get_reserves(
                token_in, token_out, timestamp
            )
            response = report_success([reserve_in, reserve_out], data["payload"])

        if not response:
            response = report_error(f"Unknown path {url.path}", data["payload"])

    except Exception as e:
        msg = f"Error processing data {data}\n{traceback.format_exc()}"
        response = report_error(msg, data["payload"])
    return response


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]

        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
