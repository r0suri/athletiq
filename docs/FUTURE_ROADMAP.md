# AthletIQ future roadmap: integrations and AI coaching

> **Status: proposal only. Nothing here is implemented.** The MVP backend stays
> feature-frozen until the deployed app is stable. Provider facts were checked on
> **2026-11-01**; several changed during 2025–2026, so re-verify each provider's current
> terms before building against it.

## Goal

Athletes keep the apps and devices they already use. AthletIQ consolidates their training
and recovery history in one place and coaches them using their actual numbers.

## Principles

1. **Numbers first, words second.** The deterministic engine (`app/domain/`) computes every
   metric. AI explains computed results; it never calculates or invents health data.
2. **Official channels only.** No password collection, scraping, or unofficial APIs, even
   where community libraries exist (e.g. Peloton, Zwift). These break without notice and
   expose users' credentials.
3. **Files before APIs.** A good FIT/TCX/GPX/CSV importer reaches nearly every platform
   today, with no approvals and no third-party dependency.
4. **Provenance on every value.** Source, external ID and import time travel with each
   record and drive deduplication, deletion and AI eligibility.
5. **Provider terms are product requirements.** Each source carries an AI-use policy;
   anything unknown is treated as *not allowed*.
6. **The user stays in control.** Least-privilege access, visible connections, disconnect
   and deletion that actually delete, export of their own data.
7. **No speculative infrastructure.** Each phase adds only what its first use needs.

## Integration channels

| Channel | How data arrives | Needs | Examples |
|---|---|---|---|
| **A. File import** | User uploads FIT, TCX, GPX, CSV or a provider's export archive | Web upload only | Garmin/Zwift/Polar FIT files, Runkeeper GPX+CSV, Strong and Peloton CSV |
| **B. Cloud API** | Server-to-server, user authorizes via OAuth 2.0 (or pastes a personal API key) | Developer registration; sometimes approval | Polar, WHOOP, Oura, Google Health API, Garmin, Strava, Hevy |
| **C. On-device SDK** | Companion mobile app reads the phone's health store and uploads | iOS/Android app, store review | Apple HealthKit, Android Health Connect |

## Provider landscape (verified 2026-11-01)

