from dapp.db import (
    get_swaps_for_pair_address,
    get_updatable_pairs,
    set_last_block_processed,
    update_stream_amount_duration_batch,
)
from dapp.util import get_amount_out, int_to_str, str_to_int, with_checksum_address


@with_checksum_address
def hook(connection, token_address, wallet, to_block):
    from dapp.streamabletoken import StreamableToken
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
