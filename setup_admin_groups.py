#!/usr/bin/env python3
"""Assign admin user to medical groups for testing."""
import json
import requests

URL = "http://localhost:9103"
DB = "odoo-clinic"
USER = "admin"
PASS = "admin"


def jsonrpc(url, method, params):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    result = resp.json()
    if "error" in result:
        error = result["error"]
        msg = error.get("data", {}).get("message", error.get("message", str(error)))
        raise Exception(f"JSON-RPC Error: {msg}")
    return result.get("result")


def call_model(uid, model, method, args=None, kwargs=None):
    return jsonrpc(f"{URL}/jsonrpc", "call", {
        "service": "object",
        "method": "execute_kw",
        "args": [DB, uid, PASS, model, method, args or [], kwargs or {}],
    })


uid = jsonrpc(f"{URL}/jsonrpc", "call", {
    "service": "common",
    "method": "authenticate",
    "args": [DB, USER, PASS, {}],
})
print(f"Authenticated as uid={uid}")

# Find medical groups
groups = call_model(uid, "res.groups", "search_read", [
    [("category_id.name", "=", "Medical")]
], {"fields": ["name", "id"]})

print(f"Found groups: {[(g['id'], g['name']) for g in groups]}")

# Add admin to all medical groups
group_ids = [g["id"] for g in groups]
call_model(uid, "res.users", "write", [[uid], {
    "groups_id": [(4, gid) for gid in group_ids]
}])
print(f"Admin user added to groups: {[g['name'] for g in groups]}")
print("Done!")
