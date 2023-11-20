import json
import logging
from os import environ

# External libraries
from eth_abi.codec import ABICodec
from eth_abi.decoding import AddressDecoder, BooleanDecoder, UnsignedIntegerDecoder
from eth_abi.registry import BaseEquals, registry_packed
from eth_utils import is_hex_address, to_checksum_address, is_checksum_address

# Constants
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


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
        if "current_block" in kwargs and "sender" in kwargs:
            current_block = kwargs["current_block"]
            sender = kwargs["sender"]
        else:
            current_block = args[-1]
            sender = args[-2]

        self.process_streams(sender, current_block)

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
