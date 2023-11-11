import sqlite3
from typing import List
from dapp.stream import Stream
from dapp.util import int_to_str, str_to_int

db_file_path = "dapp.db"


def get_connection():
    conn = sqlite3.connect(db_file_path)
    conn.cursor().execute("PRAGMA foreign_keys = ON")
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


def stream_from_row(row) -> Stream:
    return Stream(
        stream_id=row[0],
        from_address=row[1],
        to_address=row[2],
        start_block=row[3],
        block_duration=row[4],
        amount=str_to_int(row[5]),
        token_address=row[6],
        accrued=True if row[7] == 1 else False,
        pair_address=row[8] if len(row) > 8 else None,
    )


def get_wallet_non_accrued_streams(
    connection, account_address, token_address
) -> List[Stream]:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ? AND accrued = 0
        """,
        (account_address, account_address, token_address),
    )
    rows = cursor.fetchall()

    streams = []
    for row in rows:
        streams.append(stream_from_row(row))

    return streams


def get_wallet_endend_streams(
    connection, account_address, token_address, current_block
) -> List[Stream]:
    create_account_if_not_exists(connection, account_address)
    create_token_if_not_exists(connection, token_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ? AND start_block + block_duration <= ? AND accrued = 0
        """,
        (account_address, account_address, token_address, current_block),
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
    if stream.pair_address is not None:
        create_token_if_not_exists(connection, stream.pair_address)
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO stream (from_address, to_address, start_block, block_duration, amount, token_address, accrued, pair_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stream.from_address,
            stream.to_address,
            stream.start_block,
            stream.block_duration,
            int_to_str(stream.amount),
            stream.token_address,
            1 if stream.accrued else 0,
            stream.pair_address,
        ),
    )

    return cursor.lastrowid


def update_stream_amount_duration(connection, stream_id, block_duration, amount):
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE stream
        SET block_duration = ?, amount = ?
        WHERE id = ?
        """,
        (block_duration, int_to_str(amount), stream_id),
    )


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
