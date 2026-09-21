# SETUP GUIDE
## Automated Container Failure Detection, Self-Recovery and Notification
### Step-by-step instructions for setup, running, and viva demonstration

---

## PRE-REQUISITES

Install the following before starting:

| Tool | Download |
|---|---|
| Git | https://git-scm.com |
| Python 3.11+ | https://python.org |
| Docker Desktop | https://docker.com/products/docker-desktop |
| A Discord account | https://discord.com |

Verify installations:
```bash
git --version
python --version
docker --version
docker compose version
```

---

## STEP 1 — Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `devops-labca`
3. Set it to **Public**
4. Do NOT initialize with README (you already have one)

---

## STEP 2 — Set Up GitHub Secrets

These are used by GitHub Actions to push to Docker Hub securely.

1. Go to your Docker Hub account → **Account Settings → Security → New Access Token**
2. Name it `github-actions-token`, copy the token
3. Go to your GitHub repository → **Settings → Secrets and variables → Actions**
4. Add these two secrets:
   - `DOCKERHUB_USERNAME` → your Docker Hub username
   - `DOCKERHUB_TOKEN` → the token you just copied

---

## STEP 3 — Create Discord Webhook

1. Open Discord → go to your server
2. Right-click the channel you want notifications in → **Edit Channel**
3. Go to **Integrations → Webhooks → New Webhook**
4. Name it `DevOps Monitor`
5. Click **Copy Webhook URL**
6. Save this URL — you will add it to your `.env` file

---

## STEP 4 — Configure Environment Variables

```bash
# In the project root directory:
cp .env.example .env
```

Open `.env` and replace the placeholder:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

Leave all other values as their defaults for now.

---

## STEP 5 — Push Code to GitHub

```bash
cd devops-labca

git init
git add .
git commit -m "Initial commit: Flask DevOps project"
git branch -M main
git remote add origin https://github.com/<your-username>/devops-labca.git
git push -u origin main
```

This push will automatically trigger the GitHub Actions CI/CD pipeline.

---

## STEP 6 — Verify GitHub Actions Pipeline

1. Go to your GitHub repository
2. Click the **Actions** tab
3. You should see a workflow run called **CI/CD Pipeline**
4. Watch it progress through:
   - ✅ Run Automated Tests
   - ✅ Build & Push Docker Image
5. After success, check Docker Hub — you should see `<username>/flask-devops-app:latest`

---

## STEP 7 — Local Deployment with Docker Compose

### Option A: Build locally (no Docker Hub pull needed)
```bash
docker compose up -d --build
```

### Option B: Pull from Docker Hub (after CI/CD push)
```bash
# Edit docker-compose.yml — change image line to your Docker Hub image:
# image: yourusername/flask-devops-app:latest

docker compose up -d
```

Verify the container is running:
```bash
docker ps
docker logs flask-devops-app
```

Test the endpoints:
```bash
curl http://localhost:5000/
curl http://localhost:5000/health
```

Expected response from `/health`:
```json
{
  "status": "HEALTHY",
  "uptime_seconds": 12.34,
  "message": "Application is running normally"
}
```

---

## STEP 8 — Run Tests Locally

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run all 20 tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing
```

All 20 tests should pass with green output.

---

## STEP 9 — Start the Health Monitor

Open a **second terminal window** and run:

```bash
# Load environment variables (Windows PowerShell)
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]*)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
python monitor/monitor.py

# OR on Linux/macOS:
export $(grep -v '^#' .env | xargs)
python monitor/monitor.py
```

You should see:
```
=================================================================
  DevOps Health Monitor
  Automated Container Failure Detection & Self-Recovery
=================================================================
[INFO  ] Health URL      : http://localhost:5000/health
[INFO  ] Container name  : flask-devops-app
[INFO  ] Check interval  : 10s
[INFO  ] Discord alerts  : ENABLED
=================================================================

