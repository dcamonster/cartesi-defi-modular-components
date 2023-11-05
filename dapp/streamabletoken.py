import copy
import json
import time
import uuid
from pathlib import Path

from dapp.events import (
    send_balance_updated_event,
    send_deleted_all_streams_event,
    send_stream_created_event,
    send_stream_deleted_event,
    send_stream_executed_event,
)
from eth_utils import to_checksum_address

empty_storage = {"balances": {}, "streams": {}, "totalSupply": 0}


def process_streams_first(method):
    def wrapper(self, block_number, *args, **kwargs):
        self.process_virtual_trades(block_number)
        return method(self, block_number, *args, **kwargs)

    return wrapper


class StreamableToken:
    """
    StreamableToken is a class that represents a token that can be streamed.
    """

    _storage_cache = None

    def __init__(self, address: str):
        self._address = to_checksum_address(address)  # layer 1 address


    def _initialize_storage(self):
        # Create storage folder if it doesn't exist
        Path("./storage").mkdir(parents=True, exist_ok=True)
        try:
            with open("./storage/balances.json", "r") as f:
                StreamableToken._storage_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            StreamableToken._storage_cache = {}

    def get_address(self) -> str:
        """
        Get the address of the token.
        """
        return self._address

    def get_storage(self):
        """
        Get the storage for the given address.
        """
        return StreamableToken._storage_cache.get(
            self._address, copy.deepcopy(empty_storage)
        ).copy()

    def save_storage(self, balances):
        """
        Save the storage for the given address.
        """
        # Ensure the key exists in the cache, and set an empty storage if it doesn't
        StreamableToken._storage_cache.setdefault(
            self._address, copy.deepcopy(empty_storage)
        )

        # Now, save the balances for the address
        StreamableToken._storage_cache[self._address] = balances

    def _persist_storage(self):
        with open("./storage/balances.json", "w") as f:
            json.dump(StreamableToken._storage_cache, f, indent=4)

    def clear_storage(self):
        """
        Clear the storage file for this token only. Useful for testing.
        """
        self.save_storage(copy.deepcopy(empty_storage))

    def get_total_supply(self):
        """
        Get the total supply of tokens.
        """
        return int(self.get_storage().get("totalSupply", 0))

    def get_theoric_total_supply(self, timestamp: int = None):
        """
        Get the total supply of tokens. For testing purposes only.
        """
        # Iterate over addresses and sum balance of in max timestamp
        total_supply = 0
        for address in self.get_storage()["balances"]:
            balance = self.balance_of(
                address, 2**256 - 1 if timestamp is None else timestamp
            )
            assert balance >= 0, "Balance cannot be negative."
            total_supply += self.balance_of(
                address, 2**256 - 1 if timestamp is None else timestamp
            )
        return int(total_supply)

    def mint(self, amount: int, wallet: str):
        """
        Mint a given amount of tokens to a given wallet.
        """
        wallet = to_checksum_address(wallet)

        storage = self.get_storage()

        # If address exists

        # If wallet exists
        if wallet in storage["balances"]:
            # Increment balance
            storage["balances"][wallet] += int(amount)
        else:
            # Add wallet with new balance
            storage["balances"][wallet] = int(amount)
        # Increment total supply
        storage["totalSupply"] += int(amount)

        send_balance_updated_event(
            address=wallet,
            token_address=self.get_address(),
            amount=str(storage["balances"][wallet]),
            total_supply=str(storage["totalSupply"]),
        )

        # Save storage
        self.save_storage(storage)

    def burn(self, amount: int, wallet: str, timestamp: int):
        """
        Burn a given amount of tokens from a given wallet.
        """

        self.consolidate_streams(timestamp)

        wallet = to_checksum_address(wallet)

        storage = self.get_storage()

        assert timestamp is not None

        if self.balance_of(wallet, timestamp) < int(amount):
            raise ValueError("Insufficient balance to burn.")

        # Decrement balance
        storage["balances"][wallet] -= int(amount)

        # Decrement total supply
        storage["totalSupply"] -= int(amount)

        send_balance_updated_event(
            address=wallet,
            token_address=self.get_address(),
            amount=str(storage["balances"][wallet]),
            total_supply=str(storage["totalSupply"]),
        )

        # Save storage
        self.save_storage(storage)

        # self.check_balances(wallet)

    def balance_of(self, wallet: str, timestamp: int):
        """
        Calculate the balance of a given wallet at a specific timestamp.
        If no timestamp is given, use the current time.
        """
        wallet = to_checksum_address(wallet)

        # Get the balance and streams for this token's address
        storage = self.get_storage()

        # Start with the minted balance
        balance = int(storage["balances"].get(wallet, 0))

        # Prepare keys to search for streams related to the given wallet
        keys = [key for key in storage["streams"].keys() if wallet in key]

        # Iterate over keys related to the given wallet
        for key in keys:
            stream = storage["streams"][key]
            # If the stream has started
            if stream["start"] <= timestamp:
                # Calculate the amount of tokens streamed so far
                elapsed = max(0, min(timestamp - stream["start"], stream["duration"]))

                streamed = (
                    stream["amount"]
                    if stream["duration"] == 0
                    else int(stream["amount"] * elapsed // stream["duration"])
                )

                # If the stream is to the given wallet, add the streamed tokens to the balance
                if stream["to"] == wallet:
                    balance += streamed

                # If the stream is from the given wallet, subtract the streamed tokens from the balance
                if stream["from"] == wallet:
                    balance -= streamed

        return balance

    def get_stream_id(self, sender: str, receiver: str):
        return f"{sender}-{receiver}-{str(uuid.uuid4())}"

    def check_balances(self, sender: str):
        all_streams = self.get_storage()["streams"]
        critical_points = []

        # Identify critical points (start and end) for all streams related to the sender
        for s_id, s in all_streams.items():
            if s["from"] == sender or s["to"] == sender:
                critical_points.append(s["start"])
                critical_points.append(s["start"] + s["duration"])

        # Remove duplicates and sort
        critical_points = sorted(list(set(critical_points)))

        # Check the balance at each critical point
        for timestamp in critical_points:
            balance_at_timestamp = self.balance_of(sender, timestamp)
            if balance_at_timestamp < 0:
                raise ValueError(
                    f"Insufficient balance at timestamp {timestamp} due to streams."
                )

    def transfer_from(
        self,
        sender: str,
        receiver: str,
        amount: int,
        duration: int,
        start: int,
        timestamp: int,
        dir: "list[str]" = [],
        parent_id: str = "",
    ):
        """
        Create a new stream transferring a given amount of tokens from the sender to the receiver
        over a given duration. The transfer starts at the given start time, or the current time
        if no start time is given.
        """
        sender = to_checksum_address(sender)
        receiver = to_checksum_address(receiver)

        # Use the current time if no timestamp is 0
        if start == 0:
            start = timestamp
        assert start >= timestamp, "Start time must be greater than current time."

        # Get the balance and streams for this token's address
        storage = self.get_storage()

        # Init balance of receiver if not exists.
        if receiver not in storage["balances"]:
            storage["balances"][receiver] = 0

        # Create a new stream
        stream_id = self.get_stream_id(sender, receiver)
        storage["streams"][stream_id] = {
            "from": sender,
            "to": receiver,
            "amount": int(amount),
            "start": start,
            "duration": int(duration),
            "dir": dir,
            "parent_id": parent_id,
        }

        send_stream_created_event(
            id=stream_id,
            token_address=self.get_address(),
            from_address=sender,
            to_address=receiver,
            amount=str(amount),
            start=start,
            duration=duration,
            parent_id=parent_id,
        )

        self.save_storage(storage)

        # Check that the sender has enough balance during all the streams
        # self.check_balances(sender)

    def consolidate_streams(self, until_timestamp):
        """
        Accrue all the sent and received tokens from streams until a specific timestamp.
        """

        # Get the balance and streams for this token's address
        storage = self.get_storage()

        # List to store streams to delete after processing
        streams_to_delete = []

        # Iterate over streams
        for stream_id, stream in storage["streams"].items():
            # If the stream has started
            if stream["start"] <= until_timestamp:
                # Calculate the elapsed time and the amount of tokens to stream
                elapsed = max(
                    0, min(until_timestamp - stream["start"], stream["duration"])
                )
                if elapsed == 0 and stream["duration"] != 0:
                    continue  # skip streams that haven't started yet
                to_stream = (
                    stream["amount"]
                    if stream["duration"] == 0
                    else int(stream["amount"] * elapsed // stream["duration"])
                )

                # Update the sender's balance
                if stream["from"] in storage["balances"]:
                    storage["balances"][stream["from"]] -= to_stream
                    send_balance_updated_event(
                        address=to_checksum_address(stream["from"]),
                        token_address=self.get_address(),
                        amount=str(storage["balances"][stream["from"]]),
                        total_supply=str(storage["totalSupply"]),
                    )

                # Update the receiver's balance
                if stream["to"] in storage["balances"]:
                    storage["balances"][stream["to"]] += to_stream
                    send_balance_updated_event(
                        address=to_checksum_address(stream["to"]),
                        token_address=self.get_address(),
                        amount=str(storage["balances"][stream["to"]]),
                        total_supply=str(storage["totalSupply"]),
                    )

                send_stream_executed_event(
                    id=stream_id,
                    token_address=self.get_address(),
                    from_address=stream["from"],
                    to_address=stream["to"],
                    amount=str(to_stream),
                    start=stream["start"],
                    duration=elapsed,
                    parent_id=stream["parent_id"],
                )

                # Update the stream amount
                stream["amount"] -= to_stream

                # Update the stream start time
                stream["start"] += elapsed

                # Update the stream duration
                stream["duration"] -= elapsed

                streams_to_delete.append(stream_id)

        # Update finished streams
        for stream_id in streams_to_delete:
            stream = storage["streams"][stream_id]
            if stream["amount"] != 0 or stream["duration"] != 0:
                stream_new_id = self.get_stream_id(stream["from"], stream["to"])
                stream["previous_id"] = stream_id
                parent_id = stream.get("parent_id", "")
                stream["parent_id"] = parent_id if parent_id != "" else stream_id
                storage["streams"][stream_new_id] = stream
                send_stream_created_event(
                    id=stream_new_id,
                    token_address=self.get_address(),
                    from_address=stream["from"],
                    to_address=stream["to"],
                    amount=str(stream["amount"]),
                    start=stream["start"],
                    duration=stream["duration"],
                    parent_id=stream["parent_id"],
                    previous_id=stream["previous_id"],
                )
            del storage["streams"][stream_id]
            send_stream_deleted_event(id=stream_id)

        self.save_storage(storage)

    def cancel_stream(self, stream_id: str, sender: str, timestamp):
        """
        Allow a sender to cancel a specific stream.
        """
        sender = to_checksum_address(sender)

        # Accrue the balances up to the current time to account for the canceled stream
        # If the stream is not found, the balances will be accrued up to the current time
        self.consolidate_streams(timestamp)

        # Load existing balances
        storage = self.get_storage()

        # Variable to hold the id of the stream to be deleted
        id_to_delete = None

        # Check if the stream exists
        if stream_id in storage["streams"]:
            id_to_delete = stream_id
        else:
            # If the stream is not found by stream_id, check for a stream with a matching previous_id
            for existing_stream_id, stream in storage["streams"].items():
                if stream.get("previous_id") == stream_id:
                    id_to_delete = existing_stream_id
                    break

        assert id_to_delete is not None, "Stream not found."

        # Check if the user is the sender
        assert (
            storage["streams"][id_to_delete]["from"] == sender
        ), "Only the sender can cancel the stream."

        del storage["streams"][id_to_delete]

        # Write the updated data back to the file
        send_stream_deleted_event(id=id_to_delete)
        self.save_storage(storage)

    def get_stream_points(self, streams):
        points = set()
        for stream in streams.values():
            if stream["duration"] == 0:
                continue
            points.add(stream["start"])
            points.add(stream["start"] + stream["duration"])
        return sorted(list(points))

    def normalize_streams(self, manual_points=None):
        storage = self.get_storage()

        streams = storage["streams"]

        if manual_points is None:
            points = self.get_stream_points(streams)
        else:
            # Use provided points
            points = sorted(manual_points)

        # Create intervals
        intervals = [(points[i], points[i + 1]) for i in range(len(points) - 1)]

        # Create new streams based on these intervals
        new_streams = {}
        for interval in intervals:
            start, end = interval
            for stream_id, stream in streams.items():
                if (
                    stream["start"] <= start < stream["start"] + stream["duration"]
                ) or (stream["start"] < end <= stream["start"] + stream["duration"]):
                    # Stream overlaps with interval, split it
                    duration = end - start
                    amount = stream["amount"] * duration // stream["duration"]
                    new_stream_id = (
                        f"{stream['from']}-{stream['to']}-{str(uuid.uuid4())}"
                    )
                    parent_id = stream.get("parent_id", "")
                    new_streams[new_stream_id] = {
                        "from": stream["from"],
                        "to": stream["to"],
                        "amount": int(amount),
                        "start": int(start),
                        "duration": int(duration),
                        "dir": stream["dir"],
                        "previous_id": stream_id,
                        "parent_id": parent_id if parent_id != "" else stream_id,
                    }

        # save new streams
        storage["streams"] = new_streams

        send_deleted_all_streams_event(token_address=self.get_address())

        # for each new stream created, send a stream created event
        for stream_id, stream in new_streams.items():
            send_stream_created_event(
                id=stream_id,
                token_address=self.get_address(),
                from_address=stream["from"],
                to_address=stream["to"],
                amount=str(stream["amount"]),
                start=stream["start"],
                duration=stream["duration"],
                parent_id=stream["parent_id"],
                previous_id=stream["previous_id"],
            )

        self.save_storage(storage)
