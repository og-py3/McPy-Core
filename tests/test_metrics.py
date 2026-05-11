"""Tests for MetricsCollector."""
from __future__ import annotations

import time
import pytest

from mcpycore.utils.metrics import MetricsCollector


def test_initial_state():
    m = MetricsCollector()
    assert m.total_packets_in == 0
    assert m.total_packets_out == 0
    assert m.avg_latency is None


def test_count_packets_in():
    m = MetricsCollector()
    m.count_packet_in(0x24)
    m.count_packet_in(0x24)
    m.count_packet_in(0x55)
    assert m.total_packets_in == 3


def test_count_packets_out():
    m = MetricsCollector()
    m.count_packet_out(0x14)
    m.count_packet_out(0x14)
    assert m.total_packets_out == 2


def test_latency_avg():
    m = MetricsCollector()
    m.record_latency(10.0)
    m.record_latency(20.0)
    m.record_latency(30.0)
    assert m.avg_latency == 20.0


def test_latency_min_max():
    m = MetricsCollector()
    m.record_latency(5.0)
    m.record_latency(100.0)
    assert m.min_latency == 5.0
    assert m.max_latency == 100.0


def test_latency_window():
    m = MetricsCollector(latency_window=3)
    for v in [1, 2, 3, 4, 5]:
        m.record_latency(float(v))
    # window of 3 → last 3 samples: 3, 4, 5
    assert m.avg_latency == 4.0


def test_top_packets_in():
    m = MetricsCollector()
    for _ in range(5): m.count_packet_in(0x24)
    for _ in range(3): m.count_packet_in(0x55)
    top = m.top_packets_in(2)
    assert top[0] == (0x24, 5)
    assert top[1] == (0x55, 3)


def test_report_structure():
    m = MetricsCollector()
    m.count_packet_in(0x24)
    m.record_latency(42.0)
    r = m.report()
    assert "uptime_s" in r
    assert "packets_in" in r
    assert "latency_avg_ms" in r
    assert r["packets_in"] == 1
    assert r["latency_avg_ms"] == 42.0


def test_reset():
    m = MetricsCollector()
    m.count_packet_in(0x01)
    m.record_latency(50.0)
    m.reset()
    assert m.total_packets_in == 0
    assert m.avg_latency is None


def test_uptime_positive():
    m = MetricsCollector()
    time.sleep(0.01)
    assert m.uptime > 0


def test_error_count():
    m = MetricsCollector()
    m.record_error()
    m.record_error()
    r = m.report()
    assert r["errors"] == 2


def test_repr():
    m = MetricsCollector()
    assert "MetricsCollector" in repr(m)


def test_latency_samples():
    m = MetricsCollector()
    m.record_latency(10.0)
    m.record_latency(20.0)
    samples = m.latency_samples
    assert 10.0 in samples
    assert 20.0 in samples
