from dapp.pair import Pair
from dapp.stream import Stream


class Swap:
    def __init__(
        self,
        swap_id: int,
        pair: Pair,
        stream_to_pair: Stream,
        stream_to_wallet: Stream,
    ):
        self.id = swap_id
        self.pair = pair
        self.stream_to_pair = stream_to_pair
        self.stream_to_wallet = stream_to_wallet
