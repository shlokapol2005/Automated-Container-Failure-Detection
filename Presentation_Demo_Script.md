# 🎬 Live Demo Script — Automated Container Recovery

This guide gives you the exact commands to run, when to run them, and what to say to your audience while presenting your project.

---

## 🛠️ Prep (Do this 5 minutes before the demo)
Make sure Docker Desktop is running. Open your terminal in the project folder and run:
```powershell
docker compose down -v
docker compose up -d --build
```
This ensures a completely fresh, working environment.

---

## 🎭 The Live Demo Sequence

### Scene 1: Introduce the Architecture (1 min)
*Have your browser open to `http://localhost:5000` (the Flask app).*

**What to do:**
Show the browser tab running the app, then show `http://localhost:5000/health`.

**What to say:**
> *"For my project, I built a complete containerized DevOps stack. 
> At the core is a Flask REST API running in a Docker container. Right now, if we look at the `/health` endpoint, it's returning a 200 OK and says `HEALTHY`.
> But in the real world, containers crash or hang. To solve this, I built a custom health monitor that watches this endpoint and automatically recovers the system when it fails."*

---

### Scene 2: Show the Observability Dashboard (1.5 min)
*Open a new browser tab to `http://localhost:3000` (Grafana).*
*Go to Dashboards -> DevOps Monitoring.*

**What to do:**
Point to the live graphs (Uptime, Health Status, Requests).

**What to say:**
> *"Before we break the app, let's look at the observability stack. 
> I integrated Prometheus and Grafana. Prometheus scrapes metrics from the Flask app every 10 seconds. 
> This Grafana dashboard is automatically provisioned via Infrastructure as Code. You can see our app is currently healthy (Status 1) and the uptime is climbing."*

---

### Scene 3: The Failure Simulation & Auto-Recovery (3 min) — 🌟 The WOW Moment
*Have your Terminal open and visible on screen.*

**What to do:**
First, start tailing the monitor logs so the audience can see it watching the app:
```powershell
docker compose logs -f monitor
```
*(Wait a few seconds to let them see the `[OK] ✅ HEALTHY` logs ticking by)*

**What to say:**
> *"Here we can see our custom Python monitor polling the container every 10 seconds. Let's simulate a production failure."*

**What to do:**
Open a second terminal window (or PowerShell tab) and run the failure command:
```powershell
Invoke-RestMethod -Uri http://localhost:5000/simulate-failure -Method POST
```
*(Switch back to the first terminal showing the monitor logs.)*

**What to say:**
> *"I just sent a POST request that artificially crashes the application's health. Watch the monitor logs."*

**What to do:**
Let the audience watch the logs. Point out the events as they happen:
1. `⚠️ Check #1: UNHEALTHY`
2. `⚠️ Check #2: UNHEALTHY`
3. `❌ FAILURE DETECTED`
4. `🔄 Restarting container 'flask-devops-app'`
5. `✅ Service has RECOVERED successfully`

**What to say:**
> *"The monitor requires two consecutive failures to prevent false positives. 
> It detected the failure, immediately sent an alert to Discord, and used the Docker socket to restart the container from the outside. 
> In just 5 seconds, it verified the container recovered and sent a resolution alert."*

**What to do:**
Open your Discord channel and show the two rich-embed notifications (the red failure alert, and the green recovery alert).

---

### Scene 4: CI/CD & Testing (1 min)
*Open your GitHub repository in the browser, go to the "Actions" tab.*

**What to do:**
Click on the latest successful workflow run.

**What to say:**
> *"This is all backed by a robust CI/CD pipeline built with GitHub Actions. 
> Every time code is pushed, it automatically runs 26 automated Pytest cases. 
> Only if all tests pass, the pipeline builds the Docker image and pushes it to Docker Hub, ensuring broken code never reaches production."*

---

### 💡 Pro-Tips for Q&A
If they ask you questions, here are your prepared answers:

* **Why wait for 2 failures?** *"To avoid restarting the container for a transient network blip. It prevents unnecessary downtime."*
* **How does the monitor restart it?** *"The monitor container has the host's `docker.sock` mounted to it, allowing it to issue Docker SDK commands to the host daemon."*
* **Why Discord?** *"In a real enterprise environment, this webhook would go to PagerDuty, Slack, or OpsGenie. Discord works identically and is great for demonstrating webhook integrations."*
