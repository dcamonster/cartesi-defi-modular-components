import os

from dapp.db import get_connection

db_file_path = "dapp.db"


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
        CREATE TABLE IF NOT EXISTS stream (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_address TEXT NOT NULL,
            to_address TEXT NOT NULL,
            start_block INTEGER NOT NULL,
            block_duration INTEGER NOT NULL,
            amount TEXT NOT NULL,
            token_address TEXT NOT NULL,
            pair_address TEXT,
            accrued INTEGER NOT NULL,
            FOREIGN KEY (token_address) REFERENCES token(address),
            FOREIGN KEY (pair_address) REFERENCES token(address),
            FOREIGN KEY (from_address) REFERENCES account(address),
            FOREIGN KEY (to_address) REFERENCES account(address)
        )
        """
    )

    conn.commit()

    conn.close()


if __name__ == "__main__":
    initialise_db()
