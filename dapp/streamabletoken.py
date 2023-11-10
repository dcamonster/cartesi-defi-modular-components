from typing import List

from dapp.db import (
    add_stream,
    delete_stream_by_id,
    get_balance,
    get_last_block,
    get_stream_by_id,
    get_total_supply,
    get_wallet_stream_range,
    set_balance,
    set_total_supply,
    update_block_tracker,
    update_stream_amount_duration,
)
from dapp.stream import Stream
from dapp.util import (
    address_or_raise,
    apply,
    process_streams_before,
    with_checksum_address,
)


@apply(with_checksum_address)
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

    def get_wallet_stream_range(
        self, wallet: str, start_before: int, not_ended_before: int
    ) -> List[Stream]:
        return get_wallet_stream_range(
            self._connection, wallet, self._address, start_before, not_ended_before
        )

    def get_wallet_last_block(self, wallet: str) -> int:
        return get_last_block(self._connection, wallet, self._address)

    def set_wallet_last_block(self, wallet: str, block_number: int):
        return update_block_tracker(
            self._connection, wallet, self._address, block_number
        )

    def get_stream_by_id(self, stream_id: int) -> Stream:
        return get_stream_by_id(self._connection, stream_id)

    def add_stream(self, stream: Stream) -> int:
        return add_stream(self._connection, stream)

    def get_stored_total_supply(self):
        return get_total_supply(self._connection, self._address)

    def set_stored_total_supply(self, amount: int):
        return set_total_supply(self._connection, self._address, amount)

    def process_streams(self, account_address: str, current_block: int):
        last_block_processed = get_last_block(
            self._connection, account_address, self._address
        )

        start_before = max(current_block, last_block_processed)
        not_ended_before = last_block_processed
        streams = self.get_wallet_stream_range(
            account_address, start_before, not_ended_before
        )

        balance = self.get_stored_balance(account_address)
        for stream in streams:
            streamed_amount = stream.stream_amt_btw(last_block_processed, current_block)
            if stream.from_address == account_address:
                balance -= streamed_amount
            if stream.to_address == account_address:
                balance += streamed_amount

        self.set_stored_balance(account_address, balance)

        self.set_wallet_last_block(account_address, current_block)

    def mint(self, amount: int, wallet: str):
        address_or_raise(wallet)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        old_balance = self.get_stored_balance(wallet)
        old_total_supply = self.get_stored_total_supply()

        self.set_stored_balance(wallet, old_balance + amount)
        self.set_stored_total_supply(old_total_supply + amount)

    @process_streams_before
    def burn(self, amount: int, sender: str, current_block: int):
        assert current_block is not None, "Current block must be provided."
        assert self.balance_of(sender, current_block) >= amount, "Insufficient balance."

        initial_supply = self.get_stored_total_supply()
        self.set_stored_total_supply(initial_supply - amount)
        return self.set_stored_balance(sender, self.get_stored_balance(sender) - amount)

    def balance_of(self, account_address: str, at_block: int, count_received=True):
        address_or_raise(account_address)
        balance = self.get_stored_balance(account_address)
        last_block = self.get_wallet_last_block(account_address)

        streams = self.get_wallet_stream_range(account_address, at_block, last_block)

        for stream in streams:
            streamed = stream.stream_amt_btw(last_block, at_block)

            if count_received and stream.to_address == account_address:
                balance += streamed

            if stream.from_address == account_address:
                balance -= streamed

        return balance

    @process_streams_before
    def transfer(
        self,
        receiver: str,
        amount: int,
        duration: int,
        block_start: int,
        sender: str,
        current_block: int,
    ) -> int:
        address_or_raise(receiver)
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

        if duration == 0:
            self.set_stored_balance(sender, self.get_stored_balance(sender) - amount)
            self.set_stored_balance(
                receiver, self.get_stored_balance(receiver) + amount
            )
            return 0

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

    @process_streams_before
    def cancel_stream(self, stream_id: int, sender: str, current_block: int):
        stream = self.get_stream_by_id(stream_id)
        assert stream is not None, "Stream not found."
        assert stream.from_address == sender, "Sender is not the stream owner."
        assert (
            stream.start_block + stream.block_duration >= current_block
        ), "Stream is already sent."

        if stream.start_block > current_block:
            delete_stream_by_id(self._connection, stream_id)
        else:
            streamed = stream.streamed_amt(current_block)
            update_stream_amount_duration(
                self._connection,
                stream_id,
                current_block - stream.start_block,
                streamed,
            )
