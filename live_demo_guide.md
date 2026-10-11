# 🎬 Live Demo Guide — DevOps Mini Project
## Automated Container Failure Detection, Self-Recovery & Notification

---

## 🗂️ What You've Built (30-second pitch)

> A **Flask REST API** containerized with Docker, with:
> - ✅ **Automated tests** (pytest, 26 test cases across 5 test classes)
> - ✅ **CI/CD pipeline** (GitHub Actions → Docker Hub)
> - ✅ **Health monitoring** script that detects failures and **auto-restarts** the container
> - ✅ **Discord alerts** sent on failure and recovery
> - ✅ **AIOps incident diagnosis** — an LLM (Google Gemini, free tier) analyses logs + health/restart evidence and posts a structured diagnosis (cause, evidence, severity, remediation) to Discord, without ever delaying recovery

---

## 🚀 Step 1 — Start Everything (Do this BEFORE the demo)

Open **two terminal windows** side by side.

### Terminal 1 — Start the Flask container
```powershell
cd "C:\Users\Shloka Pol\OneDrive\Desktop\devops-labca"
docker compose up --build -d
```
Wait ~15 seconds for the container to be healthy. Verify:
```powershell
docker ps
```
You should see `flask-devops-app` with status `Up`.

### Terminal 2 — Start the Monitor (with Discord alerts)
```powershell
cd "C:\Users\Shloka Pol\OneDrive\Desktop\devops-labca"
docker compose logs -f monitor
```
> [!IMPORTANT]
> The monitor reads `DISCORD_WEBHOOK_URL` and `GEMINI_API_KEY` from `.env` (never paste them into commands or slides).
> Without a webhook it just logs to the terminal; without an API key it skips the AIOps report.
> Check the banner shows `AIOps diagnosis : ENABLED 🧠` before the demo.

---

## 🎭 Step 2 — Demo Script (Show in This Order)

### 🔵 Scene 1: Show the Running App (2 min)

Open browser → go to `http://localhost:5000`

Point out these endpoints (open each in browser or use curl):

| URL | What it shows |
|-----|--------------|
| `http://localhost:5000/` | Root — app is alive |
| `http://localhost:5000/health` | Health check — returns `HEALTHY` + uptime |

**What to say:**
> *"This is our Flask REST API running inside a Docker container. The `/health` endpoint is what the monitor watches — right now it returns `HEALTHY`."*

---

### 🟢 Scene 2: Show the Monitor Running (1 min)

Switch to **Terminal 2**. The output looks like:
```
=================================================================
  DevOps Health Monitor
  Automated Container Failure Detection & Self-Recovery
=================================================================
[2026-09-22 14:30:00] [OK    ] ✅  HEALTHY — HTTP 200 | uptime=45.2s
[2026-09-22 14:30:10] [OK    ] ✅  HEALTHY — HTTP 200 | uptime=55.3s
```

**What to say:**
> *"The monitor polls the `/health` endpoint every 10 seconds. As long as the app is healthy, it just logs `OK`."*

---

### 🔴 Scene 3: TRIGGER THE FAILURE ← This is the WOW moment (3 min)

Open a **third terminal** (or use PowerShell/curl):
```powershell
# Trigger simulated failure
Invoke-WebRequest -Uri http://localhost:5000/simulate-failure -Method POST | Select-Object -ExpandProperty Content
```

Or in browser: visit `http://localhost:5000/health` — it will now return `UNHEALTHY` (503).

**What to say:**
> *"I'm now simulating a production failure. The `/health` endpoint now returns HTTP 503 — UNHEALTHY."*

**Watch Terminal 2 — the monitor will:**
1. Log `WARN` on the first failure
2. Log `WARN` on the second failure
3. **Automatically restart the container** (`docker restart`)
4. Poll recovery attempts every 5 seconds
5. Confirm `HEALTHY` once recovered
6. Send **Discord notification** 🎉
7. Post the **🤖 AIOps Incident Report** (diagnosis was running in the background the whole time)

The terminal output during recovery looks like:
```
[14:31:20] [WARN  ] ⚠️  Check #1: UNHEALTHY — HTTP 503
[14:31:30] [WARN  ] ⚠️  Check #2: UNHEALTHY — HTTP 503
[14:31:30] [ERROR ] ❌  FAILURE DETECTED — HTTP 503 | status=UNHEALTHY
[14:31:30] [ACTION] 🔄  Restarting container 'flask-devops-app' ...
[14:31:31] [OK    ] ✅  Container 'flask-devops-app' restart command accepted
[14:31:31] [ACTION] 🔄  Waiting up to 60s for service to recover ...
[14:31:36] [INFO  ] ℹ️   Recovery attempt #1 → HEALTHY (timeout in 54s)
[14:31:36] [OK    ] ✅  Service has RECOVERED successfully ✅
```

---

### 🤖 Scene 3b: AIOps Incident Diagnosis (2 min)

Switch to Discord and open the **🤖 AIOps Incident Report** embed. Point out:

