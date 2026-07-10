#!/usr/bin/env python3
"""Run a DQL query against the Dynatrace Grail DQL Query API (execute -> poll).

Latest-platform path (.apps.dynatrace.com), OAuth/bearer only. Standard library only.

Auth (pick one):
  --token <bearer-or-platform-token>          use an existing token directly
  --client-id/--client-secret [+ --scope]     fetch a short-lived bearer via client_credentials

Examples:
  python3 dt_dql.py --env abc12345 --token "$DT_TOKEN" \
      --query 'fetch logs | summarize count()'

  python3 dt_dql.py --env abc12345 \
      --client-id "$DT_CLIENT_ID" --client-secret "$DT_CLIENT_SECRET" \
      --scope 'storage:buckets:read storage:logs:read' \
      --query-file ./q.dql

  python3 dt_dql.py --env abc12345 --token x --query 'fetch logs' --dry-run

Env var fallbacks: DT_ENV, DT_BASE_URL, DT_TOKEN, DT_CLIENT_ID, DT_CLIENT_SECRET,
DT_SCOPE, DT_RESOURCE, DT_SSO_URL.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_SSO_URL = "https://sso.dynatrace.com/sso/oauth2/token"
DEFAULT_SCOPE = (
    "storage:buckets:read storage:logs:read storage:events:read "
    "storage:metrics:read storage:bizevents:read storage:spans:read "
    "storage:entities:read"
)
TERMINAL_STATES = {"SUCCEEDED", "FAILED", "CANCELLED", "NOT_STARTED"}


def _post_form(url, data, timeout):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _request_json(url, token, timeout, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": "Bearer " + token}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_bearer_token(args):
    data = {
        "grant_type": "client_credentials",
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "scope": args.scope,
    }
    if args.resource:
        data["resource"] = args.resource
    if args.dry_run:
        print("[dry-run] POST " + args.sso_url, file=sys.stderr)
        print("[dry-run] form: grant_type=client_credentials, client_id=%s, "
              "scope=%s" % (args.client_id, args.scope), file=sys.stderr)
        return "DRY_RUN_TOKEN"
    result = _post_form(args.sso_url, data, args.timeout)
    token = result.get("access_token")
    if not token:
        sys.exit("error: no access_token in SSO response: " + json.dumps(result))
    return token


def run_query(args, token, query):
    base = args.base_url or (
        "https://%s.apps.dynatrace.com/platform/storage/query/v1" % args.env
    )
    execute_url = base + "/query:execute"
    poll_url = base + "/query:poll"

    payload = {"query": query}
    if args.timeframe_start:
        payload["defaultTimeframeStart"] = args.timeframe_start
    if args.timeframe_end:
        payload["defaultTimeframeEnd"] = args.timeframe_end
    if args.timezone:
        payload["timezone"] = args.timezone

    if args.dry_run:
        print("[dry-run] POST " + execute_url, file=sys.stderr)
        print("[dry-run] body: " + json.dumps(payload), file=sys.stderr)
        print("[dry-run] then GET " + poll_url + "?request-token=<token>", file=sys.stderr)
        return {"state": "DRY_RUN", "result": {"records": []}}

    resp = _request_json(execute_url, token, args.timeout, "POST", payload)
    state = resp.get("state")
    request_token = resp.get("requestToken")
    if not request_token:
        sys.exit("error: no requestToken in execute response: " + json.dumps(resp))

    deadline = time.time() + args.max_wait
    while True:
        qs = urllib.parse.urlencode({"request-token": request_token})
        resp = _request_json(poll_url + "?" + qs, token, args.timeout, "GET")
        state = resp.get("state")
        if state in TERMINAL_STATES or "result" in resp:
            return resp
        if time.time() > deadline:
            sys.exit("error: query did not finish within %ss (last state=%s)"
                     % (args.max_wait, state))
        time.sleep(args.poll_interval)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Run a DQL query via the Grail DQL Query API (execute -> poll).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--env", default=os.getenv("DT_ENV"),
                   help="Environment ID, e.g. abc12345 (or set DT_ENV).")
    p.add_argument("--base-url", default=os.getenv("DT_BASE_URL"),
                   help="Override full base, e.g. https://abc.apps.dynatrace.com/platform/storage/query/v1")
    q = p.add_mutually_exclusive_group(required=True)
    q.add_argument("--query", help="DQL query string.")
    q.add_argument("--query-file", help="Path to a file containing the DQL query.")

    p.add_argument("--token", default=os.getenv("DT_TOKEN"),
                   help="Existing bearer/platform token (or set DT_TOKEN).")
    p.add_argument("--client-id", default=os.getenv("DT_CLIENT_ID"),
                   help="OAuth client id dt0s02.* (or set DT_CLIENT_ID).")
    p.add_argument("--client-secret", default=os.getenv("DT_CLIENT_SECRET"),
                   help="OAuth client secret (or set DT_CLIENT_SECRET).")
    p.add_argument("--scope", default=os.getenv("DT_SCOPE", DEFAULT_SCOPE),
                   help="Space-separated OAuth scopes (or set DT_SCOPE).")
    p.add_argument("--resource", default=os.getenv("DT_RESOURCE"),
                   help="urn:dtaccount:<uuid> if the OAuth client requires it.")
    p.add_argument("--sso-url", default=os.getenv("DT_SSO_URL", DEFAULT_SSO_URL),
                   help="SSO token endpoint.")

    p.add_argument("--timeframe-start", help="defaultTimeframeStart (ISO-8601).")
    p.add_argument("--timeframe-end", help="defaultTimeframeEnd (ISO-8601).")
    p.add_argument("--timezone", help="Timezone, e.g. UTC or Europe/Vienna.")

    p.add_argument("--records-only", action="store_true",
                   help="Print only result.records (default prints the full result).")
    p.add_argument("--poll-interval", type=float, default=1.5,
                   help="Seconds between polls (default 1.5).")
    p.add_argument("--max-wait", type=float, default=120.0,
                   help="Max seconds to wait for completion (default 120).")
    p.add_argument("--timeout", type=float, default=30.0,
                   help="Per-request socket timeout seconds (default 30).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the requests that would be sent and exit.")
    args = p.parse_args(argv)

    if not args.base_url and not args.env:
        p.error("one of --env or --base-url is required (or set DT_ENV/DT_BASE_URL).")
    if not args.token and not (args.client_id and args.client_secret):
        p.error("provide --token, or both --client-id and --client-secret "
                "(or the matching env vars).")

    if args.query_file:
        try:
            with open(args.query_file) as fh:
                query = fh.read().strip()
        except OSError as e:
            p.error("cannot read --query-file: %s" % e)
    else:
        query = args.query.strip()
    if not query:
        p.error("query is empty.")

    token = args.token or fetch_bearer_token(args)

    try:
        resp = run_query(args, token, query)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit("HTTP %s from Dynatrace: %s" % (e.code, detail))
    except urllib.error.URLError as e:
        sys.exit("network error: %s" % e.reason)

    state = resp.get("state")
    if state == "FAILED":
        sys.exit("query FAILED: " + json.dumps(resp, indent=2))

    if args.records_only:
        out = (resp.get("result") or {}).get("records", [])
    else:
        out = resp
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
