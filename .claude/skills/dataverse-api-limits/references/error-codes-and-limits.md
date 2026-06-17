# Error codes, default limits, and headers

Reference for Dataverse **service protection API limits**. Grep tips: search
`0x8007` for hex codes, `-21470158` for SDK error codes.

## Contents
- [Default limits (per web server)](#default-limits-per-web-server)
- [The three error types](#the-three-error-types)
- [Rate-limit response headers](#rate-limit-response-headers)
- [Service protection vs. entitlement limits](#service-protection-vs-entitlement-limits)
- [FAQ facts](#faq-facts)

## Default limits (per web server)

Two of the three limits use a **5-minute (300-second) sliding window**. Limits
are evaluated **per authenticated user, per web server**. Each environment
usually has multiple web servers (trial environments get only one; the count
scales with factors including the number of user licenses purchased). Because
each server enforces independently, spreading requests across servers (affinity
cookie off) effectively multiplies your headroom.

| Measure | Description | Default limit per web server |
| --- | --- | --- |
| Number of requests | Cumulative requests the user makes | 6,000 within the 5-minute window |
| Execution time | Combined server execution time of the user's requests | 20 minutes (1,200 s / 1,200,000 ms) within the 5-minute window |
| Concurrent requests | Simultaneous requests from the user | 52 or higher |

> These are defaults and can change or vary by environment. Treat them as
> ballpark, not contracts. The number-of-requests and execution-time limits are
> evaluated over the window, so you may briefly exceed them before an error is
> returned; **exceeding the concurrent-requests limit errors immediately**.

Plug-ins / custom workflow activities: their requests do **not** count toward
these limits (they run in the sandbox, off the public endpoints), but their
**compute time is added to the execution time of the request that triggered
them**, which does count.

## The three error types

Web API returns HTTP `429 Too Many Requests` plus the hex code. The SDK for .NET
returns an `OrganizationServiceFault` whose `ErrorDetails` holds the integer
error code and a `Retry-After` `TimeSpan`.

### Number of requests
| Error code | Hex code | Message |
| --- | --- | --- |
| `-2147015902` | `0x80072322` | `Number of requests exceeded the limit of 6000 over time window of 300 seconds.` |

Mitigation: reduce records selectable per bulk action; or combine selected
operations into a batch (up to 1,000 ops) — but then watch the execution-time limit.

### Execution time
| Error code | Hex code | Message |
| --- | --- | --- |
| `-2147015903` | `0x80072321` | `Combined execution time of incoming requests exceeded limit of 1,200,000 milliseconds over time window of 300 seconds. Decrease number of concurrent requests or reduce the duration of requests and try again later.` |

Triggered by demanding work: large batches, solution imports, complex queries,
many concurrent requests. Strategies that bundle/concurrent-send to dodge the
request-count limit tend to hit this one instead.

### Concurrent requests
| Error code | Hex code | Message |
| --- | --- | --- |
| `-2147015898` | `0x80072326` | `Number of concurrent requests exceeded the limit of 52.` |

Mitigation: cap parallelism with `ParallelOptions.MaxDegreeOfParallelism`; prefer
the `x-ms-dop-hint` value over CPU-core defaults (see
[throughput-and-parallelism.md](throughput-and-parallelism.md)).

## Rate-limit response headers

Web API only. **Debugging purposes only** — do not use to control send rate;
they reset when you connect to a different server (e.g. affinity cookie removed).

| Header | Value |
| --- | --- |
| `x-ms-ratelimit-burst-remaining-xrm-requests` | Remaining requests for this connection |
| `x-ms-ratelimit-time-remaining-xrm-requests` | Remaining combined execution time across this user's connections |

## Service protection vs. entitlement limits

Two **separate**, independently evaluated systems. Batch operations are **not** a
valid way to bypass entitlement limits.

| | Service protection limits | Entitlement (Power Platform request) limits |
| --- | --- | --- |
| Window | 5-minute sliding | 24-hour |
| On exceed | Immediate `429` / fault | Occasional/reasonable overages allowed (not blocked) |
| Scope | All external web-service requests | CRUD on table rows (create/retrieve/update/delete; share & assign count as updates), incl. plug-ins, async workflows, `$batch`/ExecuteMultiple |
| Excluded | Plug-in/workflow-internal requests | Sign in/out, system metadata operations |
| Responsibility | **Developer**: avoid + retry | **Administrator**: manage/purchase capacity add-ons |

A connector call that results in a Dataverse request = 1 Power Platform request.

## FAQ facts

- **Dataverse Search** (`api/search`, not `api/data`) is exempt from these limits;
  it has its own throttle of **1 request/second/user**.
- **Application (service principal) users** get the **same** limits as everyone else.
- **Portal apps** route anonymous traffic through one service-principal account,
  so they can hit per-user limits under load — disable further requests and show
  a "server busy" message (optionally using the `Retry-After` time).
- ETL tools: confirm the vendor version supports `Retry-After`; ask the vendor
  which throughput settings to use.
- `ExecuteMultiple` is no longer limited to two concurrent operations — the
  execution-time limit made that old restriction redundant.
