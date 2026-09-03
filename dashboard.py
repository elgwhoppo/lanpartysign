import argparse
import json
import os
import signal
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from env_config import load_env_file
from latency import (
    PING_HISTORY_SECONDS,
    PING_STAGGER_SECONDS,
    PING_TARGET_INTERVAL_SECONDS,
    cycle_targets,
    default_ping_targets,
    ping_target,
)
from metrics_store import MetricsStore, RETENTION_SECONDS
from unifi import UniFiDashboardWebSocketProvider
from wan_metrics import WANMetrics


DEFAULT_BIND = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_DB_PATH = "wan_metrics.sqlite3"
DEFAULT_DEMO_DB_PATH = ":memory:"
WINDOWS = [
    ("5m", "5 min", 5 * 60),
    ("15m", "15 min", 15 * 60),
    ("1h", "1 hour", 60 * 60),
    ("6h", "6 hours", 6 * 60 * 60),
    ("24h", "24 hours", 24 * 60 * 60),
    ("72h", "72 hours", 72 * 60 * 60),
]


class CollectorStatus:
    def __init__(self):
        self._lock = threading.Lock()
        self.connected = False
        self.last_error = None
        self.last_update = None

    def mark_update(self):
        with self._lock:
            self.connected = True
            self.last_error = None
            self.last_update = time.time()

    def mark_error(self, error: Exception):
        with self._lock:
            self.connected = False
            self.last_error = str(error)

    def as_dict(self) -> Dict[str, Optional[object]]:
        with self._lock:
            return {
                "connected": self.connected,
                "last_error": self.last_error,
                "last_update": self.last_update,
            }


def main():
    root_dir = Path(__file__).resolve().parent
    load_env_file(root_dir / ".env")
    args = _parse_args()
    if args.demo and not args.db_explicit:
        args.db = DEFAULT_DEMO_DB_PATH
    store = MetricsStore(args.db)
    collector_status = CollectorStatus()
    ping_targets = default_ping_targets()
    stop_event = threading.Event()

    if args.demo:
        mode = "demo"
        _start_demo_collector(store, collector_status, stop_event)
    elif not args.no_collector:
        mode = "unifi"
        _start_unifi_collector(store, collector_status, stop_event)
    else:
        mode = "static"

    if not args.no_collector:
        _start_ping_collector(store, ping_targets, stop_event)

    server = ThreadingHTTPServer(
        (args.bind, args.port),
        _make_handler(root_dir / "web", store, collector_status, mode, ping_targets),
    )

    def stop_server(signum, frame):
        stop_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)

    print(f"LAN Party Sign dashboard serving http://{args.bind}:{args.port}")
    print(f"Collector mode: {mode}")
    if args.db == ":memory:":
        print("Recording metrics to an in-memory demo database.")
    else:
        print(f"Recording metrics to {Path(args.db).resolve()}")

    try:
        server.serve_forever()
    finally:
        stop_event.set()
        store.close()


