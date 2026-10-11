"""
Tests for the AIOps incident diagnosis feature (monitor/ai_diagnosis.py) and
its integration with the recovery flow in monitor/monitor.py.

No network, Docker daemon, or Anthropic SDK is needed: the Claude client and
Docker evidence collector are replaced with fakes.
"""

import json
import time
from types import SimpleNamespace

import pytest

import ai_diagnosis
from ai_diagnosis import (
    DiagnosisError,
    IncidentDiagnosisWorker,
    build_evidence,
    build_incident_embed,
    diagnose,
    parse_diagnosis,
    redact,
    request_diagnosis,
)


VALID = {
    "likely_cause": "Application set its health flag to UNHEALTHY after /simulate-failure was called.",
    "supporting_evidence": ["POST /simulate-failure at 10:00:01", "/health returned HTTP 503 twice"],
    "severity": "medium",
    "recommended_remediation": ["Restrict /simulate-failure to test environments"],
    "confidence": "high",
}

FAILED_CHECKS = [
    {"timestamp": "2026-10-11 10:00:05", "http_code": 503, "status": "UNHEALTHY"},
    {"timestamp": "2026-10-11 10:00:15", "http_code": 503, "status": "UNHEALTHY"},
]


# ─────────────────────────────────────────────
# Fakes
# ─────────────────────────────────────────────

class FakeClient:
    """Mimics anthropic.Anthropic().beta.messages.create(...)."""

    def __init__(self, text=None, exc=None, delay=0.0, stop_reason="end_turn", content=None):
        self.text, self.exc, self.delay, self.stop_reason = text, exc, delay, stop_reason
        self.content = content
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        content = self.content if self.content is not None else [
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=self.text),
        ]
        return SimpleNamespace(stop_reason=self.stop_reason, content=content)


def fake_collect(_name):
    return {"logs": "2026-10-11T10:00:01Z POST /simulate-failure 200\n", "container_state": {"status": "running"}}


def evidence():
    return build_evidence("flask-devops-app", "http://flask-app:5000/health", FAILED_CHECKS, [], fake_collect(None))


# ─────────────────────────────────────────────
# Diagnosis parsing
# ─────────────────────────────────────────────

class TestParseDiagnosis:
    def test_valid_json_string(self):
        d = parse_diagnosis(json.dumps(VALID))
        assert d["severity"] == "medium"
        assert d["likely_cause"].startswith("Application set")
        assert d["supporting_evidence"] == VALID["supporting_evidence"]
        assert d["recommended_remediation"] == VALID["recommended_remediation"]
        assert d["confidence"] == "high"

    def test_accepts_dict(self):
        assert parse_diagnosis(dict(VALID))["severity"] == "medium"

    def test_strips_markdown_fence(self):
        assert parse_diagnosis("```json\n" + json.dumps(VALID) + "\n```")["severity"] == "medium"

    def test_severity_is_case_insensitive(self):
        assert parse_diagnosis({**VALID, "severity": "HIGH"})["severity"] == "high"

    def test_string_remediation_becomes_list(self):
        d = parse_diagnosis({**VALID, "recommended_remediation": "Restart the database"})
        assert d["recommended_remediation"] == ["Restart the database"]

    def test_invalid_confidence_defaults_to_low(self):
        assert parse_diagnosis({**VALID, "confidence": "certain"})["confidence"] == "low"

    def test_long_fields_are_clipped(self):
        d = parse_diagnosis({**VALID, "likely_cause": "x" * 5000})
        assert len(d["likely_cause"]) <= 900

    @pytest.mark.parametrize("bad", [
        "not json at all",
        "[1, 2, 3]",
        json.dumps({**VALID, "likely_cause": ""}),
        json.dumps({**VALID, "severity": "catastrophic"}),
        json.dumps({k: v for k, v in VALID.items() if k != "severity"}),
        json.dumps({**VALID, "recommended_remediation": []}),
        "",
        None,
    ])
    def test_invalid_responses_raise(self, bad):
        with pytest.raises(DiagnosisError):
            parse_diagnosis(bad)

    def test_secrets_in_model_output_are_redacted(self):
        d = parse_diagnosis({**VALID, "likely_cause": "Bad key sk-ant-api03-abcdefghijklmnop leaked"})
        assert "sk-ant" not in d["likely_cause"]


# ─────────────────────────────────────────────
# Redaction
# ─────────────────────────────────────────────

