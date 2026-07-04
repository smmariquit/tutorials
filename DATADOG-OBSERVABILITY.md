# Datadog observability: org foundation (Phase 0)

**Datadog site:** `us5.datadoghq.com` 
**Dashboard:** https://us5.datadoghq.com 
**Owner:** smmariquit 
**Student Pack:** Pro (2 years): confirm under Organization Settings → Plan

Phase 0 is org-wide setup. Per-repo work is tracked in GitHub issues labeled `observability`.

---

## Phase 0 checklist

### Done (automated / documented)

- [x] **Synthetics**: 17 API uptime tests on US5 (`uptime/*`)
- [x] **Honeybadger uptime retired**: monitors deactivated (Datadog is source of truth)
- [x] **Service naming convention**: see table below
- [x] **Tag convention**: `env:production|preview`, `team:personal`, `hosting:vercel|cloudflare`
- [x] **GitHub issues**: `observability` label + rollout issue per active repo
- [x] **Sampling defaults**: RUM 15%, APM traces 10%, session replay off

### Manual (you, ~15 min)

- [ ] **Ad blocker**: whitelist `*.datadoghq.com` and `us5.datadoghq.com` (required to use UI)
- [ ] **Student plan**: confirm Pro active at https://us5.datadoghq.com/organization-settings/billing
- [ ] **Notifications**: https://us5.datadoghq.com/account/preferences → email; optional Slack/Discord webhook
- [ ] **Usage alerts**: Organization Settings → Usage → alert at 50% and 80%
- [ ] **GitHub integration**: https://us5.datadoghq.com/integrations/github → install on `smmariquit` + `uplbtools`
- [ ] **Supabase integration**: https://us5.datadoghq.com/integrations/supabase-cloud (when ready for DBM)
- [ ] **Rotate leaked tokens**: Honeybadger + Datadog PATs shared in chat

### Secrets (add before Phase 1 PRs)

| Secret | Scope | Notes |
|--------|-------|-------|
| `DD_API_KEY` | GitHub org secrets (`smmariquit`, `uplbtools`) + Vercel env | Server-side only |
| `DD_SITE` | All | Value: `us5.datadoghq.com` |
| `DD_RUM_APPLICATION_ID` | Per-app Vercel/CF env | From RUM app in DD UI |
| `DD_RUM_CLIENT_TOKEN` | Per-app env | Client token (public) |
| `DD_SERVICE` | Per-app env | Match service name table |
| `DD_ENV` | Per-app env | `production` / `preview` |

Create RUM apps: UX Monitoring → RUM Applications → New Application.

---

## Service names

| Service | Production URL | DD synthetics |
|---------|----------------|---------------|
| `stimmie-dev` | https://www.stimmie.dev | yes |
| `room-tba` | https://room-tba.uplbtools.me | yes |
| `phtools` | https://www.phtools.me | yes |
| `eductools` | https://eductools.vercel.app | yes |
| `uplb-casa` | https://www.uplb.casa | yes (comsci-128) |
| `tutorial` | https://tutor.stimmie.dev | yes |
| `gradesim` | (app) |: |
| `cf-worker-*` | Tier 4 APIs | add per worker |

---

## Quota guardrails

| Signal | Prod sampling |
|--------|----------------|
| RUM sessions | 15% |
| APM traces | 10% |
| Session replay | 0% (off) |
| Logs | `error` + `warn` only |
| DBM | 1–2 Supabase projects max |

---

## Rollout phases (per-repo issues)

| Phase | What | When |
|-------|------|------|
| 1 | RUM + Error Tracking | Week 1: P0 apps first |
| 2 | CI Visibility | Week 1–2: all deploy repos |
| 3 | Logs (error-only) | Week 2–3 |
| 4 | APM (`@vercel/otel` → OTLP) | Week 3–4 |
| 5 | DB Monitoring (Supabase) | Week 4: room-tba, gradesim |
| 6 | Code Security + ASM | Week 5 |

**Vercel Hobby note:** no Log/Trace Drains: use OTLP + agentless logs from app code.

---

## Repos without GitHub issues

| Repo | Reason |
|------|--------|
| `smmariquit/payflow` | Issues disabled on repo: enable in Settings or track manually |
| `portal`, `literary`, `tel-sum`, `backend`, `reviewer-app`, `uplb-dsg-website` | Repo not found under `smmariquit` / `uplbtools` |

Track payflow manually: RUM + APM + CI (P2), service `payflow`, URL https://payflow.stimmie.dev

---

## Links

- [Synthetics tests](https://us5.datadoghq.com/synthetics/tests)
- [RUM applications](https://us5.datadoghq.com/rum/list)
- [CI Visibility](https://us5.datadoghq.com/ci/pipelines)
- [Log Explorer](https://us5.datadoghq.com/logs)
- [APM Traces](https://us5.datadoghq.com/apm/traces)
- [Database Monitoring](https://us5.datadoghq.com/databases/list)
- [GitHub Student Pack: Datadog](https://education.github.com/pack)
