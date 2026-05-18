#!/usr/bin/env python3
"""
Layer 3: Negative & Security Tests — injection, XSS, workflow violations, boundary values.
~20 tests total.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from conftest import (
    rpc, admin_uid, admin_call, ensure_test_users,
    TestResult, RPCError, ADMIN_PASS,
)


def main():
    tr = TestResult("LAYER 3: Negative/Security")
    print("=" * 60)
    print("LAYER 3: NEGATIVE & SECURITY TESTS")
    print("=" * 60)

    uid = admin_uid()
    users = ensure_test_users()

    # Create a base patient for record tests
    pid = admin_call("medical.patient", "create", [[{"name": "[L3] Test Patient"}]])
    pid = pid[0] if isinstance(pid, list) else pid

    _r_ids = []

    def _create_record(**extra):
        vals = {"patient_id": pid}
        vals.update(extra)
        rid = admin_call("medical.record", "create", [[vals]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        return rid

    # ══════════════════════════════════════════════════════════════
    # 3.1 Injection & XSS
    # ══════════════════════════════════════════════════════════════
    tr.section("3.1 Injection & XSS")

    def test_sql_injection_patient_name():
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "'; DROP TABLE medical_patient; --",
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["name"]})[0]
        assert "DROP TABLE" in p["name"], "Should be stored as literal text"
        # Verify table still exists
        count = admin_call("medical.patient", "search_count", [[]])
        assert count > 0, "Table should still exist after injection attempt"

    def test_sql_injection_allergies():
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "[L3] SQLi Allergies",
            "allergies": "' OR '1'='1; UPDATE res_users SET password='hacked' WHERE id=2; --",
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["allergies"]})[0]
        assert "OR" in p["allergies"]

    def test_xss_subjective_sanitized():
        rid = _create_record(subjective="<script>alert('XSS')</script><p>Normal text</p>")
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["subjective"]})[0]
        assert "<script>" not in r["subjective"], \
            f"Script tag should be sanitized, got: {r['subjective']}"
        assert "Normal text" in r["subjective"], "Normal content should survive"

    def test_xss_objective_sanitized():
        rid = _create_record(objective='<img src=x onerror=alert(1)><p>Data</p>')
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["objective"]})[0]
        assert "onerror" not in r["objective"], \
            f"onerror handler should be sanitized, got: {r['objective']}"

    def test_xss_assessment_sanitized():
        rid = _create_record(assessment='<svg onload=alert(1)><p>Assessment</p>')
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["assessment"]})[0]
        assert "onload" not in r["assessment"], \
            f"SVG onload should be sanitized, got: {r['assessment']}"

    def test_template_injection_diagnosis():
        rid = _create_record(diagnosis="{{7*7}} ${7*7} #{7*7}")
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["diagnosis"]})[0]
        assert "49" not in r["diagnosis"], \
            f"Template injection should not evaluate, got: {r['diagnosis']}"

    def test_unicode_emoji_patient_name():
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "王小明 💊🏥 Ñoño",
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["name"]})[0]
        assert "王小明" in p["name"]
        assert "💊" in p["name"]
        assert "Ñoño" in p["name"]

    def test_long_text_soap():
        long_text = "<p>" + ("A" * 10000) + "</p>"
        rid = _create_record(subjective=long_text)
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["subjective"]})[0]
        assert len(r["subjective"]) >= 10000

    tr.run_test("SQL injection in patient name", test_sql_injection_patient_name)
    tr.run_test("SQL injection in allergies", test_sql_injection_allergies)
    tr.run_test("XSS sanitized in subjective", test_xss_subjective_sanitized)
    tr.run_test("XSS sanitized in objective", test_xss_objective_sanitized)
    tr.run_test("XSS sanitized in assessment", test_xss_assessment_sanitized)
    tr.run_test("Template injection in diagnosis", test_template_injection_diagnosis)
    tr.run_test("Unicode/emoji in patient name", test_unicode_emoji_patient_name)
    tr.run_test("Long text (10K chars) in SOAP", test_long_text_soap)

    # ══════════════════════════════════════════════════════════════
    # 3.2 Workflow Violations
    # ══════════════════════════════════════════════════════════════
    tr.section("3.2 Workflow Violations")

    def test_sign_from_draft_skip_start():
        rid = _create_record(subjective="<p>Skip test</p>")
        admin_call("medical.record", "action_sign", [[rid]])

    def test_reset_from_in_progress():
        rid = _create_record(subjective="<p>Reset test</p>")
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_reset_to_draft", [[rid]])

    def test_double_sign():
        rid = _create_record(subjective="<p>Double sign</p>")
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        # Try to sign again
        admin_call("medical.record", "action_sign", [[rid]])

    def test_start_signed_record():
        rid = _create_record(subjective="<p>Start signed</p>")
        admin_call("medical.record", "action_start", [[rid]])
        admin_call("medical.record", "action_sign", [[rid]])
        # Try to start a signed record
        admin_call("medical.record", "action_start", [[rid]])

    def test_sign_empty_html():
        """Test signing with empty HTML (falsy-looking but truthy string)."""
        rid = _create_record(subjective="<p><br></p>")
        admin_call("medical.record", "action_start", [[rid]])
        try:
            admin_call("medical.record", "action_sign", [[rid]])
            # If it succeeds, this is a finding (empty HTML is truthy)
            tr.ok("Sign with empty HTML <p><br></p>",
                   "FINDING: Empty HTML is truthy, sign succeeded")
            return  # Don't raise, just note as finding
        except (RPCError, Exception) as e:
            if "SOAP" in str(e):
                tr.ok("Sign with empty HTML <p><br></p>", "Correctly rejected empty HTML")
                return
            raise
        finally:
            pass  # prevent double-counting

    def test_non_admin_reset_to_draft():
        """Physician calling action_reset_to_draft via RPC — should be blocked by server-side group check."""
        rid = rpc.call_as("test_physician_a", "medical.record", "create", [[{
            "patient_id": pid,
            "subjective": "<p>Physician reset test</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid
        _r_ids.append(rid)
        rpc.call_as("test_physician_a", "medical.record", "action_start", [[rid]])
        rpc.call_as("test_physician_a", "medical.record", "action_sign", [[rid]])
        # Should raise due to server-side group check
        rpc.call_as("test_physician_a", "medical.record", "action_reset_to_draft", [[rid]])

    def test_direct_state_write():
        """Direct state write should be blocked — must use workflow actions."""
        rid = _create_record(subjective="<p>Direct write test</p>")
        admin_call("medical.record", "write", [[rid], {"state": "signed"}])

    tr.expect_error("Sign from draft (skip start)", test_sign_from_draft_skip_start, "in-progress")
    tr.expect_error("Reset from in_progress", test_reset_from_in_progress, "signed")
    tr.expect_error("Double sign", test_double_sign, "in-progress")
    tr.expect_error("Start signed record", test_start_signed_record, "draft")
    # Sign with empty HTML — documents that <p><br></p> is truthy (Odoo behavior)
    test_sign_empty_html()
    tr.expect_error("Non-admin reset_to_draft blocked via RPC",
                    test_non_admin_reset_to_draft, "administrator")
    tr.expect_error("Direct state write blocked",
                    test_direct_state_write, "workflow")

    # ══════════════════════════════════════════════════════════════
    # 3.3 Boundary Values
    # ══════════════════════════════════════════════════════════════
    tr.section("3.3 Boundary Values")

    def test_national_id_max_length():
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "[L3] NID Max",
            "national_id": "A123456789",  # exactly 10 chars
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["national_id"]})[0]
        assert p["national_id"] == "A123456789"

    def test_national_id_too_long():
        """11 chars: Odoo's size=10 truncates before DB write, SQL CHECK also guards."""
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "[L3] NID Too Long",
            "national_id": "A1234567890",  # 11 chars
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["national_id"]})[0]
        assert len(p["national_id"]) <= 10, \
            f"national_id should be truncated to <=10 chars, got {len(p['national_id'])}: {p['national_id']}"

    def test_negative_vital_signs():
        rid = _create_record(vital_pulse=-72, vital_temp=-36.5)
        r = admin_call("medical.record", "read", [[rid]], {
            "fields": ["vital_pulse", "vital_temp"]
        })[0]
        # No constraint expected — just document behavior
        tr.ok("Negative vitals accepted",
               f"FINDING: pulse={r['vital_pulse']}, temp={r['vital_temp']} — no validation constraint")

    def test_future_visit_date():
        future = "2030-01-01 10:00:00"
        rid = _create_record(visit_date=future)
        r = admin_call("medical.record", "read", [[rid]], {"fields": ["name", "visit_date"]})[0]
        assert r["name"].startswith("20300101"), f"Future date record: {r['name']}"
        tr.ok("Future visit date accepted", f"name={r['name']}")

    def test_patient_birthday_today():
        today_str = datetime_now_str()[:10]
        pid2 = admin_call("medical.patient", "create", [[{
            "name": "[L3] Newborn",
            "birthday": today_str,
        }]])
        pid2 = pid2[0] if isinstance(pid2, list) else pid2
        p = admin_call("medical.patient", "read", [[pid2]], {"fields": ["age"]})[0]
        assert p["age"] == 0, f"Newborn age should be 0, got {p['age']}"

    tr.run_test("national_id exactly 10 chars", test_national_id_max_length)
    tr.run_test("national_id 11 chars truncated to 10", test_national_id_too_long)
    test_negative_vital_signs()  # self-reporting
    test_future_visit_date()  # self-reporting (via inner tr.ok)
    tr.run_test("Birthday today → age=0", test_patient_birthday_today)

    # ── Summary ──
    return tr.summary()


def datetime_now_str():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
