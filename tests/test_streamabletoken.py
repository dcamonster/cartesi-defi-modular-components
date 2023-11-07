import unittest
from unittest.mock import MagicMock, Mock, patch

import requests
from dapp.db import get_connection
from dapp.streamabletoken import StreamableToken
from sqlite import clear_db
from tests.utils import calculate_total_supply_token


class TestStreamableToken(unittest.TestCase):
    def setUp(self):
        clear_db()
        self.connection = get_connection()
        self.mock_post = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}  # Mocked response
        self.mock_post.return_value = mock_response
        requests.post = self.mock_post

        self.token_address = "0x1234567890AbcdEF1234567890ABCDEF12345673"
        self.sender_address = "0x1234567890ABCDEF1234567890ABCDEF12345672"
        self.receiver_address = "0xabCDEF1234567890ABcDEF1234567890aBCDeF12"
        self.random_address = "0x1234567890ABCDEF1234567890ABCDEF12345670"
        self.random_address_2 = "0x1234567890ABCDEF1234567890ABCDEF12345671"

        self.token = StreamableToken(self.connection, self.token_address)

    def tearDown(self):
        token = StreamableToken(self.connection, self.token_address)
        calculated_supply = calculate_total_supply_token(
            self.connection, self.token_address
        )
        total_supply = token.get_stored_total_supply()
        self.assertEqual(
            calculated_supply,
            total_supply,
            "Total supply is not equal to calculated supply.",
        )

    def test_transfer_from(self):
        amount = 100
        block_duration = 0
        current_block = 0
        start_block = 0

        self.token.mint(100, self.sender_address)

        self.token.transfer_from(
            self.sender_address,
            self.receiver_address,
            amount,
            block_duration,
            start_block,
            current_block,
        )

    def test_transfer_from_stream(self):
        amount = 100
        block_duration = 1000
        current_block = 0
        start_block = 0

        self.token.mint(100, self.sender_address)

        self.assertEqual(
            self.token.get_stored_balance(self.sender_address),
            amount,
        )
        self.assertEqual(
            self.token.get_stored_total_supply(),
            amount,
        )
        # Transfer tokens in stream
        stream_id = self.token.transfer_from(
            self.sender_address,
            self.receiver_address,
            amount,
            block_duration,
            start_block,
            current_block,
        )

        # After half the duration, the receiver should have half the amount of tokens and the sender the other half
        self.assertEqual(
            self.token.balance_of(
                self.receiver_address, current_block + block_duration / 2
            ),
            amount / 2,
        )

        self.assertEqual(
            self.token.balance_of(
                self.sender_address, current_block + block_duration / 2
            ),
            amount / 2,
        )

        # After the duration, the receiver should have all the tokens and the sender none
        self.assertEqual(
            self.token.balance_of(
                self.receiver_address, current_block + block_duration
            ),
            amount,
        )

        self.assertEqual(
            self.token.balance_of(self.sender_address, current_block + block_duration),
            0,
        )

    def test_transfer_more_than_balance(self):
        current_block = 0
        start_block = 0
        block_duration = 1000
        amount = 100

        self.token.mint(amount, self.sender_address)

        # Transfering more than the balance should raise an exception
        with self.assertRaises(Exception) as context:
            try:
                self.token.transfer_from(
                    self.sender_address,
                    self.receiver_address,
                    amount * 2,
                    block_duration,
                    start_block,
                    current_block,
                )
            except Exception as e:
                self.exception = e
                assert e.args[0] == "Insufficient current balance to transfer"
                self.connection.rollback()
                raise e

        # Send half the amount
        self.token.transfer_from(
            self.sender_address,
            self.receiver_address,
            amount / 2,
            block_duration,
            start_block,
            current_block,
        )

        # Simulate the passage of half the duration
        current_block += block_duration / 2

        with self.assertRaises(Exception) as context:
            try:
                self.token.transfer_from(
                    self.sender_address,
                    self.receiver_address,
                    amount / 2 + 1, # Send more than the remaining balance
                    block_duration,
                    current_block + 100, # Start block is in the future
                    current_block,
                )
            except Exception as e:
                self.exception = e

                assert (
                    e.args[0]
                    == "Insufficient future balance to transfer. Check your streams."
                )
                self.connection.rollback()
                raise e

if __name__ == "__main__":
    unittest.main()
