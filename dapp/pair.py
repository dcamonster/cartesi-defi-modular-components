from dapp.streamabletoken import StreamableToken
from dapp.util import apply, get_pair_address, sort_tokens, with_checksum_address


@apply(with_checksum_address)
class Pair(StreamableToken):
    def __init__(self, connection, _token0: str, _token1: str):
        super().__init__(
            connection,
            get_pair_address(_token0, _token1),
        )
        (token0, token1) = sort_tokens(_token0, _token1)
        self.token0 = StreamableToken(
            connection, _token0 if token0 == _token0 else _token1
        )
        self.token1 = StreamableToken(
            connection, _token1 if token1 == _token1 else _token0
        )

    def get_reserves(self, at_timestamp):
        return (
            self.token0.balance_of(super().get_address(), at_timestamp),
            self.token1.balance_of(super().get_address(), at_timestamp),
        )

    def get_tokens(self):
        return (self.token0, self.token1)