class TestRedaction:
    @pytest.mark.parametrize("secret", [
        "https://discord.com/api/webhooks/123456789/AbCdEf_secret-token",
        "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUV",
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_abcdefghijklmnopqrstuvwxyz0123",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcDEF123_-",
        "student@somaiya.edu",
    ])
    def test_known_secret_formats(self, secret):
        out = redact(f"log line containing {secret} here")
        assert secret not in out
        assert "REDACTED" in out

    @pytest.mark.parametrize("line,leak", [
        ("password=hunter2", "hunter2"),
        ('DB_PASSWORD: "s3cr3t!"', "s3cr3t!"),
        ("api_key=abc123xyz", "abc123xyz"),
        ("Authorization: Bearer abcdef123456789", "abcdef123456789"),
        ("postgres://admin:topsecret@db:5432/app", "topsecret"),
    ])
    def test_key_value_and_auth_secrets(self, line, leak):
        assert leak not in redact(line)

    def test_normal_log_lines_are_untouched(self):
        line = '172.18.0.3 - - "GET /health HTTP/1.1" 503 45'
        assert redact(line) == line

    def test_evidence_is_redacted_recursively(self):
        ev = build_evidence(
            "c", "http://flask-app:5000/health", FAILED_CHECKS, [],
            {"logs": "token=supersecretvalue\nDISCORD https://discord.com/api/webhooks/1/abc",
             "container_state": {"error": "password=p4ss"}},
        )
        dumped = json.dumps(ev)
        for leak in ("supersecretvalue", "webhooks/1/abc", "p4ss"):
            assert leak not in dumped

    def test_prompt_sent_to_api_contains_no_secrets(self):
        client = FakeClient(text=json.dumps(VALID))
        ev = build_evidence("c", "u", FAILED_CHECKS, [], {"logs": "ANTHROPIC_API_KEY=sk-ant-api03-zzzzzzzzzzzz"})
        request_diagnosis(ev, client=client)
        sent = json.dumps(client.calls[0]["messages"])
        assert "sk-ant-api03" not in sent


# ─────────────────────────────────────────────
# API call, failures, timeouts, fallback
# ─────────────────────────────────────────────

class TestRequestDiagnosis:
    def test_success_and_request_shape(self):
        client = FakeClient(text=json.dumps(VALID))
        d = request_diagnosis(evidence(), client=client, model="claude-opus-5-5")
        assert d["severity"] == "medium"
        call = client.calls[0]
        assert call["model"] == "claude-opus-5-5"
        assert call["output_config"]["format"]["type"] == "json_schema"
        assert call["output_config"]["format"]["schema"] == ai_diagnosis.DIAGNOSIS_SCHEMA
        assert call["fallbacks"] == "default"
        assert "<evidence>" in call["messages"][0]["content"]

    def test_fallbacks_not_sent_for_other_models(self):
        client = FakeClient(text=json.dumps(VALID))
        request_diagnosis(evidence(), client=client, model="claude-haiku-5-5")
        assert "fallbacks" not in client.calls[0]
        assert "betas" not in client.calls[0]

    def test_refusal_raises(self):
        with pytest.raises(DiagnosisError, match="declined"):
            request_diagnosis(evidence(), client=FakeClient(text="", stop_reason="refusal"))

    def test_truncation_raises(self):
        with pytest.raises(DiagnosisError, match="truncated"):
            request_diagnosis(evidence(), client=FakeClient(text="{", stop_reason="max_tokens"))

    def test_no_text_block_raises(self):
        with pytest.raises(DiagnosisError):
            request_diagnosis(evidence(), client=FakeClient(content=[]))


class TestDiagnoseNeverRaises:
    def test_ok(self):
        r = diagnose(evidence(), client=FakeClient(text=json.dumps(VALID)), timeout=5)
        assert r["ok"] is True
        assert r["diagnosis"]["severity"] == "medium"

    def test_api_exception(self):
        r = diagnose(evidence(), client=FakeClient(exc=ConnectionError("API unreachable")), timeout=5)
        assert r["ok"] is False
        assert "API unreachable" in r["error"]

    def test_malformed_response(self):
        r = diagnose(evidence(), client=FakeClient(text="I think the server crashed."), timeout=5)
        assert r["ok"] is False
        assert "not valid JSON" in r["error"]

    def test_hard_timeout(self):
        start = time.time()
        r = diagnose(evidence(), client=FakeClient(text=json.dumps(VALID), delay=10), timeout=0.2)
        assert r["ok"] is False
        assert "Timed out" in r["error"]
        assert time.time() - start < 5  # did not wait for the hung call

    def test_error_messages_are_redacted(self):
        exc = RuntimeError("401 invalid x-api-key sk-ant-api03-leakedleakedleaked")
        r = diagnose(evidence(), client=FakeClient(exc=exc), timeout=5)
        assert "leakedleaked" not in r["error"]

    def test_missing_sdk_is_handled(self, monkeypatch):
        def boom(_timeout):
            raise ImportError("No module named 'anthropic'")
        monkeypatch.setattr(ai_diagnosis, "_create_client", boom)
        r = diagnose(evidence(), client=None, timeout=5)
        assert r["ok"] is False
        assert "anthropic" in r["error"]


