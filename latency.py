import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from typing import Iterable, Optional, Sequence


PING_STAGGER_SECONDS = 1
PING_TARGET_INTERVAL_SECONDS = 3
PING_HISTORY_SECONDS = 180
DEFAULT_PING_TARGETS = (
    ("cloudflare", "Cloudflare", "1.1.1.1"),
    ("google", "Google", "8.8.8.8"),
    ("quad9", "Quad9", "9.9.9.9"),
)


@dataclass(frozen=True)
class PingTarget:
    key: str
    label: str
    address: str

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PingResult:
    target_key: str
    target_label: str
    address: str
    latency_ms: Optional[float]
    success: bool
    error: Optional[str] = None

    def as_dict(self):
        return asdict(self)


def default_ping_targets() -> Sequence[PingTarget]:
    return tuple(PingTarget(*target) for target in DEFAULT_PING_TARGETS)


def ping_target(target: PingTarget, timeout_seconds: int = 5) -> PingResult:
    try:
        completed = subprocess.run(
            _ping_command(target.address),
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return PingResult(target.key, target.label, target.address, None, False, str(exc))

    output = f"{completed.stdout}\n{completed.stderr}"
    latency_ms = parse_ping_latency(output)
    if completed.returncode == 0 and latency_ms is not None:
        return PingResult(
            target.key,
            target.label,
            target.address,
            round(latency_ms, 2),
            True,
        )

    error = _last_ping_error(output) or f"ping exited with {completed.returncode}"
    return PingResult(target.key, target.label, target.address, None, False, error)


def parse_ping_latency(output: str) -> Optional[float]:
    match = re.search(r"time[=<]([0-9]+(?:\.[0-9]+)?)\s*ms", output)
    if not match:
        return None
    return float(match.group(1))


def cycle_targets(targets: Sequence[PingTarget]) -> Iterable[PingTarget]:
    while True:
        for target in targets:
            yield target


def _ping_command(address: str):
    if platform.system() == "Darwin":
        return ["ping", "-n", "-c", "1", "-W", "3000", address]
    return ["ping", "-n", "-c", "1", "-W", "3", address]


def _last_ping_error(output: str) -> Optional[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    return lines[-1][:160]
