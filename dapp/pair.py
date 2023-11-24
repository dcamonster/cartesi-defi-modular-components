class Pair:
    def __init__(
        self,
        address: str,
        last_block_processed: int,
    ):
        self.address = address
        self.last_block_processed = last_block_processed
