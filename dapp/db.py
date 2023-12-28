import sqlite3
from typing import List
from dapp.stream import Stream
from dapp.util import int_to_str, str_to_int, to_checksum_address

db_file_path = "dapp.sqlite"


def get_connection():
    conn = sqlite3.connect(db_file_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    return conn


def create_account_if_not_exists(connection, address):
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO account (address) VALUES (?)
        """,
        (address,),
    )


def create_token_if_not_exists(connection, token_address, default_total_supply=0):
    create_account_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO token (address, total_supply)
        VALUES (?, ?)
        """,
        (token_address, int_to_str(default_total_supply)),
    )


def create_pair_if_not_exists(
    connection, token_address, token_0_address, token_1_address
):
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO pair (address, token_0_address, token_1_address)
        VALUES (?, ?, ?)
        """,
        (token_address, token_0_address, token_1_address),
    )
    return cursor.lastrowid


def create_swap(connection, pair_address, token_0_address, token_1_address):
    create_pair_if_not_exists(
        connection, pair_address, token_0_address, token_1_address
    )
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO swap (pair_address)
        VALUES (?)
        """,
        (pair_address,),
    )
    return cursor.lastrowid


def stream_from_row(row) -> Stream:
    return Stream(
        stream_id=row[0],
        from_address=row[1],
        to_address=row[2],
        start_timestamp=row[3],
        duration=row[4],
        amount=str_to_int(row[5]),
        token_address=row[6],
        accrued=True if row[7] == 1 else False,
        swap_id=row[8] if len(row) > 8 else None,
    )


def get_wallet_non_accrued_streamed_amts(
    connection, account_address, token_address, until_timestamp
):
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT start_timestamp, duration, amount, to_address
        FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ? AND accrued = 0
        AND start_timestamp <= ?
        """,
        (account_address, account_address, token_address, until_timestamp),
    )

    for row in cursor:
        start_timestamp, duration, amount, to_address = row
        amount = int(amount)

        if until_timestamp < start_timestamp:
            streamed_amount = 0
        elif until_timestamp >= start_timestamp + duration:
            streamed_amount = amount
        else:
            elapsed = until_timestamp - start_timestamp
            streamed_amount = (amount * elapsed) // duration

        yield (streamed_amount if to_address == account_address else -streamed_amount)


def get_wallet_streams(connection, account_address, token_address) -> List[Stream]:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ?
        """,
        (account_address, account_address, token_address),
    )
    rows = cursor.fetchall()

    streams = []
    for row in rows:
        streams.append(stream_from_row(row))

    return streams


def get_max_end_timestamp_for_wallet(connection, account_address):
    create_account_if_not_exists(connection, account_address)

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT MAX(start_timestamp + duration)
        FROM stream
        WHERE (from_address = ? OR to_address = ?)
        """,
        (account_address, account_address),
    )

    result = cursor.fetchone()
    max_end_timestamp = result[0] if result else 0

    return max_end_timestamp


def get_wallet_endend_streams(
    connection, account_address, token_address, current_timestamp
) -> List[Stream]:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ? AND start_timestamp + duration <= ? AND accrued = 0
        """,
        (account_address, account_address, token_address, current_timestamp),
    )
    rows = cursor.fetchall()

    streams = []
    for row in rows:
        streams.append(stream_from_row(row))

    return streams


def get_stream_by_id(connection, stream_id) -> Stream:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE id = ?
        """,
        (stream_id,),
    )
    row = cursor.fetchone()

    if row is not None:
        return stream_from_row(row)
    else:
        return None


def get_balance(connection, account_address, token_address) -> int:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT amount FROM balance
        WHERE account_address = ? AND token_address = ?
        """,
        (account_address, token_address),
    )
    row = cursor.fetchone()

    return str_to_int(row[0]) if row else 0


def set_balance(connection, account_address, token_address, amount) -> None:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO balance (account_address, token_address, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(account_address, token_address)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        (account_address, token_address, int_to_str(amount)),
    )


def add_stream(connection, stream) -> int:
    create_account_if_not_exists(connection, stream.from_address)
    create_account_if_not_exists(connection, stream.to_address)
    create_token_if_not_exists(connection, stream.token_address)
    # if stream.pair_address is not None:
    #     create_token_if_not_exists(connection, stream.pair_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO stream (from_address, to_address, start_timestamp, duration, amount, token_address, accrued, swap_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stream.from_address,
            stream.to_address,
            stream.start_timestamp,
            stream.duration,
            int_to_str(stream.amount),
            stream.token_address,
            1 if stream.accrued else 0,
            stream.swap_id,
        ),
    )

    return cursor.lastrowid