def _start_unifi_collector(store: MetricsStore, status: CollectorStatus, stop_event: threading.Event):
    def run():
        while not stop_event.is_set():
            try:
                provider = UniFiDashboardWebSocketProvider.from_env()
                for metrics in provider.stream_metrics():
                    if stop_event.is_set():
                        return
                    store.record_metrics(metrics)
                    status.mark_update()
            except Exception as exc:
                status.mark_error(exc)
                print(f"[ERROR] Dashboard collector is waiting for UniFi data: {exc}")
                stop_event.wait(5)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _start_ping_collector(store: MetricsStore, targets, stop_event: threading.Event):
    def run():
        for target in cycle_targets(targets):
            if stop_event.is_set():
                return
            result = ping_target(target)
            store.record_ping(
                result.target_key,
                result.target_label,
                result.address,
                result.latency_ms,
                result.success,
            )
            stop_event.wait(PING_STAGGER_SECONDS)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _start_demo_collector(store: MetricsStore, status: CollectorStatus, stop_event: threading.Event):
    def run():
        import math
        import random

        while not stop_event.is_set():
            now = time.time()
            wave = (math.sin(now / 41) + 1) / 2
            burst = random.uniform(0, 95) if random.random() < 0.08 else 0
            download = round(35 + wave * 160 + burst, 2)
            upload = round(2 + random.uniform(0, 8), 2)
            metrics = WANMetrics(
                isp="Demo ISP",
                interface="eth8",
                status="up",
                download_mbps=download,
                upload_mbps=upload,
                total_mbps=round(download + upload, 2),
                microsoft_latency_ms=None,
                google_latency_ms=None,
                cloudflare_latency_ms=None,
                provisioned_download_kbps=892000,
                provisioned_upload_kbps=37000,
                max_download_mbps=None,
                max_upload_mbps=None,
                raw_monthly_bytes=None,
            )
            store.record_metrics(metrics, timestamp=now)
            status.mark_update()
            stop_event.wait(1)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _make_handler(static_dir: Path, store: MetricsStore, collector_status: CollectorStatus, mode: str, ping_targets):
    class DashboardRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static_dir), **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/summary":
                self._send_json(_summary_response(store, collector_status, mode, ping_targets))
                return
            if parsed.path == "/api/timeseries":
                query = parse_qs(parsed.query)
                self._send_json(_timeseries_response(store, query))
                return
            if parsed.path == "/api/health":
                self._send_json({"ok": True, "mode": mode, "collector": collector_status.as_dict()})
                return
            if parsed.path == "/":
                self.path = "/index.html"
            return super().do_GET()

        def log_message(self, format, *args):
            return

        def end_headers(self):
            if not getattr(self, "_cache_control_sent", False):
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _send_json(self, payload, status=200):
            encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self._cache_control_sent = True
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return DashboardRequestHandler


def _summary_response(store: MetricsStore, collector_status: CollectorStatus, mode: str, ping_targets):
    now = time.time()
    store.prune_if_needed(now)
    latest = store.latest()
    pings = store.pings_summary(ping_targets, PING_HISTORY_SECONDS, now=now)
    pings["now"] = now
    pings["stagger_seconds"] = PING_STAGGER_SECONDS
    pings["target_interval_seconds"] = PING_TARGET_INTERVAL_SECONDS
    return {
        "now": now,
        "mode": mode,
        "retention_seconds": store.retention_seconds,
        "sample_count": store.sample_count(),
        "collector": collector_status.as_dict(),
        "current": latest,
        "pings": pings,
        "windows": [
            {
                "key": key,
                "label": label,
                "pings": store.summarize_pings_window(seconds, ping_targets, now=now),
                **store.summarize_window(seconds, now=now),
            }
            for key, label, seconds in WINDOWS
        ],
    }


def _timeseries_response(store: MetricsStore, query):
    window_key = (query.get("window") or ["72h"])[0]
    seconds = _window_seconds(window_key)
    bucket_seconds = _bucket_seconds(seconds, (query.get("bucket") or ["auto"])[0])
    now = time.time()
    return {
        "now": now,
        "window": window_key,
        "seconds": seconds,
        "bucket_seconds": bucket_seconds,
        "points": store.timeseries(seconds, bucket_seconds, now=now),
    }


def _window_seconds(key: str) -> int:
    if key == "1m":
        return 60
    for window_key, label, seconds in WINDOWS:
        if key == window_key:
            return seconds
    return RETENTION_SECONDS


def _bucket_seconds(window_seconds: int, requested: str) -> int:
    if requested != "auto":
        try:
            return max(1, int(requested))
        except ValueError:
            pass
    return max(5, int(window_seconds / 240))


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the local LAN Party Sign metrics dashboard.")
    parser.add_argument("--bind", default=os.environ.get("DASHBOARD_BIND", DEFAULT_BIND))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DASHBOARD_PORT", DEFAULT_PORT)))
    db_default = os.environ.get("DASHBOARD_DB", DEFAULT_DB_PATH)
    parser.add_argument("--db", default=db_default)
    parser.add_argument("--no-collector", action="store_true", help="Serve the UI without collecting new metrics.")
    parser.add_argument("--demo", action="store_true", help="Record synthetic metrics for local UI testing.")
    args = parser.parse_args()
    args.db_explicit = "--db" in sys.argv or bool(os.environ.get("DASHBOARD_DB"))
    return args


if __name__ == "__main__":
    main()
