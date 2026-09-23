I'll present the document directly here instead, since writing into that eval fixture path was blocked.

# Design Doc: Centralized Feature Flag Service

**Author:** Sam Lee
**Status:** Draft for review
**Reviewers:** Platform Infra, SRE, Payments, Growth, Mobile
**Last updated:** 2026-09-23

## Introduction

Every one of our 14 services currently manages feature flags through a `flags.yaml` file checked into its own repo. A flag is toggled by editing the file, opening a PR, getting it reviewed, merging, and waiting for the next deploy to pick it up. This document proposes replacing that pattern with a single, centrally hosted flag service that all services query at runtime, and evaluates LaunchDarkly against a self-hosted Unleash deployment as the two viable options.

The immediate trigger for this proposal was the September 12 checkout incident: a flag meant to disable a broken shipping-rate provider was merged into `checkout-service` but the corresponding flag in `pricing-service` (which shares the provider integration) wasn't updated until the next scheduled deploy, six hours later. Customers saw incorrect shipping quotes for that entire window. This was the third incident in five months traceable to flag drift between services that logically share a toggle.

## Background

The YAML-per-repo pattern grew organically. `checkout-service` added a `flags.yaml` in 2022 to gate a risky payment retry change, and every service since has copied that file as boilerplate when it needed its first flag. There was never a decision to standardize on this approach — it's simply what existing services did, so new services did it too.

As of this month we have:

- 14 services, each with its own `flags.yaml`
- 187 total flag entries across all repos, of which 41 are duplicated by name across two or more services (same intent, no shared source of truth)
- No audit log of who toggled what, when, beyond the git blame on the YAML file
- No way to target a flag by user segment, percentage rollout, or environment without writing custom logic in the service itself
- Flag changes require a full deploy cycle, averaging 22 minutes from merge to production per our current CI pipeline

Three teams (Growth, Payments, Mobile) have independently built ad hoc percentage-rollout logic on top of the YAML flags because the format itself only supports booleans. That logic is different in each service, has no shared tests, and has caused two prior incidents from off-by-one errors in rollout-bucket hashing.

## Goals

1. Toggle any flag in production in under 10 seconds, with no deploy required.
2. Provide one source of truth for flags that are logically shared across services, eliminating drift like the September 12 incident.
3. Support percentage rollouts, user/account targeting, and environment-scoped overrides natively, without per-service custom logic.
4. Maintain a complete audit log: who changed what flag, when, and what the before/after value was.
5. Keep p99 flag evaluation latency under 5ms from any service, including under regional failover.
6. Provide a graceful fallback (last-known-good value or safe default) if the flag service is unreachable, so a flag-service outage never becomes a service outage.
7. Migrate all 14 services with no more than one required deploy per service.

## Non-Goals

- We are not building a general-purpose experimentation or A/B-testing analytics platform. If the chosen tool includes experiment reporting, we may use it opportunistically, but analytics depth is not a selection criterion.
- We are not replacing application configuration that isn't a flag — database connection strings, API keys, and tunables like cache TTLs stay in their existing config systems (Vault and per-service YAML respectively).
- We are not attempting to unify flag *naming conventions* retroactively across all 187 existing flags as part of this migration. That cleanup is valuable but separable, and bundling it in would roughly double the migration timeline.
- We are not evaluating build-vs-buy from scratch against every vendor in the market. We're scoping the comparison to LaunchDarkly (market leader, already used informally by Growth on a trial license) and Unleash (leading open-source, self-hostable option), because both fit our latency and audit requirements and a wider RFP would cost more in eval time than it would likely change the outcome.

## Detailed Design

### Architecture overview

Each service links a thin SDK (available for our stack: Go, Node, and Ruby) that evaluates flags locally against a cached rule set, rather than making a network call per evaluation. The SDK:

