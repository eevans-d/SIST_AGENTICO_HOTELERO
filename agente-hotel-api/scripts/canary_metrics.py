#!/usr/bin/env python3
"""
Simple helper to query Prometheus for P95 latency and error rate.

Usage:
  python scripts/canary_metrics.py --prom http://localhost:9090 \
    --latency 'histogram_quantile(0.95, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le))' \
    --errors 'sum(rate(pms_operations_total{status="failure"}[5m]))'
"""
import argparse
import sys
import requests


def query(prom_url: str, promql: str):
    resp = requests.get(f"{prom_url}/api/v1/query", params={"query": promql}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Prometheus error: {data}")
    result = data.get("data", {}).get("result", [])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prom", default="http://localhost:9090")
    parser.add_argument("--latency", default='histogram_quantile(0.95, sum(rate(pms_api_latency_seconds_bucket[5m])) by (le))')
    parser.add_argument("--errors", default='sum(rate(pms_operations_total{status="failure"}[5m]))')
    args = parser.parse_args()

    try:
        lat = query(args.prom, args.latency)
        err = query(args.prom, args.errors)
        print({
            "p95_latency_query": args.latency,
            "p95_latency_values": lat,
            "error_rate_query": args.errors,
            "error_rate_values": err,
        })
    except Exception as e:
        print({"error": str(e)}, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
