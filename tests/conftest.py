"""
Shared test configuration.

The functional suite drives the HTTP API without credentials, so it runs with
enforcement off. The auth surface itself is covered in
tests/security/test_http_auth.py, which flips the manager into a strict mode.

These have to be set before any test module imports auth.flexible_auth, which
reads them when it builds its module-level manager. pytest loads conftest first.
"""
import os

os.environ["AUTH_MODE"] = "OPEN"
os.environ.setdefault("JWT_SECRET", "test-secret-for-suite")
