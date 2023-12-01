import unittest
from unittest.mock import MagicMock, Mock, patch

import requests
from dapp.db import get_connection
from dapp.streamabletoken import StreamableToken
from sqlite import initialise_db
from tests.utils import calculate_total_supply_token


class TestStreamableToken(unittest.TestCase):
    def setUp(self):
        initialise_db()
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

    def test_initialization(self):
        total_supply = self.token.get_stored_total_supply()
        self.assertEqual(total_supply, 0, "Initial total supply should be zero.")

    def test_minting_tokens(self):
        mint_amount = 1000
        self.token.mint(mint_amount, self.sender_address)
        balance = self.token.get_stored_balance(self.sender_address)
        self.assertEqual(balance, mint_amount, "Minted amount does not match balance.")

    def test_minting_negative_amount(self):
        # Test minting a negative amount (should raise an exception)
        with self.assertRaises(ValueError):
            self.token.mint(-100, self.sender_address)

    def test_burning_tokens(self):
        # Test burning tokens
        current_block = 100
        mint_amount = 1000
        burn_amount = 500
        self.token.mint(mint_amount, self.sender_address)
        self.token.burn(
            amount=burn_amount, sender=self.sender_address, current_block=current_block
        )  # Assuming current_block is 100
        balance = self.token.balance_of(self.sender_address, current_block)
        total_supply = self.token.get_stored_total_supply()
        self.assertEqual(
            balance, mint_amount - burn_amount, "Balance after burn is incorrect."
        )
        self.assertEqual(
            total_supply,
            mint_amount - burn_amount,
            "Total supply after burn is incorrect.",
        )

    def test_burning_more_than_balance(self):
        # Test burning more than the account's balance (should raise an exception)
        mint_amount = 100
        self.token.mint(mint_amount, self.sender_address)
        with self.assertRaises(AssertionError):
            self.token.burn(
                amount=mint_amount + 1, sender=self.sender_address, current_block=100
            )

    def test_transfer_from(self):
        amount = 100
        block_duration = 0
        current_block = 0
        start_block = 0

        self.token.mint(100, self.sender_address)

        self.token.transfer(
            receiver=self.receiver_address,
            amount=amount,
            duration=block_duration,
            block_start=start_block,
            sender=self.sender_address,
            current_block=current_block,
        )

        self.assertEqual(
            self.token.balance_of(self.sender_address, current_block),
            0,
        )
        self.assertEqual(
            self.token.balance_of(self.receiver_address, current_block),
            amount,
        )
        self.assertEqual(
            self.token.get_stored_total_supply(),
            amount,
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
        stream_id = self.token.transfer(
            receiver=self.receiver_address,
            amount=amount,
            duration=block_duration,
            block_start=start_block,
            sender=self.sender_address,
            current_block=current_block,
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
                self.token.transfer(
                    receiver=self.receiver_address,
                    amount=amount * 2,
                    duration=block_duration,
                    block_start=start_block,
                    sender=self.sender_address,
                    current_block=current_block,
                )
            except Exception as e:
                self.exception = e
                assert e.args[0] == "Insufficient current balance to transfer"
                self.connection.rollback()
                raise e

        # Send half the amount
        self.token.transfer(
            receiver=self.receiver_address,
            amount=amount / 2,
            duration=block_duration,
            block_start=start_block,
            sender=self.sender_address,
            current_block=current_block,
        )

        # Simulate the passage of half the duration
        current_block += block_duration / 2

        with self.assertRaises(Exception) as context:
            try:
                self.token.transfer(
                    receiver=self.receiver_address,
                    amount=amount / 2 + 1,  # Send more than the remaining balance
                    duration=block_duration,
                    block_start=current_block + 100,  # Start block is in the future
                    sender=self.sender_address,
                    current_block=current_block,
                )
            except Exception as e:
                self.exception = e

                assert (
                    e.args[0]
                    == "Insufficient future balance to transfer. Check your streams."
                )
                self.connection.rollback()
                raise e

    def test_stream_with_zero_duration(self):
        # Test adding a stream with a duration of zero blocks (should raise an exception)
        self.token.mint(100, self.sender_address)

        self.token.transfer(
            receiver=self.receiver_address,
            amount=50,
            duration=0,
            block_start=0,
            sender=self.sender_address,
            current_block=0,
        )

        assert self.token.balance_of(self.receiver_address, 0) == 50
        assert self.token.balance_of(self.sender_address, 0) == 50

    def test_stream_with_long_duration(self):
        # Test adding a stream with a very long duration
        long_duration = 999999
        mint_amount = 1000
        self.token.mint(mint_amount, self.sender_address)
        stream_id = self.token.transfer(
            receiver=self.receiver_address,
            amount=mint_amount,
            duration=long_duration,
            block_start=0,
            sender=self.sender_address,
            current_block=0,
        )
        self.assertTrue(isinstance(stream_id, int), "Stream ID should be an integer.")

    def test_invalid_addresses(self):
        # Test methods with invalid addresses
        with self.assertRaises(ValueError):
            self.token.mint(100, "InvalidAddress")

    def test_maximum_integer_values(self):
        # Test behavior with maximum integer values
        max_int = 2**63 - 1
        self.token.mint(max_int, self.sender_address)
        balance = self.token.get_stored_balance(self.sender_address)
        self.assertEqual(balance, max_int, "Balance with max int does not match.")


if __name__ == "__main__":
    unittest.main()