def update_stream_amount_duration(connection, stream_id, duration, amount):
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE stream
        SET duration = ?, amount = ?
        WHERE id = ?
        """,
        (duration, int_to_str(amount), stream_id),
    )


def update_stream_amount_duration_batch(connection, stream_durations_amounts_ids):
    cursor = connection.cursor()
    cursor.executemany(
        """
        UPDATE stream
        SET duration = ?, amount = ?
        WHERE id = ?
        """,
        stream_durations_amounts_ids,
    )
    return cursor.lastrowid


def update_stream_accrued(connection, stream_id, accrued):
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE stream
        SET accrued = ?
        WHERE id = ?
        """,
        (1 if accrued else 0, stream_id),
    )


def delete_stream_by_id(connection, stream_id):
    cursor = connection.cursor()
    cursor.execute(
        """
        DELETE FROM stream
        WHERE id = ?
        """,
        (stream_id,),
    )


def get_total_supply(connection, token_address) -> int:
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT total_supply FROM token
        WHERE address = ?
        """,
        (token_address,),
    )
    row = cursor.fetchone()

    return str_to_int(row[0]) if row else 0


def set_total_supply(connection, token_address: str, total_supply: int):
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO token (address, total_supply)
        VALUES (?, ?)
        ON CONFLICT(address)
        DO UPDATE SET total_supply = ?
        """,
        (token_address, int_to_str(total_supply), int_to_str(total_supply)),
    )


def set_last_timestamp_processed(connection, pair_address: str, last_timestamp_processed: int):
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE pair
        SET last_timestamp_processed = ?
        WHERE address = ?
        """,
        (
            last_timestamp_processed,
            pair_address,
        ),
    )


# Test only
def stream_test(payload, sender, start_timestamp, connection):
    split_number = int(payload["args"]["split_number"])
    split_amount = int(payload["args"]["amount"]) // split_number

    sender_checksum = to_checksum_address(sender)
    receiver_checksum = to_checksum_address(payload["args"]["receiver"])
    token_checksum = to_checksum_address(payload["args"]["token"])

    create_account_if_not_exists(connection, sender_checksum)
    create_account_if_not_exists(connection, receiver_checksum)
    create_token_if_not_exists(connection, token_checksum)
    stream_data = []
    amt = str(int(split_amount))
    duration = int(payload["args"]["duration"])
    for number in range(split_number):
        stream_data.append(
            (
                sender_checksum,
                receiver_checksum,
                start_timestamp,
                duration + number,
                amt,
                token_checksum,
                0,
                None,
            )
        )

    cursor = connection.cursor()
    cursor.executemany(
        """
                INSERT INTO stream (from_address, to_address, start_timestamp, duration, amount, token_address, accrued, swap_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
        stream_data,
    )


def get_updatable_pairs(connection, wallet_address, token_address, start_timestamp):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT s.pair_address, p.token_0_address, p.token_1_address, p.last_timestamp_processed
        FROM swap s
        JOIN stream st ON s.id = st.swap_id
        JOIN pair p ON s.pair_address = p.address
        WHERE st.to_address = ? AND st.accrued = 0 
        AND p.token_0_address == ? OR p.token_1_address == ?
        AND st.start_timestamp <= ?
        """,
        (
            wallet_address,
            token_address,
            token_address,
            start_timestamp,
        ),
    )
    return cursor.fetchall()


def get_swaps_for_pair_address(connection, pair_address: str, start_timestamp: int):
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 
            st_from_pair.id AS from_pair_id,
            st_from_pair.amount AS from_pair_amount,
            st_from_pair.duration AS from_pair_duration,
            st_to_pair.amount AS to_pair_amount, 
            st_to_pair.start_timestamp AS to_pair_start_timestamp,
            st_to_pair.duration AS to_pair_duration,
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
            st_to_pair.start_timestamp <= ? AND st_from_pair.start_timestamp <= ?
        AND 
            st_to_pair.to_address = ? AND st_from_pair.from_address = ?
        """,
        (
            pair_address,
            start_timestamp,
            start_timestamp,
            pair_address,
            pair_address,
        ),
    )

    return cursor.fetchall()