| Provider | Channel | Access and approval | Useful data | Constraints that shape the design |
|---|---|---|---|---|
| **Polar** | B (+ A: FIT) | Self-serve: any Polar Flow user can register an AccessLink client; OAuth 2.0 | Exercises, daily activity, sleep, Nightly Recharge, continuous HR | Rate limits scale with the number of connected users. Single broad read scope. |
| **WHOOP** | B | Developer dashboard app; OAuth 2.0; API v2 | Recovery (score, HRV, RHR), sleep, workouts, cycles | Per-data-type scopes. Webhooks for sleep, recovery, workouts only. Published rate limits. |
| **Oura** | B | OAuth 2.0 only (personal access tokens retired Dec 2025); **10 users before Oura approval** | Sleep, readiness, activity, HR, workouts | Gen3+ users need an active Oura Membership for API access. Oura recommends one historical pull, then webhooks. |
| **Fitbit / Pixel Watch** | B | **Google Health API** with Google OAuth 2.0; all scopes are *Restricted* and require a privacy and security review | Activity, sleep, HR and more (data types still expanding) | The legacy Fitbit Web API was **turned off on 2026-10-30**. No token migration; new consent required. |
| **Hevy** | B (key) + A | Public API for **Hevy Pro** users via a per-account API key (no OAuth); labeled early release | Strength workouts, sets, exercise history, body measurements | Users paste a key; it is stored and protected exactly like an OAuth token. |
| **Garmin** | B + A | Business program; **new access requests paused** during a 2026 overhaul. New Starter tier reported as push-only, no history, capped users. Personal API keys cover only the developer's own data | Activities (FIT), all-day health | Do not depend on approval. FIT import covers Garmin users meanwhile. |
| **Strava** | B | OAuth 2.0; Standard tier needs a paid subscription; >10 athletes needs review | Activities | Data may be shown **only to that athlete**. API data **may not be used in AI models**; get written guidance first. No intermediary platforms. More breaking changes June 2027. |
| **Apple Health** | C | HealthKit entitlement; iOS app review | Workouts, HR, HRV, sleep, plus anything other apps write (e.g. Nike Run Club) | App Review 5.1.3: no advertising/marketing/data-mining use of health data. 5.1.2(i): **explicit in-app opt-in before sending personal data to third-party AI**. |
| **Health Connect** | C | Android app; Play health-permissions declaration | Same categories, from Android apps and devices | On-device only, no OAuth or server API. Default read history is 30 days unless the user grants the history permission. Google Fit APIs are deprecated in 2026 with **no replacement for the Fit REST API**. |
| **Nike Run Club** | C (via health stores) + A | **No public API** | Runs (distance, pace, HR) | NRC writes runs to Apple Health and Health Connect; reach it through the companion app. |
| **Peloton** | A (+ C) | **No official public API** (community APIs need the user's password: not used) | Workout history | CSV workout download from the Peloton website; Peloton also syncs to other platforms. |
| **Zwift** | A | **No public developer API**; selected partners only | Rides/runs with power, HR, cadence | Per-activity FIT downloads; Zwift also syncs to Strava, Garmin and others (expect duplicates). |
| **Runkeeper** | A | **API closed to new developers since 2020** | Activities, measurements | Official export: GPX per activity plus CSV files. |
| **Strong** | A | No public API | Strength workouts | CSV export from the app (verify format before building a mapper). |
| Suunto, COROS, Wahoo, TrainingPeaks, Samsung Health | — | **Not yet researched** | — | Research before prioritizing. Many also write FIT files or sync to the health stores. |

## Phase 2 centerpiece: universal file import

Most platforms above can export or share FIT, TCX, GPX or CSV. One importer reaches them all.

```
Browser ──presigned PUT──► private S3 bucket ──event──► parser Lambda ──► normalize ──► dedup ──► DynamoDB
  (size-capped,                (SSE-KMS, raw files       (FIT: Garmin's official FIT SDK;
   content-type checked)        deleted after N days)     TCX/GPX: hardened XML parser;
                                                           CSV: per-format mappers)
```

- **Formats, in order:** FIT (richest; device-native) → GPX/TCX → CSV with mappers for the
  AthletIQ template, Strong, Hevy, Runkeeper, Peloton → provider export archives (zip).
- **Safety:** size and file-count limits; zip-bomb guards; XML parsed with external entities
  disabled; CSV values never executed or re-exported unescaped; parsing isolated in its own
  Lambda with tight memory and time limits.
- **Idempotency:** each file's SHA-256 is recorded; re-uploading the same file is a no-op.
- **Import job:** `IMPORT#<ulid>` item with status and counts (imported, merged as duplicate,
  skipped with reason), shown to the user.
- **RPE gap (needs one justified engine change):** imported activities rarely contain
  perceived effort, and session load needs RPE. The engine must never invent it. Plan:
  allow `rpe = null` on imported workouts, count them as `missing_rpe` in `data_quality`,
  and let the user rate them from an "Unrated workouts" list. A heart-rate-based load
  formula (e.g. TRIMP) can be added later as a separate, tested, documented metric.

## Provider-independent data model (extends the current table)

All items stay in the user's partition (`PK = USER#<sub>`), so isolation, querying by date,
and full deletion keep working exactly as today.

| Item | Sort key | Contents |
|---|---|---|
| Workout (existing) | `WORKOUT#<local-date>#<ulid>` | Add: `start_time_utc`, `rpe` optional for imports, `avg_hr`/`max_hr` optional, `sources[]` (one entry per contributing source), per-field provenance for merged values |
| Recovery observation | `OBS#<date>#<metric>#<source>` | Normalized metric (`sleep_hours`, `hrv_rmssd_ms`, `resting_hr`, `recovery_score`, …), value, unit. Manual check-ins become `source = manual` |
| Source link | `SRC#<provider>#<external-id>` | Points to the workout or observation. Makes re-imports and webhook re-deliveries idempotent |
| Connection | `CONN#<provider>` | Status, granted scopes, consent time and policy version, sync cursor, last sync, encrypted credentials |
| Import job | `IMPORT#<ulid>` | File hash, status, counts, errors (no raw content) |

Each `sources[]` entry records: channel (`file`/`api`/`device`/`manual`), provider, external ID
or file hash, imported time, original timezone, and the source's AI-use policy at import time.

Provider-specific scores (WHOOP recovery, Oura readiness) are stored and displayed as that
provider's metric. The engine only uses metrics it has a tested formula for.

## Deduplication across devices and platforms

Duplicates are expected, not exceptional: Zwift, Peloton and Garmin forward to Strava;
Nike Run Club and Apple Watch write to Apple Health; the same Garmin run may arrive as a FIT
upload and through the API.

1. **Exact:** same provider + external ID (`SRC#` lookup), or same file hash.
2. **Cross-source match:** compatible type (ride ≈ virtual ride), start times within ±2 min
   (compared in UTC), durations within 5%, distances within 5% when both exist. Candidates
   come from a `Query` on the user's workouts for that date ±1 day. No scan, no new index.
3. **Field-level merge:** one canonical workout; each field takes its value from the
   highest-precedence source that has it: device of record (FIT, Garmin, Polar) → platform
   (Strava, Apple Health, Health Connect) → manual. The user's own RPE and notes are never
   overwritten.
4. **Recovery observations** are kept per source. The display uses a user-ordered source
   priority, similar to Health Connect's own priority setting.
5. **Reversible:** merges are recorded. "These are different workouts" splits them and
   remembers the decision.

## Backfill and incremental sync

| Source | Backfill | Incremental |
|---|---|---|
| Files | Whatever the user uploads | Re-upload; duplicates are merged |
| Polar, WHOOP, Oura, Google Health API | Bounded window (proposed 90 days) via queued job | Webhooks where offered, otherwise scheduled polling with a stored cursor |
| Garmin (if access granted) | Depends on tier (Starter: none) | Push |
| Strava | Paged history within rate limits | Webhooks |
| HealthKit / Health Connect | On first permission grant (Health Connect: 30 days unless history permission granted) | Background delivery or change tokens in the companion app, uploaded in batches |

Workers are SQS + Lambda with per-provider rate limiting and checkpoints, so jobs resume
after failures. Webhooks are treated as notifications only: verify the signature, then
fetch the record with the user's token.

## Credentials, consent, disconnection and deletion

- **Credentials:** OAuth tokens and personal API keys are encrypted with a dedicated KMS
  key (envelope encryption) before being stored on the connection item. Never logged,
  never returned by the API, never sent to an AI model. Sync workers get their own IAM role
  with only table access and KMS decrypt. Webhook routes are public but signature-checked.
  (Rejected: one Secrets Manager secret per user per provider, which bills per secret.)
- **Consent:** request the minimum scopes; show what a connection will share before the
  provider's screen; record scopes, time and policy version; show them afterwards.
- **AI consent:** a separate, explicit opt-in to AI coaching that names the AI service.
  Required on iOS by App Review 5.1.2(i) and the right default everywhere. Opting out stops
  AI use and deletes cached insights.
- **Disconnect:** revoke with the provider, delete credentials, stop sync, then let the user
  choose to keep or delete that source's imported data.
- **Deletion:** per-source delete, provider deletion webhooks honored, raw uploads expire
  automatically, and `DELETE /v1/me` removes the whole partition and the Cognito user.
- **Portability:** users can export their consolidated data (JSON/CSV).
- **Before real users:** legal review of each provider agreement, and consumer health privacy
  laws in target markets (for example, Washington's My Health My Data Act).

## AI use only where the source permits it

Each source has an AI policy: `allowed`, `allowed_with_consent`, or `prohibited`.
Unknown means `prohibited`. Today: Strava = prohibited (unless written approval);
manual and file uploads of the user's own data = allowed with the user's AI consent;
each API provider = per its current terms, reviewed before launch.

- **Two engine runs:** the dashboard runs the engine on all data. The coach runs the same
  unchanged engine on the **AI-eligible subset** (records with at least one AI-eligible
  source for the values used). Only that output reaches the model.
- **Honesty about the gap:** the coach says when it saw less, e.g. "based on 9 of 12
  workouts; 3 imported only from Strava are excluded under Strava's terms."
- **Enforced by tests:** a test proves prohibited-source data never appears in a prompt.

## Companion mobile app (needed for Apple Health and Health Connect)

- **Why:** HealthKit and Health Connect have no cloud API. A phone app is the only official
  route to Apple Watch, Nike Run Club and the many apps that write to the health stores.
- **Scope:** sign in (same Cognito pool), choose data types, background sync, connection
  status, AI consent. All analytics and coaching stay in the web app and backend.
- **Technology (proposed):** React Native with native HealthKit and Health Connect modules,
  reusing the TypeScript API types and Amplify Auth. Validate module maturity first; native
  Swift/Kotlin is the fallback.
- **Backend need:** one idempotent batch-ingest endpoint keyed by source external IDs.
- **Store requirements:** HealthKit entitlement and usage strings; Play health-permissions
  declaration; privacy policies; App Review 5.1.3 and 5.1.2(i) compliance.

## Prioritization

| Integration | Developer access | User reach (estimate; validate) | Complexity | Phase |
|---|---|---|---|---|
| FIT/TCX/GPX/CSV import | None needed | Very high (covers most platforms) | Medium | **2** |
| Polar | Self-serve | Medium | Low | **3** |
| WHOOP | Self-serve app | Medium | Low–medium | **3** |
| Oura | Self-serve ≤10 users, then approval | Medium | Low–medium | **3** |
| Hevy API key | Pro users only | Medium (strength) | Low | **3** |
| Apple Health | App Store review | Very high | High (new app) | **4** |
| Health Connect | Play review | High | High (new app) | **4** |
| Google Health API (Fitbit/Pixel) | Restricted-scope review | High | Medium | **5** |
| Garmin | Program paused | Very high | Medium | **5** (FIT import meanwhile) |
| Strava | Paid tier, review >10 users; no AI use | Very high | Medium | **5**, display-only, AI-excluded |
| Peloton, Zwift, NRC, Runkeeper, Strong APIs | No official API | — | — | **Not planned**: files and health stores instead |

## Phases

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — MVP (now)** | Manual workouts, check-ins, profile, deterministic analytics, deployed frontend, demo account | Live URL, CI green, demo works end to end |
| **1 — Foundations** | `DELETE /v1/me`; `sources[]` on workouts (manual only); optional-RPE support with `missing_rpe`; AI coaching v1 with explicit AI consent | Deletion verified; coaching grounded, cached, consented |
| **2 — Universal import** | S3 upload pipeline; FIT, GPX, TCX; CSV mappers (template, Strong, Hevy, Runkeeper, Peloton); dedup v1; unrated-workouts list | Same activity imported twice and from two formats yields one workout |
| **3 — Self-serve APIs** | Polar, WHOOP, Oura, Hevy key; KMS credentials; backfill and webhooks; recovery observations feed wellness flags | Connect → import → disconnect → delete works for each with a real account |
| **4 — Companion app** | HealthKit and Health Connect sync (brings in Apple Watch, NRC and more) | Store-approved build; dedup against file and API sources |
| **5 — Gated APIs** | Google Health API, Garmin, Strava (each only once access is granted) | Policy tests: Strava data never reaches the model |
| **6 — Conversational coach** | Read-only, user-scoped tools over AI-eligible data; evaluation set in CI | Answers cite user data; evaluations pass |

## Open questions

- Validate the reach estimates with user research before committing to phase order.
- Raw-file retention period and per-user storage budget.
- Whether recovery observations replace manual check-ins or sit alongside them
  (proposed: alongside, with the source shown).
- Research Suunto, COROS, Wahoo, TrainingPeaks and Samsung Health before phase 3 ends.

## Sources (checked 2026-11-01)

- Strava: https://dcrainmaker.com/2024/11/stravas-changes-to-kill-off-apps.html ·
  https://www.techrepublic.com/article/news-strava-api-scraping-crackdown/ ·
  https://tryterra.co/blog/strava-api-changes-2026
- WHOOP: https://developer.whoop.com/api/ ·
  https://tryterra.co/blog/whoop-api-data-access-permissions-limitations-2026
- Garmin: https://developer.garmin.com/gc-developer-program/overview ·
  https://the5krunner.com/2026/09/14/garmin-developer-api-access-paused/ ·
  https://the5krunner.com/2026/10/22/garmin-personal-api/
- Google Health API and Fitbit: https://developers.google.com/health/about
- Google Fit and Health Connect: https://developer.android.com/health-and-fitness/health-connect/migration/fit/faq ·
  https://sahha.ai/blog/google-fit-api-sunset-migration/
- Oura: https://tryterra.co/blog/oura-api-ai-apps-access-permissions-commercial-restrictions ·
  https://pypi.org/project/django-oura/
- Polar: https://www.polar.com/accesslink-api/
- Hevy: https://api.hevyapp.com/docs
- Apple: https://techcrunch.com/2025/11/13/apples-new-app-review-guidelines-clamp-down-on-apps-sharing-personal-data-with-third-party-ai ·
  App Store Review Guidelines 5.1.2 and 5.1.3
- Nike Run Club: https://sahha.ai/integrations/nike-run-club/
- Peloton (no official API): https://dev.to/albertc44/analyze-your-peloton-workout-stats-with-real-time-updates-template-and-scripts-13eb
- Zwift: https://forums.zwift.com/t/request-to-release-zwift-semi-public-api/575162
- Runkeeper: https://help.runkeeper.com/en/hc/how-to-export-your-runkeeper-data ·
  https://rollout.com/integration-guides/runkeeper/api-essentials
