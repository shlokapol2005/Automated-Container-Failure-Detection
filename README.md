# Automated Container Failure Detection, Self-Recovery & Notification

A DevOps mini-project that implements an automated software delivery pipeline and a self-healing container monitoring system using Docker, GitHub Actions, Prometheus, Grafana, and Discord.

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
    +--> Python Health Monitor
    |        |
    |        +--> Detect consecutive failures
    |        +--> Restart container using Docker SDK
    |        +--> Verify recovery
    |        +--> Send Discord notifications
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
3. A Discord notification reports the detected incident.
4. The monitor restarts the container using the Docker SDK.
5. The monitor polls the application until recovery is verified or the timeout expires.
6. A Discord notification reports the recovery outcome.

This controlled workflow demonstrates automated incident detection and recovery without requiring manual container restarts.

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
python -m pytest tests/ -v
```

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

Observe the monitor detect consecutive unhealthy checks, restart the container, verify recovery, and send Discord notifications.

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

## Future Enhancements

- AI-assisted container log analysis and incident diagnosis.
- Improved failure categorization and remediation recommendations.
- Recovery-time metrics and historical incident reporting.
- Enhanced alert escalation for repeated or unsuccessful recovery attempts.

