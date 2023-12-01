from dapp.db import set_last_block_processed, update_sream_amount
from dapp.pair import Pair
from dapp.util import get_amount_out, int_to_str, str_to_int, with_checksum_address


def get_updatable_pairs(connection, wallet_address, token_address, block_number):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT s.pair_address, p.token_0_address, p.token_1_address, p.last_block_processed
        FROM swap s
        JOIN stream st ON s.id = st.swap_id
        JOIN pair p ON s.pair_address = p.address
        WHERE st.to_address = ? AND st.accrued = 0 
        AND p.token_0_address == ? OR p.token_1_address == ?
        AND st.start_block <= ?
        """,
        (
            wallet_address,
            token_address,
            token_address,
            block_number,
        ),
    )
    return cursor.fetchall()


def get_swaps_for_pair_address(connection, pair_address: str, block_number: int):
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 
            st_from_pair.id AS from_pair_id,
            st_from_pair.amount AS from_pair_amount,
            st_to_pair.amount AS to_pair_amount, 
            st_to_pair.start_block AS to_pair_start_block,
            st_to_pair.block_duration AS to_pair_block_duration,
            st_to_pair.token_address AS to_pair_token_address
        FROM 
            swap s
        JOIN 
            stream st_to_pair ON s.id = st_to_pair.swap_id
        JOIN 
            stream st_from_pair ON s.id = st_from_pair.swap_id
        WHERE 
            s.pair_address = ?
        AND 
            st_to_pair.start_block <= ? AND st_from_pair.start_block <= ?
        AND 
            st_to_pair.to_address = ? AND st_from_pair.from_address = ?
        """,
        (
            pair_address,
            block_number,
            block_number,
            pair_address,
            pair_address,
        ),
    )

    return cursor.fetchall()


@with_checksum_address
def hook(connection, token_address, wallet, to_block):
    updatable_pairs = get_updatable_pairs(connection, wallet, token_address, to_block)
    for (
        pair_address,
        token_0_address,
        token_1_address,
        last_block_processed,
    ) in updatable_pairs:
        pair = Pair(connection, token_0_address, token_1_address)
        (reserve_in, reserve_out) = pair.get_reserves(last_block_processed)

        swaps = get_swaps_for_pair_address(connection, pair.get_address(), to_block)

        # Add swap rate to swaps
        swaps = [
            swap + ((str_to_int(swap[2]) // swap[4],) if swap[4] > 0 else (0,))
            for swap in swaps
        ]

        streams_to_update = {swap[0]: str_to_int(swap[1]) for swap in swaps}

        for block in range(last_block_processed, to_block + 1):

            def sum_swaps_token(token_address):
                return sum(
                    [
                        swap[6]
                        for swap in swaps
                        if swap[5] == token_address
                        and swap[3] <= block
                        and swap[3] + swap[4] > block
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
                if swap[3] > block or swap[3] + swap[4] <= block:
                    continue
                if swap[5] == token_0_address:
                    streams_to_update[swap[0]] += (
                        swap[6] * amount_out_token_1 // token_0_in_sum
                    )
                else:
                    streams_to_update[swap[0]] += (
                        swap[6] * amount_out_token_0 // token_1_in_sum
                    )

            reserve_in += token_0_in_sum - amount_out_token_0
            reserve_out += token_1_in_sum - amount_out_token_1

        update_sream_amount(
            connection,
            [[int_to_str(value), key] for key, value in streams_to_update.items()],
        )
        set_last_block_processed(connection, pair_address, to_block)
