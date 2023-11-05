import json
from os import environ

from dapp.util import NoticeBuffer, ReportBuffer

notice_buffer = NoticeBuffer()

report_buffer = ReportBuffer()


def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()


def send_report(notice_str):
    """
    Sends a provided notice string.

    Parameters:
    - notice_str: A string containing the notice to be sent.
    """

    report_buffer.add(notice_str)


def get_event(event_type, **args):
    """
    Generates an event in the form of a dictionary.

    Parameters:
    - event_type: Type of the event. (e.g. "StreamCreated", "StreamDeleted", etc.)
    - **args: Arguments for the event.

    Returns:
    - dict: Dictionary representation of the event.
    """
    return {"event_type": event_type, "args": args}


def send_stream_created_event(
    id,
    token_address,
    from_address,
    to_address,
    amount,
    start,
    duration,
    parent_id,
    previous_id=None,
):
    """
    Sends a StreamCreated event.

    Parameters:
    - id: ID of the stream.
    - token_address: Address of the token being streamed.
    - from_address: Address from which the stream was created.
    - to_address: Address to which the stream was created.
    - amount: Amount of tokens being streamed.
    - start: Start time of the stream.
    - duration: Duration of the stream.
    - parent_id: ID of the parent stream.
    """
    event = get_event(
        "StreamCreated",
        id=id,
        token_address=token_address,
        from_address=from_address,
        to_address=to_address,
        amount=amount,
        start=start,
        duration=duration,
        parent_id=parent_id,
        previous_id=previous_id,
    )
    send_report(json.dumps(event))


def send_stream_executed_event(
    id, token_address, from_address, to_address, amount, start, duration, parent_id
):
    """
    Sends a StreamExecuted event.

    Parameters:
    - id: ID of the stream.
    - token_address: Address of the token being streamed.
    - from_address: Address from which the stream was created.
    - to_address: Address to which the stream was created.
    - amount: Amount of tokens being streamed.
    - start: Start time of the stream.
    - duration: Duration of the stream.
    - parent_id: ID of the parent stream.
    """
    event = get_event(
        "StreamExecuted",
        id=id,
        token_address=token_address,
        from_address=from_address,
        to_address=to_address,
        amount=amount,
        start=start,
        duration=duration,
        parent_id=parent_id,
    )
    send_report(json.dumps(event))


def send_stream_deleted_event(id):
    """
    Sends a StreamDeleted event.

    Parameters:
    - id: ID of the stream.
    """
    event = get_event("StreamDeleted", id=id)
    send_report(json.dumps(event))


def send_deleted_all_streams_event(token_address):
    """
    Sends a DeletedAllStreams event.

    Parameters:
    - token_address: Address of the token.
    """
    event = get_event("DeletedAllStreams", token_address=token_address)
    send_report(json.dumps(event))


def send_balance_updated_event(address, token_address, amount, total_supply):
    """
    Sends a BalanceUpdated event.

    Parameters:
    - address: Address of the account.
    - token_address: Address of the token.
    - amount: New balance of the account.
    """
    event = get_event(
        "BalanceUpdated",
        address=address,
        token_address=token_address,
        amount=amount,
        total_supply=total_supply,
    )
    send_report(json.dumps(event))


def send_pair_created_event(token1_address, token2_address, pair_address):
    """
    Sends a PairCreated event.

    Parameters:
    - token1_address: Address of the first token in the pair.
    - token2_address: Address of the second token in the pair.
    """
    event = get_event(
        "PairCreated",
        token1=token1_address,
        token2=token2_address,
        pair_address=pair_address,
    )
    send_report(json.dumps(event))
