#!/usr/bin/env python3
"""
Master Test Runner — runs all test layers and produces a summary.
Usage: python3 tests/run_all.py [--layer N]
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))


def run_layer(name, module_name):
    """Import and run a test layer module."""
    print(f"\n{'#' * 60}")
    print(f"# {name}")
    print(f"{'#' * 60}")
    try:
        mod = __import__(module_name)
        return mod.main()
    except Exception as e:
        print(f"\nFATAL ERROR in {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Enterprise Acceptance Test Runner")
    parser.add_argument("--layer", type=int, help="Run specific layer (1,3,4,5)")
    args = parser.parse_args()

    start_time = time.time()
    results = {}

    layers = {
        1: ("Layer 1: API/Backend", "layer1_api"),
        3: ("Layer 3: Negative/Security", "layer3_negative"),
        4: ("Layer 4: Performance", "layer4_performance"),
        5: ("Layer 5: Data Integrity", "layer5_integrity"),
    }

    if args.layer:
        if args.layer not in layers:
            print(f"Unknown layer: {args.layer}. Available: {list(layers.keys())}")
            return 1
        name, mod = layers[args.layer]
        results[args.layer] = run_layer(name, mod)
    else:
        for layer_num in sorted(layers.keys()):
            name, mod = layers[layer_num]
            results[layer_num] = run_layer(name, mod)

    elapsed = time.time() - start_time

    # ── Grand Summary ──
    print(f"\n{'=' * 60}")
    print("ENTERPRISE ACCEPTANCE TEST — GRAND SUMMARY")
    print(f"{'=' * 60}")
    all_pass = True
    for layer_num in sorted(results.keys()):
        name = layers[layer_num][0]
        status = "PASSED" if results[layer_num] else "FAILED"
        icon = "  " if results[layer_num] else ">>"
        print(f"  {icon} {name}: {status}")
        if not results[layer_num]:
            all_pass = False

    print(f"\n  Total time: {elapsed:.1f}s")
    print(f"\n  {'ALL LAYERS PASSED — DEPLOYMENT READY' if all_pass else 'SOME LAYERS FAILED — NOT READY'}")
    print(f"{'=' * 60}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
