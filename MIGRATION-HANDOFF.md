# Vercel → Cloudflare Migration Handoff

**Owner:** smmariquit (GitHub) / Vercel team `stimmie` 
**Goal:** Reduce Vercel quota usage by migrating static/marketing sites to Cloudflare Pages, moving APIs to Workers, taking down retired apps, and deleting dead Vercel projects.

**Do not assume prior conversation context. Execute from this document only.**

---

## Prerequisites

1. Cloudflare account with `stimmie.dev` DNS (or ability to add CNAMEs)
2. GitHub org/user: `smmariquit` (some repos may be under `uplbtools`: check `room-tba` separately; **do not migrate room-tba**)
3. Create CF API token: Pages Edit + Workers Scripts Edit + DNS Edit
4. Add GitHub secrets per repo (or org-level):
 - `CLOUDFLARE_API_TOKEN`
 - `CLOUDFLARE_ACCOUNT_ID`
5. **Deploy pattern (all static migrations):**
 - Build in GitHub Actions (`npm ci && npm run build` or `bun install && bun run build`)
 - Deploy with `npx wrangler pages deploy <OUT_DIR>, project-name=<cf-project>`
 - **Do not** connect CF Pages Git integration (use Direct Upload / Wrangler to avoid 500 builds/mo limit)
6. After CF is live + DNS cutover verified, disconnect repo from Vercel (or delete Vercel project)

---

## Tier 1: Migrate to Cloudflare Pages

Static or static-exportable sites. Output dir is usually `dist/` (Astro/Vite) or repo root (plain HTML).

| Vercel Project | Production URL | Likely GitHub Repo | Build | Output Dir | Notes |
|----------------|----------------|-------------------|-------|------------|-------|
| `tutorial` | tutor.stimmie.dev | `smmariquit/tutorial` | `npm run build` | `dist/` | Astro static, no adapter |
| `kape` | kape.stimmie.dev | `smmariquit/kape` | none (static HTML) | `.` | Plain HTML |
| `crib` | crib.stimmie.dev | `smmariquit/the-crib` | none | `.` | Plain HTML |
| `minecraft-portfolio` | minecraft.stimmie.dev | `smmariquit/minecraft-portfolio` | none | `.` | Plain HTML |
| `freshie-guide` | guide.stimmie.dev | `smmariquit/freshie-guide` | `npm run build` | `dist/` | Astro |
| `joinpizza-fun` | www.joinpizza.fun | `smmariquit/joinpizza.fun` | `npm run build` | `dist/` | Astro |
| `uplbtools-me` | www.uplbtools.me | `smmariquit/uplbtools-me` | `npm run build` | `dist/` | Astro; apex domain |
| `data-portfolio` | data-portfolio-stimmie.vercel.app | `smmariquit/data-portfolio` | `npm run build` | `dist/` | Verify scripts |
| `scaffolding` | scaffolding.stimmie.dev | `smmariquit/scaffolding` | `npm run build` | `dist/` | Vite |
| `web-mobile` | web.stimmie.dev | `smmariquit/web-mobile` | `npm run build` | `dist/` | Verify framework |
| `ph-github-top` | (no custom domain on Vercel) | `smmariquit/ph-github-top` | `npm run build` | `dist/` | Assign `*.stimmie.dev` if desired |
| `bautista-cayabyab-clan` | bautista-cayabyab-clan.vercel.app | `smmariquit/bautista-cayabyab-clan` | `npm run build` | `out/` or `dist/` | Next.js: may need `output: 'export'` |
| `repairs` | repairs.stimmie.dev | `smmariquit/repairs` | `npm run build` | `out/` or `dist/` | Next.js marketing |
| `uxelbi` | www.uxelbi.org | `smmariquit/uxelbi` | `npm run build` | `out/` or `dist/` | External domain |
| `uplb-dsg-website` | www.uplbdsg.org | `smmariquit/uplb-dsg-website` | `npm run build` | `dist/` | External domain |
| `landing-page` | landing-page-stimmie.vercel.app | `smmariquit/landing-page` | `npm run build` | `out/` or `dist/` | Next scaffold |
| `gradesim-website` | gradesim.stimmie.dev | `smmariquit/gradesim-website` | `npm run build` | `out/` or `dist/` | Marketing only (not gradesim app) |
| `hearthcraft` | www.hearthcraft.net | `smmariquit/hearthcraft` | `npm run build` | `out/` or `dist/` | External domain |

### Tier 1 GHA template (copy per repo)

```yaml
name: Deploy to Cloudflare Pages
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
      - run: npm ci
      - run: npm run build
      - name: Deploy preview
        if: github.event_name == 'pull_request'
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name=PROJECT_NAME --branch=pr-${{ github.event.pull_request.number }}
      - name: Deploy production
        if: github.ref == 'refs/heads/main'
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name=PROJECT_NAME --branch=main
```

Adjust `dist` → `out` or `.` per repo. Create CF Pages project first: `npx wrangler pages project create PROJECT_NAME`.

### DNS cutover

For each `*.stimmie.dev` subdomain: CNAME to `<project>.pages.dev` (or custom domain in CF Pages UI). 
For apex/external domains (`uplbdsg.org`, `uxelbi.org`, `hearthcraft.net`, `joinpizza.fun`, `uplbtools.me`): update DNS at registrar or CF zone.

---

## Tier 2: CF Pages + Workers (or static only)

