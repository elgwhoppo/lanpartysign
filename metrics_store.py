import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

from wan_metrics import WANMetrics


RETENTION_SECONDS = 72 * 60 * 60


class MetricsStore:
    def __init__(self, path: str, retention_seconds: int = RETENTION_SECONDS):
        self.path = path
        self.retention_seconds = retention_seconds
        self._lock = threading.Lock()
        self._last_prune = 0.0
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._initialize()

    def close(self):
        with self._lock:
            self._conn.close()

    def record_metrics(self, metrics: WANMetrics, timestamp: Optional[float] = None):
        timestamp = timestamp or time.time()
        values = metrics.as_dict()
        values["timestamp"] = timestamp

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO wan_metrics (
                    timestamp, isp, interface, status,
                    download_mbps, upload_mbps, total_mbps,
                    microsoft_latency_ms, google_latency_ms, cloudflare_latency_ms,
                    provisioned_download_kbps, provisioned_upload_kbps,
                    max_download_mbps, max_upload_mbps, raw_monthly_bytes
                ) VALUES (
                    :timestamp, :isp, :interface, :status,
                    :download_mbps, :upload_mbps, :total_mbps,
                    :microsoft_latency_ms, :google_latency_ms, :cloudflare_latency_ms,
                    :provisioned_download_kbps, :provisioned_upload_kbps,
                    :max_download_mbps, :max_upload_mbps, :raw_monthly_bytes
                )
                """,
                values,
            )
            if timestamp - self._last_prune >= 60:
                self._prune_locked(timestamp)
            self._conn.commit()

    def record_ping(
        self,
        target_key: str,
        target_label: str,
        address: str,
        latency_ms: Optional[float],
        success: bool,
        timestamp: Optional[float] = None,
    ):
        timestamp = timestamp or time.time()

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ping_metrics (
                    timestamp, target_key, target_label, address, latency_ms, success
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (timestamp, target_key, target_label, address, latency_ms, int(success)),
            )
            if timestamp - self._last_prune >= 60:
                self._prune_locked(timestamp)
            self._conn.commit()

    def latest(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM wan_metrics ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            return _row_to_dict(row)

    def sample_count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS count FROM wan_metrics").fetchone()
            return int(row["count"])

    def summarize_window(self, seconds: int, now: Optional[float] = None) -> Dict[str, Any]:
        now = now or time.time()
        start = now - seconds

        with self._lock:
            row = self._conn.execute(
                """
                SELECT
                    COUNT(*) AS sample_count,
                    AVG(download_mbps) AS avg_download_mbps,
                    AVG(upload_mbps) AS avg_upload_mbps,
                    AVG(total_mbps) AS avg_total_mbps,
                    MAX(download_mbps) AS peak_download_mbps,
                    MAX(upload_mbps) AS peak_upload_mbps,
                    MAX(total_mbps) AS peak_total_mbps,
                    AVG(microsoft_latency_ms) AS avg_microsoft_latency_ms,
                    AVG(google_latency_ms) AS avg_google_latency_ms,
                    AVG(cloudflare_latency_ms) AS avg_cloudflare_latency_ms,
                    MAX(microsoft_latency_ms) AS peak_microsoft_latency_ms,
                    MAX(google_latency_ms) AS peak_google_latency_ms,
                    MAX(cloudflare_latency_ms) AS peak_cloudflare_latency_ms
                FROM wan_metrics
                WHERE timestamp >= ?
                """,
                (start,),
            ).fetchone()

        return {
            "seconds": seconds,
            "sample_count": int(row["sample_count"]),
            "average": {
                "download_mbps": _round(row["avg_download_mbps"]),
                "upload_mbps": _round(row["avg_upload_mbps"]),
                "total_mbps": _round(row["avg_total_mbps"]),
                "microsoft_latency_ms": _round(row["avg_microsoft_latency_ms"], 0),
                "google_latency_ms": _round(row["avg_google_latency_ms"], 0),
                "cloudflare_latency_ms": _round(row["avg_cloudflare_latency_ms"], 0),
            },
            "peak": {
                "download_mbps": _round(row["peak_download_mbps"]),
                "upload_mbps": _round(row["peak_upload_mbps"]),
                "total_mbps": _round(row["peak_total_mbps"]),
                "microsoft_latency_ms": _round(row["peak_microsoft_latency_ms"], 0),
                "google_latency_ms": _round(row["peak_google_latency_ms"], 0),
                "cloudflare_latency_ms": _round(row["peak_cloudflare_latency_ms"], 0),
            },
        }

    def summarize_pings_window(self, seconds: int, targets, now: Optional[float] = None) -> Dict[str, Any]:
        now = now or time.time()
        start = now - seconds
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT
                    target_key,
                    COUNT(*) AS sample_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS failure_count,
                    AVG(latency_ms) AS avg_latency_ms,
                    MAX(latency_ms) AS peak_latency_ms
                FROM ping_metrics
                WHERE timestamp >= ?
                GROUP BY target_key
                """,
                (start,),
            ).fetchall()

        by_key = {
            row["target_key"]: {
                "sample_count": int(row["sample_count"]),
                "failure_count": int(row["failure_count"]),
                "average_latency_ms": _round(row["avg_latency_ms"], 0),
                "peak_latency_ms": _round(row["peak_latency_ms"], 0),
            }
            for row in rows
        }
        target_summaries = []
        worst_latency = None
        for target in targets:
            summary = by_key.get(target.key, {
                "sample_count": 0,
                "failure_count": 0,
                "average_latency_ms": None,
                "peak_latency_ms": None,
            })
            if summary["peak_latency_ms"] is not None:
                worst_latency = max(worst_latency or 0, summary["peak_latency_ms"])
            target_summaries.append({**target.as_dict(), **summary})

        return {
            "targets": target_summaries,
            "worst_latency_ms": worst_latency,
        }

    def pings_summary(self, targets, history_seconds: int, now: Optional[float] = None) -> Dict[str, Any]:
        now = now or time.time()
        start = now - history_seconds
        with self._lock:
            latest_rows = {
                target.key: _row_to_dict(
                    self._conn.execute(
                        """
                        SELECT * FROM ping_metrics
                        WHERE target_key = ?
                        ORDER BY timestamp DESC
                        LIMIT 1
                        """,
                        (target.key,),
                    ).fetchone()
                )
                for target in targets
            }
            recent_rows = self._conn.execute(
                """
                SELECT * FROM ping_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (start,),
            ).fetchall()

        target_payloads = []
        for target in targets:
            target_payloads.append({
                **target.as_dict(),
                "latest": _normalize_ping_row(latest_rows.get(target.key)),
            })

        return {
            "history_seconds": history_seconds,
            "targets": target_payloads,
            "recent": [_normalize_ping_row(row) for row in recent_rows],
        }

    def timeseries(self, seconds: int, bucket_seconds: int, now: Optional[float] = None) -> List[Dict[str, Any]]:
        now = now or time.time()
        start = now - seconds

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT
                    CAST(timestamp / ? AS INTEGER) * ? AS bucket_start,
                    AVG(download_mbps) AS avg_download_mbps,
                    AVG(upload_mbps) AS avg_upload_mbps,
                    AVG(total_mbps) AS avg_total_mbps,
                    MAX(download_mbps) AS peak_download_mbps,
                    MAX(upload_mbps) AS peak_upload_mbps,
                    MAX(total_mbps) AS peak_total_mbps,
                    AVG(microsoft_latency_ms) AS avg_microsoft_latency_ms,
                    AVG(google_latency_ms) AS avg_google_latency_ms,
                    AVG(cloudflare_latency_ms) AS avg_cloudflare_latency_ms,
                    COUNT(*) AS sample_count
                FROM wan_metrics
                WHERE timestamp >= ?
                GROUP BY bucket_start
                ORDER BY bucket_start
                """,
                (bucket_seconds, bucket_seconds, start),
            ).fetchall()

        return [
            {
                "timestamp": int(row["bucket_start"]),
                "sample_count": int(row["sample_count"]),
                "average": {
                    "download_mbps": _round(row["avg_download_mbps"]),
                    "upload_mbps": _round(row["avg_upload_mbps"]),
                    "total_mbps": _round(row["avg_total_mbps"]),
                    "microsoft_latency_ms": _round(row["avg_microsoft_latency_ms"], 0),
                    "google_latency_ms": _round(row["avg_google_latency_ms"], 0),
                    "cloudflare_latency_ms": _round(row["avg_cloudflare_latency_ms"], 0),
                },
                "peak": {
                    "download_mbps": _round(row["peak_download_mbps"]),
                    "upload_mbps": _round(row["peak_upload_mbps"]),
                    "total_mbps": _round(row["peak_total_mbps"]),
                },
            }
            for row in rows
        ]

    def prune(self, now: Optional[float] = None):
        now = now or time.time()
        with self._lock:
            self._prune_locked(now)
            self._conn.commit()

    def prune_if_needed(self, now: Optional[float] = None):
        now = now or time.time()
        with self._lock:
            if now - self._last_prune >= 60:
                self._prune_locked(now)
                self._conn.commit()

    def _initialize(self):
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wan_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    isp TEXT,
                    interface TEXT,
                    status TEXT,
                    download_mbps REAL NOT NULL,
                    upload_mbps REAL NOT NULL,
                    total_mbps REAL NOT NULL,
                    microsoft_latency_ms INTEGER,
                    google_latency_ms INTEGER,
                    cloudflare_latency_ms INTEGER,
                    provisioned_download_kbps INTEGER,
                    provisioned_upload_kbps INTEGER,
                    max_download_mbps REAL,
                    max_upload_mbps REAL,
                    raw_monthly_bytes INTEGER
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_wan_metrics_timestamp ON wan_metrics(timestamp)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ping_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    target_key TEXT NOT NULL,
                    target_label TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latency_ms REAL,
                    success INTEGER NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ping_metrics_timestamp ON ping_metrics(timestamp)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ping_metrics_target_timestamp ON ping_metrics(target_key, timestamp)"
            )
            self._conn.commit()

    def _prune_locked(self, now: float):
        cutoff = now - self.retention_seconds
        self._conn.execute("DELETE FROM wan_metrics WHERE timestamp < ?", (cutoff,))
        self._conn.execute("DELETE FROM ping_metrics WHERE timestamp < ?", (cutoff,))
        self._last_prune = now


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def _normalize_ping_row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    item = dict(row)
    item["success"] = bool(item["success"])
    return item


def _round(value: Any, digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)
