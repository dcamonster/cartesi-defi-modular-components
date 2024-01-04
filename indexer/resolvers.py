from typing import Optional

import graphene
from db import get_streams, get_connection, get_swaps
from graphene_types import Address, Balance, Cursor, Stream, StreamableERC20, Swap


class Query(graphene.ObjectType):
    all_streams = graphene.List(
        Stream,
        from_address=graphene.String(default_value=None),
        to_address=graphene.String(default_value=None),
        accrued=graphene.Boolean(default_value=None),
        token_address=graphene.String(),
        simulate_future=graphene.Boolean(default_value=False),
        future_timestamp=graphene.Int(default_value=None),
    )
    all_swaps = graphene.List(
        Swap,
        from_address=graphene.String(default_value=None),
        to_address=graphene.String(default_value=None),
        pair_address=graphene.String(default_value=None),
        token_address=graphene.String(),
        simulate_future=graphene.Boolean(default_value=False),
        future_timestamp=graphene.Int(default_value=None),
    )

    all_erc20_tokens = graphene.List(
        StreamableERC20,
        pair_token_0_address=graphene.String(),
        pair_token_1_address=graphene.String(),
        token_address=graphene.String(),
        is_pair=graphene.Boolean(),
    )
    all_balances = graphene.List(
        Balance, address=graphene.String(), token_address=graphene.String()
    )

    def resolve_all_streams(
        self,
        info,
        from_address=None,
        to_address=None,
        accrued=None,
        token_address=None,
        simulate_future=None,
        future_timestamp=None,
    ):
        streams = get_streams(
            from_address=from_address,
            to_address=to_address,
            accrued=accrued,
            token_address=token_address,
            simulate_future=simulate_future,
            future_timestamp=future_timestamp,
        )

        return [
            Stream(
                stream_id=row[0],
                from_address=row[1],
                to_address=row[2],
                token_address=row[3],
                amount=row[4],
                start=row[5],
                duration=row[6],
                accrued=row[7],
                swap_id=row[8],
            )
            for row in streams
        ]

    def resolve_all_swaps(
        self,
        info,
        from_address=None,
        to_address=None,
        token_address=None,
        pair_address=None,
        simulate_future=None,
        future_timestamp=None,
    ):
        swaps = get_swaps(
            from_address=from_address,
            to_address=to_address,
            token_address=token_address,
            pair_address=pair_address,
            simulate_future=simulate_future,
            future_timestamp=future_timestamp,
        )

        return [
            Swap(
                swap_id=row[0],
                pair_address=row[1],
                to_pair=Stream(
                    stream_id=row[2],
                    from_address=row[3],
                    to_address=row[4],
                    token_address=row[5],
                    amount=row[6],
                    start=row[7],
                    duration=row[8],
                    accrued=row[9],
                    swap_id=row[10],
                ),
                from_pair=Stream(
                    stream_id=row[11],
                    from_address=row[12],
                    to_address=row[13],
                    token_address=row[14],
                    amount=row[15],
                    start=row[16],
                    duration=row[17],
                    accrued=row[18],
                    swap_id=row[19],
                ),
            )
            for row in swaps
        ]

    def resolve_all_erc20_tokens(
        self,
        info,
        pair_token_0_address: Optional[str] = None,
        pair_token_1_address: Optional[str] = None,
        token_address: Optional[str] = None,
        is_pair: Optional[bool] = None,
    ):
        # Function to build the SQL query
        def build_query():
            query = """
                SELECT
                    t.address as token_address,
                    t.total_supply,
                    p.address as pair_address,
                    p.token_0_address,
                    p.token_1_address
                FROM token t
                LEFT JOIN pair p ON t.address = p.address
                WHERE 1=1
            """
            arguments = []

            if pair_token_0_address:
                query += " AND p.token_0_address = ?"
                arguments.append(pair_token_0_address)

            if pair_token_1_address:
                query += " AND p.token_1_address = ?"
                arguments.append(pair_token_1_address)

            if token_address:
                query += " AND t.address = ?"
                arguments.append(token_address)

            if is_pair:  # Explicitly check against None
                query += " AND pair_address IS NOT NULL"

            return query, tuple(arguments)

        # Get connection and execute query
        conn = get_connection()
        query, arguments = build_query()

        cursor = conn.cursor()
        cursor.execute(query, arguments)
        results = cursor.fetchall()
        conn.close()

        # Transform the results into a list of StreamableERC20 objects
        return [
            StreamableERC20(
                token_address=row[0],
                total_supply=row[1],
                is_pair=row[2] is not None,
                pair_token_0_address=row[3],
                pair_token_1_address=row[4],
            )
            for row in results
        ]

    def resolve_all_balances(
        self, info, address: Optional[str] = None, token_address: Optional[str] = None
    ):
        conn = get_connection()

        # Begin your SQL query
        query = """
            SELECT b.account_address, b.token_address, b.amount
            FROM balance b
            WHERE 1=1
        """

        # A list to keep track of arguments to be passed
        arguments = []

        # If address is provided, filter by it
        if address:
            query += " AND b.account_address = ?"
            arguments.append(address)  # Add to our arguments list

        # If token_address is provided, filter by it
        if token_address:
            query += " AND b.token_address = ?"
            arguments.append(token_address)  # Add to our arguments list

        cursor = conn.cursor()
        cursor.execute(query, tuple(arguments))
        results = cursor.fetchall()
        conn.close()

        return [
            Balance(address=row[0], token_address=row[1], amount=row[2])
            for row in results
        ]
