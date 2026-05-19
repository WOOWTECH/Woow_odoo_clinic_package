#!/usr/bin/env python3
"""
Shared test infrastructure: JSON-RPC client, user factory, test fixtures.
Enterprise-grade acceptance testing for woow_medical_patient & woow_medical_record.
"""
import json
import os
import sys
import time
import requests
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────
URL = os.environ.get("ODOO_URL", "http://localhost:9103")
DB = os.environ.get("ODOO_DB", "odoo-clinic")
ADMIN_LOGIN = os.environ.get("ODOO_USER", "admin")
ADMIN_PASS = os.environ.get("ODOO_PASS", "admin")

# ──────────────────────────────────────────────────────────────────
# JSON-RPC Client
# ──────────────────────────────────────────────────────────────────
_request_id = 0


def jsonrpc(url, method, params):
    """Low-level JSON-RPC call."""
    global _request_id
    _request_id += 1
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": _request_id,
    }
    resp = requests.post(url, json=payload,
                         headers={"Content-Type": "application/json"},
                         timeout=120)
    result = resp.json()
    if "error" in result:
        error = result["error"]
        msg = error.get("data", {}).get("message",
              error.get("message", str(error)))
        raise RPCError(msg)
    return result.get("result")


class RPCError(Exception):
    """Raised when JSON-RPC returns an error."""
    pass


class OdooRPC:
    """Convenience wrapper for JSON-RPC calls to Odoo."""

    def __init__(self, url=URL, db=DB):
        self.url = url
        self.db = db
        self._uid_cache = {}

    def authenticate(self, login, password):
        uid = jsonrpc(f"{self.url}/jsonrpc", "call", {
            "service": "common",
            "method": "authenticate",
            "args": [self.db, login, password, {}],
        })
        if not uid:
            raise RPCError(f"Authentication failed for {login}")
        self._uid_cache[login] = (uid, password)
        return uid

    def call(self, uid, password, model, method, args=None, kwargs=None):
        return jsonrpc(f"{self.url}/jsonrpc", "call", {
            "service": "object",
            "method": "execute_kw",
            "args": [self.db, uid, password, model, method,
                     args or [], kwargs or {}],
        })

    def as_user(self, login):
        """Return (uid, password) for a cached user."""
        if login not in self._uid_cache:
            raise RPCError(f"User {login} not authenticated. Call authenticate() first.")
        return self._uid_cache[login]

    def call_as(self, login, model, method, args=None, kwargs=None):
        """Call model method as a specific user."""
        uid, password = self.as_user(login)
        return self.call(uid, password, model, method, args, kwargs)


# ──────────────────────────────────────────────────────────────────
# Global RPC instance
# ──────────────────────────────────────────────────────────────────
rpc = OdooRPC()

# ──────────────────────────────────────────────────────────────────
# Admin helpers
# ──────────────────────────────────────────────────────────────────
_admin_uid = None
_admin_pass = ADMIN_PASS


def admin_uid():
    global _admin_uid
    if _admin_uid is None:
        _admin_uid = rpc.authenticate(ADMIN_LOGIN, ADMIN_PASS)
    return _admin_uid


def admin_call(model, method, args=None, kwargs=None):
    return rpc.call(admin_uid(), _admin_pass, model, method, args, kwargs)


# ──────────────────────────────────────────────────────────────────
# Group ID cache
# ──────────────────────────────────────────────────────────────────
_group_ids = {}


def get_group_id(xml_id):
    """Get res.groups ID from XML ID, e.g. 'woow_medical_patient.group_medical_user'."""
    if xml_id not in _group_ids:
        module, name = xml_id.split(".")
        result = admin_call("ir.model.data", "search_read", [
            [("module", "=", module), ("name", "=", name), ("model", "=", "res.groups")]
        ], {"fields": ["res_id"], "limit": 1})
        if not result:
            raise RPCError(f"Group XML ID not found: {xml_id}")
        _group_ids[xml_id] = result[0]["res_id"]
    return _group_ids[xml_id]


# ──────────────────────────────────────────────────────────────────
# User factory
# ──────────────────────────────────────────────────────────────────
_test_users_created = {}

USER_PROFILES = {
    "test_physician_a": {
        "name": "Test Physician A",
        "groups": [
            "woow_medical_patient.group_medical_physician",
        ],
    },
    "test_physician_b": {
        "name": "Test Physician B",
        "groups": [
            "woow_medical_patient.group_medical_physician",
        ],
    },
    "test_basic_user": {
        "name": "Test Basic User",
        "groups": [
            "woow_medical_patient.group_medical_user",
        ],
    },
    "test_med_admin": {
        "name": "Test Med Admin",
        "groups": [
            "woow_medical_patient.group_medical_admin",
        ],
    },
}


