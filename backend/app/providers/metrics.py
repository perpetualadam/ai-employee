"""Provider metrics — structured counters for monitoring and admin dashboards."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderMetricSnapshot:
    provider_name: str
    service: str
    provision_success: int = 0
    provision_failure: int = 0
    sms_success: int = 0
    sms_failure: int = 0
    call_success: int = 0
    call_failure: int = 0
    webhook_latency_ms_total: float = 0.0
    webhook_latency_samples: int = 0
    api_latency_ms_total: float = 0.0
    api_latency_samples: int = 0
    error_count: int = 0
    retry_count: int = 0
    health_checks: int = 0

    def to_dict(self) -> dict[str, Any]:
        webhook_avg = (
            round(self.webhook_latency_ms_total / self.webhook_latency_samples, 2)
            if self.webhook_latency_samples
            else None
        )
        api_avg = (
            round(self.api_latency_ms_total / self.api_latency_samples, 2)
            if self.api_latency_samples
            else None
        )
        sms_total = self.sms_success + self.sms_failure
        call_total = self.call_success + self.call_failure
        provision_total = self.provision_success + self.provision_failure
        return {
            "provider_name": self.provider_name,
            "service": self.service,
            "provision_success_rate": _rate(self.provision_success, provision_total),
            "sms_success_rate": _rate(self.sms_success, sms_total),
            "call_success_rate": _rate(self.call_success, call_total),
            "webhook_latency_ms_avg": webhook_avg,
            "api_latency_ms_avg": api_avg,
            "error_count": self.error_count,
            "retry_count": self.retry_count,
            "health_checks": self.health_checks,
        }


def _rate(success: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(success / total, 4)


class ProviderMetricsCollector:
    """Thread-safe in-process metrics — export via admin API / structured logs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._metrics: dict[tuple[str, str], ProviderMetricSnapshot] = {}

    def _snapshot(self, provider_name: str, service: str) -> ProviderMetricSnapshot:
        key = (provider_name.lower(), service)
        if key not in self._metrics:
            self._metrics[key] = ProviderMetricSnapshot(provider_name=provider_name, service=service)
        return self._metrics[key]

    def record_sms(self, provider_name: str, *, success: bool) -> None:
        with self._lock:
            snap = self._snapshot(provider_name, "messaging")
            if success:
                snap.sms_success += 1
            else:
                snap.sms_failure += 1
                snap.error_count += 1

    def record_call(self, provider_name: str, *, success: bool) -> None:
        with self._lock:
            snap = self._snapshot(provider_name, "telephony")
            if success:
                snap.call_success += 1
            else:
                snap.call_failure += 1
                snap.error_count += 1

    def record_provision(self, provider_name: str, *, success: bool) -> None:
        with self._lock:
            snap = self._snapshot(provider_name, "numbers")
            if success:
                snap.provision_success += 1
            else:
                snap.provision_failure += 1
                snap.error_count += 1

    def record_retry(self, provider_name: str, service: str) -> None:
        with self._lock:
            self._snapshot(provider_name, service).retry_count += 1

    def record_api_latency(self, provider_name: str, service: str, latency_ms: float) -> None:
        with self._lock:
            snap = self._snapshot(provider_name, service)
            snap.api_latency_ms_total += latency_ms
            snap.api_latency_samples += 1

    def record_health_check(self, provider_name: str, service: str) -> None:
        with self._lock:
            self._snapshot(provider_name, service).health_checks += 1

    def all_snapshots(self) -> list[dict[str, Any]]:
        with self._lock:
            return [snap.to_dict() for snap in self._metrics.values()]


_metrics = ProviderMetricsCollector()


def get_provider_metrics() -> ProviderMetricsCollector:
    return _metrics