1. On startup, fetches the current flag rule set (all flags, all rules, all targeting) from the flag service over HTTPS and caches it in memory.
2. Subscribes to a streaming connection (SSE for LaunchDarkly, or Unleash's polling/SSE proxy) for incremental updates, so a flag toggle propagates to every instance of every service within roughly 1-2 seconds.
3. Falls back to the last cached rule set if the stream disconnects, and to a hardcoded default value (defined per flag at creation time) if no cache exists yet, e.g. on a fresh pod with a cold start during a flag-service outage.
4. Evaluates flags entirely in-process — no network round-trip per `isEnabled()` call — which is what gets us the sub-5ms p99 requirement.

This local-evaluation model is the main reason we're not building this in-house on top of, say, a Redis-backed config store: getting streaming propagation, SDK-side caching, and percentage-rollout hashing right and consistent across three languages is most of the actual engineering effort in a flag system, and both LaunchDarkly and Unleash have already done it.

### Data model

A flag has:

- **Key**: a globally unique string, e.g. `checkout.shipping-rate-provider-v2`. We will enforce a `<domain>.<name>` naming convention going forward (not retroactively, per Non-Goals).
- **Type**: boolean, string, number, or JSON — covering both simple kill-switches and richer config-style flags (e.g. selecting which of three shipping providers to use, not just on/off).
- **Rules**: an ordered list of targeting rules (by user ID, account ID, email domain, or custom attribute we pass in context, such as `region` or `plan-tier`), each resolving to a served value, plus a percentage rollout rule and a final default.
- **Environments**: dev, staging, and prod each have independently configurable rules for the same flag key, so a flag can be 100% on in dev while at 5% in prod.
- **Owning team**: metadata only, used for the ownership dashboard described below — not enforced at evaluation time.

### Shared flags and service boundaries

The September 12 incident happened because two services needed to agree on one flag's value and had no way to guarantee that. Under the new model, a flag key is global — any service can read `checkout.shipping-rate-provider-v2`, and there is exactly one rule set governing it, evaluated identically everywhere. Services that used to duplicate a flag under different keys will be consolidated onto one shared key during migration (see Rollout).

### Ownership, audit, and change process

Every flag has a required owning team at creation time, visible in the vendor's dashboard. All changes are already audit-logged natively by both vendors (actor, timestamp, before/after value, and an optional change comment) — no work needed there. We will add one guardrail: flags tagged `tier-1` (currently: anything touching checkout, payments, or auth) require a second approver in the dashboard before a change goes live, using LaunchDarkly's built-in approvals workflow or Unleash Enterprise's equivalent change-request flow.

### Vendor evaluation: LaunchDarkly vs. self-hosted Unleash

| Criterion | LaunchDarkly | Self-hosted Unleash |
|---|---|---|
| Hosting | Fully managed SaaS | We run it (likely as an ECS service, since that's where the rest of our platform tooling lives) |
| Pricing at our scale (~40 engineers, ~150 flags post-consolidation) | ~$28k/year on the Pro tier (per-seat, at current published rates) | Infra cost only, roughly $400/month for a small HA Postgres + ECS setup; Enterprise edition (for approvals workflow, SSO) adds a license cost we're still getting a quote on |
| Setup and ongoing ops burden | Near zero — vendor handles uptime, scaling, streaming infra | We own uptime, backups, upgrades, and the streaming/proxy layer; estimated 0.25 FTE ongoing from Platform Infra |
| SDK language support | Native SDKs for Go, Node, Ruby, plus mobile SDKs we'd want if Mobile adopts this later | Native SDKs for Go, Node, Ruby; mobile SDKs are community-maintained and less mature |
| Approvals / change-request workflow | Built in on Pro tier | Enterprise edition only |
| Data residency / control | Flag rules and targeting data leave our infra | Everything stays in our VPC — relevant since some targeting rules will reference account attributes |
| Latency | Global CDN-backed streaming edge; well under our 5ms budget in practice per public benchmarks and Growth's trial | Comparable once warmed, since evaluation is local either way; only the initial fetch and streaming updates cross our own network |
| Maturity / track record | Established, used by companies at far larger scale than us | Solid, but our on-call would be debugging *our* deployment of it, not filing a vendor ticket |

Our recommendation is to start with **LaunchDarkly**. The deciding factors are the near-zero ops burden (Platform Infra is already stretched thin post-headcount-freeze) and the fact that Growth's existing trial usage means we have real internal validation already. The main risk is cost growth as we add flags and seats — we'll set a checkpoint at the 6-month mark to reassess against Unleash if actual spend materially exceeds the $28k estimate.

## Alternatives Considered

**Keep per-service YAML, just add tooling.** We considered building a linter and a cross-repo search tool to catch drift like the September 12 case, without introducing a new runtime dependency. Rejected because it treats the symptom, not the cause: it doesn't solve the 22-minute deploy-to-toggle latency, doesn't give us percentage rollouts natively, and a linter can only catch drift after it's already been introduced in a PR, not prevent divergent runtime state.

**Build an in-house flag service on Redis.** Considered because it would keep everything in-VPC with no vendor dependency at all. Rejected primarily on effort: replicating SDK-side caching, streaming propagation, and percentage-rollout hashing correctly across three languages is a multi-quarter effort for a small team, and we'd be maintaining it indefinitely instead of Platform Infra's actual roadmap items.

**Consul or etcd as a generic config store repurposed for flags.** We already run Consul for service discovery. Considered using its KV store for flags to avoid a new system. Rejected because it has no concept of percentage rollouts, targeting rules, or audit logging out of the box — we'd be building the entire flag-evaluation layer ourselves on top of a generic KV store, which is close to the in-house-build option above with extra steps.

## Risks

- **Vendor outage or account lockout.** Mitigated by the SDK's local caching and last-known-good fallback; a LaunchDarkly outage degrades us to "flags frozen at their last value," not "flags stop working."
- **Cost overrun if flag count grows faster than expected.** Mitigated by the 6-month spend checkpoint noted above, and by the Non-Goal of not retroactively creating new flags for old ad hoc logic during migration.
- **Migration introduces a new class of incident during cutover** (a service reading a flag from the old YAML while another reads the new service, giving two different answers). Mitigated by migrating one flag at a time behind a temporary compatibility shim (see Rollout, Phase 2) rather than cutting a whole service over atomically.
- **Team pushback on a second approval step for tier-1 flags** slowing down incident response, which is precisely when flags need to change fastest. Mitigated by scoping the second-approver requirement narrowly (tier-1 only) and by allowing a documented on-call override that still gets logged, rather than a hard block.
- **Data residency concern for Enterprise/regulated customers** if any targeting rule ever needs to reference PII. Mitigated by policy: targeting rules will use internal account/user IDs and coarse attributes (plan tier, region) only, never raw PII, regardless of vendor choice.

## Rollout

**Phase 0 — Foundation (Weeks 1-2).** Stand up LaunchDarkly org, SSO integration, and the tier-1 approval workflow. Platform Infra builds and publishes the internal SDK wrapper (thin layer over the vendor SDK, so we can swap vendors later without touching call sites in 14 services) for Go, Node, and Ruby.

**Phase 1 — Pilot (Weeks 3-4).** Migrate `checkout-service` and `pricing-service` first, specifically because they were the two services involved in the September 12 incident, and because consolidating their shared flag onto one key is the clearest proof of the core value proposition. Old `flags.yaml` stays in place but unused, as a rollback path.

**Phase 2 — Staged migration (Weeks 5-10).** Remaining 12 services migrate in dependency order (services with the fewest cross-service shared flags first, to keep each migration's blast radius small). Each service runs a temporary compatibility shim that reads from both the old YAML and the new service during a one-week bake period, alerting on any mismatch before cutting over fully.

**Phase 3 — Cleanup (Weeks 11-12).** Delete all `flags.yaml` files and the shim code. Publish the `<domain>.<name>` naming convention as a requirement for all new flags. Run a retro on the September 12 incident class specifically, to confirm the new architecture would have prevented it.

**Rollback plan.** Because the compatibility shim keeps the old YAML functional throughout Phase 2, any single service can revert to YAML-only by removing the shim and redeploying — no cross-service coordination required to roll back one service. Full rollback to YAML-only across all services would only be considered if we hit a sustained, unresolvable LaunchDarkly outage or a hard blocker discovered during the pilot; given the pilot phase exists specifically to catch that early, we consider this unlikely.

## Conclusion

The per-service YAML pattern wasn't a decision, it was a default that 14 services inherited from whichever one happened to need a flag first. It's now costing us incidents, not just inconvenience — the September 12 shipping-rate bug is the third case of flag drift causing a customer-facing bug in five months, and the 22-minute deploy-to-toggle latency means every incident response involving a flag is slower than it needs to be.

We recommend adopting LaunchDarkly, migrating over a 12-week staged rollout starting with the two services already implicated in the incident that motivated this proposal, and revisiting the Unleash option at the 6-month cost checkpoint if spend outpaces the estimate in this document. The core win isn't the vendor choice — it's collapsing 14 sources of truth into one, with an audit trail and native rollout support that no amount of YAML tooling would give us.

---

Note: I couldn't write this into `input.md` in that eval-cases directory — the harness flagged it as a protected fixture file. Let me know if you'd like it saved somewhere else, or pasted into an actual Confluence page.
