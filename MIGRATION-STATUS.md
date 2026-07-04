# Migration status

**Last verified:** 2026-07-05

## Tier 1: Cloudflare Pages (~85%)

Live on CF (200 + cloudflare header): tutor, kape, crib, guide, minecraft, gradesim, web, repairs, scaffolding, hearthcraft, joinpizza, uplbtools.me, uplbdsg.org, uxelbi, data.stimmie.dev.

**Gaps:** `ph-github-top`, `bautista-cayabyab-clan` (no CF project). `landing-page` (pages.dev only). `joinpizza.fun` may still use CF Git integration: prefer GHA+wrangler.

**Not done:** Disconnect Tier 1 from Vercel (DNS already on CF for most).

## Tier 2

- **eductools:** CF project exists; scratchpad work not in real repo; OG unverified; still on Vercel.
- **atlas-of-my-skies:** not started.
- **illumina / doctor-now:** not taken down.

## Automation

- Weekly PR digest: `smmariquit/tutorials` → workflow `weekly-pr-digest.yml`
- Security: zone hardening done; 17 `security_txt` insights remain on apex hosts

## Cursor skills rollout

- Baseline `.cursor/` synced via `.github/scripts/sync-cursor-skills.py`
- Rich setups preserved: eductools, room-tba, tools, stimmie.dev
