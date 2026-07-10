---
name: cf-cli-mastery
description: >
  Master-level Cloud Foundry CF CLI skill for deploying, managing, troubleshooting, and
  operating applications on Cloud Foundry platforms. Use this skill whenever the user mentions
  cf, Cloud Foundry, cf push, cf login, PCF, TAS (Tanzu Application Service), CFAR,
  manifest.yml for CF, service brokers, buildpacks, cf spaces/orgs, Diego cells, Gorouter,
  or any Cloud Foundry platform operation. Also trigger when users ask about PaaS deployment
  workflows that involve cf commands, BOSH-managed environments, or Cloud Foundry-specific
  concepts like droplets, staging, restaging, or VCAP variables. Even if the user just says
  "deploy my app" and context suggests Cloud Foundry, use this skill.
---

# CF CLI Mastery

You are a Cloud Foundry CLI expert. Your job is to help users accomplish anything related to the `cf` CLI — from first-time deployments to production operations, troubleshooting crashed apps, designing zero-downtime deployment pipelines, managing orgs/spaces/quotas, and wiring up services.

## How to use this skill

This skill is organized in layers so you can find what you need quickly:

1. **This file (SKILL.md)** — Core workflows, decision trees, and the most important patterns. Read this first.
2. **references/commands.md** — Complete command reference organized by category. Consult when you need exact syntax, all flags for a command, or an obscure command.
3. **references/advanced.md** — Deep dives on deployment strategies, manifest files, networking, sidecars, tasks, metadata, revisions, and troubleshooting. Consult for complex scenarios.

When helping a user, think about *what they're actually trying to accomplish* rather than just answering the literal question. A user asking "how do I restart my app" might actually need a restage (if they changed a buildpack or env var that affects staging), or might need to investigate why the app keeps crashing in the first place.

## Core Mental Model

Cloud Foundry's app lifecycle has stages that matter for choosing the right command:

```
Source Code → [cf push] → Upload → Staging (buildpack + droplet) → Starting → Running
```

- **`cf restart`** — Stops and starts the app using the *existing* droplet. Fast. Use when you changed a runtime env var or just need a fresh process.
- **`cf restage`** — Re-runs staging to build a *new* droplet, then starts. Slower. Use when you changed something that affects compilation (buildpack, staging env var, stack).
- **`cf push`** — Uploads new source, stages a new droplet, and starts. The full pipeline. Use when source code changed.

This distinction matters a lot for production operations. Restaging an app unnecessarily doubles your deployment time. Restarting when you needed a restage means your env var change won't take effect.

## Authentication & Targeting

```bash
# Interactive login (preferred — doesn't leak creds in shell history)
cf login -a https://api.example.com

# Non-interactive (for CI/CD — use env vars, not -p flag)
export CF_USERNAME="deploy-bot"
export CF_PASSWORD="$SECRET"
cf api https://api.example.com
cf auth
cf target -o my-org -s production

# SSO login
cf login -a https://api.example.com --sso
```

Important: discourage users from passing `-p password` on the command line — it lands in shell history. The `CF_USERNAME`/`CF_PASSWORD` env var approach or `--sso` is safer.

## The Deployment Decision Tree

When a user wants to deploy, walk through this:

1. **First deployment or source code changed?** → `cf push`
2. **Need zero-downtime?**
   - Yes, simple case → `cf push --strategy rolling`
   - Yes, want to validate first → `cf push --strategy canary` (pauses after 1 instance for you to check)
   - Yes, need full control → Blue-green (push to new app name, `cf map-route`, validate, `cf unmap-route` old)
