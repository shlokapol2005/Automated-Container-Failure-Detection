# Automated Container Failure Detection, Self-Recovery & Notification

A DevOps mini-project that implements an automated software delivery pipeline and a self-healing container monitoring system using Docker, GitHub Actions, Prometheus, Grafana, and Discord — with optional **AIOps incident diagnosis** powered by the Claude API.

## Overview

Container failures can interrupt application availability and require manual intervention. This project demonstrates a system that monitors a containerized Flask application, detects consecutive health-check failures, automatically restarts the affected container, verifies recovery, and sends incident notifications through Discord.

The project also implements a CI/CD pipeline that automates testing, Docker image building, and publishing to Docker Hub.

## Features

- **Version Control:** Git and GitHub for source-code management.
- **Automated Testing:** pytest test suite for application endpoints and behavior.
- **Containerization:** Docker image using Flask and Gunicorn.
- **CI/CD Pipeline:** GitHub Actions automates testing, image building, and Docker Hub publishing.
- **Health Monitoring:** Python monitor periodically checks application health.
- **Failure Detection:** Detects two consecutive unhealthy health checks before initiating recovery.
- **Automatic Recovery:** Uses the Docker SDK to restart the application container.
- **Recovery Verification:** Checks whether the application returns to a healthy state within a configured timeout.
- **Metrics and Observability:** Prometheus collects application metrics, and Grafana provides visualization.
- **Discord Notifications:** Sends alerts when a failure is detected and when recovery succeeds or fails.
- **Failure Simulation:** Provides an endpoint to simulate an unhealthy state for controlled testing.
- **AIOps Incident Diagnosis (optional):** After a confirmed failure, collects Docker logs, HTTP status, timestamps, and restart history, redacts secrets, and asks Claude for a structured diagnosis (likely cause, supporting evidence, severity, recommended remediation). The result is sent as an enhanced Discord embed together with the final recovery status. AI runs on a background thread and **never controls or delays recovery**.

## Architecture

```text
Developer
    |
    v
Git Push to GitHub
    |
    v
GitHub Actions
    |
    +--> Automated Tests
    |
    +--> Docker Build and Smoke Test
              |
              v
          Docker Hub

Local Environment
    |
    v
Docker Compose
    |
    +--> Flask Application
    |        |
    |        +--> /health
    |        +--> /metrics
    |
    +--> Python Health Monitor (monitor.py)              [main thread — deterministic]
    |        |
    |        +--> Detect 2 consecutive failures
    |        +--> Restart container using Docker SDK  (immediately)
    |        +--> Verify recovery
    |        +--> Send standard Discord notifications
    |        |
    |        +--> AIOps worker (ai_diagnosis.py)          [background thread — advisory only]
    |                 |
    |                 +--> Collect evidence: Docker logs, container state,
    |                 |    HTTP status + timestamps, restart history
    |                 +--> Redact secrets (keys, tokens, webhooks, passwords, e-mails)
    |                 +--> Claude API → structured JSON diagnosis (timeout-bounded)
    |                 +--> Wait for recovery outcome from main thread
    |                 +--> Send enhanced "AIOps Incident Report" Discord embed
    |                      (falls back to "AI diagnosis unavailable" on any error)
    |
    +--> Prometheus
    |
    +--> Grafana
```

## Technology Stack

| Component | Technology |
|---|---|
| Application | Python, Flask |
| Application server | Gunicorn |
| Testing | pytest |
| Containerization | Docker |
| Multi-container deployment | Docker Compose |
| CI/CD | GitHub Actions |
| Container registry | Docker Hub |
| Monitoring and recovery | Python, Docker SDK |
| Metrics collection | Prometheus |
| Dashboards | Grafana |
| Notifications | Discord Webhooks |
| AIOps diagnosis (optional) | Claude API (`anthropic` Python SDK) |
| Version control | Git, GitHub |

## Application Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Displays application information |
| `/health` | GET | Returns application health and uptime |
| `/metrics` | GET | Exposes metrics for Prometheus |
| `/simulate-failure` | POST | Simulates an unhealthy application state |
| `/reset` | POST | Resets the simulated failure state |

The failure simulation endpoint is intended for development and demonstration purposes.

## How Self-Recovery Works

1. The Python monitor periodically requests the application's `/health` endpoint.
2. If two consecutive checks fail, the monitor declares a failure.
3. If AIOps is enabled, a background diagnosis worker is started (this returns instantly).
4. The monitor **immediately** restarts the container using the Docker SDK.
5. A Discord notification reports the detected incident.
6. The monitor polls the application until recovery is verified or the timeout expires.
7. A Discord notification reports the recovery outcome (and an escalation alert after `MAX_RESTARTS`).
8. The recovery outcome is handed to the AIOps worker, which sends the enhanced incident report.

This controlled workflow demonstrates automated incident detection and recovery without requiring manual container restarts.

## AIOps Intelligent Incident Diagnosis

Implemented in [`monitor/ai_diagnosis.py`](monitor/ai_diagnosis.py) and wired into `handle_failure()` in [`monitor/monitor.py`](monitor/monitor.py).

**Evidence sent to Claude** (after redaction):

| Evidence | Source |
|---|---|
| Last `AI_LOG_LINES` container log lines (with timestamps) | Docker SDK `container.logs()` |
| Container state: status, exit code, OOM-killed, Docker health, restart count | Docker SDK `container.attrs` |
| The two failed health checks: timestamp, HTTP status, API status, body | Monitor |
| Recent restart history: time, success, recovered, recovery time | Monitor |

