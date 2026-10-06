"""
Pytest test suite for the Flask DevOps API.
Tests all endpoints: /, /health, /simulate-failure, /reset

conftest.py (in the project root) adds app/ to sys.path so that
`from app import app` resolves to app/app.py correctly.
"""

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        # Reset the simulate flag before every test
        client.post("/reset")
        yield client


# ─────────────────────────────────────────────
# Tests for GET /
# ─────────────────────────────────────────────

class TestIndexEndpoint:
    def test_index_returns_200(self, client):
        """Root endpoint should respond with HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_json(self, client):
        """Root endpoint should return JSON content-type."""
        response = client.get("/")
        assert response.content_type == "application/json"

    def test_index_contains_message(self, client):
        """Root endpoint JSON body should contain a 'message' key."""
        response = client.get("/")
        data = response.get_json()
        assert "message" in data

    def test_index_contains_status(self, client):
        """Root endpoint JSON body should contain status 'online'."""
        response = client.get("/")
        data = response.get_json()
        assert data.get("status") == "online"

    def test_index_contains_version(self, client):
        """Root endpoint JSON body should contain a version field."""
        response = client.get("/")
        data = response.get_json()
        assert "version" in data


# ─────────────────────────────────────────────
# Tests for GET /health
# ─────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200_when_healthy(self, client):
        """Health endpoint should return HTTP 200 in normal state."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint should return JSON content-type."""
        response = client.get("/health")
        assert response.content_type == "application/json"

    def test_health_status_is_healthy(self, client):
        """Health endpoint should report HEALTHY in normal state."""
        response = client.get("/health")
        data = response.get_json()
        assert data.get("status") == "HEALTHY"

    def test_health_contains_uptime(self, client):
        """Health endpoint should include uptime_seconds field."""
        response = client.get("/health")
        data = response.get_json()
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_health_contains_message(self, client):
        """Health endpoint should include a message field when healthy."""
        response = client.get("/health")
        data = response.get_json()
        assert "message" in data


# ─────────────────────────────────────────────
# Tests for POST /simulate-failure
# ─────────────────────────────────────────────

class TestSimulateFailureEndpoint:
    def test_simulate_failure_returns_200(self, client):
        """Simulate-failure endpoint should return HTTP 200 on activation."""
        response = client.post("/simulate-failure")
        assert response.status_code == 200

    def test_simulate_failure_returns_json(self, client):
        """Simulate-failure endpoint should return JSON."""
        response = client.post("/simulate-failure")
        assert response.content_type == "application/json"

    def test_simulate_failure_contains_message(self, client):
        """Simulate-failure should return a message confirming activation."""
        response = client.post("/simulate-failure")
        data = response.get_json()
        assert "message" in data

    def test_health_returns_503_after_simulate(self, client):
        """After simulate-failure, /health should return HTTP 503."""
        client.post("/simulate-failure")
        response = client.get("/health")
        assert response.status_code == 503

    def test_health_status_unhealthy_after_simulate(self, client):
        """After simulate-failure, /health status should be UNHEALTHY."""
        client.post("/simulate-failure")
        response = client.get("/health")
        data = response.get_json()
        assert data.get("status") == "UNHEALTHY"

    def test_health_has_reason_when_unhealthy(self, client):
        """Unhealthy response should include a 'reason' field."""
        client.post("/simulate-failure")
        response = client.get("/health")
        data = response.get_json()
        assert "reason" in data


# ─────────────────────────────────────────────
# Tests for POST /reset
# ─────────────────────────────────────────────

class TestResetEndpoint:
    def test_reset_returns_200(self, client):
        """Reset endpoint should return HTTP 200."""
        response = client.post("/reset")
        assert response.status_code == 200

    def test_reset_returns_json(self, client):
        """Reset endpoint should return JSON."""
        response = client.post("/reset")
        assert response.content_type == "application/json"

    def test_reset_clears_failure_flag(self, client):
        """After reset, /health should return HEALTHY again."""
        client.post("/simulate-failure")
        assert client.get("/health").status_code == 503

        client.post("/reset")
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "HEALTHY"

    def test_reset_contains_message(self, client):
        """Reset endpoint should return a message field."""
        response = client.post("/reset")
        data = response.get_json()
        assert "message" in data


# ─────────────────────────────────────────────
# Tests for GET /metrics (Prometheus endpoint)
# ─────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        """Metrics endpoint should return HTTP 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type_is_prometheus(self, client):
        """Metrics endpoint should return Prometheus text/plain content-type."""
        response = client.get("/metrics")
        assert "text/plain" in response.content_type

    def test_metrics_exposes_health_status_gauge(self, client):
        """Metrics should include flask_health_status gauge."""
        response = client.get("/metrics")
        assert b"flask_health_status" in response.data

    def test_metrics_exposes_request_counter(self, client):
        """Metrics should include flask_requests_total counter after requests."""
        # Make a request so the counter is non-zero
        client.get("/")
        response = client.get("/metrics")
        assert b"flask_requests_total" in response.data

    def test_metrics_health_status_zero_when_unhealthy(self, client):
        """After simulate-failure, flask_health_status in /metrics should be 0."""
        client.post("/simulate-failure")
        client.get("/health")  # Trigger health check to update gauge
        response = client.get("/metrics")
        data = response.data.decode("utf-8")
        # The line should show flask_health_status 0.0
        assert "flask_health_status 0.0" in data

    def test_metrics_uptime_gauge_present(self, client):
        """Metrics should include flask_uptime_seconds gauge."""
        client.get("/health")  # Trigger uptime update
        response = client.get("/metrics")
        assert b"flask_uptime_seconds" in response.data
