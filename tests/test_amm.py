import unittest
from unittest.mock import MagicMock, Mock, patch

import requests
from dapp.amm import AMM
from dapp.db import get_connection
from dapp.hook import hook
from dapp.pair import Pair
from dapp.streamabletoken import StreamableToken
from dapp.util import get_amount_out
from sqlite import initialise_db
from tests.utils import calculate_total_supply_token


class TestAmm(unittest.TestCase):
    def setUp(self):
        initialise_db()
        self.connection = get_connection()
        self.mock_post = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}  # Mocked response
        self.mock_post.return_value = mock_response
        requests.post = self.mock_post

        self.token_one_address = "0x1234567890ABCDEF1234567890ABCDEF12345678"
        self.token_two_address = "0x1234567890ABCDEF1234567890ABCDEF12345679"
        self.lp_address = "0x1234567890ABCDEF1234567890ABCDEF12345672"
        self.trader_address = "0xabCDEF1234567890ABcDEF1234567890aBCDeF12"
        self.random_address = "0x1234567890ABCDEF1234567890ABCDEF12345670"

        self.token_one = StreamableToken(self.connection, self.token_one_address)
        self.token_two = StreamableToken(self.connection, self.token_two_address)
        self.pair = Pair(
            self.connection, self.token_one_address, self.token_two_address
        )
        self.amm = AMM(self.connection)

        self.initial_balance = 100 * 10**18
        self.token_one.mint(self.initial_balance, self.lp_address)
        self.token_two.mint(self.initial_balance, self.lp_address)

    def tearDown(self):
        for token in [self.token_one, self.token_two, self.pair]:
            calculated_supply = calculate_total_supply_token(
                self.connection, token.get_address()
            )
            total_supply = token.get_stored_total_supply()
            self.assertEqual(
                calculated_supply,
                total_supply,
                "Total supply is not equal to calculated supply.",
            )

    @patch("requests.post")
    def test_add_and_remove_liquidity(self, mock_post):
        current_block = 0
        # Test Add liquidity
        liquidity = self.amm.add_liquidity(
            self.token_one_address,
            self.token_two_address,
            self.initial_balance,
            self.initial_balance,
            0,
            0,
            self.lp_address,
            self.lp_address,
            current_block,
        )

        token_one_balance = self.token_one.balance_of(self.lp_address, current_block)
        token_two_balance = self.token_two.balance_of(self.lp_address, current_block)

        self.assertEqual(
            token_one_balance,
            0,
            "Token one balance is less than 0 after adding liquidity.",
        )
        self.assertEqual(
            token_two_balance,
            0,
            "Token two balance is less than 0 after adding liquidity.",
        )

        current_block += 1

        # Test Remove liquidity
        self.amm.remove_liquidity(
            self.token_one_address,
            self.token_two_address,
            liquidity,
            0,
            0,
            self.lp_address,
            self.lp_address,
            current_block,
        )

        # Check if the stored balances after removing liquidity are not less than 0
        token_one_balance_after = self.token_one.balance_of(
            self.lp_address, current_block
        )
        token_two_balance_after = self.token_two.balance_of(
            self.lp_address, current_block
        )

        self.assertGreaterEqual(
            token_one_balance_after,
            0,
            "Token one balance is less than 0 after removing liquidity.",
        )
        self.assertGreaterEqual(
            token_two_balance_after,
            0,
            "Token two balance is less than 0 after removing liquidity.",
        )

    @patch("requests.post")
    def test_swap(self, mock_post):
        current_block = 0
        # Test Add liquidity
        self.amm.add_liquidity(
            self.token_one_address,
            self.token_two_address,
            self.initial_balance,
            self.initial_balance,
            0,
            0,
            self.lp_address,
            self.lp_address,
            current_block,
        )

        self.token_one.mint(self.initial_balance, self.trader_address)

        (token_one_reserve, token_two_reserve) = self.pair.get_reserves(current_block)
        token_two_out = get_amount_out(
            self.initial_balance, token_one_reserve, token_two_reserve
        )
        self.amm.swap_exact_tokens_for_tokens(
            amount_in=self.initial_balance,
            amount_out_min=0,
            path=[self.token_one_address, self.token_two_address],
            start=current_block + 100,
            duration=10000,
            to=self.trader_address,
            msg_sender=self.trader_address,
            current_block=current_block,
        )

        hook(
            self.connection,
            self.pair.get_address(),
            self.trader_address,
            current_block + 20000,
        )

        print(token_two_out)
        actual_balance = self.token_two.balance_of(
            self.trader_address, current_block + 300
        )
        difference = token_two_out / actual_balance
        print((1 - difference) * 100)


if __name__ == "__main__":
    unittest.main()
