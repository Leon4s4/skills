# CF CLI Advanced Topics

## Table of Contents

1. [Deployment Strategies Deep Dive](#1-deployment-strategies-deep-dive)
2. [Docker Deployments](#2-docker-deployments)
3. [Manifest Deep Dive](#3-manifest-deep-dive)
4. [Multi-Process Apps](#4-multi-process-apps)
5. [Sidecar Processes](#5-sidecar-processes)
6. [Health Check Configuration](#6-health-check-configuration)
7. [Advanced Networking](#7-advanced-networking)
8. [Application Security Groups (ASGs)](#8-application-security-groups-asgs)
9. [Droplets & Packages](#9-droplets--packages)
10. [CI/CD Patterns](#10-cicd-patterns)
11. [Troubleshooting Error Catalog](#11-troubleshooting-error-catalog)
12. [Performance Tuning](#12-performance-tuning)
13. [CF CLI v7 vs v8](#13-cf-cli-v7-vs-v8)

---

## 1. Deployment Strategies Deep Dive

### Rolling Deployment

Rolling deployment is the recommended zero-downtime strategy for most apps.

```bash
cf push my-app --strategy rolling
```

**How it works internally:**
1. CF creates new instances running the new code
2. Waits for each new instance to pass its health check
3. Routes traffic to the new instance
4. Stops an equivalent old instance
5. Repeats until all instances are replaced

**Tuning with `max-in-flight`:**
```bash
# Replace 2 instances at a time (faster but less safe)
cf push my-app --strategy rolling --max-in-flight 2
```

Default `max-in-flight` is 1. Higher values speed up deployment but reduce safety margin — if a bad instance gets through health checks, more old instances will be gone before you notice.

**Cancellation:**
```bash
cf cancel-deployment my-app
```
This reverts to the previous droplet using a rolling strategy. It's not instant — it does its own rolling replacement.

### Canary Deployment

```bash
cf push my-app --strategy canary
```

**How it works:**
1. CF deploys exactly 1 new instance
2. Deployment **pauses** — the new instance receives real traffic alongside old instances
3. You inspect logs, metrics, error rates
4. If satisfied: `cf continue-deployment my-app` (proceeds as rolling)
5. If not: `cf cancel-deployment my-app` (reverts)

This is ideal for critical services where you want human verification before full rollout.

### Blue-Green Deployment (Manual)

For maximum control, blue-green gives you two complete environments:

```bash
# Current "blue" app is running at my-app.apps.example.com

# 1. Push new version with a temporary name
cf push my-app-green -f manifest.yml --no-route

# 2. Smoke-test the green instance
cf ssh my-app-green -c "curl localhost:8080/health"

# 3. Map production route to green
cf map-route my-app-green apps.example.com --hostname my-app

# 4. Now both blue and green receive traffic — verify green is healthy

# 5. Unmap route from blue
cf unmap-route my-app apps.example.com --hostname my-app

# 6. All traffic now goes to green. If happy:
cf delete my-app -f
cf rename my-app-green my-app
```

Blue-green has the advantage of keeping the old version fully running for instant rollback (just remap routes), but it temporarily uses 2x the resources.

---

## 2. Docker Deployments

CF can deploy Docker images instead of source code:

```bash
cf push my-app --docker-image registry.example.com/org/image:tag
```

**Private registries:**
```bash
cf push my-app \
  --docker-image registry.example.com/org/image:tag \
  --docker-username myuser
# CF prompts for password, or set CF_DOCKER_PASSWORD env var
```

**In manifest:**
```yaml
applications:
- name: my-app
  docker:
    image: registry.example.com/org/image:tag
    username: myuser
  env:
    CF_DOCKER_PASSWORD: ((docker-password))
```

**Requirements:**
- The `diego_docker` feature flag must be enabled by the platform admin
- Image must listen on the `PORT` environment variable (CF injects this)
- Image must be accessible from the Diego cells (network connectivity)
- CF ignores the Dockerfile's `EXPOSE` — it sets the port via `PORT` env var

**Gotcha:** Docker apps skip buildpack staging entirely. There's no buildpack detection, no `staging_info.yml`. The droplet *is* the Docker image. This means `cf restage` re-pulls the image tag (so `:latest` will pick up new pushes to that tag).

---

## 3. Manifest Deep Dive

### All Supported Attributes

```yaml
applications:
- name: my-app                          # Required
  # Resources
  memory: 512M                          # Per-instance memory
  disk_quota: 1G                        # Per-instance disk
  log-rate-limit-per-second: 1K         # Log rate limit
  instances: 2                          # Number of instances

  # Build & Runtime
  buildpacks: [java_buildpack]          # Ordered list of buildpacks
  command: java -jar app.jar            # Override default start command
  stack: cflinuxfs4                     # Base filesystem
  docker:                               # OR deploy a Docker image
    image: myregistry/myimage:tag
    username: myuser

  # Startup
  timeout: 120                          # Startup health check timeout (seconds)
  health-check-type: http               # http | port | process
  health-check-http-endpoint: /health   # For http type
  health-check-invocation-timeout: 5    # Per-check timeout (seconds)

  # Routing
  routes:
    - route: my-app.apps.example.com
    - route: api.example.com/v2
      protocol: http2                   # http1 (default) or http2
  random-route: false
  no-route: false                       # true for workers

  # Environment & Services
  env:
    KEY: value
  services:
    - my-database
    - my-cache

  # Multi-process
  processes:
    - type: web
      instances: 3
      memory: 512M
    - type: worker
      instances: 2
      memory: 256M
      command: bundle exec sidekiq
      health-check-type: process
      no-route: true

  # Sidecars
  sidecars:
    - name: log-shipper
      process_types: [web]
      command: ./log-shipper
      memory: 64M

  # Metadata
  metadata:
    labels:
      env: production
      team: platform
    annotations:
      contact: oncall@example.com

  # Misc
  buildpack: (deprecated — use buildpacks)
  path: ./target/app.jar               # Local path to upload
  no-start: false                       # Push without starting
```

### Variable Substitution

```yaml
applications:
- name: ((app-name))
  instances: ((instances))
  env:
    DB_URL: ((db-url))
```

**Providing values:**
```bash
# Inline
cf push --var app-name=my-api --var instances=3 --var db-url=postgres://...

# From file
cf push --vars-file vars-prod.yml
```

**vars-prod.yml:**
```yaml
app-name: my-api
instances: 3
db-url: postgres://user:pass@host:5432/db
```

### Manifest Inheritance (Multiple Apps)

```yaml
---
applications:
- name: frontend
  memory: 256M
  buildpacks: [staticfile_buildpack]
  path: ./frontend/dist

- name: backend
  memory: 1G
  buildpacks: [java_buildpack]
  path: ./backend/target/app.jar
  services:
    - my-database
```

Push all: `cf push` (deploys both). Push one: `cf push frontend`.

---

## 4. Multi-Process Apps

A single app can define multiple process types with independent scaling and configuration:

```yaml
applications:
- name: my-app
  processes:
    - type: web
      instances: 3
      memory: 512M
      command: bundle exec puma -p $PORT
      health-check-type: http
      health-check-http-endpoint: /health
    - type: worker
      instances: 2
      memory: 256M
      command: bundle exec sidekiq
      health-check-type: process
      no-route: true
    - type: scheduler
      instances: 1
      memory: 128M
      command: bundle exec clockwork config/clock.rb
      health-check-type: process
      no-route: true
```

**Scaling individual processes:**
```bash
cf scale my-app --process web -i 5
cf scale my-app --process worker -i 3
```

All processes share the same droplet (code), but can have different commands, memory, instances, and health checks.

---

## 5. Sidecar Processes

Sidecars run alongside your main process in the same container. They share the filesystem and network namespace, making them ideal for log shippers, metric agents, service meshes, and config reloaders.

```yaml
sidecars:
  - name: envoy-proxy
    process_types: [web]
    command: /usr/local/bin/envoy -c /etc/envoy/config.yaml
    memory: 128M
  - name: fluentd
    process_types: [web, worker]
    command: fluentd -c /etc/fluentd/fluentd.conf
    memory: 64M
```

**Important:**
- Sidecar memory counts against the process's memory limit. A web process with 512M and a 128M sidecar has 384M available for the app.
- If a sidecar crashes, the entire container is restarted.
- Sidecars can't be scaled independently — they follow the process they're attached to.
- Sidecars can communicate with the main process via localhost.

---

## 6. Health Check Configuration

CF uses health checks to determine when an instance is ready to receive traffic and when a crashed instance should be restarted.

**Types:**

| Type | How It Works | When to Use |
|------|-------------|-------------|
| `http` | GET request to endpoint, expects 200-299 | Web apps with a health endpoint |
| `port` | TCP connection to app port | Apps that listen on a port but don't have HTTP health endpoints |
| `process` | Checks if process is running | Workers, schedulers, non-networked processes |

**Configuration:**
```bash
# Via CLI
cf set-health-check my-app http --endpoint /health --invocation-timeout 10

# Via manifest
health-check-type: http
health-check-http-endpoint: /health
health-check-invocation-timeout: 10  # seconds per check attempt
timeout: 120                         # total startup timeout
```

**Startup vs Liveness:**
- During startup: CF checks repeatedly until the health check passes or `timeout` is exceeded. If timeout is exceeded, the instance is marked crashed.
- After startup: CF checks periodically. If the check fails, the instance is marked crashed and restarted.

**Common pitfall:** Setting `timeout` too low for slow-starting apps (Java, .NET). If your app takes 90 seconds to start, set timeout to at least 120.

---

## 7. Advanced Networking

### Internal Routes (Container-to-Container)

Internal routes are only accessible from other CF apps — they don't go through the external router.

```bash
# Create internal route
cf map-route backend apps.internal --hostname my-backend

# Allow frontend to reach backend
cf add-network-policy frontend --destination-app backend --protocol tcp --port 8080

# In frontend code, call: http://my-backend.apps.internal:8080
```

**Cross-space communication:**
```bash
cf add-network-policy frontend \
  --destination-app backend \
  -s other-space \
  -o other-org \
  --protocol tcp \
  --port 8080
```

### TCP Routing

For non-HTTP protocols (databases, MQTT, custom protocols):

```bash
# Admin creates a shared TCP domain with a router group
cf create-shared-domain tcp.example.com --router-group default-tcp

# Developer creates a TCP route
cf create-route tcp.example.com --port 1883

# Map to app
cf map-route my-mqtt-app tcp.example.com --port 1883
```

### Route Services

Route services intercept requests before they reach the app — useful for rate limiting, authentication, logging.

```bash
# Create a route service (user-provided)
cf create-user-provided-service rate-limiter -r https://rate-limiter.apps.example.com

# Bind it to a route
cf bind-route-service apps.example.com rate-limiter --hostname my-app
```

Traffic flow: Client → Router → Route Service → Router → App

---

## 8. Application Security Groups (ASGs)

ASGs are IP-based firewall rules controlling outbound traffic from app containers.

**Scope:**
- **Running ASGs** — Applied to running app instances
- **Staging ASGs** — Applied during staging (buildpack compilation)
- **Default ASGs** — Applied to all apps in the foundation
- **Space-scoped ASGs** — Applied to apps in specific spaces

**Typical setup pattern:**

1. Create restrictive default ASGs (block everything except necessary):
```json
[
  {"protocol": "tcp", "destination": "0.0.0.0/0", "ports": "443", "description": "HTTPS outbound"},
  {"protocol": "tcp", "destination": "10.0.0.0/8", "ports": "3306,5432,6379", "description": "Internal DBs"}
]
```

2. Apply as default: `cf bind-running-security-group my-default-asg`

3. Create space-specific ASGs for teams that need additional access:
```bash
cf bind-security-group additional-access my-org my-space --lifecycle running
```

**Important:** ASGs are additive — you can't use them to deny traffic that another ASG allows. If the default ASG allows 0.0.0.0/0:443, a space ASG can't restrict that.

---

## 9. Droplets & Packages

Understanding the internal model helps with advanced operations:

```
Source Code → Package → (Staging via Buildpack) → Droplet → (Start) → Running Instance
```

- **Package** — The uploaded source code or Docker image reference
- **Droplet** — The compiled, runnable artifact (tarball of compiled code + runtime deps)

```bash
# List droplets for an app
cf droplets my-app

# List packages
cf packages my-app

# Via API: create a droplet from a specific package
cf curl /v3/builds -X POST -d '{"package":{"guid":"PACKAGE_GUID"}}'
```

Droplets are what revisions track. When you `cf rollback`, you're deploying a previous droplet.

---

## 10. CI/CD Patterns

### Basic Pipeline Script

```bash
#!/bin/bash
set -euo pipefail

# Auth (use env vars, not CLI flags)
export CF_USERNAME="$DEPLOY_USER"
export CF_PASSWORD="$DEPLOY_PASSWORD"
cf api "$CF_API" --skip-ssl-validation
cf auth
cf target -o "$CF_ORG" -s "$CF_SPACE"

# Deploy with rolling strategy
cf push my-app \
  --strategy rolling \
  --vars-file "vars-${ENVIRONMENT}.yml"

echo "Deployment complete"
```

### Blue-Green Pipeline

```bash
#!/bin/bash
set -euo pipefail

APP_NAME="my-app"
GREEN_NAME="${APP_NAME}-green"
DOMAIN="apps.example.com"

# Push green (no route)
cf push "$GREEN_NAME" -f manifest.yml --no-route

# Smoke test
cf ssh "$GREEN_NAME" -c "curl -sf localhost:\$PORT/health" || {
  echo "Health check failed, deleting green"
  cf delete "$GREEN_NAME" -f
  exit 1
}

# Switch traffic
cf map-route "$GREEN_NAME" "$DOMAIN" --hostname "$APP_NAME"
cf unmap-route "$APP_NAME" "$DOMAIN" --hostname "$APP_NAME"

# Cleanup
cf delete "$APP_NAME" -f
cf rename "$GREEN_NAME" "$APP_NAME"
```

### Database Migration Pattern

```bash
# Run migration as a task before deployment
cf run-task my-app --command "rake db:migrate" --name "pre-deploy-migrate" -m 1G

# Wait for task to complete
while true; do
  STATUS=$(cf tasks my-app | grep "pre-deploy-migrate" | awk '{print $3}')
  if [ "$STATUS" = "SUCCEEDED" ]; then break; fi
  if [ "$STATUS" = "FAILED" ]; then echo "Migration failed"; exit 1; fi
  sleep 5
done

# Now deploy
cf push my-app --strategy rolling
```

---

## 11. Troubleshooting Error Catalog

### Staging Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Staging error: no matching buildpack` | CF can't detect the app type | Specify `buildpacks` in manifest; check detection files (e.g., `package.json`, `pom.xml`) |
| `Staging error: insufficient resources` | Not enough Diego cell capacity | Ask admin to scale; reduce memory in manifest |
| `Staging timed out` | Compilation takes too long | Increase staging timeout (admin setting); use a pre-compiled artifact |
| `Buildpack compile failed` | Dependency resolution or compilation error | Check `cf logs APP --recent` for staging logs; fix dependencies |

### Runtime Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Process has crashed` | App exited non-zero | `cf logs APP --recent` — look for exceptions; `cf ssh APP` to inspect |
| `Instance crashed with exit description: OOM` | Out of memory | `cf scale APP -m 1G`; investigate memory leaks |
| `Start unsuccessful` | App didn't pass health check in time | Increase `timeout`; check `health-check-type` and endpoint |
| `App instance exited` with port error | App not binding to `$PORT` | Configure app to listen on `PORT` env var |

### Route Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `The route is already in use` | Another app owns this route | `cf routes` to find the owner; use different hostname |
| `502 Bad Gateway` | App isn't responding on its port | Check app health; ensure correct `PORT` binding; increase timeout |
| `404 Not Found` from router | Route exists but no app is mapped | `cf map-route APP DOMAIN --hostname HOST` |

### Service Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Service instance not found` | Wrong name or wrong space | `cf target -s SPACE`; `cf services` to check |
| `Binding failed` | Service broker error or plan restriction | Check `cf service INSTANCE` for status; contact admin |
| `VCAP_SERVICES empty after bind` | App not restarted | `cf restart APP` after binding |

### Auth Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Not authenticated` | Token expired | `cf login` again |
| `Not authorized` | Insufficient role | Need `SpaceDeveloper` for push; ask admin for role |
| `API endpoint not set` | No `cf api` was run | `cf api https://api.example.com` |

---

## 12. Performance Tuning

### Memory Sizing

Start conservative and adjust based on monitoring:

| App Type | Starting Memory | Notes |
|----------|----------------|-------|
| Static site (nginx) | 64-128M | Very lightweight |
| Node.js | 256-512M | Watch for memory leaks |
| Python/Ruby | 256-512M | Worker processes multiply usage |
| Java (Spring Boot) | 768M-1G | JVM overhead; set `-Xmx` to 50-75% of limit |
| .NET Core | 256-512M | Generally efficient |

**Monitoring usage:**
```bash
cf app my-app  # Shows memory usage per instance
```

If you're consistently using >80% of memory, scale up. If <30%, scale down.

### Instance Count Strategy

- **Minimum 2 instances** for production (1 instance = zero redundancy during restarts)
- Scale based on traffic, not CPU (CF doesn't expose CPU metrics via CLI)
- Use autoscaler if available: `cf bind-service my-app autoscaler`

### Disk Quota

Default is usually 1G. Increase if your app writes temp files, caches, or has large dependencies:
```bash
cf scale my-app -k 2G
```

### Log Rate Limiting

If your app generates excessive logs (hurting platform performance):
```bash
cf scale my-app -l 1K  # Limit to 1KB/sec per instance
```

---

## 13. CF CLI v7 vs v8

**Key differences in v8:**
- V3 API is the default (v7 used V2 for many commands)
- `--strategy rolling` and `--strategy canary` are first-class push flags
- Service operations are async by default (use `-w` or `--wait` to wait)
- `cf service` output includes "last operation" status
- Label selector support: `cf apps --labels "env=production"`
- `cf rollback` command for reverting to previous revisions
- `cf continue-deployment` for canary workflows
- Improved `cf push` with better manifest support
- `--max-in-flight` for rolling deployments

**Upgrade path:** v7 → v8 is generally smooth. Main change is that service commands that were synchronous are now async. Scripts that do `cf create-service && cf bind-service` need to either add `-w` or poll for completion.

```bash
# v7 style (synchronous)
cf create-service postgres small mydb
cf bind-service my-app mydb

# v8 style (async — need to wait)
cf create-service postgres small mydb -w
cf bind-service my-app mydb -w
```
