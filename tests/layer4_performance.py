#!/usr/bin/env python3
"""
Layer 4: Performance Tests — bulk operations, timing assertions.
~10 tests total.
"""
import sys
import os
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from conftest import (
    rpc, admin_uid, admin_call, ensure_test_users,
    TestResult, RPCError, ADMIN_PASS, OdooRPC, URL, DB,
)

# Timing thresholds (seconds)
THRESHOLDS = {
    "single_patient_create": 3.0,
    "single_record_create": 3.0,
    "bulk_100_patients": 120.0,
    "bulk_50_records": 120.0,
    "patient_list_read": 3.0,
    "workflow_transition": 2.0,
    "search_complex_domain": 3.0,
}


def main():
    tr = TestResult("LAYER 4: Performance")
    print("=" * 60)
    print("LAYER 4: PERFORMANCE TESTS")
    print("=" * 60)

    uid = admin_uid()
    users = ensure_test_users()

    # Create base patient for record tests
    pid = admin_call("medical.patient", "create", [[{"name": "[L4] Perf Patient"}]])
    pid = pid[0] if isinstance(pid, list) else pid

    # ══════════════════════════════════════════════════════════════
    # 4.1 Single Operation Timing
    # ══════════════════════════════════════════════════════════════
    tr.section("4.1 Single Operation Timing")

    def test_single_patient_create_time():
        t0 = time.time()
        admin_call("medical.patient", "create", [[{"name": "[L4] Timing Patient"}]])
        elapsed = time.time() - t0
        assert elapsed < THRESHOLDS["single_patient_create"], \
            f"Patient create took {elapsed:.2f}s (threshold: {THRESHOLDS['single_patient_create']}s)"

    def test_single_record_create_time():
        t0 = time.time()
        admin_call("medical.record", "create", [[{
            "patient_id": pid,
            "subjective": "<p>Timing test</p>",
        }]])
        elapsed = time.time() - t0
        assert elapsed < THRESHOLDS["single_record_create"], \
            f"Record create took {elapsed:.2f}s (threshold: {THRESHOLDS['single_record_create']}s)"

    def test_workflow_transition_time():
        rid = admin_call("medical.record", "create", [[{
            "patient_id": pid,
            "subjective": "<p>Workflow timing</p>",
        }]])
        rid = rid[0] if isinstance(rid, list) else rid

        t0 = time.time()
        admin_call("medical.record", "action_start", [[rid]])
        elapsed_start = time.time() - t0

        t0 = time.time()
        admin_call("medical.record", "action_sign", [[rid]])
        elapsed_sign = time.time() - t0

        total = elapsed_start + elapsed_sign
        assert total < THRESHOLDS["workflow_transition"] * 2, \
            f"Workflow took {total:.2f}s (threshold: {THRESHOLDS['workflow_transition'] * 2}s)"

    def test_search_complex_domain():
        t0 = time.time()
        admin_call("medical.record", "search_read", [
            [("state", "=", "draft"), ("patient_id.name", "like", "L4")]
        ], {"fields": ["name", "state", "patient_id"], "limit": 50})
        elapsed = time.time() - t0
        assert elapsed < THRESHOLDS["search_complex_domain"], \
            f"Complex search took {elapsed:.2f}s"

    tr.run_test("Single patient create < 3s", test_single_patient_create_time)
    tr.run_test("Single record create < 3s", test_single_record_create_time)
    tr.run_test("Workflow transition < 4s total", test_workflow_transition_time)
    tr.run_test("Complex domain search < 3s", test_search_complex_domain)

    # ══════════════════════════════════════════════════════════════
    # 4.2 Bulk Operations
    # ══════════════════════════════════════════════════════════════
    tr.section("4.2 Bulk Operations")

    def test_bulk_100_patients():
        t0 = time.time()
        patient_ids = []
        for i in range(100):
            r = admin_call("medical.patient", "create", [[{
                "name": f"[L4] Bulk Patient {i:03d}",
                "phone": f"09{i:08d}",
            }]])
            r = r[0] if isinstance(r, list) else r
            patient_ids.append(r)
        elapsed = time.time() - t0
        assert len(patient_ids) == 100, f"Created {len(patient_ids)} patients, expected 100"

        # Verify sequential numbers
        patients = admin_call("medical.patient", "read", [patient_ids], {
            "fields": ["medical_no"]
        })
        numbers = sorted([int(p["medical_no"][1:]) for p in patients])
        for i in range(1, len(numbers)):
            assert numbers[i] == numbers[i - 1] + 1, \
                f"Gap in bulk patient sequence: {numbers[i-1]} -> {numbers[i]}"

        assert elapsed < THRESHOLDS["bulk_100_patients"], \
            f"Bulk 100 patients took {elapsed:.2f}s (threshold: {THRESHOLDS['bulk_100_patients']}s)"

    def test_bulk_50_records_same_day():
        t0 = time.time()
        record_ids = []
        for i in range(50):
            r = admin_call("medical.record", "create", [[{
                "patient_id": pid,
                "subjective": f"<p>Bulk record #{i}</p>",
            }]])
            r = r[0] if isinstance(r, list) else r
            record_ids.append(r)
        elapsed = time.time() - t0
        assert len(record_ids) == 50

        # Verify sequential daily numbers
        records = admin_call("medical.record", "read", [record_ids], {"fields": ["name"]})
        today = datetime.now().strftime("%Y%m%d")
        today_nums = sorted([
            int(r["name"].split("-")[1])
            for r in records
            if r["name"].startswith(today)
        ])
        for i in range(1, len(today_nums)):
            assert today_nums[i] == today_nums[i - 1] + 1, \
                f"Gap in bulk record sequence: {today_nums[i-1]} -> {today_nums[i]}"

        assert elapsed < THRESHOLDS["bulk_50_records"], \
            f"Bulk 50 records took {elapsed:.2f}s (threshold: {THRESHOLDS['bulk_50_records']}s)"

    def test_patient_list_read_100():
        t0 = time.time()
        patients = admin_call("medical.patient", "search_read", [
            [("name", "like", "[L4] Bulk")]
        ], {"fields": ["medical_no", "name", "phone", "gender", "age"], "limit": 100})
        elapsed = time.time() - t0
        assert len(patients) >= 50, f"Expected >=50 bulk patients, got {len(patients)}"
        assert elapsed < THRESHOLDS["patient_list_read"], \
            f"List read took {elapsed:.2f}s"

    def test_concurrent_patient_creation():
        """5 threads × 10 patients each = 50 patients, no gaps."""
        results = {"ids": [], "errors": []}
        lock = threading.Lock()

        def create_patients(thread_idx):
            try:
                thread_rpc = OdooRPC()
                t_uid = thread_rpc.authenticate("admin", "admin")
                for i in range(10):
                    r = thread_rpc.call(t_uid, "admin", "medical.patient", "create", [[{
                        "name": f"[L4] Concurrent T{thread_idx} P{i}",
                    }]])
                    r = r[0] if isinstance(r, list) else r
                    with lock:
                        results["ids"].append(r)
            except Exception as e:
                with lock:
                    results["errors"].append(str(e))

        threads = []
        for t in range(5):
            th = threading.Thread(target=create_patients, args=(t,))
            threads.append(th)
            th.start()

        for th in threads:
            th.join(timeout=60)

        assert not results["errors"], f"Errors during concurrent creation: {results['errors']}"
        assert len(results["ids"]) == 50, f"Expected 50, got {len(results['ids'])}"

        # Verify no duplicate medical_no
        patients = admin_call("medical.patient", "read", [results["ids"]], {
            "fields": ["medical_no"]
        })
        medical_nos = [p["medical_no"] for p in patients]
        assert len(set(medical_nos)) == len(medical_nos), \
            f"Duplicate medical_no found in concurrent creation!"

    def test_bulk_workflow():
        """Start + sign 20 records sequentially."""
        rids = []
        for i in range(20):
            r = admin_call("medical.record", "create", [[{
                "patient_id": pid,
                "subjective": f"<p>Bulk workflow #{i}</p>",
            }]])
            r = r[0] if isinstance(r, list) else r
            rids.append(r)

        t0 = time.time()
        for rid in rids:
            admin_call("medical.record", "action_start", [[rid]])
            admin_call("medical.record", "action_sign", [[rid]])
        elapsed = time.time() - t0

        # Verify all signed
        records = admin_call("medical.record", "read", [rids], {"fields": ["state"]})
        assert all(r["state"] == "signed" for r in records)
        assert elapsed < 60, f"Bulk workflow took {elapsed:.2f}s"

    tr.run_test("Bulk create 100 patients (no gaps)", test_bulk_100_patients)
    tr.run_test("Bulk create 50 records same day (no gaps)", test_bulk_50_records_same_day)
    tr.run_test("Read 100 patients list < 3s", test_patient_list_read_100)
    tr.run_test("Concurrent 5-thread patient creation (no duplicates)", test_concurrent_patient_creation)
    tr.run_test("Bulk workflow 20 records start+sign", test_bulk_workflow)

    # ── Summary ──
    return tr.summary()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
