# ADR-0003 — Drop Redis and WebSockets from the MVP

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

The original architecture diagram specifies Redis for caching, session storage and a task
queue for alerts and heavy jobs, plus WebSockets for pushing real-time alerts to the
dashboard. Both are standard for a production system at scale. This system's actual
characteristics are different:

- **Read-mostly and near-static.** The feature table and model change only when the
  pipeline is re-run — every few weeks, deliberately. There is no stream of writes.
- **Single backend instance.** Render's free tier runs one container that sleeps after
  15 minutes idle. There is no second process to share a cache with.
- **Alerts change once a day.** They are driven by a daily weather forecast, not by events.
- **Concurrency ≈ 1.** A demo, an examiner, the author.

Redis free tiers exist (Upstash, Redis Cloud) so cost is not the blocker — complexity is.

## Options considered

### A — Implement Redis and WebSockets as diagrammed

**Pros** Matches the diagram exactly; looks impressive on paper; genuinely correct at scale.
**Cons** A cache shared between processes solves a problem we do not have with one process;
a task queue needs a worker, and Render's free tier gives one service — the worker would
have nowhere to live; WebSockets do not survive Render's idle sleep, so the "live" channel
would silently die between demos and reconnect logic becomes mandatory to hide it; roughly
2–3 weeks of the schedule spent on infrastructure that serves one concurrent user.

### B — In-process cache + scheduled cron + polling

**Pros** `functools.lru_cache` and a dict with TTLs cover a single-instance cache
completely; GitHub Actions cron (free, 2,000 min/mo) replaces the queue for the one
genuinely scheduled job — the daily monitoring run — and gets logs and retries for free;
alerts change daily, so polling on page load is not a compromise, it is the correct
fidelity; weeks returned to the ML and agent layers, which are where the project's actual
contribution lies.
**Cons** Diverges from the submitted diagram — must be explained, not hidden; cache is lost
on every cold start (recomputed in ms from parquet, so immaterial); no true push channel.

### C — Redis now, WebSockets later

**Pros** Half the infrastructure credit for half the work.
**Cons** Worst of both — an external dependency and a network hop added to solve nothing,
since a single sleeping instance gains nothing from a remote cache.

## Decision

**Option B — cut both from the MVP.**

The deciding factor: Redis and WebSockets solve multi-instance and real-time-push problems
that this system does not have, and Render's free tier (one sleeping container, no worker)
means implementing them would produce infrastructure that is inert at best and quietly
broken at worst. The honest engineering position is that a daily-refreshed alert feed
polled on page load matches the data's actual update frequency.

Both stay in the report as **production considerations** with the scaling thresholds that
would trigger them — that is a stronger answer to a reviewer than a Redis instance caching a
single-user application, because it demonstrates knowing *when* infrastructure earns its
place.

## Consequences

**Positive**
- Fewer moving parts, fewer failure modes, fewer accounts, faster cold starts.
- ~2–3 weeks returned to ML and agents.
- Deployment stays within one free-tier service.
- Forces an explicit, defensible argument about scale rather than cargo-culting a diagram.

**Negative**
- Deviation from the diagram must be defended — mitigated by this ADR, which *is* the
  defence.
- Cache is per-instance and lost on sleep; recompute is milliseconds, so no user impact.
- No sub-daily alert latency. Acceptable: the upstream forecast updates hourly at best,
  and heat action is a day-scale decision.
- If the project ever needed multiple instances, this must be revisited before scaling.

**Revisit if** the system needs >1 backend instance, sub-minute alert latency, or
multi-user sessions with shared state. The trigger to add Redis is a second process, not a
sense that it is missing.
