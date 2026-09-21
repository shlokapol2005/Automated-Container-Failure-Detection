# Automated Container Failure Detection, Self-Recovery and Notification
### DevOps Mini Project — Flask · Docker · GitHub Actions · Discord

---

## Project Overview

This project implements a complete DevOps pipeline demonstrating:

| Requirement | Implementation |
|---|---|
| Version Control | Git + GitHub |
| Working Application | Flask REST API |
| Application Build | pip install + Docker build |
| Automated Testing | pytest (20 tests) |
| Containerisation | Docker + Docker Compose |
| CI/CD Pipeline | GitHub Actions |
| Deployment | Docker Compose (local) |
| Health Monitoring | Custom Python monitor |
| Failure Detection | HTTP /health polling |
| Automatic Recovery | docker restart |
| Notification | Discord webhook |
| Documentation | README + SETUP_GUIDE |

---

## Architecture

```
Developer
    │
    ▼  git push
GitHub Repository
    │
    ▼
GitHub Actions CI/CD
    ├── Run pytest tests
    ├── Build Docker image
    └── Push to Docker Hub
              │
              ▼
        Docker Compose  (local laptop)
              │
              ▼
          Flask API
         /    \
        /      \
    GET /    GET /health
                │
                ▼
         Health Monitor (monitor.py)
                │
        ┌───────┴────────┐
        │                │
     HEALTHY          UNHEALTHY
        │                │
    Continue        docker restart
                         │
                    Wait for recovery
                         │
                    GET /health
                         │
                    HEALTHY again
                         │
                  Discord Notification
```

---

## Project Structure

```
devops-labca/
├── app/
│   ├── app.py               # Flask application
│   └── requirements.txt     # Python dependencies
├── tests/
│   ├── __init__.py
│   └── test_app.py          # pytest test suite (20 tests)
├── monitor/
│   └── monitor.py           # Health monitor + auto-recovery
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions pipeline
├── Dockerfile               # Container image definition
├── .dockerignore
├── docker-compose.yml       # Local deployment
├── pytest.ini               # Test configuration
├── .env.example             # Environment variable template
├── .gitignore
├── README.md                # This file
└── SETUP_GUIDE.md           # Step-by-step setup instructions
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/devops-labca.git
cd devops-labca
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your Discord webhook URL
```

### 3. Start with Docker Compose

```bash
docker compose up -d --build
```

### 4. Verify the application

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
```

### 5. Run the health monitor

```bash
# In a separate terminal
python monitor/monitor.py
```

### 6. Trigger failure (for demonstration)

```bash
curl -X POST http://localhost:5000/simulate-failure
```

Watch the monitor detect the failure, restart the container, confirm recovery, and send a Discord notification.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application status |
| GET | `/health` | Health check (used by monitor) |
| POST | `/simulate-failure` | **Trigger failure for demo** |
| POST | `/reset` | Clear failure flag manually |

---

## Running Tests

```bash
# Install dependencies
pip install -r app/requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## CI/CD Pipeline

Every `git push` to `main` triggers GitHub Actions:

1. **Checkout** source code
2. **Install** Python dependencies
3. **Run** pytest (all 20 tests must pass)
4. **Build** Docker image
5. **Push** image to Docker Hub

Configure these GitHub Secrets:
- `DOCKERHUB_USERNAME` — your Docker Hub username
- `DOCKERHUB_TOKEN` — Docker Hub access token

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | _(required)_ | Discord incoming webhook URL |
| `HEALTH_URL` | `http://localhost:5000/health` | Health check endpoint |
| `CONTAINER_NAME` | `flask-devops-app` | Docker container to restart |
| `CHECK_INTERVAL` | `10` | Seconds between health checks |
| `RECOVERY_TIMEOUT` | `60` | Max seconds to wait for recovery |

---

## Demonstration Flow

See **SETUP_GUIDE.md** for the complete step-by-step viva demonstration guide.

---

## Technologies Used

- **Python 3.11** + **Flask 3.0** — Web application
- **pytest** — Automated testing
- **Docker** + **Docker Compose** — Containerisation and deployment
- **GitHub Actions** — CI/CD pipeline
- **Docker Hub** — Container image registry
- **Discord Webhooks** — Failure and recovery notifications
