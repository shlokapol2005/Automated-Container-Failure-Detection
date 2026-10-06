"""
Flask REST API - DevOps Mini Project
Automated Container Failure Detection, Self-Recovery and Notification
"""

import os
import time
import logging
from flask import Flask, jsonify, Response
from prometheus_client import (
    Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)

# ── Structured logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Application state ─────────────────────────────────────────────────────────
START_TIME = time.time()

# This flag is used to simulate application failure for demonstration purposes.
# When set to True via /simulate-failure, the /health endpoint returns UNHEALTHY.
# NOTE: gunicorn MUST run with --workers=1 so this flag is shared across
#       all requests within the same process.
_SIMULATE_FAILURE = False


# ── Prometheus metrics ─────────────────────────────────────────────────────────
# These are scraped by Prometheus every 15s and visualised in Grafana.

REQUEST_COUNTER = Counter(
    "flask_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint"],
)
HEALTH_STATUS_GAUGE = Gauge(
    "flask_health_status",
    "Current health status: 1 = HEALTHY, 0 = UNHEALTHY",
)
UPTIME_GAUGE = Gauge(
    "flask_uptime_seconds",
    "Application uptime in seconds",
)
FAILURE_SIMULATION_COUNTER = Counter(
    "flask_failures_simulated_total",
    "Number of times failure simulation was triggered",
)

# Initialise health gauge to healthy at startup
HEALTH_STATUS_GAUGE.set(1)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    """Root endpoint — basic application info."""
    REQUEST_COUNTER.labels(method="GET", endpoint="/").inc()
    logger.info("GET / → 200")
    return jsonify({
        "message": "Flask DevOps API is running",
        "version": "1.0.0",
        "status": "online",
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    Returns HEALTHY normally, or UNHEALTHY when failure is simulated.
    Polled by monitor/monitor.py every CHECK_INTERVAL seconds.
    Also scraped by the Docker and Docker Compose HEALTHCHECK directives.
    """
    global _SIMULATE_FAILURE
    REQUEST_COUNTER.labels(method="GET", endpoint="/health").inc()

    if _SIMULATE_FAILURE:
        HEALTH_STATUS_GAUGE.set(0)
        logger.warning("GET /health → 503 UNHEALTHY (simulated failure active)")
        return jsonify({
            "status": "UNHEALTHY",
            "reason": "Simulated failure triggered for demonstration",
            "uptime_seconds": round(time.time() - START_TIME, 2),
        }), 503

    uptime = round(time.time() - START_TIME, 2)
    HEALTH_STATUS_GAUGE.set(1)
    UPTIME_GAUGE.set(uptime)
    logger.info("GET /health → 200 HEALTHY | uptime=%.2fs", uptime)
    return jsonify({
        "status": "HEALTHY",
        "uptime_seconds": uptime,
        "message": "Application is running normally",
    }), 200


@app.route("/simulate-failure", methods=["POST"])
def simulate_failure():
    """
    Intentionally make /health return UNHEALTHY.
    Triggers the monitoring → detection → restart → recovery → notification flow.
    """
    global _SIMULATE_FAILURE
    _SIMULATE_FAILURE = True
    FAILURE_SIMULATION_COUNTER.inc()
    HEALTH_STATUS_GAUGE.set(0)
    logger.warning("POST /simulate-failure → failure simulation ACTIVATED")
    return jsonify({
        "message": "Failure simulation ACTIVATED",
        "info": "The /health endpoint will now return UNHEALTHY (HTTP 503)",
        "hint": "The monitor will detect this and restart the container",
    }), 200


@app.route("/reset", methods=["POST"])
def reset():
    """
    Clears the simulated failure flag.
    Container restart clears this automatically, but this endpoint
    is useful for manual resets during testing.
    """
    global _SIMULATE_FAILURE
    _SIMULATE_FAILURE = False
    HEALTH_STATUS_GAUGE.set(1)
    logger.info("POST /reset → application reset to HEALTHY state")
    return jsonify({
        "message": "Application reset to HEALTHY state",
    }), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    """
    Prometheus metrics endpoint.
    Scraped by Prometheus every 15 seconds.
    Exposed metrics:
      - flask_requests_total          (counter, per endpoint)
      - flask_health_status           (gauge, 1=HEALTHY 0=UNHEALTHY)
      - flask_uptime_seconds          (gauge)
      - flask_failures_simulated_total (counter)
    Visualised in Grafana at http://localhost:3000
    """
    UPTIME_GAUGE.set(round(time.time() - START_TIME, 2))
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