**Structured output** (enforced with a JSON schema via `output_config.format`, then validated by `parse_diagnosis()`):

```json
{
  "likely_cause": "The app's health flag was set to UNHEALTHY via POST /simulate-failure ...",
  "supporting_evidence": ["Two consecutive HTTP 503 at 10:00:05 and 10:00:15", "..."],
  "severity": "low | medium | high | critical",
  "recommended_remediation": ["Restrict /simulate-failure to test environments", "..."],
  "confidence": "low | medium | high"
}
```

**Discord output** — one extra embed, *AIOps Incident Report*, colour-coded by severity, with fields: Failure details · Likely cause · Supporting evidence · Recommended action · Final recovery status.

**Safety guarantees**

- The restart is deterministic and issued before (and independently of) any AI work. AI output is only displayed — never executed or used for decisions.
- The AI call has a hard wall-clock deadline (`AI_TIMEOUT`). Missing key, missing SDK, network errors, rate limits, refusals, malformed JSON, and timeouts all degrade to an *"AI diagnosis unavailable"* note — standard alerts are unaffected.
- Secrets are redacted from logs and evidence **before** they leave the host, and again from the model's reply.
- Container logs are treated as untrusted data in the prompt (prompt-injection guard).

**Configuration** (all optional — see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Claude API key. Empty → AIOps disabled, monitor behaves exactly as before |
| `AI_DIAGNOSIS` | `true` | Master switch |
| `AI_MODEL` | `claude-opus-5-5` | Claude model used for diagnosis |
| `AI_EFFORT` | `low` | `low` / `medium` / `high` — lower is faster and cheaper |
| `AI_TIMEOUT` | `30` | Seconds before the AI call is abandoned |
| `AI_LOG_LINES` | `100` | Number of container log lines sent as evidence |

## CI/CD Workflow

The GitHub Actions pipeline automates the delivery process:

1. A push to the configured branch triggers the workflow.
2. Automated tests execute.
3. The Docker image is built and smoke-tested.
4. If the required checks pass, the image is published to Docker Hub.
5. The image is tagged for identification and reuse.

Docker Hub publishing requires repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

The latest GitHub Actions run should be checked to confirm the pipeline succeeds.

## Getting Started

### Prerequisites

- Git
- Docker Desktop with Docker Compose
- Python 3.11 or a compatible configured Python environment
- GitHub account
- Docker Hub account
- Discord webhook for notifications

### 1. Clone the repository

```bash
git clone https://github.com/shlokapol2005/Automated-Container-Failure-Detection.git
cd Automated-Container-Failure-Detection
```

### 2. Configure environment variables

Create a local `.env` file from the provided template:

```powershell
Copy-Item .env.example .env
```

Configure the Discord webhook and other required variables in `.env`. Never commit actual credentials or webhook URLs.

To enable AIOps diagnosis, also set `ANTHROPIC_API_KEY` (create one at https://platform.claude.com). Leave it empty to run without AI.

### 3. Start the application stack

```powershell
docker compose up -d --build
```

Check the running services:

```powershell
docker compose ps
```

### 4. Verify application health

```powershell
Invoke-WebRequest http://localhost:5000/health -UseBasicParsing
```

A healthy application should return HTTP 200 and report `HEALTHY`.

### 5. Open monitoring interfaces

| Service | URL |
|---|---|
| Application health | http://localhost:5000/health |
| Application metrics | http://localhost:5000/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Dashboard availability depends on the current Grafana provisioning configuration.

## Running Tests

Run the test suite locally:

```powershell
pip install -r app/requirements.txt
python -m pytest tests/ -v
```

`tests/test_ai_diagnosis.py` covers diagnosis parsing, secret redaction, API failures, refusals, timeouts, the background worker, the fallback embed, and proves that a slow or crashing AI call never delays the restart. These tests use fakes — no Docker daemon, network, API key, or `anthropic` package is required.

The GitHub Actions workflow also runs automated checks. Refer to its latest successful run for the verified test count and results.

## Demonstrating Failure Recovery

Open a terminal and follow the monitor logs:

```powershell
docker compose logs -f monitor
```

In a second terminal, simulate a failure:

```powershell
Invoke-RestMethod -Uri http://localhost:5000/simulate-failure -Method POST
```

Observe the monitor detect consecutive unhealthy checks, restart the container, verify recovery, and send Discord notifications. With `ANTHROPIC_API_KEY` set, a third Discord message — **🤖 AIOps Incident Report** — arrives with the AI diagnosis and the final recovery status.

Verify that the application has recovered:

```powershell
Invoke-WebRequest http://localhost:5000/health -UseBasicParsing
```

## Security Considerations

- Store webhook URLs and credentials in environment variables.
- Keep `.env` out of version control.
- Restrict Docker socket access because it provides significant control over the Docker daemon.
- Keep failure simulation endpoints restricted to testing environments.
- Avoid exposing sensitive information in application logs or notifications.
- Container logs are redacted (API keys, tokens, JWTs, webhook URLs, passwords, URL credentials, e-mails) before being sent to the Claude API.
- If a webhook URL or API key is ever pasted somewhere public, rotate it immediately.

## Future Enhancements

- Recovery-time metrics and historical incident reporting (e.g. export AI severity to Prometheus).
- Feed past incident reports back to the diagnosis as additional context.
- Enhanced alert escalation for repeated or unsuccessful recovery attempts.

