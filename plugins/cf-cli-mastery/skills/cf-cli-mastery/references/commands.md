# CF CLI Complete Command Reference

## Table of Contents

1. [Authentication & Targeting](#1-authentication--targeting)
2. [App Lifecycle](#2-app-lifecycle)
3. [App Inspection](#3-app-inspection)
4. [Scaling](#4-scaling)
5. [Environment Variables](#5-environment-variables)
6. [Services](#6-services)
7. [User-Provided Services](#7-user-provided-services)
8. [Service Keys](#8-service-keys)
9. [Routes & Domains](#9-routes--domains)
10. [Network Policies](#10-network-policies)
11. [Orgs & Spaces](#11-orgs--spaces)
12. [Roles & Users](#12-roles--users)
13. [Quotas](#13-quotas)
14. [Buildpacks](#14-buildpacks)
15. [Stacks](#15-stacks)
16. [Security Groups](#16-security-groups)
17. [Feature Flags](#17-feature-flags)
18. [Tasks](#18-tasks)
19. [SSH](#19-ssh)
20. [Logs & Events](#20-logs--events)
21. [Labels & Annotations](#21-labels--annotations)
22. [Revisions & Rollback](#22-revisions--rollback)
23. [Plugins](#23-plugins)
24. [cf curl](#24-cf-curl)
25. [Miscellaneous](#25-miscellaneous)

---

## 1. Authentication & Targeting

```
cf api API_URL [--skip-ssl-validation]
```
Set or view the target API endpoint. `--skip-ssl-validation` for self-signed certs (dev only).

```
cf login [-a API_URL] [-u USERNAME] [-p PASSWORD] [-o ORG] [-s SPACE] [--sso] [--sso-passcode CODE]
```
Interactive login. Prefer not passing `-p` (shell history). Use `--sso` for single sign-on flows.

```
cf auth [USERNAME PASSWORD] [--client-credentials]
```
Non-interactive auth. Reads `CF_USERNAME`/`CF_PASSWORD` env vars if args omitted. `--client-credentials` for OAuth client credentials grant.

```
cf target [-o ORG] [-s SPACE]
```
Set or view targeted org/space. Omit flags to see current target.

```
cf logout
```

```
cf oauth-token
```
Print the current OAuth token. Useful for scripting API calls outside the CLI.

---

## 2. App Lifecycle

```
cf push [APP_NAME] [flags]
```

**Key flags:**
| Flag | Description |
|------|-------------|
| `-f MANIFEST` | Path to manifest file (default: `./manifest.yml`) |
| `-p PATH` | Path to app source directory or archive |
| `-b BUILDPACK` | Buildpack (repeatable for multi-buildpack) |
| `-c COMMAND` | Custom start command |
| `-i INSTANCES` | Number of instances |
| `-m MEMORY` | Memory per instance (e.g., `512M`, `1G`) |
| `-k DISK` | Disk quota per instance |
| `-l LOG_RATE` | Log rate limit per second |
| `-s STACK` | Stack to use |
| `-t TIMEOUT` | Startup timeout in seconds |
| `-d DOMAIN` | Domain for default route |
| `--hostname HOST` | Hostname for default route |
| `--path PATH` | URL path for route |
| `--no-route` | Don't create or map any route |
| `--random-route` | Generate random route name |
| `--no-start` | Push but don't start the app |
| `--no-wait` | Return immediately (async push) |
| `--strategy rolling` | Rolling zero-downtime deployment |
| `--strategy canary` | Canary deployment (pause after 1 instance) |
| `--max-in-flight N` | Max instances to update simultaneously (rolling/canary) |
| `--var KEY=VALUE` | Variable substitution for manifest |
| `--vars-file FILE` | YAML file for variable substitution |
| `--docker-image IMAGE` | Deploy Docker image instead of source |
| `--docker-username USER` | Docker registry username |
| `--task` | Push as task-only (no web process) |

```
cf start APP
cf stop APP
cf restart APP         # Restarts with existing droplet
cf restage APP         # Rebuilds droplet then restarts
cf delete APP [-f] [-r]   # -f = force, -r = also delete routes
cf rename APP NEW_NAME
```

```
cf continue-deployment APP
```
Resume a paused canary deployment.

```
cf cancel-deployment APP
```
Cancel in-progress rolling/canary deployment, revert to previous droplet.

---

## 3. App Inspection

```
cf apps                    # List all apps in current space
cf app APP                 # Detailed app info (instances, memory, routes, state)
cf app APP --guid          # Print just the app GUID
```

---

## 4. Scaling

```
cf scale APP [-i INSTANCES] [-m MEMORY] [-k DISK] [-l LOG_RATE] [-f]
```
`-f` forces restart for memory/disk changes without confirmation.

---

## 5. Environment Variables

```
cf env APP                              # View all env vars (user, VCAP_APPLICATION, VCAP_SERVICES, system)
cf set-env APP VAR_NAME VAR_VALUE       # Set user env var (requires cf restart to take effect)
cf unset-env APP VAR_NAME               # Remove user env var
```

**System-wide env var groups (admin):**
```
cf running-environment-variable-group
cf set-running-environment-variable-group '{"KEY":"VALUE"}'
cf staging-environment-variable-group
cf set-staging-environment-variable-group '{"KEY":"VALUE"}'
```

---

## 6. Services

```
cf marketplace [-e SERVICE]            # List available services; -e for plan details
cf services                            # List service instances in current space
cf service SERVICE_INSTANCE            # Detailed service info
```

```
cf create-service SERVICE PLAN INSTANCE [-c PARAMS_JSON] [-t TAGS] [-b BROKER] [-w]
```
`-c` can be inline JSON or `@file.json`. `-w` waits for async creation.

```
cf update-service INSTANCE [-p NEW_PLAN] [-c PARAMS_JSON] [-t TAGS] [--upgrade] [-w]
cf delete-service INSTANCE [-f] [-w]
cf rename-service INSTANCE NEW_NAME
```

```
cf bind-service APP INSTANCE [-c BIND_PARAMS_JSON]
cf unbind-service APP INSTANCE
```
Binding injects credentials into `VCAP_SERVICES`. Requires `cf restart` to pick up changes.

```
cf share-service INSTANCE -s OTHER_SPACE [-o OTHER_ORG]
cf unshare-service INSTANCE -s OTHER_SPACE [-o OTHER_ORG]
```
Share a service instance across spaces.

---

## 7. User-Provided Services

```
cf create-user-provided-service INSTANCE -p CREDENTIALS
cf create-user-provided-service INSTANCE -p "host, port, dbname"   # Interactive prompts
cf create-user-provided-service INSTANCE -p @creds.json
cf create-user-provided-service INSTANCE -l syslog://host:port     # Log drain
cf create-user-provided-service INSTANCE -r https://route-service  # Route service
cf create-user-provided-service INSTANCE -t "tag1, tag2"           # Tags
```

```
cf update-user-provided-service INSTANCE [-p CREDS] [-l SYSLOG_URL] [-r ROUTE_URL] [-t TAGS]
```

---

## 8. Service Keys

```
cf create-service-key INSTANCE KEY_NAME [-c PARAMS_JSON]
cf service-keys INSTANCE
cf service-key INSTANCE KEY_NAME
cf delete-service-key INSTANCE KEY_NAME [-f]
```
Service keys generate credentials for use outside CF (CI/CD, local dev, external apps).

---

## 9. Routes & Domains

```
cf routes                              # List routes in current space
cf create-route DOMAIN [--hostname H] [--path P] [--port PORT]
cf map-route APP DOMAIN [--hostname H] [--path P] [--port PORT]
cf unmap-route APP DOMAIN [--hostname H] [--path P] [--port PORT]
cf delete-route DOMAIN [--hostname H] [--path P] [--port PORT] [-f]
cf check-route DOMAIN [--hostname H] [--path P]
cf delete-orphaned-routes [-f]
```

```
cf domains                             # List all domains
cf create-private-domain ORG DOMAIN
cf delete-private-domain DOMAIN [-f]
cf create-shared-domain DOMAIN [--router-group RG] [--internal]
cf delete-shared-domain DOMAIN [-f]
```

**Route examples:**
| Command | Resulting URL |
|---------|---------------|
| `cf create-route example.com` | `example.com` |
| `cf create-route example.com --hostname api` | `api.example.com` |
| `cf create-route example.com --hostname api --path v2` | `api.example.com/v2` |
| `cf create-route tcp.example.com --port 5000` | `tcp.example.com:5000` |

---

## 10. Network Policies

```
cf network-policies [--source APP]
cf add-network-policy SOURCE_APP --destination-app DEST_APP [--protocol tcp|udp] [--port RANGE] [-s SPACE] [-o ORG]
cf remove-network-policy SOURCE_APP --destination-app DEST_APP [--protocol tcp|udp] [--port RANGE] [-s SPACE] [-o ORG]
```

Cross-space policies: use `-s OTHER_SPACE -o OTHER_ORG` to allow traffic to apps in different spaces.

---

## 11. Orgs & Spaces

```
cf orgs
cf org ORG [--guid]
cf create-org ORG
cf delete-org ORG [-f]
cf rename-org ORG NEW_ORG
```

```
cf spaces
cf space SPACE [--guid]
cf create-space SPACE [-o ORG]
cf delete-space SPACE [-f]
cf rename-space SPACE NEW_SPACE
```

---

## 12. Roles & Users

**Org roles:** `OrgManager`, `OrgAuditor`, `BillingManager`
**Space roles:** `SpaceManager`, `SpaceDeveloper`, `SpaceAuditor`, `SpaceSupporter`

```
cf set-org-role USERNAME ORG ROLE
cf unset-org-role USERNAME ORG ROLE
cf org-users ORG [-a]                  # -a for all users including inherited

cf set-space-role USERNAME ORG SPACE ROLE
cf unset-space-role USERNAME ORG SPACE ROLE
cf space-users ORG SPACE
```

A user must have at least an org-level role before a space role can be assigned.

```
cf create-user USERNAME [--origin ORIGIN]
cf delete-user USERNAME [-f]
cf passwd                              # Change own password (UAA only)
```

---

## 13. Quotas

**Org quotas:**
```
cf quotas
cf quota QUOTA_NAME
cf create-quota NAME [-m MEMORY] [-i INSTANCES] [-r ROUTES] [-s SERVICES] [-a] [--allow-paid-service-plans] [-l LOG_RATE]
cf update-quota NAME [same flags]
cf set-org-quota ORG QUOTA
cf unset-org-quota ORG QUOTA
cf delete-quota NAME [-f]
```

**Space quotas:**
```
cf space-quotas
cf space-quota QUOTA_NAME
cf create-space-quota NAME [-m MEMORY] [-i INSTANCES] [-r ROUTES] [-s SERVICES] [-a] [--allow-paid-service-plans] [-l LOG_RATE]
cf update-space-quota NAME [same flags]
cf set-space-quota SPACE QUOTA
cf unset-space-quota SPACE QUOTA
cf delete-space-quota NAME [-f]
```

---

## 14. Buildpacks

```
cf buildpacks
cf create-buildpack NAME PATH POSITION [--enable|--disable]
cf update-buildpack NAME [-p PATH] [-i POSITION] [-s STACK] [--enable|--disable] [--lock|--unlock]
cf delete-buildpack NAME [-f] [-s STACK]
```

`POSITION` is detection order (1 = checked first). `--lock` prevents operator auto-updates.

**Multi-buildpack push:**
```
cf push my-app -b https://github.com/custom-bp.git -b java_buildpack
```
Last buildpack in list is the "final" one that provides the start command.

---

## 15. Stacks

```
cf stacks
cf stack STACK_NAME
```
Common stacks: `cflinuxfs3`, `cflinuxfs4`, `windows`. Stack determines the base OS image.

---

## 16. Security Groups

```
cf security-groups
cf security-group NAME
cf create-security-group NAME RULES_FILE.json
cf update-security-group NAME RULES_FILE.json
cf delete-security-group NAME [-f]
```

**Binding:**
```
cf bind-security-group NAME ORG [SPACE] [--lifecycle running|staging]
cf unbind-security-group NAME ORG [SPACE] [--lifecycle running|staging]
cf bind-running-security-group NAME       # Default for all running apps
cf unbind-running-security-group NAME
cf bind-staging-security-group NAME       # Default for all staging apps
cf unbind-staging-security-group NAME
```

**Rules file format:**
```json
[
  {
    "protocol": "tcp",
    "destination": "10.0.0.0/8",
    "ports": "3306,5432",
    "description": "Allow DB access"
  },
  {
    "protocol": "tcp",
    "destination": "0.0.0.0/0",
    "ports": "443",
    "log": true,
    "description": "Allow HTTPS outbound"
  }
]
```

---

## 17. Feature Flags

```
cf feature-flags
cf feature-flag FLAG_NAME
cf enable-feature-flag FLAG_NAME
cf disable-feature-flag FLAG_NAME
```

Common flags: `diego_ssh`, `user_org_creation`, `route_sharing`, `service_instance_sharing`, `diego_docker`.

---

## 18. Tasks

```
cf run-task APP --command "COMMAND" [--name NAME] [-m MEMORY] [-k DISK] [-l LOG_RATE]
cf tasks APP
cf terminate-task APP TASK_ID
```

Tasks run in the same container image (droplet) as the app but as a separate one-off process. They don't receive HTTP traffic and exit when the command finishes.

---

## 19. SSH

```
cf ssh APP [-i INSTANCE_INDEX]              # Interactive shell
cf ssh APP -c "COMMAND"                      # Run command, return output
cf ssh APP -L LOCAL_PORT:REMOTE_HOST:REMOTE_PORT   # Port forwarding / tunnel
cf ssh APP -N -T -L 63306:my-db.internal:3306      # Database tunnel (no shell)
```

**Enable/disable SSH:**
```
cf enable-ssh APP
cf disable-ssh APP
cf ssh-enabled APP
cf allow-space-ssh SPACE
cf disallow-space-ssh SPACE
cf space-ssh-allowed SPACE
```

SSH requires `diego_ssh` feature flag to be enabled (admin).

---

## 20. Logs & Events

```
cf logs APP                # Real-time streaming (Ctrl+C to stop)
cf logs APP --recent       # Recent historical logs (~1500 lines)
```

```
cf events APP              # Deployment, crash, scale events
```

Log output includes source tags: `APP/PROC/WEB` (app stdout), `RTR` (router), `STG` (staging), `CELL` (Diego cell).

---

## 21. Labels & Annotations

```
cf set-label RESOURCE RESOURCE_NAME KEY=VALUE [KEY2=VALUE2 ...]
cf unset-label RESOURCE RESOURCE_NAME KEY [KEY2 ...]
cf labels RESOURCE RESOURCE_NAME
```

Resources: `app`, `buildpack`, `domain`, `org`, `route`, `service-broker`, `service-instance`, `service-offering`, `service-plan`, `space`, `stack`.

**Filtering apps by labels:**
```
cf apps --labels "env=production"
cf apps --labels "env in (staging,production)"
cf apps --labels "team=platform,env=production"   # AND
```

---

## 22. Revisions & Rollback

```
cf revisions APP
cf rollback APP --version REVISION_NUMBER
```

Revisions track deployable snapshots (droplet + config). Rollback deploys the specified revision using a rolling strategy.

---

## 23. Plugins

```
cf plugins                                 # List installed plugins
cf install-plugin PLUGIN [-r REPO]         # Install from path, URL, or repo
cf uninstall-plugin PLUGIN_NAME
cf repo-plugins [-r REPO_NAME]             # List plugins in a repo
cf add-plugin-repo REPO_NAME URL
cf list-plugin-repos
```

**Popular community plugins:**
- `cf-targets` — Manage multiple CF targets
- `top` — Real-time app metrics
- `Statistics` — App statistics and usage
- `Buildpack Usage` — Which apps use which buildpacks

---

## 24. cf curl

```
cf curl PATH [-X METHOD] [-d DATA] [-H HEADER]
```

Sends authenticated requests to the Cloud Controller API. Handles auth tokens automatically.

```bash
# V3 examples
cf curl /v3/apps
cf curl /v3/apps?names=my-app
cf curl /v3/apps/APP_GUID/processes
cf curl /v3/apps/APP_GUID/tasks -X POST -d '{"command":"rake db:migrate"}'

# Pagination
cf curl "/v3/apps?per_page=50&page=2"
```

---

## 25. Miscellaneous

```
cf help [-a]                  # Help; -a lists all commands
cf help COMMAND               # Detailed help for specific command
cf version                    # CLI version
cf config [--locale LOCALE] [--trace true|false|FILE]
cf curl /v3/info              # Foundation info (API version, build, etc.)
```