3. **Changed a buildpack or staging env var?** → `cf restage APP`
4. **Changed a runtime env var?** → `cf restart APP`
5. **Just need to bounce processes?** → `cf restart APP`
6. **App crashed and you want the same code running again?** → `cf restart APP` (or just `cf start APP` if it's stopped)

## Manifest.yml — Getting It Right

The manifest is the source of truth for your app's configuration. Always prefer manifest over CLI flags for reproducibility.

```yaml
---
applications:
- name: my-api
  memory: 512M
  disk_quota: 1G
  instances: 3
  buildpacks:
    - java_buildpack
  command: java -Xmx400m -jar app.jar
  stack: cflinuxfs4
  timeout: 120
  health-check-type: http
  health-check-http-endpoint: /health
  env:
    SPRING_PROFILES_ACTIVE: cloud
    LOG_LEVEL: INFO
  services:
    - my-database
    - my-cache
  routes:
    - route: my-api.apps.example.com
    - route: api.example.com/v2
  processes:
    - type: worker
      command: java -jar app.jar --worker
      memory: 256M
      instances: 2
      health-check-type: process
      no-route: true
  sidecars:
    - name: log-forwarder
      process_types: [web]
      command: ./log-forwarder
      memory: 64M
```

### Variable Substitution

Manifests support `((variable))` syntax for parameterization:

```yaml
applications:
- name: ((app-name))
  instances: ((instance-count))
  env:
    DB_URL: ((database-url))
```

Apply with: `cf push --var app-name=my-api --var instance-count=3` or `cf push --vars-file vars-production.yml`

### Key Manifest Gotchas

- `memory` is per-instance, not total. 3 instances x 512M = 1.5G of org quota.
- `routes` replaced the old `host`/`domain`/`hosts`/`domains` attributes. Use the new format.
- `no-route: true` is for worker processes that shouldn't receive HTTP traffic. Don't confuse with `random-route`.
- `buildpacks` (plural, list) replaced `buildpack` (singular). The list is ordered — last buildpack is the "final" one that sets the start command.
- `timeout` is the startup timeout in seconds. If your Java app takes 90 seconds to boot, set this higher than the default 60.

## Service Wiring

Services are how CF apps get databases, caches, message queues, etc.

```bash
# See what's available
cf marketplace
cf marketplace -e postgresql  # details for a specific service

# Create and bind
cf create-service postgresql small my-db
cf bind-service my-app my-db
cf restart my-app  # REQUIRED — binding doesn't auto-restart

# Check what got injected
cf env my-app  # look at VCAP_SERVICES
```

The bound service credentials appear in `VCAP_SERVICES` env var as JSON. Most buildpacks (Spring, Node.js, etc.) auto-detect and configure connections.

### User-Provided Services (for external resources)

```bash
# External database not in marketplace
cf create-user-provided-service my-external-db -p '{"uri":"postgres://user:pass@host:5432/db"}'

# Syslog drain
cf create-user-provided-service my-log-drain -l syslog://logs.example.com:514

# Route service (proxies traffic through a service)
cf create-user-provided-service my-rate-limiter -r https://rate-limiter.example.com
```

### Service Keys (for non-CF clients)

```bash
# Generate creds for a CI/CD tool or local dev
cf create-service-key my-db ci-key
cf service-key my-db ci-key  # view the credentials
```

## Troubleshooting Playbook

When an app is misbehaving, here's the diagnostic sequence:

```bash
# 1. What's the current state?
cf app my-app                  # instances, memory, state, routes

# 2. What happened recently?
cf events my-app               # crashes, restages, scale events

# 3. What do the logs say?
cf logs my-app --recent        # last ~1500 lines of history

# 4. Is it a staging or runtime problem?
# If the app never started → staging issue (buildpack, dependencies)
# If it started then crashed → runtime issue (code bug, OOM, port binding)

# 5. Get inside the container
cf ssh my-app                  # interactive shell
cf ssh my-app -c "ps aux"     # one-off command
cf ssh my-app -c "cat /home/vcap/staging_info.yml"  # see staging details

# 6. Check environment
cf env my-app                  # all env vars including VCAP_SERVICES

# 7. Hit the app locally from inside the container
cf ssh my-app -c "curl localhost:8080/health"

# 8. Direct API inspection
cf curl /v3/apps/$(cf app my-app --guid)/processes
```

### Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| App crashes immediately on start | Port binding — app must listen on `$PORT` | Set app to bind to `PORT` env var (e.g., `server.port=${PORT:8080}`) |
| App OOM-killed (exit code 137) | Exceeding memory limit | `cf scale my-app -m 1G` or fix memory leak |
| Staging fails "no buildpack" | Wrong buildpack or missing detection file | Specify buildpack in manifest or check detection requirements |
| "Route already exists" on push | Another app has the route | Check `cf routes`, use `--random-route` for dev, or pick a different hostname |
| 502 Bad Gateway | App taking too long to start | Increase `timeout` in manifest, check `health-check-type` config |
| "Insufficient resources" | Org/space quota exceeded | `cf org my-org` to check quota, ask admin to increase |

## Scaling

```bash
# Horizontal (more instances — preferred for stateless apps)
cf scale my-app -i 5

# Vertical (more memory/disk per instance)
cf scale my-app -m 1G -k 2G

# Check current allocation
cf app my-app
```

Horizontal scaling is instant (just starts new containers). Vertical scaling requires restart.

## Routes & Networking

```bash
# Map additional route to app (useful for blue-green)
cf map-route my-app apps.example.com --hostname api-v2

# Internal routes (container-to-container, not internet-facing)
cf map-route backend apps.internal --hostname my-backend
cf add-network-policy frontend --destination-app backend --port 8080

# TCP route (non-HTTP traffic)
cf create-route my-space tcp.example.com --port 5000
cf map-route my-tcp-app tcp.example.com --port 5000

# Clean up unused routes
cf delete-orphaned-routes -f
```

### Container-to-Container Networking

For microservices that need to talk directly (bypassing the external router):

```bash
# 1. Map an internal route
cf map-route backend apps.internal --hostname my-backend

# 2. Create a network policy allowing frontend → backend
cf add-network-policy frontend --destination-app backend --protocol tcp --port 8080

# 3. Frontend can now reach: http://my-backend.apps.internal:8080
```

## Org/Space/Role Management

```bash
# Create structure
cf create-org acme-corp
cf create-space production -o acme-corp
cf create-space staging -o acme-corp

# Assign roles (org role first, then space role)
cf set-org-role alice@example.com acme-corp OrgManager
cf set-space-role alice@example.com acme-corp production SpaceDeveloper

# Audit who has access
cf org-users acme-corp
cf space-users acme-corp production
```

Roles: `OrgManager`, `OrgAuditor`, `BillingManager` at org level. `SpaceManager`, `SpaceDeveloper`, `SpaceAuditor` at space level. A user needs at least an org role before they can get a space role.

## Using `cf curl` for API Access

When the CLI doesn't expose what you need, talk to the Cloud Controller API directly:

```bash
# List all apps (V3 API)
cf curl /v3/apps

# Get app details by GUID
cf curl /v3/apps/$(cf app my-app --guid)

# View app processes
cf curl /v3/apps/$(cf app my-app --guid)/processes

# Create a task via API
cf curl /v3/apps/$(cf app my-app --guid)/tasks -X POST -d '{"command":"rake db:migrate"}'

# Filter with query params
cf curl "/v3/apps?names=my-app&space_guids=$(cf space my-space --guid)"
```

The V3 API is the current API. V2 is deprecated but still works on older foundations.

## CF CLI Environment Variables

These control the CLI's own behavior:

| Variable | Purpose |
|----------|---------|
| `CF_HOME` | Override config directory (default: `~/.cf`) |
| `CF_TRACE` | Set to `true` or a file path to log all API requests/responses |
| `CF_USERNAME` / `CF_PASSWORD` | Non-interactive auth for CI/CD |
| `CF_DIAL_TIMEOUT` | Connection timeout in seconds |
| `CF_COLOR` | `true`/`false` to force-enable/disable colored output |

`CF_TRACE=true` is extremely valuable for debugging — it shows you exactly what API calls the CLI is making.

## Tasks (One-off Jobs)

```bash
# Run a database migration
cf run-task my-app --command "rake db:migrate" --name "db-migrate" -m 512M

# Check task status
cf tasks my-app

# Terminate a task
cf terminate-task my-app TASK_ID
```

Tasks use the same droplet as the app but run as a separate process. They don't receive HTTP traffic and terminate when the command completes.

## Metadata (Labels & Annotations)

```bash
# Label apps for filtering
cf set-label app my-app env=production team=platform
cf set-label app my-api env=staging team=backend

# Query by label
cf apps --labels "env=production"
cf apps --labels "team in (platform,backend)"

# Annotations (longer-form metadata, not queryable)
cf set-label app my-app --annotation "contact=oncall@example.com"
```

## App Revisions & Rollback

```bash
# List revisions
cf revisions my-app

# Rollback to a previous revision
cf rollback my-app --version 3

# Cancel an in-progress deployment
cf cancel-deployment my-app
```

Revisions track droplet + configuration changes. Rolling back deploys the old droplet with a rolling strategy. This is one of the safest ways to recover from a bad deployment.

## Reference Files

For detailed command syntax and advanced topics, read:
- `references/commands.md` — Full command reference with all flags and examples
- `references/advanced.md` — Deep dives on deployment strategies, manifest options, networking, Docker deployments, sidecars, troubleshooting error catalog, and more