| Vercel Project | Action | Repo | Notes |
|----------------|--------|------|-------|
| `eductools` | **Migrate** | `smmariquit/eductools` | Vite SPA → Pages (`dist/`). Move `api/og.tsx` to **Cloudflare Worker** (replaces `@vercel/og`). `vercel.json` has rewrite to `index.html` + `api/og` function. |
| `atlas-of-my-skies` | **Migrate** | `smmariquit/atlas-of-my-skies` | Next.js: static export if possible, else keep minimal SSR on CF with OpenNext later |
| `illumina` | **TAKE DOWN** | `smmariquit/illumina` | Flutter/hackathon: remove Vercel project, do not migrate |
| `doctor-now-global` | **TAKE DOWN** | `smmariquit/doctor-now-global` | User does not need it live |
| `doctor-now-global-ui` | **TAKE DOWN** | (subfolder in doctor-now-global repo) | Delete Vercel project |

**Skip:** pharmadash, math-mock (replaced by tutee portal: remove from Vercel if present)

---

## Tier 4: Move APIs to Cloudflare Workers

Migrate serverless/API routes off Vercel. Frontends can move to CF Pages in same pass or stay on Vercel until API is moved.

| Vercel Project | Repo | API to move | Replace |
|----------------|------|-------------|---------|
| `toastmasters` | `smmariquit/toastmasters` | `/api/*` | `@vercel/kv` → **Cloudflare KV**; OpenAI calls in Worker |
| `telegraphic-summary` | `smmariquit/telegraphic-summary` | OpenAI routes | Worker proxy; static/SSR frontend on Pages |
| `173-autostudy` | `smmariquit/173-autostudy` | `/api/send-email` + rate limit | `@upstash/redis` → **CF KV** or CF Rate Limiting |
| `backend` | `smmariquit/backend` | all routes | Worker or retire if unused |
| `reviewer-app` | `smmariquit/reviewer-app` | all routes | Worker |
| `kimiroutes-evals` | `smmariquit/kimiroutes-evals` | eval API | Worker or Pages only |

After Workers live: remove Vercel project or leave frontend-only on CF Pages.

---

## Take down (remove from Vercel, do not migrate)

| Vercel Project | Notes |
|----------------|-------|
| `pharmadash` | User does not need live |
| `math-mock` | Replaced by tutee portal |
| `parokya-ni-stimmie` | Retire |
| `nextjs-ai-chatbot` | Retire |
| `illumina` | Retire |
| `doctor-now-global` | Retire |
| `doctor-now-global-ui` | Retire |

---

## Tier 5: Delete Vercel projects only

Remove from Vercel dashboard (`vercel project rm <name>`). No migration.

| Delete | Reason |
|--------|--------|
| `website` | No production URL |
| `main` | No production URL |
| `comsci-full` | No production URL |
| `smileconnect` | No production URL |
| `crewmate-dashboard` | No production URL |
| `room-tba` | Superseded by `saan-ang-room` |
| `room-tba-fix-events-missing` | Dead branch deploy |
| `cursorph02-x3do` | Duplicate hackathon deploy |
| `cursorph02-sg1h` | Duplicate |
| `cursorph02-eg9u` | Duplicate (if exists) |
| `v0-juan-s-loan-dashboard` | v0 throwaway |
| `v0-recreate-ui-from-screenshot` | v0 throwaway |

### Keep on Vercel (do NOT delete)

| Keep | URL |
|------|-----|
| `cursorph02` | cursorph02-stimmie.vercel.app (only cursorph02 instance) |
| `portal` | portal-five-drab.vercel.app |
| `literary` | literary-rust.vercel.app |
| `tel-sum` | tel-sum.vercel.app |
| `frontend` | payflow.stimmie.dev |
| `backend` | backend-rust-seven-58.vercel.app (migrate API to Worker per Tier 4, but **do not delete** project until cutover done) |

Also **keep on Vercel** (not in scope for this handoff):

- `stimmie-dev` (www.stimmie.dev)
- `tools` (www.phtools.me)
- `saan-ang-room` / Room TBA (room-tba.uplbtools.me)
- `comsci-128` (www.uplb.casa)
- `gradesim` (app, not gradesim-website)

---

## Execution order

1. Create CF Pages projects + GHA workflow for **tutorial** (pilot)
2. Verify DNS + SSL on tutor.stimmie.dev
3. Batch Tier 1 repos (group by build command: Astro `dist/`, HTML `.`, Next `out/`)
4. Tier 2: eductools + atlas-of-my-skies; take down illumina/doctor-now
5. Tier 5: delete dead Vercel projects
6. Take down pharmadash, math-mock, parokya, nextjs-ai-chatbot
7. Tier 4: Workers for toastmasters, 173-autostudy, telegraphic-summary, etc.
8. Disconnect migrated repos from Vercel Git integration

---

## Acceptance criteria

- [ ] All Tier 1 URLs resolve on Cloudflare Pages with valid SSL
- [ ] Tier 1 Vercel projects removed or disconnected
- [ ] eductools OG images work via Worker
- [ ] Tier 5 projects deleted from Vercel
- [ ] Retired apps return 404 or domain removed (illumina, doctor-now, pharmadash, etc.)
- [ ] portal, literary, tel-sum, frontend, backend, cursorph02 still exist on Vercel
- [ ] No regression on Room TBA, stimmie.dev, phtools.me, uplb.casa

---

## Reference: Vercel CLI

```bash
vercel project ls
vercel project rm <name>   # delete project
vercel domains ls          # verify DNS before cutover
```

## Reference: Wrangler

```bash
npx wrangler login
npx wrangler pages project create tutorial
npx wrangler pages deploy dist --project-name=tutorial --branch=main
```
