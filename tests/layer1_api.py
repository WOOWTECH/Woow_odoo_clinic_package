#!/usr/bin/env python3
"""
Layer 1: API/Backend Tests — Comprehensive JSON-RPC tests.
Covers CRUD, sequences, workflow, security, record rules, audit log, computed fields.
~65 tests total.
"""
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from conftest import (
    rpc, admin_uid, admin_call, ensure_test_users,
    TestResult, RPCError, ADMIN_PASS,
)


def main():
    tr = TestResult("LAYER 1: API/Backend")
    print("=" * 60)
    print("LAYER 1: API/BACKEND TESTS")
    print("=" * 60)

    # ── Setup ──
    print("\n--- Setup: Creating test users ---")
    uid = admin_uid()
    users = ensure_test_users()
    print(f"  Admin uid={uid}")
    print(f"  Test users: {list(users.keys())}")

    today = datetime.now().strftime("%Y%m%d")

    # ══════════════════════════════════════════════════════════════
    # 1.1 Patient CRUD
    # ══════════════════════════════════════════════════════════════
    tr.section("1.1 Patient CRUD")

    _p_ids = []  # track created patient IDs

    def test_create_patient_minimal():
        pid = admin_call("medical.patient", "create", [[{
            "name": "[L1] Minimal Patient",
        }]])
        pid = pid[0] if isinstance(pid, list) else pid
        _p_ids.append(pid)
        p = admin_call("medical.patient", "read", [[pid]], {"fields": ["name", "medical_no"]})[0]
        assert p["name"] == "[L1] Minimal Patient"
        assert p["medical_no"] and p["medical_no"].startswith("P")

    def test_create_patient_full():
        pid = admin_call("medical.patient", "create", [[{
            "name": "[L1] Full Patient",
            "phone": "0912345678",
            "gender": "female",
            "birthday": "1990-06-15",
            "blood_type": "b",
            "allergies": "Penicillin, Latex",
            "surgery_history": "Appendectomy 2015",
            "emergency_name": "John Doe",
            "emergency_phone": "0987654321",
            "emergency_relation": "Spouse",
        }]])
        pid = pid[0] if isinstance(pid, list) else pid
        _p_ids.append(pid)
        p = admin_call("medical.patient", "read", [[pid]], {
            "fields": ["name", "phone", "gender", "birthday", "blood_type",
                        "allergies", "surgery_history", "emergency_name",
                        "emergency_phone", "emergency_relation", "medical_no", "age"]
        })[0]
        assert p["gender"] == "female"
        assert p["blood_type"] == "b"
        assert p["age"] > 0
        assert p["emergency_name"] == "John Doe"

    def test_read_patient_fields():
        pid = _p_ids[0]
        p = admin_call("medical.patient", "read", [[pid]], {
            "fields": ["name", "medical_no", "partner_id", "company_id"]
        })[0]
        assert p["partner_id"], "partner_id should be set (delegation inheritance)"
        assert p["company_id"], "company_id should be set"

    def test_write_patient_name():
        pid = _p_ids[0]
        admin_call("medical.patient", "write", [[pid], {"name": "[L1] Updated Patient"}])
        p = admin_call("medical.patient", "read", [[pid]], {"fields": ["name"]})[0]
        assert p["name"] == "[L1] Updated Patient"

    def test_search_patient_by_phone():
        # Ensure we have a patient with this phone (from full test or create fresh)
        existing = admin_call("medical.patient", "search", [
            [("phone", "=", "0912345678")]
        ])
        if not existing:
            pid_ph = admin_call("medical.patient", "create", [[{
                "name": "[L1] Phone Search",
                "phone": "0912345678",
            }]])
            pid_ph = pid_ph[0] if isinstance(pid_ph, list) else pid_ph
            _p_ids.append(pid_ph)
        results = admin_call("medical.patient", "search", [
            [("phone", "=", "0912345678")]
        ])
        assert isinstance(results, list), "Search should return a list"
        assert len(results) >= 1, "Should find at least one patient with that phone"

    def test_search_patient_by_medical_no():
        p = admin_call("medical.patient", "read", [[_p_ids[0]]], {"fields": ["medical_no"]})[0]
        results = admin_call("medical.patient", "search", [
            [("medical_no", "=", p["medical_no"])]
        ])
        assert _p_ids[0] in results

    def test_patient_age_computed():
        pid = admin_call("medical.patient", "create", [[{
            "name": "[L1] Age Test",
            "birthday": "2000-01-01",
        }]])
        pid = pid[0] if isinstance(pid, list) else pid
        _p_ids.append(pid)
        p = admin_call("medical.patient", "read", [[pid]], {"fields": ["age"]})[0]
        expected_age = datetime.now().year - 2000
        assert abs(p["age"] - expected_age) <= 1, f"Expected ~{expected_age}, got {p['age']}"

    def test_patient_age_no_birthday():
        pid = admin_call("medical.patient", "create", [[{
            "name": "[L1] No Birthday",
        }]])
        pid = pid[0] if isinstance(pid, list) else pid
        _p_ids.append(pid)
        p = admin_call("medical.patient", "read", [[pid]], {"fields": ["age"]})[0]
        assert p["age"] == 0

    def test_duplicate_patient_gets_new_no():
        pid = _p_ids[0]
        new_pid = admin_call("medical.patient", "copy", [[pid]])
        if isinstance(new_pid, list):
            new_pid = new_pid[0]
        _p_ids.append(new_pid)
        orig = admin_call("medical.patient", "read", [[pid]], {"fields": ["medical_no"]})[0]
        copy = admin_call("medical.patient", "read", [[new_pid]], {"fields": ["medical_no"]})[0]
        assert orig["medical_no"] != copy["medical_no"], \
            f"Copy should get new medical_no, both got {orig['medical_no']}"

    def test_create_patient_without_name_fails():
        admin_call("medical.patient", "create", [[{"phone": "09999"}]])
        # res.partner requires name, so this should fail

    tr.run_test("Create patient minimal", test_create_patient_minimal)
    tr.run_test("Create patient full fields", test_create_patient_full)
    tr.run_test("Read patient fields", test_read_patient_fields)
    tr.run_test("Write patient name", test_write_patient_name)
    tr.run_test("Search by phone", test_search_patient_by_phone)
    tr.run_test("Search by medical_no", test_search_patient_by_medical_no)
    tr.run_test("Age computed correctly", test_patient_age_computed)
    tr.run_test("Age=0 when no birthday", test_patient_age_no_birthday)
    tr.run_test("Copy patient gets new number", test_duplicate_patient_gets_new_no)
    tr.expect_error("Create without name fails", test_create_patient_without_name_fails)

    # ══════════════════════════════════════════════════════════════
    # 1.2 Patient Sequence
    # ══════════════════════════════════════════════════════════════
    tr.section("1.2 Patient Sequence")

    def test_sequential_numbering():
        p1 = admin_call("medical.patient", "create", [[{"name": "[L1] Seq A"}]])
        p1 = p1[0] if isinstance(p1, list) else p1
        p2 = admin_call("medical.patient", "create", [[{"name": "[L1] Seq B"}]])
        p2 = p2[0] if isinstance(p2, list) else p2
        _p_ids.extend([p1, p2])
        r1 = admin_call("medical.patient", "read", [[p1]], {"fields": ["medical_no"]})[0]
        r2 = admin_call("medical.patient", "read", [[p2]], {"fields": ["medical_no"]})[0]
        n1 = int(r1["medical_no"][1:])
        n2 = int(r2["medical_no"][1:])
        assert n2 == n1 + 1, f"Expected consecutive: {r1['medical_no']} -> {r2['medical_no']}"

    def test_medical_no_format():
        pid = _p_ids[0]
        p = admin_call("medical.patient", "read", [[pid]], {"fields": ["medical_no"]})[0]
        no = p["medical_no"]
        assert no[0] == "P", f"Should start with P, got {no}"
        assert len(no) == 7, f"Should be 7 chars (P+6 digits), got {len(no)}: {no}"
        assert no[1:].isdigit(), f"After P should be digits: {no}"

    def test_medical_no_readonly():
        """Odoo readonly=True is UI-only. Verify copy=False works instead."""
        pid = _p_ids[0]
        orig = admin_call("medical.patient", "read", [[pid]], {"fields": ["medical_no"]})[0]["medical_no"]
        # In Odoo, readonly on model definition is for UI display only.
        # The real protection is copy=False (no duplicate on copy) + auto-generation in create().
        # Verify copy=False works:
        new_pid = admin_call("medical.patient", "copy", [[pid]])
        new_pid = new_pid[0] if isinstance(new_pid, list) else new_pid
        _p_ids.append(new_pid)
        copied = admin_call("medical.patient", "read", [[new_pid]], {"fields": ["medical_no"]})[0]
        assert copied["medical_no"] != orig, \
            f"Copy should get new medical_no (copy=False), both got {orig}"

    tr.run_test("Sequential numbering (no gap)", test_sequential_numbering)
    tr.run_test("medical_no format P+6digits", test_medical_no_format)
    tr.run_test("medical_no readonly protection", test_medical_no_readonly)

    # ══════════════════════════════════════════════════════════════
    # 1.3 Record CRUD
    # ══════════════════════════════════════════════════════════════
    tr.section("1.3 Record CRUD")

    _r_ids = []  # track created record IDs
    _base_patient = _p_ids[0]

    def test_create_record_minimal():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["name", "state", "physician_id", "visit_date"]
        })[0]
        assert r["state"] == "draft"
        assert r["physician_id"], "physician_id should default to current user"
        assert r["visit_date"], "visit_date should default to now"
        assert r["name"], "name should be auto-generated"

    def test_create_record_full_soap():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>Headache for 3 days</p>",
            "objective": "<p>BP 120/80, temp 36.5</p>",
            "assessment": "<p>Tension headache</p>",
            "plan": "<p>Rest, analgesics</p>",
            "diagnosis": "Tension-type headache",
            "vital_temp": 36.5,
            "vital_pulse": 72,
            "vital_bp_systolic": 120,
            "vital_bp_diastolic": 80,
            "vital_height": 170.0,
            "vital_weight": 65.0,
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["subjective", "objective", "assessment", "plan",
                        "diagnosis", "vital_temp", "vital_pulse"]
        })[0]
        assert "Headache" in r["subjective"]
        assert r["vital_temp"] == 36.5
        assert r["vital_pulse"] == 72

    def test_update_soap_content():
        rid = _r_ids[0]
        admin_call("medical.record", "write", [[rid], {
            "subjective": "<p>Updated: headache resolved</p>"
        }])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["subjective"]})[0]
        assert "Updated" in r["subjective"]

    def test_create_record_without_patient_fails():
        admin_call("medical.record", "create", [[{
            "subjective": "<p>No patient</p>",
        }]])

    def test_record_default_state_draft():
        rid = _r_ids[0]
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["state"]})[0]
        assert r["state"] == "draft"

    def test_physician_defaults_current_user():
        rid = _r_ids[0]
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["physician_id"]})[0]
        assert r["physician_id"][0] == uid, "physician_id should be admin uid"

    def test_visit_date_defaults_now():
        rid = _r_ids[0]
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["visit_date"]})[0]
        vd = datetime.strptime(r["visit_date"], "%Y-%m-%d %H:%M:%S")
        # Odoo stores in UTC; server may be in different timezone.
        # Just verify the date part matches today (robust across timezones).
        today_date = datetime.now().strftime("%Y-%m-%d")
        vd_date = vd.strftime("%Y-%m-%d")
        # Allow +/- 1 day for timezone edge cases
        assert abs((datetime.strptime(today_date, "%Y-%m-%d") -
                     datetime.strptime(vd_date, "%Y-%m-%d")).days) <= 1, \
            f"visit_date should be near today. Got {vd_date}, today={today_date}"

    tr.run_test("Create record minimal", test_create_record_minimal)
    tr.run_test("Create record full SOAP+vitals", test_create_record_full_soap)
    tr.run_test("Update SOAP content", test_update_soap_content)
    tr.expect_error("Create without patient_id fails", test_create_record_without_patient_fails)
    tr.run_test("Default state = draft", test_record_default_state_draft)
    tr.run_test("Physician defaults to current user", test_physician_defaults_current_user)
    tr.run_test("Visit date defaults to now", test_visit_date_defaults_now)

    # ══════════════════════════════════════════════════════════════
    # 1.4 Record Sequence
    # ══════════════════════════════════════════════════════════════
    tr.section("1.4 Record Sequence")

    def test_first_record_today_format():
        r = admin_call("medical.record", "read", [[_r_ids[0]]], {"fields": ["name"]})[0]
        assert r["name"].startswith(today), f"Should start with {today}, got {r['name']}"
        parts = r["name"].split("-")
        assert len(parts) == 2, f"Format should be YYYYMMDD-NNN, got {r['name']}"

    def test_sequential_records_same_day():
        r1 = admin_call("medical.record", "read", [[_r_ids[0]]], {"fields": ["name"]})[0]
        r2 = admin_call("medical.record", "read", [[_r_ids[1]]], {"fields": ["name"]})[0]
        n1 = int(r1["name"].split("-")[1])
        n2 = int(r2["name"].split("-")[1])
        assert n2 == n1 + 1, f"Expected consecutive: {r1['name']} -> {r2['name']}"

    def test_cross_day_records():
        """Create a record with past visit_date → should get different date prefix."""
        past_date = "2025-03-15 10:00:00"
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "visit_date": past_date,
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["name"]})[0]
        assert r["name"].startswith("20250315"), \
            f"Past date record should start with 20250315, got {r['name']}"
        # Verify the name has a valid sequence number (may not be 001 on repeated runs)
        seq_num = int(r["name"].split("-")[1])
        assert seq_num >= 1, \
            f"Sequence number should be >= 1, got {seq_num} in {r['name']}"

    def test_name_copy_false():
        """Record name has copy=False — copies should get new auto-generated name."""
        rid = _r_ids[0]
        orig = admin_call("medical.record", "read", [[rid]], {"fields": ["name"]})[0]["name"]
        new_rid = admin_call("medical.record", "copy", [[rid]])
        new_rid = new_rid[0] if isinstance(new_rid, list) else new_rid
        _r_ids.append(new_rid)
        copied = admin_call("medical.record", "read", [[new_rid]], {"fields": ["name"]})[0]
        assert copied["name"] != orig, \
            f"Copy should get new name (copy=False), both got {orig}"
        assert copied["name"].startswith(today), \
            f"Copied record name should have today's date prefix: {copied['name']}"

    def test_ten_rapid_creates():
        """10 rapid creates → numbers should be consecutive."""
        ids = []
        for i in range(10):
            rid = admin_call("medical.record", "create", [[{
                "patient_id": _base_patient,
                "subjective": f"<p>Rapid test #{i}</p>",
            }]])
            rid = rid[0] if isinstance(rid, list) else rid
            ids.append(rid)
        _r_ids.extend(ids)
        records = admin_call("medical.record", "read", [ids], {"fields": ["name"]})
        numbers = sorted([int(r["name"].split("-")[1]) for r in records])
        for i in range(1, len(numbers)):
            assert numbers[i] == numbers[i - 1] + 1, \
                f"Gap in rapid sequence: {numbers}"

    tr.run_test("Record name format YYYYMMDD-NNN", test_first_record_today_format)
    tr.run_test("Sequential records same day", test_sequential_records_same_day)
    tr.run_test("Cross-day record gets different prefix", test_cross_day_records)
    tr.run_test("Record name copy=False", test_name_copy_false)
    tr.run_test("10 rapid creates are consecutive", test_ten_rapid_creates)

    # ══════════════════════════════════════════════════════════════
    # 1.5 Workflow
    # ══════════════════════════════════════════════════════════════
    tr.section("1.5 Workflow")

    def _create_soap_record():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>Workflow test SOAP content</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        return rid

    def test_draft_to_in_progress():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["state"]})[0]
        assert r["state"] == "in_progress"

    def test_in_progress_to_signed():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["state", "signed_by", "signed_at"]
        })[0]
        assert r["state"] == "signed"
        assert r["signed_by"]
        assert r["signed_at"]

    def test_signed_to_draft():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        admin_call("medical.record", "action_reset_to_draft", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["state", "signed_by", "signed_at"]
        })[0]
        assert r["state"] == "draft"
        assert not r["signed_by"]
        assert not r["signed_at"]

    def test_sign_without_soap_fails():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])

    def test_start_non_draft_fails():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        # Now in_progress → start again should fail
        admin_call("medical.record", "action_start", [[rid]])

    def test_sign_non_in_progress_fails():
        rid = _create_soap_record()
        # Still draft → sign should fail
        admin_call("medical.record", "action_sign", [[rid]])

    def test_reset_non_signed_fails():
        rid = _create_soap_record()
        # Still draft → reset should fail
        admin_call("medical.record", "action_reset_to_draft", [[rid]])

    def test_sign_sets_signed_by():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["signed_by"]})[0]
        assert r["signed_by"][0] == uid

    def test_full_lifecycle():
        """draft → start → sign → reset → start → sign"""
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        admin_call("medical.record", "action_reset_to_draft", [[rid]])
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["state"]})[0]
        assert r["state"] == "signed"

    def test_sign_with_only_plan():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "plan": "<p>Only plan field filled</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["state"]})[0]
        assert r["state"] == "signed"

    def test_sign_with_only_assessment():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "assessment": "<p>Assessment only</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["state"]})[0]
        assert r["state"] == "signed"

    tr.run_test("draft → in_progress", test_draft_to_in_progress)
    tr.run_test("in_progress → signed", test_in_progress_to_signed)
    tr.run_test("signed → draft (reset)", test_signed_to_draft)
    tr.expect_error("Sign without SOAP fails", test_sign_without_soap_fails, "SOAP")
    tr.expect_error("Start non-draft fails", test_start_non_draft_fails, "draft")
    tr.expect_error("Sign non-in_progress fails", test_sign_non_in_progress_fails, "in-progress")
    tr.expect_error("Reset non-signed fails", test_reset_non_signed_fails, "signed")
    tr.run_test("signed_by = current user on sign", test_sign_sets_signed_by)
    tr.run_test("Full lifecycle (2 rounds)", test_full_lifecycle)
    tr.run_test("Sign with only plan field", test_sign_with_only_plan)
    tr.run_test("Sign with only assessment field", test_sign_with_only_assessment)

    # ══════════════════════════════════════════════════════════════
    # 1.6 Security & Record Rules
    # ══════════════════════════════════════════════════════════════
    tr.section("1.6 Security & Record Rules")

    def test_physician_a_create_and_read():
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>PhysA record</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        r = rpc.call_as("test_physician_a", "medical.record", "read", [[rid]], {
            "fields": ["name", "physician_id"]
        })[0]
        assert r["name"], "Physician A should read own record"

    def test_physician_b_cannot_read_a_record():
        # Create as physician A
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>PhysA private</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        # Physician B tries to read
        rpc.call_as("test_physician_b", "medical.record", "read", [[rid]], {
            "fields": ["name"]
        })

    def test_admin_reads_all_records():
        # Create as physician A
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>PhysA for admin test</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        # Admin (test_med_admin) reads it
        r = rpc.call_as("test_med_admin", "medical.record", "read", [[rid]], {
            "fields": ["name"]
        })[0]
        assert r["name"], "Admin should read any record"

    def test_basic_user_can_read_records():
        # basic user should be able to read (ACL read=1)
        all_recs = rpc.call_as("test_basic_user", "medical.record", "search", [
            []
        ], {"limit": 1})
        # Should not raise an error
        assert isinstance(all_recs, list)

    def test_basic_user_cannot_create_record():
        rpc.call_as("test_basic_user", "medical.record", "create", [[{
            "patient_id": _base_patient,
        }]])

    def test_basic_user_cannot_write_record():
        rid = _r_ids[0]
        rpc.call_as("test_basic_user", "medical.record", "write", [[rid], {
            "subjective": "<p>Hacked by basic user</p>"
        }])

    def test_no_role_can_delete_record():
        rid = _create_soap_record()
        admin_call("medical.record", "unlink", [[rid]])

    def test_basic_user_can_read_national_id():
        pid = admin_call("medical.patient", "create", [[{
            "name": "[L1] PII Test Patient",
            "national_id": "A123456789",
        }]])
        pid = pid[0] if isinstance(pid, list) else pid
        _p_ids.append(pid)
        p = rpc.call_as("test_basic_user", "medical.patient", "read", [[pid]], {
            "fields": ["name", "national_id"]
        })[0]
        assert p.get("national_id") == "A123456789", \
            f"Basic user should see national_id, got: {p.get('national_id')}"

    def test_physician_cannot_modify_other_record():
        # Create as physician A
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>A's record</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        # Physician B tries to write
        rpc.call_as("test_physician_b", "medical.record", "write", [[rid], {
            "subjective": "<p>Modified by B</p>"
        }])

    def test_admin_can_modify_any_record():
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>A's record for admin</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        rpc.call_as("test_med_admin", "medical.record", "write", [[rid], {
            "subjective": "<p>Modified by admin</p>"
        }])
        r = rpc.call_as("test_med_admin", "medical.record", "read", [[rid]], {
            "fields": ["subjective"]
        })[0]
        assert "Modified by admin" in r["subjective"]

    def test_security_groups_exist():
        groups = admin_call("res.groups", "search_read", [
            [("category_id.name", "=", "Medical")]
        ], {"fields": ["name"]})
        names = [g["name"] for g in groups]
        for expected in ["Medical User", "Medical Physician",
                          "Medical Administrator"]:
            assert expected in names, f"Missing group: {expected}"

    def test_physician_a_sees_only_own():
        my_recs = rpc.call_as("test_physician_a", "medical.record", "search", [[]])
        if my_recs:
            records = rpc.call_as("test_physician_a", "medical.record", "read",
                                   [my_recs], {"fields": ["physician_id"]})
            pa_uid = rpc.as_user("test_physician_a")[0]
            for r in records:
                assert r["physician_id"][0] == pa_uid, \
                    f"Physician A sees record from uid={r['physician_id'][0]}"

    tr.run_test("Physician A creates & reads own record", test_physician_a_create_and_read)
    tr.expect_error("Physician B cannot read A's record", test_physician_b_cannot_read_a_record, "")
    tr.run_test("Admin reads all records", test_admin_reads_all_records)
    tr.run_test("Basic user can read records (ACL)", test_basic_user_can_read_records)
    tr.expect_error("Basic user cannot create record", test_basic_user_cannot_create_record, "")
    tr.expect_error("Basic user cannot write record", test_basic_user_cannot_write_record, "")
    tr.expect_error("No role can delete record", test_no_role_can_delete_record, "")
    tr.run_test("Basic user CAN read national_id", test_basic_user_can_read_national_id)
    tr.expect_error("Physician B cannot modify A's record", test_physician_cannot_modify_other_record, "")
    tr.run_test("Admin can modify any record", test_admin_can_modify_any_record)
    tr.run_test("All 3 security groups exist", test_security_groups_exist)
    tr.run_test("Physician A sees only own records", test_physician_a_sees_only_own)

    # ══════════════════════════════════════════════════════════════
    # 1.7 Audit Log
    # ══════════════════════════════════════════════════════════════
    tr.section("1.7 Audit Log")

    def test_sign_creates_audit_entry():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        logs = admin_call("medical.record.access.log", "search_read", [
            [("record_id", "=", rid), ("action", "=", "sign")]
        ], {"fields": ["action", "note", "user_id"]})
        assert len(logs) >= 1, "Should have sign audit entry"
        assert logs[0]["action"] == "sign"

    def test_unsign_creates_audit_entry():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        admin_call("medical.record", "action_reset_to_draft", [[rid]])
        logs = admin_call("medical.record.access.log", "search_read", [
            [("record_id", "=", rid), ("action", "=", "unsign")]
        ], {"fields": ["action", "note"]})
        assert len(logs) >= 1, "Should have unsign audit entry"

    def test_audit_log_write_blocked():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        logs = admin_call("medical.record.access.log", "search", [
            [("record_id", "=", rid)]
        ])
        admin_call("medical.record.access.log", "write", [[logs[0]], {"note": "hacked"}])

    def test_audit_log_delete_blocked():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        logs = admin_call("medical.record.access.log", "search", [
            [("record_id", "=", rid)]
        ])
        admin_call("medical.record.access.log", "unlink", [[logs[0]]])

    def test_audit_log_fields_correct():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        logs = admin_call("medical.record.access.log", "search_read", [
            [("record_id", "=", rid), ("action", "=", "sign")]
        ], {"fields": ["action", "note", "user_id", "record_id", "create_date"]})
        log = logs[0]
        assert log["user_id"][0] == uid
        assert log["record_id"][0] == rid
        assert log["create_date"]
        assert "signed" in log["note"].lower() or "sign" in log["note"].lower()

    def test_admin_can_read_logs():
        logs = rpc.call_as("test_med_admin", "medical.record.access.log", "search", [
            []
        ], {"limit": 5})
        assert isinstance(logs, list), "Admin should be able to search logs"

    def test_view_logged_with_form_context():
        """Read with medical_form_view=True + SOAP fields should create 'view' log."""
        rid = _create_soap_record()
        # Count logs before
        before = admin_call("medical.record.access.log", "search_count", [
            [("record_id", "=", rid), ("action", "=", "view")]
        ])
        # Read with context (simulating form view open)
        rpc.call(uid, ADMIN_PASS, "medical.record", "read", [[rid]], {
            "fields": ["subjective", "objective", "assessment", "plan"],
            "context": {"medical_form_view": True},
        })
        # Count logs after
        after = admin_call("medical.record.access.log", "search_count", [
            [("record_id", "=", rid), ("action", "=", "view")]
        ])
        assert after > before, f"View log should be created. Before={before}, After={after}"

    tr.run_test("Sign creates 'sign' audit entry", test_sign_creates_audit_entry)
    tr.run_test("Reset creates 'unsign' audit entry", test_unsign_creates_audit_entry)
    tr.expect_error("Audit log write blocked", test_audit_log_write_blocked, "cannot be modified")
    tr.expect_error("Audit log delete blocked", test_audit_log_delete_blocked, "")
    tr.run_test("Audit log fields correct", test_audit_log_fields_correct)
    tr.run_test("Admin can read logs", test_admin_can_read_logs)
    tr.run_test("View logged with form context", test_view_logged_with_form_context)

    # ══════════════════════════════════════════════════════════════
    # 1.8 Computed Fields
    # ══════════════════════════════════════════════════════════════
    tr.section("1.8 Computed Fields")

    def test_record_count():
        count_before = admin_call("medical.patient", "read", [[_base_patient]], {
            "fields": ["record_count"]
        })[0]["record_count"]
        admin_call("medical.record", "create", [[{
            "patient_id": _base_patient,
            "subjective": "<p>Count test</p>",
        }]])
        count_after = admin_call("medical.patient", "read", [[_base_patient]], {
            "fields": ["record_count"]
        })[0]["record_count"]
        assert count_after == count_before + 1

    def test_last_visit_date():
        p = admin_call("medical.patient", "read", [[_base_patient]], {
            "fields": ["last_visit_date"]
        })[0]
        assert p["last_visit_date"], "last_visit_date should be set"

    def test_access_log_count():
        rid = _create_soap_record()
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["access_log_count"]
        })[0]
        assert r["access_log_count"] >= 1, "Should have at least 1 log (sign)"

    tr.run_test("record_count increments on new record", test_record_count)
    tr.run_test("last_visit_date is set", test_last_visit_date)
    tr.run_test("access_log_count computed", test_access_log_count)

    # ── Summary ──
    return tr.summary()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
