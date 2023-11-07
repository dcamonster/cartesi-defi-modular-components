import sqlite3
from typing import List
from dapp.stream import Stream
from dapp.util import int_to_str, str_to_int

db_file_path = "dapp.db"


def get_connection():
    return sqlite3.connect(db_file_path)


def get_all_wallet_streams(connection, wallet_address, token_address) -> List[Stream]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT * FROM stream
        WHERE (from_address = ? OR to_address = ?) AND token_address = ?
        """,
        (wallet_address, wallet_address, token_address),
    )
    rows = cursor.fetchall()

    streams = []
    for row in rows:
        stream = Stream(
            stream_id=row[0],
            from_address=row[1],
            to_address=row[2],
            start_block=row[3],
            block_duration=row[4],
            amount=str_to_int(row[5]),
            token_address=row[6],
            pair_address=row[7] if len(row) > 7 else None,
        )
        streams.append(stream)

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
        stream = Stream(
            stream_id=row[0],
            from_address=row[1],
            to_address=row[2],
            start_block=row[3],
            block_duration=row[4],
            amount=str_to_int(row[5]),
            token_address=row[6],
            pair_address=row[7] if len(row) > 7 else None,
        )
        return stream
    else:
        return None


def get_balance(connection, wallet_address, token_address) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT amount FROM balance
        WHERE wallet_address = ? AND token_address = ?
        """,
        (wallet_address, token_address),
    )
    row = cursor.fetchone()

    return str_to_int(row[0]) if row else 0


def set_balance(connection, wallet_address, token_address, amount) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO balance (wallet_address, token_address, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(wallet_address, token_address)
        DO UPDATE SET amount = EXCLUDED.amount
        """,
        (wallet_address, token_address, int_to_str(amount)),
    )


def add_stream(connection, stream) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO stream (from_address, to_address, start_block, block_duration, amount, token_address, pair_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stream.from_address,
            stream.to_address,
            stream.start_block,
            stream.block_duration,
            int_to_str(stream.amount),
            stream.token_address,
            stream.pair_address,
        ),
    )

    return cursor.lastrowid


def update_stream_by_id(connection, stream_id, block_duration, amount):
    cursor = connection.cursor()
    cursor.execute(
        """
        UPDATE stream
        SET block_duration = ?, amount = ?
        WHERE id = ?
        """,
        (block_duration, int_to_str(amount), stream_id),
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
