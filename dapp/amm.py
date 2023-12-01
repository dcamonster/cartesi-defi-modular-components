from dapp.db import create_swap
from dapp.streamabletoken import StreamableToken
from dapp.util import (
    MINIMUM_LIQUIDITY,
    ZERO_ADDRESS,
    apply,
    get_amount_out,
    quote,
    with_checksum_address,
)
from dapp.pair import Pair
import math


@apply(with_checksum_address)
class AMM:
    def __init__(self, connection):
        self.connection = connection

    def get_reserves(self, token_a, token_b, at_block):
        pair = Pair(self.connection, token_a, token_b)
        (reserve_0, reserve_1) = pair.get_reserves(at_block)
        return (
            (reserve_0, reserve_1)
            if token_a == pair.get_tokens()[0]
            else (reserve_1, reserve_0)
        )

    def _add_liquidity(
        self,
        token_a,
        token_b,
        token_a_desired,
        token_b_desired,
        token_a_min,
        token_b_min,
        current_block,
    ):
        (reserve_a, reserve_b) = self.get_reserves(token_a, token_b, current_block)

        if reserve_a == 0 and reserve_b == 0:
            amount_a = int(token_a_desired)
            amount_b = int(token_b_desired)
        else:
            amount_b_optimal = quote(token_a_desired, reserve_a, reserve_b)
            if amount_b_optimal <= token_b_desired:
                assert amount_b_optimal >= token_b_min, "AMM: INSUFFICIENT_B_AMOUNT"
                amount_a = int(token_a_desired)
                amount_b = int(amount_b_optimal)
            else:
                amount_a_optimal = quote(token_b_desired, reserve_b, reserve_a)
                assert amount_a_optimal <= token_a_desired, "AMM: INSUFFICIENT_A_AMOUNT"
                assert amount_a_optimal >= token_a_min, "AMM: INSUFFICIENT_A_AMOUNT"
                amount_a = int(amount_a_optimal)
                amount_b = int(token_b_desired)

        return amount_a, amount_b

    def add_liquidity(
        self,
        token_a,
        token_b,
        token_a_desired,
        token_b_desired,
        token_a_min,
        token_b_min,
        to,
        msg_sender,
        current_block,
    ):
        pair = Pair(self.connection, token_a, token_b)
        pair_address = pair.get_address()
        (reserve_a, reserve_b) = self.get_reserves(token_a, token_b, current_block)

        (amount_a, amount_b) = self._add_liquidity(
            token_a,
            token_b,
            token_a_desired,
            token_b_desired,
            token_a_min,
            token_b_min,
            current_block,
        )

        StreamableToken(self.connection, token_a).transfer(
            receiver=pair_address,
            amount=amount_a,
            duration=0,
            block_start=current_block,
            sender=msg_sender,
            current_block=current_block,
        )
        StreamableToken(self.connection, token_b).transfer(
            receiver=pair_address,
            amount=amount_b,
            duration=0,
            block_start=current_block,
            sender=msg_sender,
            current_block=current_block,
        )

        total_supply = pair.get_stored_total_supply()

        if total_supply == 0:
            liquidity = math.floor(math.sqrt(amount_a * amount_b)) - MINIMUM_LIQUIDITY
            assert liquidity > 0, "AMM: INSUFFICIENT_LIQUIDITY_MINTED"
            pair.mint(
                MINIMUM_LIQUIDITY, ZERO_ADDRESS
            )  # permanently lock the first MINIMUM_LIQUIDITY tokens
        else:
            liquidity = min(
                amount_a * total_supply // reserve_a,
                amount_b * total_supply // reserve_b,
            )

        assert liquidity > 0, "AMM: INSUFFICIENT_LIQUIDITY_MINTED"

        pair.mint(liquidity, to)

        return liquidity

    def remove_liquidity(
        self,
        token_a,
        token_b,
        liquidity,
        amount_a_min,
        amount_b_min,
        to,
        msg_sender,
        current_block,
    ):
        pair = Pair(self.connection, token_a, token_b)
        pair_address = pair.get_address()
        pair.transfer(
            receiver=pair_address,
            amount=liquidity,
            duration=0,
            block_start=current_block,
            sender=msg_sender,
            current_block=current_block,
        )

        (reserve_0, reserve_1) = pair.get_reserves(current_block)
        (token_0, token_1) = pair.get_tokens()

        total_supply = pair.get_stored_total_supply()

        amount_0 = liquidity * reserve_0 // total_supply
        amount_1 = liquidity * reserve_1 // total_supply

        assert amount_0 >= 0, "AMM: INSUFFICIENT_LIQUIDITY_BURNED"
        assert amount_1 >= 0, "AMM: INSUFFICIENT_LIQUIDITY_BURNED"

        pair.burn(amount=liquidity, sender=pair_address, current_block=current_block)

        token_0.transfer(
            receiver=to,
            amount=amount_0,
            duration=0,
            block_start=current_block,
            sender=pair_address,
            current_block=current_block,
        )

        token_1.transfer(
            receiver=to,
            amount=amount_1,
            duration=0,
            block_start=current_block,
            sender=pair_address,
            current_block=current_block,
        )

        (amount_a, amount_b) = (
            (amount_0, amount_1) if token_0 == token_a else (amount_1, amount_0)
        )

        assert amount_a >= amount_a_min, "AMM: INSUFFICIENT_A_AMOUNT"
        assert amount_b >= amount_b_min, "AMM: INSUFFICIENT_B_AMOUNT"

        return amount_0, amount_1

    def swap_exact_tokens_for_tokens(
        self,
        amount_in,
        amount_out_min,
        path,
        start,
        duration,
        to,
        msg_sender,
        current_block,
    ):
        """
        Swap exact tokens for tokens
        """
        assert len(path) == 2, "AMM: INVALID_PATH"
        if start == 0:
            start = current_block
        assert start >= current_block, "AMM: INVALID_START_TIME"

        pair = Pair(self.connection, path[0], path[1])

        (token_0, token_1) = pair.get_tokens()

        swap_id = create_swap(
            self.connection,
            pair.get_address(),
            token_0.get_address(),
            token_1.get_address(),
        )

        if duration == 0:
            (reserve_in, reserve_out) = self.get_reserves(path[0], path[1], start)
            amount_out = get_amount_out(amount_in, reserve_in, reserve_out)
            assert amount_out >= amount_out_min, "AMM: INSUFFICIENT_OUTPUT_AMOUNT"
            k_before = reserve_in * reserve_out
            k_after = (reserve_in + amount_in) * (reserve_out - amount_out)
            assert k_after >= k_before, "AMM: K"
            token_0.transfer(
                receiver=pair.get_address(),
                amount=amount_in,
                duration=0,
                block_start=current_block,
                sender=msg_sender,
                current_block=current_block,
                swap_id=swap_id,
            )
            token_1.transfer_from(
                receiver=to,
                amount=amount_out,
                duration=0,
                block_start=current_block,
                sender=pair.get_address(),
                current_block=current_block,
                swap_id=swap_id,
            )
        else:
            token_0.transfer(
                receiver=pair.get_address(),
                amount=amount_in,
                duration=duration,
                block_start=start,
                sender=msg_sender,
                current_block=current_block,
                swap_id=swap_id,
            )
            token_1.transfer(
                receiver=to,
                amount=0,
                duration=0,
                block_start=start,
                sender=pair.get_address(),
                current_block=current_block,
                swap_id=swap_id,
            )
