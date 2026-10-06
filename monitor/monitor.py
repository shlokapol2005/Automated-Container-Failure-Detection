"""
monitor.py
──────────────────────────────────────────────────────────────────────────────
Health Monitor with Automatic Container Recovery and Discord Notifications

Automated Container Failure Detection, Self-Recovery and Notification
DevOps Mini Project

WHAT THIS SCRIPT DOES:
  1. Periodically calls GET /health on the Flask container
  2. If HEALTHY  → logs OK, continues watching
  3. If UNHEALTHY (2 consecutive) →
       a. Sends Discord "failure detected" alert
       b. Issues `docker restart <container>`
       c. Polls recovery (every 5s, up to RECOVERY_TIMEOUT)
       d. Sends Discord "recovered" alert with recovery time
       e. If restarts this session >= MAX_RESTARTS → sends escalation alert
  4. Tracks total restarts per session to detect persistent failures

ENVIRONMENT VARIABLES (set in .env or docker-compose environment):
  DISCORD_WEBHOOK_URL  – Discord Incoming Webhook URL (required for alerts)
  HEALTH_URL           – Full URL of the /health endpoint
                         (default: http://localhost:5000/health)
  CONTAINER_NAME       – Docker container name to restart on failure
                         (default: flask-devops-app)
  CHECK_INTERVAL       – Seconds between health checks (default: 10)
  RECOVERY_TIMEOUT     – Max seconds to wait for recovery (default: 60)
  MAX_RESTARTS         – Restarts before escalation alert (default: 5)

USAGE:
  # On host:
  python monitor/monitor.py

  # Via Docker Compose (recommended):
  docker compose up -d
──────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime


# ─────────────────────────────────────────────
# Configuration (from environment variables)
# ─────────────────────────────────────────────

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
HEALTH_URL          = os.environ.get("HEALTH_URL", "http://localhost:5000/health")
CONTAINER_NAME      = os.environ.get("CONTAINER_NAME", "flask-devops-app")
CHECK_INTERVAL      = int(os.environ.get("CHECK_INTERVAL", "10"))
RECOVERY_TIMEOUT    = int(os.environ.get("RECOVERY_TIMEOUT", "60"))
MAX_RESTARTS        = int(os.environ.get("MAX_RESTARTS", "5"))


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────

_session_restart_count = 0   # Total restarts issued in this monitoring session


# ─────────────────────────────────────────────
# Logging helpers
# ─────────────────────────────────────────────

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    icons = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERROR": "❌", "ACTION": "🔄"}
    icon = icons.get(level, "  ")
    print(f"[{timestamp()}] [{level:6s}] {icon}  {message}", flush=True)


# ─────────────────────────────────────────────
# Discord notification
# ─────────────────────────────────────────────

def send_discord_notification(title: str, description: str, color: int) -> None:
    """
    Send a rich embed message to Discord via webhook.
    color: Discord embed color integer (e.g. 0xFF0000 = red, 0x00FF00 = green)
    """
    if not DISCORD_WEBHOOK_URL:
        log("WARN", "DISCORD_WEBHOOK_URL not set — skipping Discord notification")
        return

    color_label = {0xFF0000: "🔴", 0x00FF00: "🟢", 0xFF6600: "🟠", 0xFF0066: "🆘"}.get(color, "🔵")

    payload = json.dumps({
        "content": f"{color_label} **{title}**\n{description}\n_Container: `{CONTAINER_NAME}` • {timestamp()}_",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": f"Container: {CONTAINER_NAME} • {timestamp()}"}
        }]
    }).encode("utf-8")

    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                log("OK", "Discord notification sent successfully")
            else:
                log("WARN", f"Discord returned unexpected status: {resp.status}")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = "(no body)"
        log("WARN", f"Discord HTTP {exc.code}: {body}")
    except Exception as exc:
        log("WARN", f"Failed to send Discord notification: {exc}")


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

def check_health() -> dict:
    """
    Call the /health endpoint.
    Returns a dict with keys:
      - healthy   (bool)
      - status    (str)   "HEALTHY" | "UNHEALTHY" | "UNREACHABLE"
      - http_code (int | None)
      - body      (dict | None)
    """
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            http_code = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            api_status = body.get("status", "UNKNOWN")
            healthy = http_code == 200 and api_status == "HEALTHY"
            return {"healthy": healthy, "status": api_status,
                    "http_code": http_code, "body": body}
    except urllib.error.HTTPError as exc:
        # 503 is expected when failure is simulated
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except Exception:
            body = {}
        return {"healthy": False, "status": body.get("status", "UNHEALTHY"),
                "http_code": exc.code, "body": body}
    except Exception as exc:
        return {"healthy": False, "status": "UNREACHABLE",
                "http_code": None, "body": None}


# ─────────────────────────────────────────────
# Container management
# ─────────────────────────────────────────────

def restart_container(name: str) -> bool:
    """
    Restart the named Docker container.
    Returns True if the docker restart command succeeded.
    When running inside a container, this works via the mounted Docker socket
    (/var/run/docker.sock) which gives access to the host Docker daemon.
    """
    log("ACTION", f"Restarting container '{name}' ...")
    result = subprocess.run(
        ["docker", "restart", name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log("OK", f"Container '{name}' restart command accepted")
        return True
    else:
        log("ERROR", f"docker restart failed: {result.stderr.strip()}")
        return False


def wait_for_recovery(timeout: int) -> bool:
    """
    Poll /health until HEALTHY is returned or timeout is reached.
    Returns True if recovered within timeout.
    """
    log("ACTION", f"Waiting up to {timeout}s for service to recover ...")
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        time.sleep(5)
        result = check_health()
        elapsed = round(deadline - time.time(), 0)
        log("INFO", f"  Recovery attempt #{attempt} → {result['status']} (timeout in {int(elapsed)}s)")
        if result["healthy"]:
            return True
    return False


# ─────────────────────────────────────────────
# Recovery flow
# ─────────────────────────────────────────────

def handle_failure(result: dict) -> None:
    """
    Full failure → restart → recovery → notification flow.
    Tracks restarts per session and sends escalation if threshold is exceeded.
    """
    global _session_restart_count

    http_code = result.get("http_code")
    api_status = result.get("status")
    failure_detected_at = time.time()

    log("ERROR", f"FAILURE DETECTED — HTTP {http_code} | status={api_status}")

    # Step 1: Notify Discord of failure detection
    send_discord_notification(
        title="🚨 Service Failure Detected",
        description=(
            f"**Container:** `{CONTAINER_NAME}`\n"
            f"**Health URL:** `{HEALTH_URL}`\n"
            f"**HTTP Status:** `{http_code}`\n"
            f"**API Status:** `{api_status}`\n\n"
            "⏳ Initiating automatic recovery ..."
        ),
        color=0xFF0000  # Red
    )

    # Step 2: Restart the container
    restarted = restart_container(CONTAINER_NAME)
    if not restarted:
        log("ERROR", "Could not restart container — manual intervention required")
        send_discord_notification(
            title="❌ Container Restart Failed",
            description=(
                f"**Container:** `{CONTAINER_NAME}`\n"
                "The `docker restart` command failed.\n"
                "**Manual intervention is required.**"
            ),
            color=0xFF0000
        )
        return

    _session_restart_count += 1
    log("INFO", f"Session restart count: {_session_restart_count} / {MAX_RESTARTS}")

    # Step 3: Wait for recovery
    recovered = wait_for_recovery(RECOVERY_TIMEOUT)
    recovery_time = round(time.time() - failure_detected_at, 1)

    if recovered:
        log("OK", f"Service has RECOVERED successfully ✅ (took {recovery_time}s)")
        send_discord_notification(
            title="✅ Service Recovered Successfully",
            description=(
                f"**Container:** `{CONTAINER_NAME}`\n"
                f"**Health URL:** `{HEALTH_URL}`\n"
                f"**Recovery time:** `{recovery_time}s` from failure detection to HEALTHY\n\n"
                "The container was automatically restarted and the service "
                "is now responding **HEALTHY**.\n\n"
                f"_Session restarts: {_session_restart_count} / {MAX_RESTARTS} — Monitoring continues ..._"
            ),
            color=0x00FF00  # Green
        )
    else:
        log("ERROR", f"Service did NOT recover within {RECOVERY_TIMEOUT}s")
        send_discord_notification(
            title="⛔ Recovery Failed — Timeout Exceeded",
            description=(
                f"**Container:** `{CONTAINER_NAME}`\n"
                f"The service did not return HEALTHY within **{RECOVERY_TIMEOUT} seconds** "
                "after restart.\n\n"
                "**Manual investigation required.**"
            ),
            color=0xFF6600  # Orange
        )

    # Step 4: Escalation check — warn if container keeps failing repeatedly
    if _session_restart_count >= MAX_RESTARTS:
        log("ERROR", f"ESCALATION: Container has been restarted {_session_restart_count} times this session")
        send_discord_notification(
            title="🆘 Repeated Failure — Escalation",
            description=(
                f"**Container:** `{CONTAINER_NAME}`\n"
                f"This container has been automatically restarted **{_session_restart_count} times** "
                "in this monitoring session.\n\n"
                "This indicates a **persistent failure**, not a transient one.\n"
                "**Immediate manual investigation is required.**\n\n"
                "_The monitor will continue watching but this is a critical alert._"
            ),
            color=0xFF0066  # Magenta/red
        )


# ─────────────────────────────────────────────
# Main monitoring loop
# ─────────────────────────────────────────────

def main() -> None:
    print("=" * 65)
    print("  DevOps Health Monitor")
    print("  Automated Container Failure Detection & Self-Recovery")
    print("=" * 65)
    log("INFO", f"Health URL       : {HEALTH_URL}")
    log("INFO", f"Container name   : {CONTAINER_NAME}")
    log("INFO", f"Check interval   : {CHECK_INTERVAL}s")
    log("INFO", f"Recovery timeout : {RECOVERY_TIMEOUT}s")
    log("INFO", f"Max restarts     : {MAX_RESTARTS} (escalation threshold)")
    log("INFO", f"Discord alerts   : {'ENABLED' if DISCORD_WEBHOOK_URL else 'DISABLED (set DISCORD_WEBHOOK_URL)'}")
    print("=" * 65)
    print()

    consecutive_failures = 0

    while True:
        result = check_health()

        if result["healthy"]:
            uptime = result["body"].get("uptime_seconds", "?") if result["body"] else "?"
            log("OK", f"HEALTHY — HTTP 200 | uptime={uptime}s")
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            log("WARN", f"Check #{consecutive_failures}: {result['status']} — HTTP {result['http_code']}")

            if consecutive_failures >= 2:
                # Two consecutive failures → trigger recovery flow
                handle_failure(result)
                consecutive_failures = 0

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        log("INFO", "Monitor stopped by user (Ctrl+C)")
        sys.exit(0)