# ─────────────────────────────────────────────
# Embed building
# ─────────────────────────────────────────────

class TestIncidentEmbed:
    def _total_len(self, embed):
        return len(embed["title"]) + len(embed["description"]) + sum(
            len(f["name"]) + len(f["value"]) for f in embed["fields"])

    def test_embed_with_diagnosis(self):
        ai = {"ok": True, "diagnosis": parse_diagnosis(VALID), "duration": 3.2}
        e = build_incident_embed("flask-devops-app", FAILED_CHECKS, ai,
                                 {"restarted": True, "recovered": True, "recovery_time": 12.5}, 1, 5)
        names = [f["name"] for f in e["fields"]]
        assert any("Failure details" in n for n in names)
        assert any("Likely cause" in n for n in names)
        assert any("Recommended action" in n for n in names)
        assert any("Final recovery status" in n for n in names)
        assert "MEDIUM" in e["description"]
        assert "Recovered" in e["fields"][-1]["value"]
        assert "503" in e["fields"][0]["value"]
        assert e["color"] == ai_diagnosis.SEVERITY_COLORS["medium"]

    def test_embed_without_diagnosis(self):
        ai = {"ok": False, "error": "Timed out after 30s", "duration": 30}
        e = build_incident_embed("c", FAILED_CHECKS, ai, {"restarted": True, "recovered": False}, 2, 5)
        assert "unavailable" in e["description"]
        assert "Timed out" in e["description"]
        assert "Not recovered" in e["fields"][-1]["value"]

    def test_embed_respects_discord_limits(self):
        big = {**VALID, "supporting_evidence": ["e" * 400] * 10, "recommended_remediation": ["r" * 400] * 10}
        ai = {"ok": True, "diagnosis": parse_diagnosis(big), "duration": 1}
        e = build_incident_embed("c", FAILED_CHECKS, ai, {"restarted": True, "recovered": True}, 1, 5)
        assert all(len(f["value"]) <= 1024 for f in e["fields"])
        assert self._total_len(e) <= 6000


# ─────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────

class TestWorker:
    def _worker(self, client, notify, **kw):
        return IncidentDiagnosisWorker(
            "flask-devops-app", "http://flask-app:5000/health", FAILED_CHECKS, [],
            notify=notify, client=client, collect=fake_collect, **kw)

    def test_start_returns_immediately_even_if_api_is_slow(self):
        w = self._worker(FakeClient(text=json.dumps(VALID), delay=1.0), notify=lambda e: None, timeout=5)
        start = time.time()
        w.start()
        assert time.time() - start < 0.2
        w.report_recovery(restarted=True, recovered=True, recovery_time=5)
        assert w.done.wait(5)

    def test_sends_report_after_recovery_outcome(self):
        sent = []
        w = self._worker(FakeClient(text=json.dumps(VALID)), notify=sent.append, timeout=5).start()
        time.sleep(0.2)
        assert sent == []  # waits for the recovery outcome
        w.report_recovery(restarted=True, recovered=True, recovery_time=7.0, restart_count=1)
        assert w.done.wait(5)
        assert len(sent) == 1
        assert "7.0s" in sent[0]["fields"][-1]["value"]

    def test_api_failure_still_sends_fallback_report(self):
        sent = []
        w = self._worker(FakeClient(exc=TimeoutError("read timed out")), notify=sent.append, timeout=5).start()
        w.report_recovery(restarted=True, recovered=True, recovery_time=3)
        assert w.done.wait(5)
        assert "unavailable" in sent[0]["description"]

    def test_notify_and_collect_errors_never_escape(self):
        def broken_notify(_):
            raise RuntimeError("discord down")

        def broken_collect(_):
            raise RuntimeError("docker socket missing")

        w = IncidentDiagnosisWorker("c", "u", FAILED_CHECKS, [], notify=broken_notify,
                                    client=FakeClient(text=json.dumps(VALID)), collect=broken_collect)
        w.start()
        w.report_recovery(restarted=True, recovered=True)
        assert w.done.wait(5)

    def test_reports_even_if_outcome_never_arrives(self):
        sent = []
        w = self._worker(FakeClient(text=json.dumps(VALID)), notify=sent.append,
                         timeout=5, outcome_wait=0.1).start()
        assert w.done.wait(5)
        assert "unknown" in sent[0]["fields"][-1]["value"]


