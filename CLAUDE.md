# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**calm-misp** demonstrates **threat-informed architecture validation** by integrating:
- **CALM** (Common Architecture Modelling Language by FINOS) — architecture as code, validated via `@finos/calm-cli`
- **MISP** (Malware Information Sharing Platform) — threat intelligence (IOCs: domains, IPs, URLs)

The CI/CD pipeline validates a CALM architecture against live MISP threat data **before** building. If any node endpoint matches a known IOC, the build fails.

## Commands

**Run MISP locally:**
```bash
docker compose -f docker/docker-compose.yml up -d
```

**Seed MISP with demo IOCs:**
```bash
MISP_URL=https://localhost MISP_API_KEY=<key> python scripts/misp_seed.py
```

**CALM structural validation:**
```bash
npm install -g @finos/calm-cli
calm validate --pattern calm/hello-world.pattern.json --architecture calm/hello-world.architecture.json
```

**MISP threat check (pre-build gate):**
```bash
MISP_URL=https://localhost MISP_API_KEY=<key> python scripts/misp_check.py calm/hello-world.architecture.json
```

**Build the Java app:**
```bash
mvn package
java -jar target/hello-world.jar   # starts on port 7070
curl localhost:7070                 # → Hello World
```

## Architecture

```
calm/hello-world.pattern.json       CALM pattern (JSON Schema — defines structure)
calm/hello-world.architecture.json  CALM instantiation (actual values — validated against pattern)
calm/controls/
  misp-threat-check.requirement.json  Control requirement: what MISP check must do
  misp-threat-check.config.json       Control config: MISP URL

scripts/misp_seed.py    Adds evil.example.com + malicious.badactor.net to MISP
scripts/misp_check.py   Reads architecture → extracts hosts → queries MISP → exit 1 if blocked

docker/docker-compose.yml   MISP stack (misp-core, misp-modules, mariadb, redis)

src/main/java/com/example/HelloWorldApp.java   Java 23 + Javalin web API (port 7070)
pom.xml                                        Maven build → target/hello-world.jar

.github/workflows/build.yml   CI: CALM validate → start MISP → seed → check → mvn package
```

## How the MISP check works

`scripts/misp_check.py`:
1. Parses the architecture JSON and extracts `host`/`url` values from node interfaces
2. For each value, calls `POST /attributes/restSearch` on MISP with `to_ids=true`
3. Exits `1` (blocks build) if any match is found; exits `0` if all clean

**Demo scenarios:**

| Architecture `host` value | In MISP? | Result |
|---|---|---|
| `api.hello-world.com` | No | ✅ Build proceeds |
| `evil.example.com` | Yes (`to_ids=true`) | ❌ Build blocked |

To test the fail case: change `host` in `calm/hello-world.architecture.json` to `evil.example.com` and re-run `misp_check.py`.

## CALM control model

CALM controls are metadata references — the CALM CLI only validates structure. Enforcement (the actual MISP query) is done by `misp_check.py` as a separate CI step. The control files (`requirement.json` / `config.json`) document the intent and configuration.
