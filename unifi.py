import json
import os
import ssl
import time
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

from multiprocessing.connection import Connection

from env_config import load_env_file
from wan_metrics import (
    ERROR_RESPONSE,
    WANMetrics,
    WANMetricsProvider,
    extract_primary_wan_metrics,
    format_mbps_for_display,
)


DEFAULT_HOST = "192.168.1.1"
DEFAULT_SITE = "default"
DEFAULT_USERNAME = "dashboard-api"
DEFAULT_DISPLAY_METRIC = "total"
RECONNECT_MIN_SECONDS = 2
RECONNECT_MAX_SECONDS = 60

DASHBOARD_SUBSCRIPTION = {
    "type": "subscribe",
    "subscription": "dashboard",
    "enabled": True,
    "meta": {
        "history_seconds": 86400,
        "widget_params": {
            "radio_activity": {},
        },
    },
}


class AuthenticationExpired(Exception):
    pass


class UniFiDashboardWebSocketProvider(WANMetricsProvider):
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        site: str = DEFAULT_SITE,
        verify_ssl: bool = False,
    ):
        self.host = _normalize_host(host)
        self.username = username
        self.password = password
        self.site = site
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{self.host}"
        self.login_url = f"{self.base_url}/api/auth/login"
        self.websocket_url = (
            f"wss://{self.host}/proxy/network/wss/s/{self.site}/events"
            "?clients=v2&next_ai_notifications=true"
        )
        self._session = None
        self._token = None

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None):
        load_env_file(env_path or Path(__file__).resolve().parent / ".env")
        password = os.environ.get("UNIFI_PASSWORD")
        if not password:
            raise ValueError("Set UNIFI_PASSWORD in .env for UniFi login.")

        return cls(
            host=os.environ.get("UNIFI_HOST", DEFAULT_HOST),
            username=os.environ.get("UNIFI_USERNAME", DEFAULT_USERNAME),
            password=password,
            site=os.environ.get("UNIFI_SITE", DEFAULT_SITE),
            verify_ssl=_env_truthy(os.environ.get("UNIFI_VERIFY_SSL")),
        )

    def authenticate(self):
        requests = _load_requests()
        if not self.verify_ssl:
            requests.packages.urllib3.disable_warnings()

        self._session = requests.Session()
        response = self._session.post(
            self.login_url,
            json={
                "username": self.username,
                "password": self.password,
                "remember": True,
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
            verify=self.verify_ssl,
        )
        response.raise_for_status()

        token = self._session.cookies.get("TOKEN")
        if not token:
            raise RuntimeError("UniFi login succeeded but did not return a TOKEN cookie.")
        self._token = token

    def stream_metrics(self) -> Iterable[WANMetrics]:
        backoff_seconds = RECONNECT_MIN_SECONDS

        while True:
            try:
                if not self._token:
                    self.authenticate()

                for metrics in self._stream_once():
                    backoff_seconds = RECONNECT_MIN_SECONDS
                    yield metrics

            except AuthenticationExpired:
                print("[WARN] UniFi session expired; re-authenticating before reconnect.")
                self._token = None
            except Exception as exc:
                print(f"[ERROR] UniFi dashboard WebSocket error: {exc}")

            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, RECONNECT_MAX_SECONDS)

    def _stream_once(self) -> Iterable[WANMetrics]:
        websocket = _load_websocket()
        sslopt = {}
        if not self.verify_ssl:
            sslopt = {"cert_reqs": ssl.CERT_NONE}

        try:
            ws = websocket.create_connection(
                self.websocket_url,
                cookie=f"TOKEN={self._token}",
                origin=self.base_url,
                sslopt=sslopt,
                timeout=30,
            )
        except Exception as exc:
            if _is_auth_failure(exc):
                self._token = None
                raise AuthenticationExpired() from exc
            raise

        try:
            ws.send(json.dumps(DASHBOARD_SUBSCRIPTION, separators=(",", ":")))

            while True:
                try:
                    raw_message = ws.recv()
                except Exception as exc:
                    if _is_auth_failure(exc):
                        self._token = None
                        raise AuthenticationExpired() from exc
                    raise

                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode("utf-8")
                if "dashboard:sync" not in raw_message:
                    continue

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError as exc:
                    print(f"[WARN] Ignoring invalid UniFi WebSocket JSON frame: {exc}")
                    continue

                metrics = extract_primary_wan_metrics(message)
                if metrics:
                    yield metrics
        finally:
            ws.close()


def unifi_child(pipe_conn: Optional[Connection] = None):
    try:
        provider = UniFiDashboardWebSocketProvider.from_env()
    except Exception as exc:
        _publish_error_forever(pipe_conn, exc)
        return

    display_metric = os.environ.get("UNIFI_DISPLAY_METRIC", DEFAULT_DISPLAY_METRIC).lower()
    counter = 0

    for metrics in provider.stream_metrics():
        selected_mbps = _select_display_metric(metrics, display_metric)
        formatted_value = format_mbps_for_display(selected_mbps)
        payload = {
            "data": formatted_value,
            "metrics": metrics.as_dict(),
        }

        if pipe_conn:
            pipe_conn.send(payload)
        else:
            print(payload)

        counter += 1
        if counter % 50 == 0:
            print(
                "[MAIN THREAD] 50 UniFi dashboard updates have passed. "
                f"Current output of unifi.py to sign.py: {formatted_value}"
            )


def _select_display_metric(metrics: WANMetrics, display_metric: str) -> float:
    if display_metric == "download":
        return metrics.download_mbps
    if display_metric == "upload":
        return metrics.upload_mbps
    return metrics.total_mbps


def _publish_error_forever(pipe_conn: Optional[Connection], error: Exception):
    print(f"[ERROR] UniFi collector is not configured: {error}")
    payload = {
        "data": ERROR_RESPONSE,
        "error": str(error),
    }
    while True:
        if pipe_conn:
            pipe_conn.send(payload)
        else:
            print(payload)
        time.sleep(5)


def _normalize_host(host: str) -> str:
    parsed = urlparse(host)
    if parsed.netloc:
        return parsed.netloc
    return host.rstrip("/")


def _env_truthy(value: Optional[str]) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_requests():
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests with: pip3 install requests") from exc
    return requests


def _load_websocket():
    try:
        import websocket
    except ImportError as exc:
        raise RuntimeError("Install websocket-client with: pip3 install websocket-client") from exc
    return websocket


def _is_auth_failure(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    return status_code in {401, 403}


if __name__ == "__main__":
    unifi_child()
