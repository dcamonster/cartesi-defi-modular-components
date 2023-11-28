from dapp.db import set_last_block_processed, update_sream_amount
from dapp.pair import Pair
from dapp.stream import Stream
from dapp.swap import Swap
from dapp.util import get_amount_out, int_to_str, str_to_int, with_checksum_address


def get_updatable_pairs(connection, wallet_address, block_number):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT s.pair_address, p.token_0_address, p.token_1_address, p.last_block_processed
        FROM swap s
        JOIN stream st ON s.id = st.swap_id
        JOIN pair p ON s.pair_address = p.address
        WHERE st.to_address = ? AND st.accrued = 0 
        AND st.start_block <= ?
        """,
        (
            wallet_address,
            block_number,
        ),
    )
    return cursor.fetchall()


def get_swaps_for_pair_address(connection, pair: Pair, block_number: int):
    cursor = connection.cursor()

    pair_address = pair.get_address()

    # Realizar la consulta
    cursor.execute(
        """
        SELECT s.id, st.*
        FROM swap s
        JOIN stream st ON s.id = st.swap_id
        WHERE s.pair_address = ?
        AND st.start_block <= ?
        """,
        (pair_address, block_number),
    )

    swap_data = {}
    for row in cursor.fetchall():
        swap_id = row[0]
        stream_data = row[1:]

        if swap_id not in swap_data:
            swap_data[swap_id] = {
                "pair": None,
                "streams": [],
            }

        swap_data[swap_id]["streams"].append(Stream(*stream_data))

    swaps = []
    for swap_id, data in swap_data.items():
        stream_to_pair = (
            data["streams"][0]
            if data["streams"][0].to_address == pair_address
            else data["streams"][1]
        )

        stream_to_wallet = (
            data["streams"][0]
            if stream_to_pair == data["streams"][1]
            else data["streams"][1]
        )
        swap = Swap(swap_id, pair, stream_to_pair, stream_to_wallet)
        swaps.append(swap)

    return swaps


@with_checksum_address
def hook(connection, token_address, wallet, to_block):
    updatable_pairs = get_updatable_pairs(connection, wallet, to_block)
    for (
        pair_address,
        token_0_address,
        token_1_address,
        last_block_processed,
    ) in updatable_pairs:
        pair = Pair(connection, token_0_address, token_1_address)
        swaps = get_swaps_for_pair_address(connection, pair, to_block)
        (reserve_in, reserve_out) = pair.get_reserves(last_block_processed)

        for block in range(last_block_processed, to_block + 1):
            token_0_in_sum = sum(
                [
                    str_to_int(swap.stream_to_pair.amount)
                    // swap.stream_to_pair.block_duration
                    for swap in swaps
                    if swap.stream_to_pair.token_address == token_0_address
                    and swap.stream_to_pair.is_active(block)
                ]
            )
            token_1_in_sum = sum(
                [
                    str_to_int(swap.stream_to_pair.amount)
                    // swap.stream_to_pair.block_duration
                    for swap in swaps
                    if swap.stream_to_pair.token_address == token_1_address
                    and swap.stream_to_pair.is_active(block)
                ]
            )

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
                if not swap.stream_to_pair.is_active(block):
                    continue
                if swap.stream_to_pair.token_address == token_0_address:
                    amt = (
                        str_to_int(swap.stream_to_pair.amount)
                        // swap.stream_to_pair.block_duration
                    )
                    swap.stream_to_wallet.amount = int_to_str(
                        str_to_int(swap.stream_to_wallet.amount)
                        + (amt * amount_out_token_1 // token_0_in_sum)
                    )
                else:
                    amt = (
                        swap.stream_to_pair.amount // swap.stream_to_pair.block_duration
                    )
                    swap.stream_to_wallet.amount = int_to_str(
                        str_to_int(swap.stream_to_wallet.amount)
                        + (amt * amount_out_token_0 // token_1_in_sum)
                    )
            # then update reserves
            reserve_in += token_0_in_sum - amount_out_token_0
            reserve_out += token_1_in_sum - amount_out_token_1

        streams_to_update = [
            [swap.stream_to_wallet.amount, swap.stream_to_wallet.id] for swap in swaps
        ]

        update_sream_amount(connection, streams_to_update)
        set_last_block_processed(connection, pair_address, to_block)
