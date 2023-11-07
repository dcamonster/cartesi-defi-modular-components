import json
import logging
from os import environ
from eth_utils import to_checksum_address, is_hex_address
import requests

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def hex_to_str(hex):
    """Decode a hex string prefixed with "0x" into a UTF-8 string"""
    return bytes.fromhex(hex[2:]).decode("utf-8")


def str_to_hex(str):
    """Encode a string as a hex string, adding the "0x" prefix"""
    return "0x" + str.encode("utf-8").hex()


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

rollup_server = environ.get("ROLLUP_HTTP_SERVER_URL", "http://127.0.0.1:5004")


def str_to_int(string):
    """Converts a string to an integer. Returns 0 if conversion is not possible."""
    try:
        return int(float(string))
    except (TypeError, ValueError):
        return 0


def int_to_str(integer):
    """Converts an integer to a string. Returns '0' if the input is None or not an integer."""
    try:
        return str(int(integer))
    except (TypeError, ValueError):
        return "0"


def with_checksum_address(func):
    def wrapper(*args, **kwargs):
        args = tuple(
            to_checksum_address(arg) if is_hex_address(arg) else arg for arg in args
        )
        return func(*args, **kwargs)

    return wrapper


def apply_decorator_to_all_methods(decorator):
    def class_decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value):
                setattr(cls, attr_name, decorator(attr_value))
        return cls

    return class_decorator


class NoticeBuffer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NoticeBuffer, cls).__new__(cls)
            cls._instance._notices = []
        return cls._instance

    def add(self, notice_str):
        """Adds a notice to the buffer."""
        self._notices.append(notice_str)

    def send_all(self):
        """Sends all buffered notices."""
        for notice in self._notices:
            self._send_single_notice(notice)
        # Clear the buffer after sending
        self._notices = []

    def send_all_grouped(self, batch_size=1000):
        """Sends all buffered notices in batches of a specified size."""

        for i in range(0, len(self._notices), batch_size):
            batch = self._notices[i : i + batch_size]
            grouped_notices = json.dumps(batch)
            logger.info(f"Sending grouped notices: {grouped_notices}")
            notice = {"payload": self._str2hex(grouped_notices)}
            response = requests.post(rollup_server + "/notice", json=notice)
            logger.info(
                f"Received notice status {response.status_code} body {response.content}"
            )

        # Clear the buffer after sending
        self._notices = []

    def clear(self):
        """Clears all buffered notices without sending them."""
        self._notices = []

    def _send_single_notice(self, notice_str):
        """Internal method to send a single notice."""
        logger.info(f"Sending buffered notice: {notice_str}")
        notice = {"payload": self._str2hex(notice_str)}
        response = requests.post(rollup_server + "/notice", json=notice)
        logger.info(
            f"Received notice status {response.status_code} body {response.content}"
        )

    @staticmethod
    def _str2hex(str):
        """Encodes a string as a hex string."""
        return "0x" + str.encode("utf-8").hex()


class ReportBuffer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ReportBuffer, cls).__new__(cls)
            cls._instance._reports = []
        return cls._instance

    def add(self, report_str):
        """Adds a report to the buffer."""
        self._reports.append(report_str)

    def send_all(self):
        """Sends all buffered reports."""
        for report in self._reports:
            self._send_single_report(report)
        # Clear the buffer after sending
        self._reports = []

    def send_all_grouped(self, batch_size=1000):
        """Sends all buffered reports in batches of a specified size."""

        for i in range(0, len(self._reports), batch_size):
            batch = self._reports[i : i + batch_size]
            grouped_reports = json.dumps(batch)
            logger.info(f"Sending grouped reports: {grouped_reports}")
            report = {"payload": self._str2hex(grouped_reports)}
            response = requests.post(rollup_server + "/report", json=report)
            logger.info(
                f"Received report status {response.status_code} body {response.content}"
            )

        # Clear the buffer after sending
        self._reports = []

    def clear(self):
        """Clears all buffered reports without sending them."""
        self._reports = []

    def _send_single_report(self, report_str):
        """Internal method to send a single report."""
        logger.info(f"Sending buffered report: {report_str}")
        report = {"payload": self._str2hex(report_str)}
        response = requests.post(rollup_server + "/report", json=report)
        logger.info(
            f"Received report status {response.status_code} body {response.content}"
        )

    @staticmethod
    def _str2hex(str):
        """Encodes a string as a hex string."""
        return "0x" + str.encode("utf-8").hex()
