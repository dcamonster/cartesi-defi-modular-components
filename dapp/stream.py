from typing import Optional


class Stream:
    def __init__(
        self,
        stream_id: int,
        from_address: str,
        to_address: str,
        start_timestamp: int,
        duration: int,
        amount: int,
        token_address: str,
        accrued: bool,
        swap_id: Optional[str] = None,
    ):
        self.id = stream_id
        self.from_address = from_address
        self.to_address = to_address
        self.start_timestamp = start_timestamp
        self.duration = duration
        self.amount = amount
        self.token_address = token_address
        self.accrued = accrued
        self.swap_id = swap_id

    def has_started(self, current_timestamp: int) -> bool:
        return current_timestamp >= self.start_timestamp

    def has_ended(self, current_timestamp: int) -> bool:
        return current_timestamp >= self.start_timestamp + self.duration

    def is_active(self, current_timestamp: int) -> bool:
        return self.has_started(current_timestamp) and not self.has_ended(current_timestamp)

    def streamed_amt(self, until_timestamp: int) -> int:
        if not self.has_started(until_timestamp):
            return 0
        if self.has_ended(until_timestamp):
            return self.amount

        elapsed = until_timestamp - self.start_timestamp
        return (self.amount * elapsed) // self.duration