def ensure_test_users():
    """Create all test users if they don't exist. Authenticate them."""
    for login, profile in USER_PROFILES.items():
        if login in _test_users_created:
            continue
        # Check if user already exists
        existing = admin_call("res.users", "search", [
            [("login", "=", login)]
        ])
        if existing:
            uid = existing[0]
        else:
            # Get group IDs
            group_ids = [get_group_id(g) for g in profile["groups"]]
            # Also include base.group_user (internal user)
            base_user_gid = get_group_id("base.group_user")
            all_groups = list(set(group_ids + [base_user_gid]))

            uid = admin_call("res.users", "create", [[{
                "name": profile["name"],
                "login": login,
                "password": login,  # password = login for test users
                "groups_id": [(6, 0, all_groups)],
            }]])
            if isinstance(uid, list):
                uid = uid[0]

        # Authenticate
        rpc.authenticate(login, login)
        _test_users_created[login] = uid

    return _test_users_created


# ──────────────────────────────────────────────────────────────────
# Test result tracking
# ──────────────────────────────────────────────────────────────────
class TestResult:
    """Simple test result tracker."""

    def __init__(self, layer_name):
        self.layer_name = layer_name
        self.passed = []
        self.failed = []
        self.errors = []
        self.current_section = ""

    def section(self, name):
        self.current_section = name
        print(f"\n--- {name} ---")

    def ok(self, name, detail=""):
        full = f"{self.current_section}: {name}" if self.current_section else name
        self.passed.append(full)
        detail_str = f" ({detail})" if detail else ""
        print(f"  PASS: {name}{detail_str}")

    def fail(self, name, reason=""):
        full = f"{self.current_section}: {name}" if self.current_section else name
        self.failed.append((full, reason))
        print(f"  FAIL: {name} - {reason}")

    def error(self, name, exc):
        full = f"{self.current_section}: {name}" if self.current_section else name
        self.errors.append((full, str(exc)))
        print(f"  ERROR: {name} - {exc}")

    def run_test(self, name, func, *args, **kwargs):
        """Run a single test function with error handling."""
        try:
            func(*args, **kwargs)
            self.ok(name)
            return True
        except AssertionError as e:
            self.fail(name, str(e))
            return False
        except RPCError as e:
            self.fail(name, f"RPCError: {e}")
            return False
        except Exception as e:
            self.error(name, e)
            return False

    def expect_error(self, name, func, error_substring="", *args, **kwargs):
        """Run a test that is expected to raise an error."""
        try:
            func(*args, **kwargs)
            self.fail(name, "Expected error but succeeded")
            return False
        except (RPCError, Exception) as e:
            if error_substring and error_substring not in str(e):
                self.fail(name, f"Wrong error: {e}")
                return False
            self.ok(name, f"correctly raised: {str(e)[:80]}")
            return True

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.errors)
        print(f"\n{'=' * 60}")
        print(f"{self.layer_name} SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Total:   {total}")
        print(f"  Passed:  {len(self.passed)}")
        print(f"  Failed:  {len(self.failed)}")
        print(f"  Errors:  {len(self.errors)}")

        if self.failed:
            print(f"\n  Failed tests:")
            for name, reason in self.failed:
                print(f"    - {name}: {reason}")

        if self.errors:
            print(f"\n  Errored tests:")
            for name, reason in self.errors:
                print(f"    - {name}: {reason}")

        status = "PASSED" if not self.failed and not self.errors else "FAILED"
        print(f"\n  Status: {status}")
        print(f"{'=' * 60}")
        return len(self.failed) == 0 and len(self.errors) == 0


# ──────────────────────────────────────────────────────────────────
# Cleanup helper
# ──────────────────────────────────────────────────────────────────
def cleanup_test_data(prefix="[TEST"):
    """Remove test patients/records with a given prefix in name."""
    # Delete records first (due to restrict on patient)
    rec_ids = admin_call("medical.record", "search", [
        [("patient_id.name", "like", prefix)]
    ])
    if rec_ids:
        # Delete audit logs first
        log_ids = admin_call("medical.record.access.log", "search", [
            [("record_id", "in", rec_ids)]
        ])
        # Audit logs can't be deleted via ORM, use SQL approach or skip
        # For testing, we archive records instead
        pass

    # Patients: we can't easily clean up due to audit log constraints
    # Tests should be idempotent and use unique prefixes
