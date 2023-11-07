from typing import Optional

class Stream:
    def __init__(
        self,
        stream_id: int,
        from_address: str,
        to_address: str,
        start_block: int,
        block_duration: int,
        amount: int,
        token_address: str,
        pair_address: Optional[str] = None,
    ):
        self.id = stream_id
        self.from_address = from_address
        self.to_address = to_address
        self.start_block = start_block
        self.block_duration = block_duration
        self.amount = amount
        self.token_address = token_address
        self.pair_address = pair_address

    def is_live(self, current_block: int) -> bool:
        return current_block < self.start_block + self.block_duration

    def streamed_amount(self, at_block: int) -> int:
        if at_block < self.start_block:
            return 0
        if at_block >= self.start_block + self.block_duration:
            return self.amount

        elapsed = at_block - self.start_block
        return (self.amount * elapsed) // self.block_duration
