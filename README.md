# calm-misp

A proof-of-concept demonstrating **threat-informed architecture validation** — CALM architecture models validated against live MISP threat intelligence data before every build.

> "CALM and MISP should be friends."

## What this does

[CALM](https://calm.finos.org/) (Common Architecture Modelling Language by FINOS) lets you define software architecture as code. [MISP](https://www.misp-project.org/) stores Indicators of Compromise (IOCs) — known-malicious domains, IPs, and URLs.

This project wires the two together: when you build, a pre-build gate reads your CALM architecture file, extracts every external endpoint, and checks them against live MISP threat data. If any endpoint is a known IOC, **the build fails**.

```
CALM architecture file
        │
        ▼
  Extract hosts/domains from node interfaces
        │
        ▼
  Query MISP REST API  ──► IOC found (to_ids=true)?
        │                         │
        │ No                      │ Yes
        ▼                         ▼
  ✅ Build proceeds          ❌ Build blocked
```

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (`npm`)
- Python 3.11+
- Java 23 + Maven

## Quick start

### 1. Start MISP

```bash
docker compose -f docker/docker-compose.yml up -d
```

Wait ~2 minutes for MISP to initialise, then open [https://localhost](https://localhost).
Default credentials: `admin@admin.test` / `admin`.

### 2. Get your MISP API key

Log in to MISP → top-right menu → **My Profile** → copy the **Automation key**.

### 3. Seed demo IOCs

```bash
MISP_URL=https://localhost MISP_API_KEY=<your-key> python scripts/misp_seed.py
```

This adds two malicious domains to MISP:
- `evil.example.com`
- `malicious.badactor.net`

### 4. Validate the CALM architecture

```bash
npm install -g @finos/calm-cli
calm validate \
  --pattern calm/hello-world.pattern.json \
  --architecture calm/hello-world.architecture.json
```

### 5. Run the MISP threat check

```bash
MISP_URL=https://localhost MISP_API_KEY=<your-key> \
  python scripts/misp_check.py calm/hello-world.architecture.json
```

Expected output (the architecture uses `api.hello-world.com`, which is not in MISP):

```
Checking 1 indicator(s) against MISP at https://localhost...
  Checking: api.hello-world.com ... clean

[PASS] All 1 indicator(s) are clean. Proceeding with build.
```

### 6. Build and run the Hello World API

```bash
mvn package
java -jar target/hello-world.jar
curl localhost:7070   # → Hello World
```

## Demo: blocking a build

Edit `calm/hello-world.architecture.json` and change the service host to a known-bad domain:

```json
"host": "evil.example.com"
```

Re-run the threat check:

```bash
MISP_URL=https://localhost MISP_API_KEY=<your-key> \
  python scripts/misp_check.py calm/hello-world.architecture.json
```

Expected output:

```
Checking 1 indicator(s) against MISP at https://localhost...
  Checking: evil.example.com ... BLOCKED (found in MISP IOC database)

[FAIL] Build blocked. 1 indicator(s) matched known threats in MISP:
  - evil.example.com
```

## Repository layout

```
calm/
  hello-world.pattern.json        CALM pattern (reusable, JSON Schema)
  hello-world.architecture.json   CALM instantiation (concrete values)
  controls/
    misp-threat-check.requirement.json   Control requirement definition
    misp-threat-check.config.json        Control configuration (MISP URL)

docker/
  docker-compose.yml    MISP stack (core, modules, MariaDB, Redis)

scripts/
  misp_seed.py    Populates MISP with demo IOCs
  misp_check.py   Pre-build gate — queries MISP, exits 1 if blocked

src/main/java/com/example/
  HelloWorldApp.java    Javalin web API on port 7070

.github/workflows/
  build.yml    CI: CALM validate → MISP check → mvn package
```

## How CALM controls fit in

The `calm/controls/` files document the intent of the MISP check in CALM's control model. The CALM CLI validates structural compliance (nodes, relationships, interfaces). The actual threat intelligence enforcement is performed by `scripts/misp_check.py` as a separate CI step — this is the extension point that could be published to [CALM Hub](https://calm.finos.org/) for reuse across teams.

## CI/CD

Pushing to `main` (or opening a PR) triggers the GitHub Actions workflow (`.github/workflows/build.yml`):

1. CALM structural validation
2. Start MISP via Docker Compose
3. Seed IOCs
4. MISP threat check — blocks if any architecture endpoint is a known IOC
5. `mvn package`
