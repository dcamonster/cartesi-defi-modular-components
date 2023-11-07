from typing import List

from dapp.db import (
    add_stream,
    delete_stream_by_id,
    get_all_wallet_streams,
    get_balance,
    get_stream_by_id,
    get_total_supply,
    set_balance,
    set_total_supply,
    update_stream_by_id,
)
from dapp.stream import Stream
from dapp.util import (
    apply_decorator_to_all_methods,
    with_checksum_address,
    ZERO_ADDRESS,
)


def process_streams_first(method):
    def wrapper(self, block_number, *args, **kwargs):
        self.process_virtual_trades(block_number)
        return method(self, block_number, *args, **kwargs)

    return wrapper


@apply_decorator_to_all_methods(with_checksum_address)
class StreamableToken:
    def __init__(self, connection, address: str):
        self._connection = connection
        self._address = address

    def get_address(self) -> str:
        return self._address

    def get_stored_balance(self, wallet: str):
        return get_balance(self._connection, wallet, self._address)

    def set_stored_balance(self, wallet: str, amount: int):
        return set_balance(self._connection, wallet, self._address, amount)

    def get_all_wallet_streams(self, wallet: str) -> List[Stream]:
        return get_all_wallet_streams(self._connection, wallet, self._address)

    def get_stream_by_id(self, stream_id: int) -> Stream:
        return get_stream_by_id(self._connection, stream_id)

    def add_stream(self, stream: Stream) -> int:
        return add_stream(self._connection, stream)

    def get_stored_total_supply(self):
        return get_total_supply(self._connection, self._address)

    def set_stored_total_supply(self, amount: int):
        return set_total_supply(self._connection, self._address, amount)

    def mint(self, amount: int, wallet: str):
        old_balance = self.get_stored_balance(wallet)
        old_total_supply = self.get_stored_total_supply()

        self.set_stored_balance(wallet, old_balance + amount)
        self.set_stored_total_supply(old_total_supply + amount)

    def burn(self, amount: int, wallet: str, current_block: int):
        assert current_block is not None, "Current block must be provided."
        assert self.balance_of(wallet, current_block) < amount, "Insufficient balance."

        initial_supply = self.get_stored_total_supply()
        self.set_stored_total_supply(initial_supply - amount)
        return self.add_stream(
            Stream(
                "",
                wallet,
                ZERO_ADDRESS,
                current_block,
                0,
                amount,
                self.get_address(),
            )
        )

    def balance_of(self, wallet_address: str, at_block: int, count_received=True):
        balance = self.get_stored_balance(wallet_address)

        streams = self.get_all_wallet_streams(wallet_address)

        for stream in streams:
            if stream.start_block <= at_block:
                streamed = stream.streamed_amount(at_block)

                if count_received and stream.to_address == wallet_address:
                    balance += streamed

                if stream.from_address == wallet_address:
                    balance -= streamed

        return balance

    def transfer_from(
        self,
        sender: str,
        receiver: str,
        amount: int,
        duration: int,
        block_start: int,
        current_block: int,
    ) -> int:
        block_start = current_block if block_start == 0 else block_start
        assert block_start >= current_block, "Start block must be in the future."
        assert duration >= 0, "Duration must be positive."
        assert sender != receiver, "Sender and receiver must be different."
        assert amount > 0, "Amount must be positive."

        balance = self.balance_of(sender, current_block)
        assert balance >= amount, "Insufficient current balance to transfer."
        future_balance_after_send = self.balance_of(
            sender, block_start + duration, False
        )
        assert (
            block_start == current_block or future_balance_after_send >= amount
        ), "Insufficient future balance to transfer. Check your streams."

        return self.add_stream(
            Stream(
                "",
                sender,
                receiver,
                block_start,
                duration,
                amount,
                self.get_address(),
            )
        )

    def cancel_stream(self, stream_id: int, sender: str, current_block: int):
        stream = self.get_stream_by_id(stream_id)
        assert stream is not None, "Stream not found."
        assert stream.from_address == sender, "Sender is not the stream owner."
        assert (
            stream.start_block + stream.block_duration > current_block
        ), "Stream is already sent."

        if stream.start_block > current_block:
            delete_stream_by_id(self._connection, stream_id)
        else:
            streamed = stream.streamed_amount(current_block)
            update_stream_by_id(
                self._connection,
                stream_id,
                current_block - stream.start_block,
                streamed,
            )
