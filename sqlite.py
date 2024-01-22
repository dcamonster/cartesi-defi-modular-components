import os

from dapp.db import get_connection

db_file_path = os.getenv("DB_FILE_PATH", "dapp.sqlite")


def initialise_db():
    try:
        os.remove(db_file_path)
    except FileNotFoundError:
        pass

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS account (
            address TEXT PRIMARY KEY
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS token (
            address TEXT PRIMARY KEY,
            total_supply TEXT NOT NULL,
            FOREIGN KEY (address) REFERENCES account(address)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pair (
            address TEXT PRIMARY KEY,
            token_0_address TEXT NOT NULL,
            token_1_address TEXT NOT NULL,
            last_timestamp_processed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (address) REFERENCES token(address)
            FOREIGN KEY (token_0_address) REFERENCES token(address)
            FOREIGN KEY (token_1_address) REFERENCES token(address)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS balance (
            amount TEXT NOT NULL,
            account_address TEXT NOT NULL,
            token_address TEXT NOT NULL,
            FOREIGN KEY (account_address) REFERENCES account(address),
            FOREIGN KEY (token_address) REFERENCES token(address),
            PRIMARY KEY (account_address, token_address)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS swap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_address TEXT NOT NULL,
            FOREIGN KEY (pair_address) REFERENCES token(address)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stream (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_address TEXT NOT NULL,
            to_address TEXT NOT NULL,
            start_timestamp INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            amount TEXT NOT NULL,
            token_address TEXT NOT NULL,
            accrued INTEGER NOT NULL,
            swap_id TEXT,
            FOREIGN KEY (token_address) REFERENCES token(address),
            FOREIGN KEY (from_address) REFERENCES account(address),
            FOREIGN KEY (to_address) REFERENCES account(address),
            FOREIGN KEY (swap_id) REFERENCES swap(id)
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_stream_from_address ON stream(from_address)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_stream_to_address ON stream(to_address)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_stream_token_address ON stream(token_address)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stream_accrued ON stream(accrued)")

    conn.commit()

    conn.close()


if __name__ == "__main__":
    initialise_db()
