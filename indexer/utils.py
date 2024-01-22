import hashlib

from eth_utils import is_hex_address, to_checksum_address

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


def addresses_to_hex(address1, address2):
    address1, address2 = to_checksum_address(address1), to_checksum_address(address2)
    concatenated_addresses = address1 + address2
    sha256_hash = hashlib.sha256(concatenated_addresses.encode()).digest()
    ethereum_address = "0x" + sha256_hash[-20:].hex()
    return ethereum_address


def sort_tokens(token0, token1):
    token0, token1 = to_checksum_address(token0), to_checksum_address(token1)
    return (token0, token1) if token0 < token1 else (token1, token0)


def get_pair_address(token0, token1):
    token0, token1 = to_checksum_address(token0), to_checksum_address(token1)
    sorted_tokens = sort_tokens(token0, token1)
    return to_checksum_address(addresses_to_hex(sorted_tokens[0], sorted_tokens[1]))
