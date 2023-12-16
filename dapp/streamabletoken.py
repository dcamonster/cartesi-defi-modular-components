from typing import List, Optional

from dapp.db import (
    add_stream,
    delete_stream_by_id,
    get_balance,
    get_stream_by_id,
    get_swaps_for_pair_address,
    get_total_supply,
    get_updatable_pairs,
    get_wallet_endend_streams,
    set_balance,
    set_last_block_processed,
    set_total_supply,
    update_stream_amount_duration_batch,
    update_stream_accrued,
    update_stream_amount_duration,
    get_wallet_non_accrued_streamed_amts,
)
from dapp.stream import Stream
from dapp.util import (
    address_or_raise,
    apply,
    get_amount_out,
    int_to_str,
    process_streams_before,
    str_to_int,
    with_checksum_address,
)


@with_checksum_address
def hook(connection, token_address, wallet, to_block):
    updatable_pairs = get_updatable_pairs(connection, wallet, token_address, to_block)
    for (
        pair_address,
        token_0_address,
        token_1_address,
        last_block_processed,
    ) in updatable_pairs:
        (reserve_in, reserve_out) = (
            StreamableToken(connection, token_0_address).balance_of(
                pair_address, last_block_processed
            ),
            StreamableToken(connection, token_1_address).balance_of(
                pair_address, last_block_processed
            ),
        )

        swaps = get_swaps_for_pair_address(connection, pair_address, to_block)

        # Add swap rate to swaps
        swaps = [
            swap + ((str_to_int(swap[3]) // swap[5],) if swap[5] > 0 else (0,))
            for swap in swaps
        ]

        streams_to_update = {
            swap[0]: {"amount": str_to_int(swap[1]), "duration": swap[2]}
            for swap in swaps
        }

        for block in range(last_block_processed, to_block + 1):

            def sum_swaps_token(token_address):
                return sum(
                    [
                        swap[7]
                        for swap in swaps
                        if swap[6] == token_address
                        and swap[4] <= block
                        and swap[4] + swap[5] > block
                    ]
                )

            token_0_in_sum = sum_swaps_token(token_0_address)
            token_1_in_sum = sum_swaps_token(token_1_address)

            amount_out_token_1 = (
                get_amount_out(token_0_in_sum, reserve_in, reserve_out)
                if token_0_in_sum != 0
                else 0
            )
            amount_out_token_0 = (
                get_amount_out(token_1_in_sum, reserve_out, reserve_in)
                if token_1_in_sum != 0
                else 0
            )

            # Check k
            k_before = reserve_in * reserve_out
            k_after = (reserve_in + token_0_in_sum - amount_out_token_0) * (
                reserve_out + token_1_in_sum - amount_out_token_1
            )
            assert k_after >= k_before, "AMM: K"

            # then update swaps
            for swap in swaps:
                if swap[4] > block or swap[4] + swap[5] <= block:
                    continue
                if swap[6] == token_0_address:
                    streams_to_update[swap[0]]["amount"] += (
                        swap[7] * amount_out_token_1 // token_0_in_sum
                    )
                else:
                    streams_to_update[swap[0]]["amount"] += (
                        swap[7] * amount_out_token_0 // token_1_in_sum
                    )
                streams_to_update[swap[0]]["duration"] += 1

            reserve_in += token_0_in_sum - amount_out_token_0
            reserve_out += token_1_in_sum - amount_out_token_1

        update_stream_amount_duration_batch(
            connection,
            [
                [value["duration"], int_to_str(value["amount"]), key]
                for key, value in streams_to_update.items()
            ],
        )
        set_last_block_processed(connection, pair_address, to_block)


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

    def get_wallet_endend_streams(
        self, wallet: str, current_block: int
    ) -> List[Stream]:
        return get_wallet_endend_streams(
            self._connection, wallet, self._address, current_block
        )

    def set_stream_accrued(self, stream_id: int):
        return update_stream_accrued(self._connection, stream_id, True)

    def get_stream_by_id(self, stream_id: int) -> Stream:
        return get_stream_by_id(self._connection, stream_id)

    def add_stream(self, stream: Stream) -> int:
        return add_stream(self._connection, stream)

    def get_stored_total_supply(self):
        return get_total_supply(self._connection, self._address)

    def set_stored_total_supply(self, amount: int):
        return set_total_supply(self._connection, self._address, amount)

    def process_streams(self, account_address: str, current_block: int):
        hook(self._connection, self._address, account_address, current_block)

        ended_streams = self.get_wallet_endend_streams(account_address, current_block)

        balance = self.get_stored_balance(account_address)
        for stream in ended_streams:
            self.set_stream_accrued(stream.id)
            streamed_amount = stream.streamed_amt(current_block)
            if stream.from_address == account_address:
                balance -= streamed_amount
                balance_to = (
                    self.get_stored_balance(stream.to_address) + streamed_amount
                )
                self.set_stored_balance(stream.to_address, balance_to)
            if stream.to_address == account_address:
                balance += streamed_amount
                balance_from = (
                    self.get_stored_balance(stream.from_address) - streamed_amount
                )
                self.set_stored_balance(stream.from_address, balance_from)
        self.set_stored_balance(account_address, balance)

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

        streamed_amounts = get_wallet_non_accrued_streamed_amts(
            self._connection, account_address, self._address, at_block
        )

        balance += sum(
            streamed for streamed in streamed_amounts if count_received or streamed < 0
        )

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
        swap_id: Optional[int] = None,
    ) -> int:
        address_or_raise(receiver)
        block_start = current_block if block_start == 0 else block_start
        assert block_start >= current_block, "Start block must be in the future."
        assert duration >= 0, "Duration must be positive."
        assert sender != receiver, "Sender and receiver must be different."
        assert amount >= 0, "Amount must be positive."

        future_balance_after_send = self.balance_of(
            sender, block_start + duration, False
        )
        assert (
            future_balance_after_send >= amount
        ), "Insufficient future balance to transfer. Check your streams."

        # if duration == 0:
        #     self.set_stored_balance(sender, self.get_stored_balance(sender) - amount)
        #     self.set_stored_balance(
        #         receiver, self.get_stored_balance(receiver) + amount
        #     )
        #     return 0

        return self.add_stream(
            Stream(
                stream_id="",
                from_address=sender,
                to_address=receiver,
                start_block=block_start,
                block_duration=duration,
                amount=amount,
                token_address=self.get_address(),
                accrued=False,
                swap_id=swap_id,
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
