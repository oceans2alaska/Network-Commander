from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .config import Settings, get_settings
from .unifi_service import LatencyResult, SummaryDiagnostics, UnifiDiagnosticsService


app = FastAPI(
    title="Network Commander - UniFi Diagnostics",
    version="0.1.0",
    description="Small helper service exposing UniFi diagnostics over HTTP.",
)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
    <html>
      <head>
        <title>Network Commander - UniFi Diagnostics</title>
        <style>
          body {
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f172a;
            color: #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
          }
          .card {
            background: #020617;
            border-radius: 1rem;
            padding: 2rem 2.5rem;
            box-shadow: 0 25px 50px -12px rgb(15 23 42 / 0.8);
            max-width: 640px;
            width: 100%;
          }
          h1 {
            font-size: 1.8rem;
            margin: 0 0 0.5rem;
          }
          p {
            margin: 0.25rem 0 1rem;
            color: #9ca3af;
          }
          code {
            background: #020617;
            padding: 0.15rem 0.4rem;
            border-radius: 0.25rem;
            font-size: 0.9rem;
          }
          a {
            color: #38bdf8;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
          ul {
            padding-left: 1.25rem;
            margin: 0.5rem 0 0;
          }
          li {
            margin: 0.15rem 0;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Network Commander is running ✅</h1>
          <p>Your UniFi diagnostics service is up. Try these endpoints:</p>
          <ul>
            <li><a href="/docs"><code>/docs</code></a> – Interactive API docs</li>
            <li><a href="/health"><code>/health</code></a> – Controller + site health</li>
            <li><a href="/diagnostics/summary"><code>/diagnostics/summary</code></a> – High-level summary</li>
            <li><a href="/diagnostics/clients"><code>/diagnostics/clients</code></a> – Connected clients</li>
            <li><a href="/diagnostics/vlans"><code>/diagnostics/vlans</code></a> – VLAN / network config</li>
          </ul>
        </div>
      </body>
    </html>
    """


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