| Field | What it shows |
|---|---|
| Severity / Confidence | Colour-coded severity (low → critical) |
| 🚨 Failure details | HTTP status, API status, first and confirming failed-check timestamps |
| 🧠 Likely cause | The AI's root-cause hypothesis |
| 🔎 Supporting evidence | Log lines / status codes it based the answer on |
| 🛠️ Recommended action | Concrete remediation steps |
| 🔁 Final recovery status | Recovered in Xs / not recovered / restart failed |

**What to say:**
> *"When the monitor confirms a failure, it restarts the container immediately — that path is fully deterministic. In parallel, a background worker collects the last 100 log lines, container state, HTTP status, timestamps and restart history, redacts any secrets, and asks Google Gemini for a structured diagnosis. The AI is advisory only: it can't trigger or delay a restart."*

**Optional — prove the fallback (1 min):** set `AI_TIMEOUT=0.1` in `.env`, run `docker compose up -d monitor`, and trigger the failure again. Recovery and the standard alerts are identical; the AIOps embed now says **"AI diagnosis unavailable — Timed out"**. Set it back to `30` afterwards.

---

### 🟡 Scene 4: Show GitHub Actions CI/CD (2 min)

Open GitHub → your repo → **Actions tab**

Show the pipeline stages:
1. ✅ **Run Tests & Smoke Test** — runs the full pytest suite (app + AIOps) + live integration smoke test
2. ✅ **Build & Push Docker Image** — only runs if tests pass, pushes to Docker Hub

**What to say:**
> *"Every time I push to `main`, GitHub Actions automatically runs the tests. If they pass, it builds and pushes a new Docker image to Docker Hub. This is the CI/CD pipeline."*

---

### 🧪 Scene 5: Show the Tests (1 min)

Run tests live in Terminal 1:
```powershell
cd "C:\Users\Shloka Pol\OneDrive\Desktop\devops-labca"
pytest tests/ -v
```

Output shows 103 tests:
- `tests/test_app.py` — 26 tests across 5 classes:
  - `TestIndexEndpoint` (5 tests)
  - `TestHealthEndpoint` (5 tests)
  - `TestSimulateFailureEndpoint` (6 tests)
  - `TestResetEndpoint` (4 tests)
  - `TestMetricsEndpoint` (6 tests — covers Prometheus /metrics endpoint)
- `tests/test_ai_diagnosis.py` — 77 AIOps tests: Gemini + Claude providers, diagnosis parsing, secret redaction, API failures, refusals, timeouts, fallback embed, background worker, and *"slow AI never delays the restart"*

**What to say:**
> *"We have 26 automated test cases covering every endpoint and scenario — including the failure simulation, recovery flow, and the Prometheus metrics endpoint. CI also enforces a minimum 80% code coverage threshold. These run automatically in GitHub Actions on every push."*

---

## 🧹 Step 3 — Clean Up After Demo

```powershell
docker compose down
```

---

## 💡 Talking Points (If Asked Questions)

| Question | Answer |
|----------|--------|
| *Why 2 consecutive failures before restart?* | Avoids false positives — a single slow response shouldn't trigger a restart |
| *What if Docker itself crashes?* | The monitor would log `UNREACHABLE` — a production system would use orchestration like Kubernetes |
| *Why Discord alerts?* | In production, you'd use PagerDuty or Slack. Discord is free and instant for demo purposes |
| *Why not just use Docker's own restart policy?* | Docker's `restart: unless-stopped` just restarts — our monitor adds *detection*, *notification*, and *recovery verification* |
| *What does the CI/CD pipeline gate?* | The Docker image is only pushed if ALL tests pass — broken code never reaches Docker Hub |
| *What if the AI is wrong or the API is down?* | The AI never decides anything — the restart is deterministic and happens first. API errors/timeouts just produce an "AI diagnosis unavailable" note |
| *Does the AI cost money?* | No — it uses Google Gemini's free tier. Claude (paid) is supported as an alternative via `ANTHROPIC_API_KEY` |
| *Do you send secrets to the AI?* | No — logs are redacted (API keys, tokens, webhook URLs, passwords, e-mails) before they leave the host, and `.env` is never committed |
| *Why an LLM and not a rule-based classifier?* | Log messages are free text; an LLM can correlate log lines, status codes and restart history into a readable root-cause hypothesis. Structured JSON output keeps it machine-checkable |

---

## ⚡ Quick Commands Cheat Sheet

```powershell
# Start all 4 services (app + monitor + prometheus + grafana)
docker compose up -d --build

# Check all containers are running
docker ps

# Check app health
Invoke-WebRequest http://localhost:5000/health | Select-Object -ExpandProperty Content

# Check Prometheus metrics
Invoke-WebRequest http://localhost:5000/metrics | Select-Object -ExpandProperty Content

# Trigger failure
Invoke-WebRequest -Uri http://localhost:5000/simulate-failure -Method POST

# Watch monitor + AIOps logs
docker compose logs -f monitor

# Run only the AIOps tests
pytest tests/test_ai_diagnosis.py -v

# Reset manually (without restart)
Invoke-WebRequest -Uri http://localhost:5000/reset -Method POST

# Run tests
pytest tests/ -v

# Open Grafana dashboard in browser
Start-Process "http://localhost:3000"   # login: admin / admin

# Open Prometheus in browser
Start-Process "http://localhost:9090"

# Stop everything
docker compose down
```
