"""
Flask REST API - DevOps Mini Project
Automated Container Failure Detection, Self-Recovery and Notification
"""

import os
import time
from flask import Flask, jsonify

app = Flask(__name__)

# Startup time for uptime calculation
START_TIME = time.time()

# This flag is used to simulate application failure for demonstration purposes.
# When set to True via the /simulate-failure endpoint, the /health endpoint
# will return an UNHEALTHY status, triggering the monitoring and recovery flow.
_SIMULATE_FAILURE = False


@app.route("/", methods=["GET"])
def index():
    """Root endpoint - basic application response."""
    return jsonify({
        "message": "Flask DevOps API is running",
        "version": "1.0.0",
        "status": "online"
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """
    Health check endpoint.
    Returns HEALTHY normally, or UNHEALTHY when failure is simulated.
    Used by the monitoring script to determine container health.
    """
    global _SIMULATE_FAILURE

    if _SIMULATE_FAILURE:
        return jsonify({
            "status": "UNHEALTHY",
            "reason": "Simulated failure triggered for demonstration",
            "uptime_seconds": round(time.time() - START_TIME, 2)
        }), 503

    uptime = round(time.time() - START_TIME, 2)
    return jsonify({
        "status": "HEALTHY",
        "uptime_seconds": uptime,
        "message": "Application is running normally"
    }), 200


@app.route("/simulate-failure", methods=["POST"])
def simulate_failure():
    """
    Intentionally make the /health endpoint return UNHEALTHY.
    This is used during the college demonstration to trigger the
    monitoring → detection → restart → recovery → notification flow.
    """
    global _SIMULATE_FAILURE
    _SIMULATE_FAILURE = True
    return jsonify({
        "message": "Failure simulation ACTIVATED",
        "info": "The /health endpoint will now return UNHEALTHY (HTTP 503)",
        "hint": "The monitor will detect this and restart the container"
    }), 200


@app.route("/reset", methods=["POST"])
def reset():
    """
    Clears the simulated failure flag.
    This is automatically cleared on container restart anyway,
    but this endpoint is useful for manual resets during testing.
    """
    global _SIMULATE_FAILURE
    _SIMULATE_FAILURE = False
    return jsonify({
        "message": "Application reset to HEALTHY state"
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