[2026-09-21 21:00:00] [OK    ] ✅  HEALTHY — HTTP 200 | uptime=45.2s
[2026-09-21 21:00:10] [OK    ] ✅  HEALTHY — HTTP 200 | uptime=55.3s
```

---

## STEP 10 — Trigger Failure (Demonstration)

In a **third terminal window**, trigger the simulated failure:

```bash
curl -X POST http://localhost:5000/simulate-failure
```

Response:
```json
{
  "message": "Failure simulation ACTIVATED",
  "info": "The /health endpoint will now return UNHEALTHY (HTTP 503)"
}
```

Watch the **monitor terminal** — within 20 seconds you will see:
```
[WARN  ] ⚠️  Check #1: UNHEALTHY — HTTP 503
[WARN  ] ⚠️  Check #2: UNHEALTHY — HTTP 503
[ERROR ] ❌  FAILURE DETECTED — HTTP 503 | status=UNHEALTHY
[ACTION] 🔄  Restarting container 'flask-devops-app' ...
[OK    ] ✅  Container 'flask-devops-app' restart command accepted
[ACTION] 🔄  Waiting up to 60s for service to recover ...
[INFO  ] ℹ️   Recovery attempt #1 → HEALTHY (timeout in 55s)
[OK    ] ✅  Service has RECOVERED successfully ✅
```

Check Discord — you will receive three notifications:
1. 🚨 Service Failure Detected
2. ✅ Service Recovered Successfully

---

## VIVA DEMONSTRATION SCRIPT

Follow this sequence during the viva:

### 1. GitHub Repository
> "This is our GitHub repository. All code is version-controlled here. Every push triggers our CI/CD pipeline automatically."

### 2. Source Code
> "The application is a Flask REST API. The /health endpoint reports application health — HEALTHY or UNHEALTHY. We have a /simulate-failure endpoint to intentionally trigger failure for this demonstration."

### 3. Automated Tests
```bash
pytest tests/ -v
```
> "We have 20 automated tests covering all endpoints including the failure simulation. These all run in GitHub Actions before any Docker image is built."

### 4. GitHub Actions
> "Here in the Actions tab you can see our CI/CD pipeline. It runs tests, builds the Docker image, and pushes it to Docker Hub automatically on every push."

### 5. Docker Hub
> "The image is pushed here to Docker Hub. This is our container registry. The CI/CD pipeline tags the image with :latest and a SHA tag."

### 6. Docker Compose Deployment
```bash
docker compose up -d
docker ps
```
> "We deploy locally using Docker Compose. Docker Compose manages the container lifecycle."

### 7. Running Container + Health Check
```bash
curl http://localhost:5000/health
```
> "The application is live and returning HEALTHY status."

### 8. Start Monitoring
```bash
python monitor/monitor.py
```
> "This is our monitoring script. It polls /health every 10 seconds. If two consecutive failures are detected, it automatically restarts the container."

### 9. Trigger Failure
```bash
curl -X POST http://localhost:5000/simulate-failure
```
> "I'm now triggering a simulated failure. The /health endpoint will immediately start returning HTTP 503 UNHEALTHY."

### 10. Show Automatic Recovery
> "Watch the monitor — it detects the failure, restarts the container, waits for it to recover, confirms health, and sends a Discord notification."

### 11. Discord Notification
> "And here in Discord we received the notification confirming the service was automatically recovered."

### 12. Summary
> "This project demonstrates the complete DevOps pipeline: version control with Git and GitHub, automated testing with pytest, containerisation with Docker, CI/CD with GitHub Actions, image registry with Docker Hub, local deployment with Docker Compose, health monitoring, automatic failure recovery, and alerting with Discord — all working together as an integrated system."

---

## TROUBLESHOOTING

### Container won't start
```bash
docker compose logs flask-devops-app
```

### Monitor can't connect to container
Make sure the container is running:
```bash
docker ps | grep flask-devops-app
```

### discord notification not sending
- Check that `.env` has the correct `DISCORD_WEBHOOK_URL`
- Make sure the environment is loaded before running the monitor

### GitHub Actions failing at Docker push
- Verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are set correctly
- The token must have Read & Write permissions

### Tests failing
```bash
# Make sure you're running from the project root
pytest tests/ -v
```
