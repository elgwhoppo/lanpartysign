from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional


ERROR_RESPONSE = "UHH"


@dataclass(frozen=True)
class WANMetrics:
    isp: Optional[str]
    interface: Optional[str]
    status: Optional[str]
    download_mbps: float
    upload_mbps: float
    total_mbps: float
    microsoft_latency_ms: Optional[int]
    google_latency_ms: Optional[int]
    cloudflare_latency_ms: Optional[int]
    provisioned_download_kbps: Optional[int]
    provisioned_upload_kbps: Optional[int]
    max_download_mbps: Optional[float]
    max_upload_mbps: Optional[float]
    raw_monthly_bytes: Optional[int]

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WANMetricsProvider:
    def stream_metrics(self) -> Iterable[WANMetrics]:
        raise NotImplementedError


def bytes_per_second_to_mbps(value: Any) -> float:
    return round((float(value or 0) * 8) / 1000000, 2)


def format_mbps_for_display(value: Optional[float]) -> str:
    """Format Mbps to the compact 7-segment bandwidth field."""
    if value is None:
        return ERROR_RESPONSE

    try:
        mbps = float(value)
    except (TypeError, ValueError):
        return ERROR_RESPONSE

    if mbps < 0:
        return ERROR_RESPONSE
    if mbps >= 1000:
        gbps = min(mbps / 1000, 9.9)
        return f"{gbps:.1f}G"
    if mbps >= 100:
        return str(min(int(round(mbps)), 999))
    if mbps >= 10:
        return f"{mbps:.1f}"
    return f"{mbps:.2f}"


def extract_primary_wan_metrics(message: Dict[str, Any]) -> Optional[WANMetrics]:
    if (message.get("meta") or {}).get("message") != "dashboard:sync":
        return None

    wan_details = list(_iter_wan_details(message))
    if not wan_details:
        return None

    detail = _choose_primary_wan(wan_details)
    return normalize_unifi_wan_detail(detail)


def normalize_unifi_wan_detail(detail: Dict[str, Any]) -> WANMetrics:
    isp = detail.get("isp") or {}
    capabilities = isp.get("capabilities") or {}
    status = detail.get("status") or {}
    stats = detail.get("stats") or {}
    activity = stats.get("activity") or {}

    download_mbps = bytes_per_second_to_mbps(activity.get("rx_bytes-r"))
    upload_mbps = bytes_per_second_to_mbps(activity.get("tx_bytes-r"))
    total_mbps = round(download_mbps + upload_mbps, 2)

    return WANMetrics(
        isp=isp.get("name"),
        interface=status.get("interface_name"),
        status=status.get("state"),
        download_mbps=download_mbps,
        upload_mbps=upload_mbps,
        total_mbps=total_mbps,
        microsoft_latency_ms=None,
        google_latency_ms=None,
        cloudflare_latency_ms=None,
        provisioned_download_kbps=_to_int(capabilities.get("download_kilobits_per_second")),
        provisioned_upload_kbps=_to_int(capabilities.get("upload_kilobits_per_second")),
        max_download_mbps=bytes_per_second_to_mbps(activity.get("max_rx_bytes-r"))
        if activity.get("max_rx_bytes-r") is not None else None,
        max_upload_mbps=bytes_per_second_to_mbps(activity.get("max_tx_bytes-r"))
        if activity.get("max_tx_bytes-r") is not None else None,
        raw_monthly_bytes=_to_int(stats.get("monthly_bytes")),
    )


def _iter_wan_details(message: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for data_item in message.get("data") or []:
        if not isinstance(data_item, dict):
            continue
        wan = data_item.get("wan") or {}
        for detail in wan.get("wan_details") or []:
            if isinstance(detail, dict):
                yield detail


def _choose_primary_wan(wan_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    for detail in wan_details:
        status = detail.get("status") or {}
        if status.get("is_active") or status.get("up") or status.get("state") == "up":
            return detail
    return wan_details[0]


def _service_latencies(latencies: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    values = {}
    for item in latencies:
        if not isinstance(item, dict):
            continue
        service_name = item.get("service_name")
        latency = _to_int(item.get("latency"))
        if service_name and latency is not None:
            values[service_name] = latency
    return values


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
