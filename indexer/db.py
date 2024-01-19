import sqlite3
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# Add the parent directory of `dapp` to the Python path
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from dapp.db import get_max_end_timestamp_for_wallet, get_wallet_token_streamed
from dapp.hook import hook

from utils import with_checksum_address

db_file_path =  os.getenv("DB_FILE_PATH", "dapp.sqlite")


def get_connection():
    # Opening the connection in read-write mode
    conn = sqlite3.connect(f"file:{db_file_path}?mode=rw", uri=True)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Disable auto-commit mode
    conn.isolation_level = None

    return conn


def close_connection(conn):
    conn.close()


def create_last_cursor_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS last_cursor (
            id INTEGER PRIMARY KEY,
            last_cursor_value TEXT
        )
    """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO last_cursor (id, last_cursor_value) VALUES (1, NULL)
    """
    )
    conn.commit()


def get_last_cursor():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_cursor_value FROM last_cursor WHERE id = 1")
    result = cursor.fetchone()
    return result[0] if result else None


def set_last_cursor(cursor_value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE last_cursor SET last_cursor_value = ? WHERE id = 1
    """,
        (cursor_value,),
    )
    conn.commit()


@with_checksum_address
def get_streams(
    from_address=None,
    to_address=None,
    accrued=None,
    token_address=None,
    simulate_future=None,
    future_timestamp=None,
):
    conn = get_connection()
    conn.execute("SAVEPOINT get_streams")
    try:
        if simulate_future:
            account_address = from_address if from_address else to_address
            if not account_address:
                raise Exception("Must provide either from_address or to_address")
            max_timestamp = (
                future_timestamp
                if future_timestamp
                else get_max_end_timestamp_for_wallet(conn, account_address)
            )
            tokens = get_wallet_token_streamed(conn, account_address)
            for t in tokens:
                hook(conn, t[0], account_address, max_timestamp)

        where_clause = []
        params = []

        if from_address:
            where_clause.append("s.from_address = ?")
            params.append(from_address)

        if to_address:
            where_clause.append("s.to_address = ?")
            params.append(to_address)

        if token_address:
            where_clause.append("s.token_address = ?")
            params.append(token_address)

        where_sql = " AND ".join(where_clause) if where_clause else "1=1"

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT 
                s.id,
                s.from_address,
                s.to_address,
                s.token_address,
                s.amount,
                s.start_timestamp,
                s.duration,
                s.accrued,
                s.swap_id
            FROM stream s
            WHERE {where_sql}
        """,
            params,
        )
        results = cursor.fetchall()
    finally:
        conn.execute("ROLLBACK TO SAVEPOINT get_streams")
        conn.execute("RELEASE SAVEPOINT get_streams")
        conn.close()

    return results


@with_checksum_address
def get_swaps(
    from_address=None,
    to_address=None,
    token_address=None,
    pair_address=None,
    future_timestamp=None,
    simulate_future=None,
):
    conn = get_connection()
    conn.execute("SAVEPOINT get_swaps")
    try:
        if simulate_future:
            account_address = from_address if from_address else to_address
            if not account_address:
                raise Exception("Must provide either from_address or to_address")
            max_timestamp = (
                future_timestamp
                if future_timestamp
                else get_max_end_timestamp_for_wallet(conn, account_address)
            )
            tokens = get_wallet_token_streamed(conn, account_address)
            for t in tokens:
                hook(conn, t[0], account_address, max_timestamp)

        where_clause = []
        outter_where_clause = []
        params = []

        # Build the WHERE clause based on provided addresses
        if from_address:
            where_clause.append("s.from_address = ? OR s.to_address = ?")
            params.append(from_address)
            params.append(from_address)

        if to_address:
            where_clause.append("s.to_address = ? OR s.from_address = ?")
            params.append(to_address)
            params.append(to_address)

        if token_address:
            where_clause.append("s.token_address = ?")
            params.append(token_address)

        if pair_address:
            outter_where_sql.append("sw.pair_address = ?")
            params.append(pair_address)

        where_sql = " AND ".join(where_clause) if where_clause else "1=1"
        outter_where_sql = (
            " AND ".join(outter_where_clause) if outter_where_clause else "1=1"
        )

        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                sw.id AS swap_id,
                sw.pair_address,
                s1.id AS s1_id,
                s1.from_address AS s1_from_address,
                s1.to_address AS s1_to_address,
                s1.token_address AS s1_token_address,
                s1.amount AS s1_amount,
                s1.start_timestamp AS s1_start_timestamp,
                s1.duration AS s1_duration,
                s1.accrued AS s1_accrued,
                s1.swap_id AS s1_swap_id,
                s2.id AS s2_id,
                s2.from_address AS s2_from_address,
                s2.to_address AS s2_to_address,
                s2.token_address AS s2_token_address,
                s2.amount AS s2_amount,
                s2.start_timestamp AS s2_start_timestamp,
                s2.duration AS s2_duration,
                s2.accrued AS s2_accrued,
                s2.swap_id AS s2_swap_id
            FROM swap sw
            JOIN stream s1 ON sw.id = s1.swap_id AND s1_to_address = sw.pair_address
            JOIN stream s2 ON sw.id = s2.swap_id AND s2_from_address = sw.pair_address
            WHERE sw.id IN (
                SELECT distinct s.swap_id
                FROM stream s
                WHERE s.swap_id IS NOT NULL AND {where_sql}
            )
            AND {outter_where_sql}
            """,
            params,
        )
        results = cursor.fetchall()
    finally:
        conn.execute("ROLLBACK TO SAVEPOINT get_swaps")
        conn.execute("RELEASE SAVEPOINT get_swaps")
        conn.close()

    return results
