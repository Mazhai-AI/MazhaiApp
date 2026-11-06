"""Optional background keep-alive pinger, independent of request handling."""

import logging
import os
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

log = logging.getLogger("mazhai.keep_alive")
INTERVAL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 10


def start_keep_alive():
    """Start a daemon pinger only when KEEP_ALIVE_URL is configured."""
    url = os.getenv("KEEP_ALIVE_URL", "").strip()
    if not url:
        log.info("Keep-alive monitor disabled: KEEP_ALIVE_URL is not configured")
        return None

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        log.warning("Keep-alive monitor disabled: KEEP_ALIVE_URL must be an HTTP(S) URL")
        return None

    stop_event = threading.Event()

    def ping():
        while not stop_event.wait(INTERVAL_SECONDS):
            request = Request(url, headers={"User-Agent": "MazhaiApp-KeepAlive/1.0"})
            try:
                with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    log.info("Keep-alive ping completed: HTTP %s", response.status)
            except HTTPError as exc:
                # An HTTP response (including 4xx/5xx) still confirms the host responded.
                log.warning("Keep-alive target responded with HTTP %s", exc.code)
            except (URLError, TimeoutError, OSError) as exc:
                log.warning("Keep-alive ping failed: %s", exc)

    thread = threading.Thread(target=ping, name="mazhai-keep-alive", daemon=True)
    thread.start()
    log.info(
        "Keep-alive monitor started (interval=%ss, timeout=%ss)",
        INTERVAL_SECONDS,
        REQUEST_TIMEOUT_SECONDS,
    )
    return stop_event
