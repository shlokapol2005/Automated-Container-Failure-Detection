# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile
# Flask DevOps Mini Project
# Automated Container Failure Detection, Self-Recovery and Notification
# ─────────────────────────────────────────────────────────────────────────────

# Use official slim Python image for smaller image size
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Set environment variables
# PYTHONDONTWRITEBYTECODE  : Prevents Python from writing .pyc files
# PYTHONUNBUFFERED         : Ensures print/log output is sent straight to stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Install dependencies first (separate layer for Docker cache efficiency)
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ .

# Expose the application port
EXPOSE 5000

# Health check: Docker will automatically monitor container health
# - interval: check every 30 seconds
# - timeout: 10 second response deadline
# - retries: mark unhealthy after 3 consecutive failures
# - start-period: give the app 10 seconds to boot before first check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run the application using Gunicorn (production-grade WSGI server)
# - workers=2       : 2 worker processes (suitable for a small demo)
# - bind=0.0.0.0:5000 : bind to all interfaces on port 5000
# IMPORTANT: workers=1 is intentional.
# The app uses a module-level global flag (_SIMULATE_FAILURE) to simulate failures.
# Multiple workers do NOT share memory — each worker has its own copy of the flag,
# so POST /simulate-failure would only affect one worker, making /health return
# HEALTHY from other workers even after failure is triggered. workers=1 avoids this.
CMD ["gunicorn", "--workers=1", "--bind=0.0.0.0:5000", "app:app"]
