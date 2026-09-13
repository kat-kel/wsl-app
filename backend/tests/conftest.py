import os

# Set before any test module imports app.main, which builds settings at import time.
# Two keys so the rotation path (old and new valid at once) is covered.
TEST_WRITE_API_KEY = "test-write-api-key-0123456789abcdef"
TEST_ROTATED_API_KEY = "test-rotated-api-key-0123456789abcdef"
os.environ.setdefault("WRITE_API_KEYS", f"{TEST_WRITE_API_KEY},{TEST_ROTATED_API_KEY}")

import pytest

from app.api.security import API_KEY_HEADER_NAME


@pytest.fixture()
def write_headers() -> dict[str, str]:
    return {API_KEY_HEADER_NAME: TEST_WRITE_API_KEY}


@pytest.fixture()
def all_write_api_keys() -> list[str]:
    return [TEST_WRITE_API_KEY, TEST_ROTATED_API_KEY]
