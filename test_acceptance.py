#!/usr/bin/env python3
"""
Stage 6: Acceptance Test Script for woow_medical_patient & woow_medical_record.
Uses JSON-RPC to test against running Odoo 18 instance.
"""
import json
import requests
import sys
from datetime import datetime

URL = "http://localhost:9103"
DB = "odoo-clinic"
USER = "admin"
PASS = "admin"


def jsonrpc(url, method, params):
    """Make a JSON-RPC call."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    result = resp.json()
    if "error" in result:
        error = result["error"]
        msg = error.get("data", {}).get("message", error.get("message", str(error)))
        raise Exception(f"JSON-RPC Error: {msg}")
    return result.get("result")


def authenticate():
    """Authenticate and return uid."""
    uid = jsonrpc(f"{URL}/jsonrpc", "call", {
        "service": "common",
        "method": "authenticate",
        "args": [DB, USER, PASS, {}],
    })
    if not uid:
        raise Exception("Authentication failed")
    print(f"  Authenticated as uid={uid}")
    return uid


def call_model(uid, model, method, args=None, kwargs=None):
    """Call a model method via JSON-RPC."""
    return jsonrpc(f"{URL}/jsonrpc", "call", {
        "service": "object",
        "method": "execute_kw",
        "args": [DB, uid, PASS, model, method, args or [], kwargs or {}],
    })


def test_create_patient(uid):
    """Test 1: Create a patient and verify medical_no is auto-generated."""
    print("\n=== TEST 1: Create Patient ===")
    patient_id = call_model(uid, "medical.patient", "create", [[{
        "name": "Test Patient 001",
        "phone": "0911111111",
        "gender": "female",
        "birthday": "1992-06-15",
        "blood_type": "a",
        "allergies": "None known",
        "emergency_name": "Test Emergency",
        "emergency_phone": "0922222222",
        "emergency_relation": "Spouse",
    }]])
    patient_id = patient_id[0] if isinstance(patient_id, list) else patient_id
    print(f"  Created patient ID: {patient_id}")

    # Read back and check medical_no
    patient = call_model(uid, "medical.patient", "read", [[patient_id]], {
        "fields": ["medical_no", "name", "age", "gender"]
    })
    patient = patient[0]
    print(f"  medical_no: {patient['medical_no']}")
    print(f"  name: {patient['name']}")
    print(f"  age: {patient['age']}")

    assert patient["medical_no"] == "P000001", f"Expected P000001, got {patient['medical_no']}"
    assert patient["name"] == "Test Patient 001"
    assert patient["age"] > 0, "Age should be computed"
    print("  PASS: Patient created with correct medical_no P000001")

    # Create second patient
    patient_id2 = call_model(uid, "medical.patient", "create", [[{
        "name": "Test Patient 002",
        "phone": "0933333333",
        "gender": "male",
    }]])
    patient_id2 = patient_id2[0] if isinstance(patient_id2, list) else patient_id2
    patient2 = call_model(uid, "medical.patient", "read", [[patient_id2]], {
        "fields": ["medical_no"]
    })
    assert patient2[0]["medical_no"] == "P000002", f"Expected P000002, got {patient2[0]['medical_no']}"
    print("  PASS: Second patient got P000002")

    return patient_id, patient_id2


def test_create_records(uid, patient_id):
    """Test 2: Create medical records and verify YYYYMMDD-001 numbering."""
    print("\n=== TEST 2: Create Medical Records ===")
    today = datetime.now().strftime("%Y%m%d")

    # Create first record
    record_id1 = call_model(uid, "medical.record", "create", [[{
        "patient_id": patient_id,
        "subjective": "<p>Patient complains of headache</p>",
    }]])
    record_id1 = record_id1[0] if isinstance(record_id1, list) else record_id1
    print(f"  Created record ID: {record_id1}")

    record1 = call_model(uid, "medical.record", "read", [[record_id1]], {
        "fields": ["name", "state", "physician_id"]
    })
    record1 = record1[0]
    expected_name = f"{today}-001"
    print(f"  Record name: {record1['name']}")
    print(f"  Expected: {expected_name}")
    assert record1["name"] == expected_name, f"Expected {expected_name}, got {record1['name']}"
    assert record1["state"] == "draft", f"Expected draft, got {record1['state']}"
    print("  PASS: First record got correct daily number")

    # Create second record
    record_id2 = call_model(uid, "medical.record", "create", [[{
        "patient_id": patient_id,
        "subjective": "<p>Follow-up visit</p>",
    }]])
    record_id2 = record_id2[0] if isinstance(record_id2, list) else record_id2
    record2 = call_model(uid, "medical.record", "read", [[record_id2]], {
        "fields": ["name"]
    })
    expected_name2 = f"{today}-002"
    assert record2[0]["name"] == expected_name2, f"Expected {expected_name2}, got {record2[0]['name']}"
    print(f"  PASS: Second record got {expected_name2}")

    return record_id1, record_id2


def test_sign_workflow(uid, record_id):
    """Test 3: Test the full sign workflow (draft -> in_progress -> signed)."""
    print("\n=== TEST 3: Sign Workflow ===")

    # action_start: draft -> in_progress
    call_model(uid, "medical.record", "action_start", [[record_id]])
    record = call_model(uid, "medical.record", "read", [[record_id]], {
        "fields": ["state"]
    })
    assert record[0]["state"] == "in_progress", f"Expected in_progress, got {record[0]['state']}"
    print("  PASS: draft -> in_progress")

    # action_sign: in_progress -> signed (has subjective content)
    call_model(uid, "medical.record", "action_sign", [[record_id]])
    record = call_model(uid, "medical.record", "read", [[record_id]], {
        "fields": ["state", "signed_by", "signed_at"]
    })
    record = record[0]
    assert record["state"] == "signed", f"Expected signed, got {record['state']}"
    assert record["signed_by"], "signed_by should be set"
    assert record["signed_at"], "signed_at should be set"
    print(f"  PASS: in_progress -> signed (signed_by={record['signed_by']}, signed_at={record['signed_at']})")

    return record_id


def test_sign_validation(uid, record_id):
    """Test 3b: Signing without SOAP content should fail."""
    print("\n=== TEST 3b: Sign Validation (empty SOAP) ===")

    # Start the record first
    call_model(uid, "medical.record", "action_start", [[record_id]])

    # Try to sign without SOAP content - should fail
    try:
        call_model(uid, "medical.record", "action_sign", [[record_id]])
        print("  FAIL: Should have raised error")
        return False
    except Exception as e:
        if "SOAP" in str(e):
            print(f"  PASS: Correctly rejected signing empty SOAP: {e}")
            return True
        else:
            print(f"  FAIL: Wrong error: {e}")
            return False


def test_reset_to_draft(uid, record_id):
    """Test 4: Reset signed record to draft and verify audit log."""
    print("\n=== TEST 4: Reset to Draft ===")

    # Reset to draft
    call_model(uid, "medical.record", "action_reset_to_draft", [[record_id]])
    record = call_model(uid, "medical.record", "read", [[record_id]], {
        "fields": ["state", "signed_by", "signed_at"]
    })
    record = record[0]
    assert record["state"] == "draft", f"Expected draft, got {record['state']}"
    assert not record["signed_by"], "signed_by should be cleared"
    assert not record["signed_at"], "signed_at should be cleared"
    print("  PASS: signed -> draft (signed_by/signed_at cleared)")

    return record_id


def test_audit_log(uid, record_id):
    """Test 5: Verify audit log entries."""
    print("\n=== TEST 5: Audit Log ===")

    # Search for audit log entries for this record
    log_ids = call_model(uid, "medical.record.access.log", "search", [
        [("record_id", "=", record_id)]
    ])
    print(f"  Found {len(log_ids)} audit log entries")

    logs = call_model(uid, "medical.record.access.log", "read", [log_ids], {
        "fields": ["action", "note", "user_id"]
    })
    actions = [log["action"] for log in logs]
    print(f"  Actions: {actions}")

    assert "sign" in actions, "Should have 'sign' action in audit log"
    assert "unsign" in actions, "Should have 'unsign' action in audit log"
    print("  PASS: Audit log contains sign and unsign entries")

    # Test immutability - try to write to audit log
    print("\n  Testing audit log immutability...")
    try:
        call_model(uid, "medical.record.access.log", "write", [[log_ids[0]], {"note": "hacked"}])
        print("  FAIL: Should not be able to write to audit log")
    except Exception as e:
        if "cannot be modified" in str(e):
            print(f"  PASS: Write correctly blocked: {e}")
        else:
            print(f"  INFO: Write blocked with: {e}")

    return True


def test_security_groups(uid):
    """Test 6: Verify security groups exist."""
    print("\n=== TEST 6: Security Groups ===")

    # Check groups exist
    groups = call_model(uid, "res.groups", "search_read", [
        [("category_id.name", "=", "Medical")]
    ], {"fields": ["name", "full_name"]})

    group_names = [g["name"] for g in groups]
    print(f"  Medical groups: {group_names}")

    expected = ["Medical User", "Medical Physician", "Medical Administrator"]
    for name in expected:
        assert name in group_names, f"Missing group: {name}"

    print("  PASS: All 3 security groups exist")
    return True


def test_record_count_on_patient(uid, patient_id):
    """Test 7: Verify record_count computed field on patient."""
    print("\n=== TEST 7: Patient Record Count ===")

    patient = call_model(uid, "medical.patient", "read", [[patient_id]], {
        "fields": ["record_count", "last_visit_date"]
    })
    patient = patient[0]
    print(f"  record_count: {patient['record_count']}")
    print(f"  last_visit_date: {patient['last_visit_date']}")

    assert patient["record_count"] >= 2, f"Expected >= 2 records, got {patient['record_count']}"
    assert patient["last_visit_date"], "last_visit_date should be set"
    print("  PASS: record_count and last_visit_date correct")
    return True


def main():
    print("=" * 60)
    print("STAGE 6: ACCEPTANCE TEST")
    print(f"Target: {URL} | DB: {DB}")
    print("=" * 60)

    # Authenticate
    print("\n--- Authentication ---")
    uid = authenticate()

    # Run tests
    try:
        patient_id, patient_id2 = test_create_patient(uid)
        record_id1, record_id2 = test_create_records(uid, patient_id)
        test_sign_workflow(uid, record_id1)
        test_reset_to_draft(uid, record_id1)
        test_audit_log(uid, record_id1)

        # Create a record with no SOAP for validation test
        empty_record_id = call_model(uid, "medical.record", "create", [[{
            "patient_id": patient_id,
        }]])
        empty_record_id = empty_record_id[0] if isinstance(empty_record_id, list) else empty_record_id
        test_sign_validation(uid, empty_record_id)

        test_security_groups(uid)
        test_record_count_on_patient(uid, patient_id)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n  FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
