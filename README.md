## Network Commander - UniFi Diagnostics

**Network Commander** is a small UniFi controller helper that exposes useful diagnostics over HTTP and is designed to run as a container.

It connects to a UniFi Network Controller (or UniFi OS / UDM) and summarizes:

- **Latency**: average ping to one or more targets
- **VLANs**: number of configured VLAN networks
- **Clients**: how many clients are currently connected
- **Throughput (approx)**: aggregate traffic counters from clients
- **Site health**: basic status from the controller

You deploy this as a Docker container and point it at your existing UniFi controller.

---

### Configuration

The service is configured entirely via environment variables:

- **`UNIFI_CONTROLLER_URL`**: Base URL to your controller, e.g. `https://unifi.example.com:8443`
- **`UNIFI_USERNAME`**: Controller username (local admin account is recommended)
- **`UNIFI_PASSWORD`**: Controller password
- **`UNIFI_SITE`**: Site name / ID, defaults to `default`
- **`UNIFI_IS_UDM_PRO`**: `true` if using UniFi OS / UDM / Dream Machine, else `false`
- **`UNIFI_VERIFY_SSL`**: `true` to validate SSL certs, `false` to skip verification
- **`PING_TARGETS`**: Comma‑separated hosts to ping for latency, e.g. `1.1.1.1,8.8.8.8`

All credentials should be supplied via environment variables or container secrets, never committed to Git.

---

### Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export UNIFI_CONTROLLER_URL="https://unifi.example.com:8443"
export UNIFI_USERNAME="your_user"
export UNIFI_PASSWORD="your_password"
export UNIFI_SITE="default"
export UNIFI_IS_UDM_PRO="false"
export UNIFI_VERIFY_SSL="true"
export PING_TARGETS="1.1.1.1,8.8.8.8"

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Once running, hit:

- `GET /health` – controller connectivity + basic site info
- `GET /diagnostics/summary` – high‑level metrics (latency, VLANs, clients, throughput)
- `GET /diagnostics/clients` – list of connected clients
- `GET /diagnostics/vlans` – list of VLAN/network definitions

---

### Docker usage

Build the image:

```bash
docker build -t network-commander .
```

Run the container:

```bash
docker run --rm -p 8080:8080 \
  -e UNIFI_CONTROLLER_URL="https://unifi.example.com:8443" \
  -e UNIFI_USERNAME="your_user" \
  -e UNIFI_PASSWORD="your_password" \
  -e UNIFI_SITE="default" \
  -e UNIFI_IS_UDM_PRO="false" \
  -e UNIFI_VERIFY_SSL="true" \
  -e PING_TARGETS="1.1.1.1,8.8.8.8" \
  network-commander
```

You can then browse to `http://localhost:8080/docs` for the interactive Swagger UI.

---

### Notes / ideas for future expansion

- **Historical trends** by periodically sampling and storing stats
- **Prometheus metrics** endpoint for easy scraping
- **Alerting hooks** (webhooks, Slack, etc.) for threshold breaches
- **Multi‑site support** exposed in the API

