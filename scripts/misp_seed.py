#!/usr/bin/env python3
"""
Seeds a MISP instance with demo IOCs for the calm-misp proof-of-concept.

Adds two malicious domains that will block a build if referenced in the
CALM architecture file.

Usage:
    MISP_URL=https://localhost MISP_API_KEY=<key> python scripts/misp_seed.py

Environment variables:
    MISP_URL      Base URL of the MISP instance (default: https://localhost)
    MISP_API_KEY  MISP automation key
"""

import os
import sys
import json
import urllib.request
import urllib.error
import ssl

MISP_URL = os.environ.get("MISP_URL", "https://localhost").rstrip("/")
MISP_API_KEY = os.environ.get("MISP_API_KEY", "")

# Domains that represent known-bad infrastructure — these will block a build
MALICIOUS_DOMAINS = [
    "evil.example.com",
    "malicious.badactor.net",
]


def misp_request(path: str, payload: dict) -> dict:
    url = f"{MISP_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": MISP_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    # Skip TLS verification for the local self-signed cert
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())


def create_event() -> str:
    print("Creating MISP event...")
    payload = {
        "Event": {
            "info": "calm-misp demo — known bad infrastructure",
            "distribution": 0,
            "threat_level_id": 1,   # High
            "analysis": 2,          # Completed
        }
    }
    result = misp_request("/events/add", payload)
    event_id = result["Event"]["id"]
    print(f"  Event created: id={event_id}")
    return event_id


def add_attribute(event_id: str, domain: str) -> None:
    print(f"  Adding IOC: {domain}")
    payload = {
        "Attribute": {
            "event_id": event_id,
            "type": "domain",
            "category": "Network activity",
            "value": domain,
            "to_ids": True,
            "comment": "Known malicious domain — added by calm-misp demo seed script",
        }
    }
    misp_request(f"/attributes/add/{event_id}", payload)


def publish_event(event_id: str) -> None:
    print(f"  Publishing event {event_id}...")
    misp_request(f"/events/publish/{event_id}", {})


def main() -> None:
    if not MISP_API_KEY:
        print("ERROR: MISP_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"Seeding MISP at {MISP_URL} with {len(MALICIOUS_DOMAINS)} demo IOCs...\n")
    event_id = create_event()
    for domain in MALICIOUS_DOMAINS:
        add_attribute(event_id, domain)
    publish_event(event_id)
    print("\nDone. The following domains will now block a CALM architecture build:")
    for domain in MALICIOUS_DOMAINS:
        print(f"  - {domain}")


if __name__ == "__main__":
    main()
