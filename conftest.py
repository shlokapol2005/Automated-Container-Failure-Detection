"""
conftest.py — pytest configuration
Ensures the app/ and monitor/ directories are on sys.path for all tests.
"""
import sys
import os

# Make app/app.py importable as `app` from any test file
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

# Make monitor/monitor.py and monitor/ai_diagnosis.py importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "monitor"))
