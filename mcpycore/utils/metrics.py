"""
MetricsCollector — lightweight metrics for connection health monitoring.

Tracks packet counts, latency, bytes transferred, and uptime.

Usage::

    metrics = MetricsCollector()
    metrics.count_packet_in(0x24)
    metrics.count_packet_out(0x14)
    metrics.record_latency(42.3)

    report = metrics.report()
    print(report)
"""
from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any


class MetricsCollector:
    """
    Collects runtime metrics for one client session.

    All counters reset on ``reset()``.
    """

    def __init__(self, latency_window: int = 100) -> None:
        self._start_time = time.monotonic()
        self._packets_in:  Counter[int] = Counter()
        self._packets_out: Counter[int] = Counter()
        self._bytes_in:  int = 0
        self._bytes_out: int = 0
        self._latency_samples: deque[float] = deque(maxlen=latency_window)
        self._errors: int = 0

    # ── Counters ──────────────────────────────────────────────────────────

    def count_packet_in(self, packet_id: int, size: int = 0) -> None:
        self._packets_in[packet_id] += 1
        self._bytes_in += size

    def count_packet_out(self, packet_id: int, size: int = 0) -> None:
        self._packets_out[packet_id] += 1
        self._bytes_out += size

    def record_latency(self, ms: float) -> None:
        self._latency_samples.append(ms)

    def record_error(self) -> None:
        self._errors += 1

    # ── Aggregates ────────────────────────────────────────────────────────

    @property
    def uptime(self) -> float:
        """Seconds since this collector was created."""
        return time.monotonic() - self._start_time

    @property
    def total_packets_in(self) -> int:
        return sum(self._packets_in.values())

    @property
    def total_packets_out(self) -> int:
        return sum(self._packets_out.values())

    @property
    def avg_latency(self) -> float | None:
        if not self._latency_samples:
            return None
        return sum(self._latency_samples) / len(self._latency_samples)

    @property
    def min_latency(self) -> float | None:
        return min(self._latency_samples) if self._latency_samples else None

    @property
    def max_latency(self) -> float | None:
        return max(self._latency_samples) if self._latency_samples else None

    @property
    def latency_samples(self) -> list[float]:
        return list(self._latency_samples)

    def top_packets_in(self, n: int = 10) -> list[tuple[int, int]]:
        return self._packets_in.most_common(n)

    def top_packets_out(self, n: int = 10) -> list[tuple[int, int]]:
        return self._packets_out.most_common(n)

    # ── Report ────────────────────────────────────────────────────────────

    def report(self) -> dict[str, Any]:
        avg = self.avg_latency
        return {
            "uptime_s":       round(self.uptime, 2),
            "packets_in":     self.total_packets_in,
            "packets_out":    self.total_packets_out,
            "bytes_in":       self._bytes_in,
            "bytes_out":      self._bytes_out,
            "latency_avg_ms": round(avg, 2) if avg is not None else None,
            "latency_min_ms": round(self.min_latency, 2) if self.min_latency is not None else None,
            "latency_max_ms": round(self.max_latency, 2) if self.max_latency is not None else None,
            "errors":         self._errors,
            "top_cb_ids":     [(f"0x{pid:02X}", cnt) for pid, cnt in self.top_packets_in(5)],
            "top_sb_ids":     [(f"0x{pid:02X}", cnt) for pid, cnt in self.top_packets_out(5)],
        }

    def reset(self) -> None:
        self._start_time = time.monotonic()
        self._packets_in.clear()
        self._packets_out.clear()
        self._bytes_in = 0
        self._bytes_out = 0
        self._latency_samples.clear()
        self._errors = 0

    def __repr__(self) -> str:
        return (
            f"MetricsCollector("
            f"in={self.total_packets_in}, "
            f"out={self.total_packets_out}, "
            f"latency={self.avg_latency:.1f}ms)" if self.avg_latency else
            f"MetricsCollector(in={self.total_packets_in}, out={self.total_packets_out})"
        )
