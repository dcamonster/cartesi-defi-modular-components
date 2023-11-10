from dapp.streamabletoken import StreamableToken
from dapp.util import with_checksum_address, ZERO_ADDRESS


def get_unique_addresses_for_token(connection, token_address):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT from_address FROM stream WHERE token_address = ?
        UNION
        SELECT DISTINCT to_address FROM stream WHERE token_address = ?
        """,
        (token_address, token_address),
    )
    stream_addresses = set(cursor.fetchall())

    cursor.execute(
        """
        SELECT DISTINCT account_address FROM balance WHERE token_address = ?
        """,
        (token_address,),
    )
    balance_addresses = set(cursor.fetchall())

    unique_addresses = {
        address for tup in (stream_addresses | balance_addresses) for address in tup
    }

    return list(unique_addresses)


@with_checksum_address
def calculate_total_supply_token(connection, token_address):
    addresses = get_unique_addresses_for_token(connection, token_address)
    token = StreamableToken(connection, token_address)
    total_supply = 0
    for wallet in [address for address in addresses if address != ZERO_ADDRESS]:
        balance = token.balance_of(wallet, 2**63 - 1)
        assert balance >= 0, "Balance cannot be negative."
        total_supply += balance
    return total_supply
