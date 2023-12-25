import json
import logging
import hashlib
from os import environ

# External libraries
from eth_abi.codec import ABICodec
from eth_abi.decoding import AddressDecoder, BooleanDecoder, UnsignedIntegerDecoder
from eth_abi.registry import BaseEquals, registry_packed
from eth_utils import is_hex_address, to_checksum_address, is_checksum_address

# Constants
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MINIMUM_LIQUIDITY = 100000
MAX_INT64 = 2**63 - 1
USER_FEES = 0  # per 1000


# Custom Decoder Classes
class PackedBooleanDecoder(BooleanDecoder):
    data_byte_size = 1


class PackedAddressDecoder(AddressDecoder):
    data_byte_size = 20


# Registering Custom Decoders
registry_packed.register_decoder(BaseEquals("bool"), PackedBooleanDecoder, label="bool")
registry_packed.register_decoder(
    BaseEquals("address"), PackedAddressDecoder, label="address"
)
registry_packed.register_decoder(
    BaseEquals("uint"), UnsignedIntegerDecoder, label="uint"
)

# Codec for packed data
default_codec_packed = ABICodec(registry_packed)
decode_packed = default_codec_packed.decode


# Conversion utilities
def hex_to_str(hex_str):
    """Decode a hex string prefixed with "0x" into a UTF-8 string"""
    return bytes.fromhex(hex_str[2:]).decode("utf-8")


def str_to_hex(string):
    """Encode a string as a hex string, adding the "0x" prefix"""
    return "0x" + string.encode("utf-8").hex()


def str_to_int(string):
    """Converts a string to an integer. Returns 0 if conversion is not possible."""
    try:
        return int(string)
    except (TypeError, ValueError):
        return 0


def int_to_str(integer):
    """Converts an integer to a string. Returns '0' if the input is None or not an integer."""
    try:
        return str(int(integer))
    except (TypeError, ValueError):
        return "0"


# Decorators
def with_checksum_address(func):
    def wrapper(*args, **kwargs):
        new_args = tuple(
            to_checksum_address(arg) if is_hex_address(arg) else arg for arg in args
        )
        new_kwargs = {
            key: to_checksum_address(value) if is_hex_address(value) else value
            for key, value in kwargs.items()
        }
        return func(*new_args, **new_kwargs)

    return wrapper


def process_streams_before(func):
    def wrapper(self, *args, **kwargs):
        if not "current_timestamp" in kwargs or not "sender" in kwargs:
            raise ValueError("current_timestamp and sender must be provided.")
        current_timestamp = kwargs["current_timestamp"]
        sender = kwargs["sender"]

        self.process_streams(sender, current_timestamp)

        return func(self, *args, **kwargs)

    return wrapper


def apply(decorator):
    def class_decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value):
                setattr(cls, attr_name, decorator(attr_value))
        return cls

    return class_decorator


# Logging Configuration
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "message": record.msg,
            "level": record.levelname,
            "timestamp": record.created,
        }
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        return json.dumps(log_entry)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Main code or configuration
rollup_server = environ.get("ROLLUP_HTTP_SERVER_URL", "http://127.0.0.1:5004")


# Utilities
def address_or_raise(address):
    if not is_checksum_address(address):
        raise ValueError(f"Invalid address {address}")
    return address


# Amm
def addresses_to_hex(address1, address2):
    address1, address2 = to_checksum_address(address1), to_checksum_address(address2)
    concatenated_addresses = address1 + address2
    sha256_hash = hashlib.sha256(concatenated_addresses.encode()).digest()
    ethereum_address = "0x" + sha256_hash[-20:].hex()
    return ethereum_address


def sort_tokens(token0: str, token1: str):
    token0, token1 = to_checksum_address(token0), to_checksum_address(token1)
    return (token0, token1) if token0 < token1 else (token1, token0)


def get_pair_address(token0, token1):
    token0, token1 = to_checksum_address(token0), to_checksum_address(token1)
    sorted_tokens = sort_tokens(token0, token1)
    return to_checksum_address(addresses_to_hex(sorted_tokens[0], sorted_tokens[1]))


def quote(amount_a: int, reserve_a: int, reserve_b: int):
    assert amount_a > 0, "AmmLibrary: INSUFFICIENT_AMOUNT"
    assert reserve_a > 0 and reserve_b > 0, "AmmLibrary: INSUFFICIENT_LIQUIDITY"

    return int((amount_a * reserve_b) // reserve_a)


def get_amount_out(amount_in, reserve_in, reserve_out):
    if amount_in <= 0:
        raise ValueError("AMM: INSUFFICIENT_INPUT_AMOUNT")
    if reserve_in <= 0 or reserve_out <= 0:
        raise ValueError("AMM: INSUFFICIENT_LIQUIDITY")

    amount_in_with_fee = amount_in * (1000 - USER_FEES)
    numerator = amount_in_with_fee * reserve_out
    denominator = reserve_in * 1000 + amount_in_with_fee
    amount_out = numerator // denominator

    return int(amount_out)
