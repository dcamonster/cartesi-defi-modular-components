import os
import sqlite3

db_file_path = "dapp.db"

# Delete the file if it exists
try:
    os.remove(db_file_path)
except FileNotFoundError:
    pass

# Connect to the SQLite database
conn = sqlite3.connect(db_file_path)
cursor = conn.cursor()

# Create 'account' table
cursor.execute("""
CREATE TABLE IF NOT EXISTS account (
    address TEXT PRIMARY KEY
)
""")

# Create 'balance' table
cursor.execute("""
CREATE TABLE IF NOT EXISTS balance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,
    account TEXT NOT NULL,
    FOREIGN KEY (account) REFERENCES account(address)
)
""")

# Create 'stream' table
cursor.execute("""
CREATE TABLE IF NOT EXISTS stream (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_account TEXT NOT NULL,
    to_account TEXT NOT NULL,
    start_block INTEGER NOT NULL,
    block_duration INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    pair_account TEXT,
    FOREIGN KEY (from_account) REFERENCES account(address),
    FOREIGN KEY (to_account) REFERENCES account(address),
    FOREIGN KEY (pair_account) REFERENCES account(address)
)
""")

# Commit the changes
conn.commit()

# Close the connection
conn.close()
