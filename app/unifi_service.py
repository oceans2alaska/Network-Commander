from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

from unifi_controller_api import UnifiController
from unifi_controller_api.exceptions import UnifiAPIError, UnifiAuthenticationError

from .config import get_settings


@dataclass
class LatencyResult:
    target: str
    avg_ms: Optional[float]
    success: bool
    error: Optional[str] = None


@dataclass
class SummaryDiagnostics:
    site: str
    client_count: int
    vlan_count: int
    total_tx_bytes: int
    total_rx_bytes: int
    avg_latency_ms: Optional[float]
    latencies: List[LatencyResult]
    generated_at: datetime


class UnifiDiagnosticsService:
    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._controller = UnifiController(
            controller_url=str(settings.unifi_controller_url),
            username=settings.unifi_username,
            password=settings.unifi_password,
            is_udm_pro=settings.unifi_is_udm_pro,
            verify_ssl=settings.unifi_verify_ssl,
        )

    @property
    def site_name(self) -> str:
        return self._settings.unifi_site

    # ---------- UniFi data ----------

    def get_site_health(self) -> Dict[str, Any]:
        """Return basic site health information."""
        try:
            sites = self._controller.get_unifi_site(include_health=True, raw=False)
        except (UnifiAuthenticationError, UnifiAPIError) as exc:
            raise RuntimeError(f"Failed to query UniFi site health: {exc}") from exc

        target_site = None
        for site in sites or []:
            if site.name == self.site_name:
                target_site = site
                break

        if not target_site:
            raise RuntimeError(f"Site '{self.site_name}' not found on controller")

        health = {}
        if target_site.health and getattr(target_site.health, "subsystems", None):
            for name, subsystem in target_site.health.subsystems.items():
                health[name] = {
                    "status": getattr(subsystem, "status", None),
                    "reachable": getattr(subsystem, "reachable", None),
                }

        return {
            "site_id": target_site.name,
            "site_desc": getattr(target_site, "desc", None) or target_site.name,
            "health": health,
        }

    def get_clients(self) -> List[Dict[str, Any]]:
        """Return a simplified list of connected clients."""
        try:
            clients = self._controller.get_unifi_site_client(site_name=self.site_name, raw=False)
        except (UnifiAuthenticationError, UnifiAPIError) as exc:
            raise RuntimeError(f"Failed to query UniFi clients: {exc}") from exc

        results: List[Dict[str, Any]] = []
        for client in clients or []:
            identifier = getattr(client, "name", None) or getattr(client, "hostname", None) or getattr(client, "mac", None)
            results.append(
                {
                    "id": getattr(client, "id", None),
                    "name": identifier,
                    "ip": getattr(client, "ip", None),
                    "mac": getattr(client, "mac", None),
                    "ap_mac": getattr(client, "ap_mac", None),
                    "radio": getattr(client, "radio", None),
                    "is_wired": getattr(client, "is_wired", None),
                    "rx_bytes": int(getattr(client, "rx_bytes", 0) or 0),
                    "tx_bytes": int(getattr(client, "tx_bytes", 0) or 0),
                    "uptime": getattr(client, "uptime", None),
                    "signal": getattr(client, "signal", None),
                    "noise": getattr(client, "noise", None),
                    "satisfaction": getattr(client, "satisfaction", None),
                }
            )
        return results

    def get_vlans(self) -> List[Dict[str, Any]]:
        """Return network configurations / VLANs."""
        try:
            netconfs = self._controller.get_unifi_site_networkconf(site_name=self.site_name, raw=False)
        except (UnifiAuthenticationError, UnifiAPIError) as exc:
            raise RuntimeError(f"Failed to query UniFi networks: {exc}") from exc

        results: List[Dict[str, Any]] = []
        for net in netconfs or []:
            results.append(
                {
                    "id": getattr(net, "id", None),
                    "name": getattr(net, "name", None),
                    "purpose": getattr(net, "purpose", None),
                    "subnet": getattr(net, "ip_subnet", None),
                    "vlan": getattr(net, "vlan", None),
                    "dhcp_enabled": getattr(net, "dhcpd_enabled", None),
                }
            )
        return results

    # ---------- Latency ----------

    def measure_latency(self) -> List[LatencyResult]:
        """Ping all configured targets once and return per-target latency."""
        import subprocess

        latencies: List[LatencyResult] = []
        for target in self._settings.ping_targets:
            try:
                # Use a single ping to keep this fast; parse the "time=" value.
                completed = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", target],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if completed.returncode != 0:
                    latencies.append(LatencyResult(target=target, avg_ms=None, success=False, error="ping failed"))
                    continue

                ms: Optional[float] = None
                for line in (completed.stdout or "").splitlines():
                    if "time=" in line:
                        # e.g. "64 bytes from 1.1.1.1: icmp_seq=1 ttl=58 time=10.6 ms"
                        try:
                            part = line.split("time=", 1)[1]
                            ms_str = part.split(" ", 1)[0]
                            ms = float(ms_str)
                        except Exception:
                            ms = None
                        break

                latencies.append(
                    LatencyResult(
                        target=target,
                        avg_ms=ms,
                        success=ms is not None,
                        error=None if ms is not None else "failed to parse latency",
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive
                latencies.append(LatencyResult(target=target, avg_ms=None, success=False, error=str(exc)))

        return latencies

    # ---------- Summary ----------

    def get_summary(self) -> SummaryDiagnostics:
        clients = self.get_clients()
        vlans = self.get_vlans()
        latencies = self.measure_latency()

        total_tx = sum(int(c.get("tx_bytes") or 0) for c in clients)
        total_rx = sum(int(c.get("rx_bytes") or 0) for c in clients)

        successful_latencies = [l.avg_ms for l in latencies if l.success and l.avg_ms is not None]
        avg_latency = mean(successful_latencies) if successful_latencies else None

        return SummaryDiagnostics(
            site=self.site_name,
            client_count=len(clients),
            vlan_count=len({v.get("vlan") for v in vlans if v.get("vlan") is not None}),
            total_tx_bytes=total_tx,
            total_rx_bytes=total_rx,
            avg_latency_ms=avg_latency,
            latencies=latencies,
            generated_at=datetime.utcnow(),
        )

