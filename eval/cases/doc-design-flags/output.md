# Feature flags: adopt LaunchDarkly, retire per-service YAML

**TL;DR:** Replace the 14 per-service `flags.yaml` files with a single hosted flag service. Recommend LaunchDarkly over self-hosted Unleash, mainly for near-zero ops burden while Platform Infra is short-staffed. Rollout is 12 weeks in four phases, starting with `checkout-service` and `pricing-service`. Reviewers (Platform Infra, SRE, Payments, Growth, Mobile) to weigh in on the draft.

**Status:** Draft for review · **Author:** Sam Lee · **Last updated:** 2026-09-23

## Flag drift across services keeps causing incidents

On September 12, a flag disabling a broken shipping-rate provider was merged into `checkout-service`, but the matching flag in `pricing-service` (which shares the provider integration) didn't update until the next scheduled deploy, six hours later. Customers saw incorrect shipping quotes the whole time. It's the third incident in five months caused by flag drift between services that logically share a toggle.

The root cause is how flags got here: `checkout-service` added a `flags.yaml` in 2022 for a payment-retry change, and every service since copied it as boilerplate — never a deliberate standard. Today that leaves us with:

- 14 services, each with its own `flags.yaml`; toggling one means a PR, review, merge, and a wait for deploy (avg. 22 minutes merge-to-production).
- 187 flag entries total, 41 duplicated by name across two or more services with no shared source of truth.
- No audit log beyond git blame, and no built-in way to target by segment, percentage, or environment.
- Growth, Payments, and Mobile each built their own ad hoc percentage-rollout logic on top of boolean-only YAML flags — untested, inconsistent, and the source of two prior incidents from off-by-one errors in rollout-bucket hashing.

## Proposal: a centrally hosted flag service

Each service links a thin SDK (Go, Node, Ruby) that caches the full rule set in memory on startup, subscribes to streaming updates (SSE for LaunchDarkly, polling/SSE proxy for Unleash) so a toggle reaches every instance in roughly 1-2 seconds, and evaluates flags in-process with no per-call network round trip — meeting the sub-5ms p99 requirement. If the stream drops, the SDK falls back to its last cached rule set; on a cold start with no cache (e.g. during a flag-service outage), it falls back to a hardcoded default set per flag. This local-evaluation model is also why we're not building this in-house on Redis: getting caching, streaming, and rollout-hashing right across three languages is most of the engineering effort in a flag system, and both vendors have already done it.

A flag has a globally unique key (`<domain>.<name>`, enforced going forward, not retroactively), a type (boolean, string, number, or JSON), an ordered list of targeting rules plus a percentage rollout and default, and independent rules per environment (dev/staging/prod). Owning team is tracked as metadata only, not enforced at evaluation. Because a flag key is global with exactly one rule set, services that used to duplicate a flag under different keys — the September 12 failure mode — get consolidated onto one shared key during migration.

Every flag requires an owning team at creation. Both vendors natively audit-log actor, timestamp, before/after value, and comment, so no extra work there. New guardrail: `tier-1` flags (checkout, payments, auth) require a second approver before going live, via LaunchDarkly's built-in approvals or Unleash Enterprise's change-request flow.

Out of scope: a general experimentation/analytics platform, non-flag config (DB strings, API keys, cache TTLs — stay in Vault/YAML), retroactively renaming the 187 existing flags (separable, would roughly double the timeline), and a full vendor RFP (scoped to LaunchDarkly and Unleash, the two that meet our latency/audit bar).

## LaunchDarkly vs. self-hosted Unleash

| Criterion | LaunchDarkly | Self-hosted Unleash |
|---|---|---|
| Hosting | Fully managed SaaS | We run it (likely ECS) |
| Cost at ~40 engineers, ~150 flags | ~$28k/yr, Pro tier | ~$400/mo infra (HA Postgres + ECS); Enterprise license (approvals, SSO) quote pending |
| Ops burden | Near zero | ~0.25 FTE ongoing, Platform Infra |
| SDKs | Go, Node, Ruby native, plus mobile | Go, Node, Ruby native; mobile SDKs community-maintained |
| Approvals workflow | Built into Pro tier | Enterprise edition only |
| Data residency | Leaves our infra | Stays in our VPC |
| Latency | Well under 5ms budget per public benchmarks and Growth's trial | Comparable once warmed; only initial fetch/streaming cross our network |
| Track record | Proven at much larger scale | Solid, but on-call debugs our own deployment, not a vendor |

Recommend starting with **LaunchDarkly**: near-zero ops burden matters most while Platform Infra is stretched thin post-headcount-freeze, and Growth's existing trial gives us real internal validation. Main risk is cost growth as flags/seats increase — reassess against Unleash at a 6-month spend checkpoint if actual cost materially exceeds $28k.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep per-service YAML, add a linter/cross-repo search | Treats the symptom: doesn't fix the 22-minute deploy latency or add native percentage rollouts, and only catches drift after it's already in a PR |
| Build in-house on Redis | Multi-quarter effort to replicate caching, streaming, and rollout-hashing across three languages, then maintain it indefinitely instead of Platform Infra's actual roadmap |
| Repurpose Consul/etcd (we already run Consul) | No built-in percentage rollout, targeting, or audit log — we'd be building the entire evaluation layer ourselves, close to the in-house option with extra steps |

## Risks

- **Vendor outage or account lockout** — SDK's local cache and last-known-good fallback mean flags freeze at their last value rather than stop working.
- **Cost overrun** if flag count grows faster than expected — mitigated by the 6-month checkpoint and by not creating new flags retroactively during migration.
- **Cutover incidents** where one service reads old YAML and another reads the new service, giving different answers — mitigated by migrating one flag at a time behind a temporary compatibility shim rather than an atomic per-service cutover.
- **Pushback on the tier-1 second-approval step** slowing incident response — mitigated by scoping it to tier-1 only and allowing a logged on-call override instead of a hard block.
- **PII in targeting rules** — mitigated by policy: rules use internal account/user IDs and coarse attributes (plan tier, region) only, never raw PII, regardless of vendor.

## Rollout: 12 weeks, four phases

1. **Weeks 1-2 — Foundation.** Stand up the LaunchDarkly org, SSO, and tier-1 approval workflow. Platform Infra publishes an internal SDK wrapper (Go, Node, Ruby) thin enough to swap vendors later without touching call sites.
2. **Weeks 3-4 — Pilot.** Migrate `checkout-service` and `pricing-service` first — the two services involved in the September 12 incident — consolidating their shared flag onto one key. Old `flags.yaml` stays in place, unused, as a rollback path.
3. **Weeks 5-10 — Staged migration.** Remaining 12 services migrate in dependency order, fewest cross-service shared flags first. Each runs a temporary compatibility shim reading both old YAML and the new service for a one-week bake, alerting on any mismatch before full cutover.
4. **Weeks 11-12 — Cleanup.** Delete all `flags.yaml` files and shim code, publish the `<domain>.<name>` naming convention as a requirement for new flags, and retro the September 12 incident class to confirm the new architecture would have prevented it.

**Rollback:** any single service can revert to YAML-only by removing its shim and redeploying, with no cross-service coordination needed. Full rollback across all services would only be considered on a sustained, unresolvable LaunchDarkly outage or a hard blocker found during the pilot — unlikely, since the pilot exists to catch that early.

## Open questions

- Unleash Enterprise license cost is still being quoted; relevant only if the 6-month checkpoint triggers a reassessment.
