# Learning Moment — kubectl Error Output Misread as Resource Data

## What happened

The ELS dashboard was showing fabricated data in the Controllers row:

```
Controllers: ds=5, deploy=5 | DS: 08:45:19.307571, 08:45:19.308855 | Deploy: 08:45:19.343560...
```

Those values that looked like daemonset and deployment names were actually
**timestamps from kubectl error output** — specifically from `memcache.go` error lines
emitted when kubectl cannot reach the API server:

```
E0503 08:51:35.059201   92327 memcache.go:265] "Unhandled Error" err="couldn't get current
server API group list: Get \"https://127.0.0.1:49590/api?timeout=32s\": dial tcp
127.0.0.1:49590: connect: connection refused"
```

The state collector's `run_command()` helper was returning stderr as output when
stdout was empty. The parsers then treated those error lines as valid kubectl output
and extracted the timestamps as resource names.

---

## Why this happened

The `run_command()` helper had this logic:

```python
if stdout:
    return stdout
if stderr:
    return stderr   # <-- bug: returns error text as if it were valid output
return ""
```

When kubectl fails with `connection refused`, stdout is empty and stderr contains
the error. The helper returned the error text, which the daemonset/deployment
parsers then split on whitespace and extracted "names" from — picking up the
timestamps in the error lines.

---

## The fix

Filter known kubectl connection error patterns before returning stderr:

```python
if stderr and any(indicator in stderr for indicator in [
    "connection refused",
    "couldn't get current server",
    "dial tcp",
    "no such host",
    "Unable to connect",
    "The connection to the server",
]):
    return ""   # no cluster reachable — return empty, not error text
```

This means the dashboard shows **unknown / visibility-limited** instead of
fabricated data when no cluster is reachable.

---

## ELS parallel

This is the same class of problem as reading stale CNI config files:

| State collector bug | CNI residual problem |
|---|---|
| Error text returned as resource output | Stale CNI config left in `/etc/cni/net.d/` |
| Parser extracts garbage "names" from error lines | kubelet picks up wrong CNI from stale config |
| Dashboard shows fabricated healthy state | Cluster shows wrong CNI identity |
| Fix: filter errors before parsing | Fix: clean up stale config before reinstalling |

In both cases: **garbage in, garbage out**. The fix is always at the input boundary,
not in the parser.

---

## Product principle reinforced

> Evidence beats confident guessing.

The dashboard must be honest about what it cannot see. Showing
`unknown / visibility-limited` when no cluster is reachable is correct behaviour.
Showing fabricated green status with invented resource names is a product failure.

This fix enforces the evidence principle at the data collection layer — the right place.

---

## ELS layer

L4.5 — Kubernetes API Layer. The error occurs because the API server is unreachable,
which is an L4.5 visibility gap. The fix ensures that gap is represented honestly
in the dashboard rather than papered over with error text.
