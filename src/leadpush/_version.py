from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

SDK_NAME = "leadpush"
API_VERSION = "v1"
DEFAULT_BASE_URL = f"https://api.leadpush.io/{API_VERSION}"
DEFAULT_TIMEOUT = 30.0

try:
    SDK_VERSION = version(SDK_NAME)
except PackageNotFoundError:
    SDK_VERSION = "dev-main"

DEFAULT_USER_AGENT = f"{SDK_NAME}/{SDK_VERSION} (api={API_VERSION})"