# ─────────────────────────────────────────────
# Integration with monitor.handle_failure — AI never delays recovery
# ─────────────────────────────────────────────

@pytest.fixture
def monitor_env(monkeypatch):
    import monitor
    events = []
    monkeypatch.setattr(monitor, "_session_restart_count", 0)
    monkeypatch.setattr(monitor, "_restart_history", monitor.deque(maxlen=10))
    monkeypatch.setattr(monitor, "restart_container",
                        lambda name: events.append(("restart", time.time())) or True)
    monkeypatch.setattr(monitor, "wait_for_recovery", lambda timeout: True)
    monkeypatch.setattr(monitor, "send_discord_notification",
                        lambda title, description, color: events.append(("alert", title)))
    monkeypatch.setattr(monitor, "send_discord_embed", lambda embed: events.append(("ai_report", embed)))
    return monitor, events


FAIL_RESULT = {"healthy": False, "status": "UNHEALTHY", "http_code": 503, "body": {}}


class TestMonitorIntegration:
    def test_ai_disabled_preserves_standard_flow(self, monitor_env, monkeypatch):
        monitor, events = monitor_env
        monkeypatch.setattr(ai_diagnosis, "ANTHROPIC_API_KEY", "")
        monitor.handle_failure(FAIL_RESULT, FAILED_CHECKS)
        kinds = [e[0] for e in events]
        assert kinds == ["restart", "alert", "alert"]
        assert events[1][1] == "🚨 Service Failure Detected"
        assert events[2][1] == "✅ Service Recovered Successfully"
        assert monitor._session_restart_count == 1
        assert monitor._restart_history[-1]["recovered"] is True

    def test_slow_ai_does_not_delay_restart(self, monitor_env, monkeypatch):
        monitor, events = monitor_env
        monkeypatch.setattr(ai_diagnosis, "ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_diagnosis, "AI_DIAGNOSIS", True)
        slow = FakeClient(text=json.dumps(VALID), delay=1.5)
        monkeypatch.setattr(ai_diagnosis, "_create_client", lambda timeout: slow)
        monkeypatch.setattr(ai_diagnosis, "collect_docker_evidence", fake_collect)

        start = time.time()
        monitor.handle_failure(FAIL_RESULT, FAILED_CHECKS)
        elapsed = time.time() - start

        assert elapsed < 1.0, "handle_failure waited for the AI call"
        restart_at = next(t for k, t in events if k == "restart")
        assert restart_at - start < 0.5
        assert [k for k, _ in events][:3] == ["restart", "alert", "alert"]

        # The AI report arrives later, independently
        deadline = time.time() + 5
        while time.time() < deadline and not any(k == "ai_report" for k, _ in events):
            time.sleep(0.05)
        report = next(e for k, e in events if k == "ai_report")
        assert "MEDIUM" in report["description"]
        assert "Recovered" in report["fields"][-1]["value"]

    def test_ai_crash_does_not_affect_recovery(self, monitor_env, monkeypatch):
        monitor, events = monitor_env
        monkeypatch.setattr(ai_diagnosis, "ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_diagnosis, "AI_DIAGNOSIS", True)

        def explode(*a, **kw):
            raise RuntimeError("worker could not start")
        monkeypatch.setattr(ai_diagnosis, "IncidentDiagnosisWorker", explode)

        monitor.handle_failure(FAIL_RESULT, FAILED_CHECKS)
        assert [k for k, _ in events] == ["restart", "alert", "alert"]

    def test_restart_failure_reported_to_ai(self, monitor_env, monkeypatch):
        monitor, events = monitor_env
        monkeypatch.setattr(monitor, "restart_container", lambda name: False)
        monkeypatch.setattr(ai_diagnosis, "ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(ai_diagnosis, "AI_DIAGNOSIS", True)
        monkeypatch.setattr(ai_diagnosis, "_create_client",
                            lambda timeout: FakeClient(exc=ConnectionError("offline")))
        monkeypatch.setattr(ai_diagnosis, "collect_docker_evidence", fake_collect)

        monitor.handle_failure(FAIL_RESULT, FAILED_CHECKS)
        titles = [v for k, v in events if k == "alert"]
        assert "❌ Container Restart Failed" in titles

        deadline = time.time() + 5
        while time.time() < deadline and not any(k == "ai_report" for k, _ in events):
            time.sleep(0.05)
        report = next(e for k, e in events if k == "ai_report")
        assert "unavailable" in report["description"]
        assert "Restart failed" in report["fields"][-1]["value"]
