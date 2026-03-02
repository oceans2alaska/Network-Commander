from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings, get_settings
from .unifi_service import LatencyResult, SummaryDiagnostics, UnifiDiagnosticsService


app = FastAPI(
    title="Network Commander - UniFi Diagnostics",
    version="0.1.0",
    description="Small helper service exposing UniFi diagnostics over HTTP.",
)


def get_service() -> UnifiDiagnosticsService:
    try:
        return UnifiDiagnosticsService()
    except Exception as exc:
        # Defer detailed error to the endpoints where we can surface it cleanly
        raise HTTPException(status_code=500, detail=f"Failed to initialize UniFi controller: {exc}")


class HealthResponse(BaseModel):
    site_id: str
    site_desc: str
    health: dict
    timestamp: datetime


class LatencyItem(BaseModel):
    target: str
    avg_ms: Optional[float]
    success: bool
    error: Optional[str] = None


class SummaryResponse(BaseModel):
    site: str
    client_count: int
    vlan_count: int
    total_tx_bytes: int
    total_rx_bytes: int
    avg_latency_ms: Optional[float]
    latencies: List[LatencyItem]
    generated_at: datetime


@app.get("/health", response_model=HealthResponse)
def health(
    svc: UnifiDiagnosticsService = Depends(get_service),
) -> HealthResponse:
    try:
        data = svc.get_site_health()
        return HealthResponse(
            site_id=data["site_id"],
            site_desc=data["site_desc"],
            health=data["health"],
            timestamp=datetime.utcnow(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/diagnostics/summary", response_model=SummaryResponse)
def diagnostics_summary(
    svc: UnifiDiagnosticsService = Depends(get_service),
) -> SummaryResponse:
    try:
        summary: SummaryDiagnostics = svc.get_summary()
        latencies = [
            LatencyItem(
                target=l.target,
                avg_ms=l.avg_ms,
                success=l.success,
                error=l.error,
            )
            for l in summary.latencies
        ]
        return SummaryResponse(
            site=summary.site,
            client_count=summary.client_count,
            vlan_count=summary.vlan_count,
            total_tx_bytes=summary.total_tx_bytes,
            total_rx_bytes=summary.total_rx_bytes,
            avg_latency_ms=summary.avg_latency_ms,
            latencies=latencies,
            generated_at=summary.generated_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/diagnostics/clients")
def diagnostics_clients(
    svc: UnifiDiagnosticsService = Depends(get_service),
) -> JSONResponse:
    try:
        return JSONResponse(content={"site": svc.site_name, "clients": svc.get_clients()})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/diagnostics/vlans")
def diagnostics_vlans(
    svc: UnifiDiagnosticsService = Depends(get_service),
) -> JSONResponse:
    try:
        return JSONResponse(content={"site": svc.site_name, "vlans": svc.get_vlans()})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/config")
def show_config(settings: Settings = Depends(get_settings)) -> dict:
    # Helpful debug endpoint that does not reveal secrets
    return {
        "unifi_controller_url": str(settings.unifi_controller_url),
        "unifi_site": settings.unifi_site,
        "unifi_is_udm_pro": settings.unifi_is_udm_pro,
        "unifi_verify_ssl": settings.unifi_verify_ssl,
        "ping_targets": settings.ping_targets,
    }

