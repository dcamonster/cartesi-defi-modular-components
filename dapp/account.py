from dapp.stream import Stream
from eth_utils import to_checksum_address


class Account:
    def __init__(self, token_address: str, user_address: str):
        self.token_address = to_checksum_address(token_address)
        self.user_address = to_checksum_address(user_address)
        self.balance = 0
        self.streams = []

    def update_balance(self, new_balance: int):
        # Update the user's balance for the token
        self.balance = new_balance
