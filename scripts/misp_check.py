#!/usr/bin/env python3
"""
Pre-build MISP threat intelligence check for CALM architectures.

Reads a CALM architecture JSON file, extracts all host/domain values from
node interfaces, then queries a MISP instance for each. Exits with a
non-zero code if any value matches a known IOC (to_ids=true), blocking
the build.

Usage:
    MISP_URL=https://localhost MISP_API_KEY=<key> \
        python scripts/misp_check.py calm/hello-world.architecture.json

Environment variables:
    MISP_URL      Base URL of the MISP instance (default: https://localhost)
    MISP_API_KEY  MISP automation key
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request


MISP_URL = os.environ.get("MISP_URL", "https://localhost").rstrip("/")
MISP_API_KEY = os.environ.get("MISP_API_KEY", "")


def extract_indicators(architecture: dict) -> list[str]:
    """Walk the architecture and collect host/url values from node interfaces."""
    indicators = []
    for node in architecture.get("nodes", []):
        for iface in node.get("interfaces", []):
            for field in ("host", "url", "hostname", "address"):
                value = iface.get(field)
                if value and isinstance(value, str):
                    indicators.append(value)
    return list(set(indicators))


def query_misp(value: str) -> list[dict]:
    """Search MISP for an exact attribute match. Returns matching attributes."""
    url = f"{MISP_URL}/attributes/restSearch"
    payload = {
        "returnFormat": "json",
        "value": value,
        "type": "domain",
        "to_ids": True,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": MISP_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx) as resp:
        result = json.loads(resp.read())
    return result.get("response", {}).get("Attribute", [])


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <architecture-file>", file=sys.stderr)
        sys.exit(1)

    arch_file = sys.argv[1]
    if not MISP_API_KEY:
        print("ERROR: MISP_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    with open(arch_file) as f:
        architecture = json.load(f)

    indicators = extract_indicators(architecture)
    if not indicators:
        print("No indicators found in architecture. Nothing to check.")
        sys.exit(0)

    print(f"Checking {len(indicators)} indicator(s) against MISP at {MISP_URL}...")
    blocked = []

    for indicator in indicators:
        print(f"  Checking: {indicator} ... ", end="", flush=True)
        try:
            matches = query_misp(indicator)
        except urllib.error.URLError as e:
            print(f"\nERROR: Could not reach MISP at {MISP_URL}: {e}", file=sys.stderr)
            sys.exit(2)

        if matches:
            print("BLOCKED (found in MISP IOC database)")
            blocked.append(indicator)
        else:
            print("clean")

    if blocked:
        print(
            f"\n[FAIL] Build blocked. {len(blocked)} indicator(s) matched known threats in MISP:",
            file=sys.stderr,
        )
        for b in blocked:
            print(f"  - {b}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[PASS] All {len(indicators)} indicator(s) are clean. Proceeding with build.")


if __name__ == "__main__":
    main()
