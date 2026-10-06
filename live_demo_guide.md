# 🎬 Live Demo Guide — DevOps Mini Project
## Automated Container Failure Detection, Self-Recovery & Notification

---

## 🗂️ What You've Built (30-second pitch)

> A **Flask REST API** containerized with Docker, with:
> - ✅ **Automated tests** (pytest, 15 test cases)
> - ✅ **CI/CD pipeline** (GitHub Actions → Docker Hub)
> - ✅ **Health monitoring** script that detects failures and **auto-restarts** the container
> - ✅ **Discord alerts** sent on failure and recovery

---

## 🚀 Step 1 — Start Everything (Do this BEFORE the demo)

Open **two terminal windows** side by side.

### Terminal 1 — Start the Flask container
```powershell
cd "C:\Users\Shloka Pol\OneDrive\Desktop\devops-labca"
docker-compose up --build -d
```
Wait ~15 seconds for the container to be healthy. Verify:
```powershell
docker ps
```
You should see `flask-devops-app` with status `Up`.

### Terminal 2 — Start the Monitor (with Discord alerts)
```powershell
cd "C:\Users\Shloka Pol\OneDrive\Desktop\devops-labca"
$env:DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"
python monitor/monitor.py
```
> [!IMPORTANT]
> Replace `YOUR_DISCORD_WEBHOOK_URL_HERE` with your actual Discord webhook URL.
> If you don't have one, you can still run the monitor — it will just skip Discord and log to the terminal.

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

### 🟡 Scene 4: Show GitHub Actions CI/CD (2 min)

Open GitHub → your repo → **Actions tab**

Show the pipeline stages:
1. ✅ **Run Automated Tests** — runs all 15 pytest cases
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

Output shows 15 tests across 4 classes:
- `TestIndexEndpoint` (5 tests)
- `TestHealthEndpoint` (5 tests)
- `TestSimulateFailureEndpoint` (6 tests)
- `TestResetEndpoint` (4 tests)

**What to say:**
> *"We have 15 automated test cases covering every endpoint and scenario — including the failure simulation and recovery flow. These run automatically in GitHub Actions on every push."*

---

## 🧹 Step 3 — Clean Up After Demo

```powershell
docker-compose down
```

---

## 💡 Talking Points (If Asked Questions)

| Question | Answer |
|----------|--------|
| *Why 2 consecutive failures before restart?* | Avoids false positives — a single slow response shouldn't trigger a restart |
| *What if Docker itself crashes?* | The monitor would log `UNREACHABLE` — a production system would use orchestration like Kubernetes |
| *Why Discord alerts?* | In production, you'd use PagerDuty or Slack. Discord is free and instant for demo purposes |
| *Why not just use Docker's own restart policy?* | Docker's `restart: unless-stopped` just restarts — our monitor adds *detection*, *notification*, and *recovery verification* |
| *What does the CI/CD pipeline gate?* | The Docker image is only pushed if ALL 15 tests pass — broken code never reaches Docker Hub |

---

## ⚡ Quick Commands Cheat Sheet

```powershell
# Start everything
docker-compose up -d

# Check container status
docker ps

# Check app health
Invoke-WebRequest http://localhost:5000/health | Select-Object -ExpandProperty Content

# Trigger failure
Invoke-WebRequest -Uri http://localhost:5000/simulate-failure -Method POST

# Reset manually (without restart)
Invoke-WebRequest -Uri http://localhost:5000/reset -Method POST

# Run tests
pytest tests/ -v

# Stop everything
docker-compose down
```
