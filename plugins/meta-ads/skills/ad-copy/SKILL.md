---
name: ad-copy
description: Generate direct-response Facebook/Instagram ad copy (primary text, headlines, descriptions) for a brand in your Great Ads AI workspace, grounded in that brand's real voice, guardrails, and proven winning patterns. Runs on the Great Ads AI hosted API with your one API key — free, no credits billed. Use when the user says "write ad copy", "Meta ad copy for <brand>", "Facebook/Instagram ad text", "headlines for my ad", or "/ad-copy".
---

# Ad Copy (hosted)

This skill is a **thin client** for the Great Ads AI hosted API. It reads your brand's
voice, audience, guardrails, and proven winning patterns from your workspace; you (Claude)
do the actual copywriting, grounded in that brand data instead of generic filler. The only
credential needed is the user's **one** Great Ads API key — no OpenAI/Gemini keys, no local
generation, and this is a **read-only, free** call (no credits billed, since it never
renders or saves anything).

All API calls go through `scripts/brand.py` (stdlib-only; no pip installs). It reads
`GREAT_ADS_INTERNAL_API_KEY` + `GREAT_ADS_INTERNAL_BASE_URL` from
`~/.config/great-marketing-ai/great-marketing-ai.env`.

## Flow

1. **Pick the brand.** If the user didn't name one, list the workspace's brands and ask:
   ```bash
   python scripts/brand.py brands
   ```
2. **Load its voice.** Never invent voice, offers, or claims — pull them from the brand:
   ```bash
   python scripts/brand.py brand <brand-slug>
   ```
   Read and honor:
   - `voice.tone` / `voice.summary` — the register and personality for every line.
   - `voice.avoid_words` + `guards.words_to_avoid` — hard word bans. Never use these.
   - `guards.donts` / `guards.claims_to_avoid` — non-negotiable compliance rails. Never
     write a banned claim (settlement amounts, medical guarantees, outcome promises a
     regulated brand can't make) even if it would read as higher-converting.
   - `guards.dos` — lean into these.
   - `paid_media.meta_ads.dos` / `.donts` — Meta-specific channel rails, honor verbatim.
   - `paid_media.core_terms` — the services worth featuring in the hook/offer.
   - `paid_media.ad_headlines.winning` (`headline` + `why_it_works`) — study before writing
     headlines; model the proven angle and language, don't just copy the line.
   - `paid_media.ad_headlines.avoid` (`headline` + `reason`) — hard-reject; never ship a
     headline matching these or their pattern.
   - `creative_winners.winners` (`hook` + `why_it_works` + `metrics`) — real measured wins
     from this brand's own Meta data; lead new copy with a proven angle when one exists.
   - `creative_winners.avoid` — steer clear of angles that already lost.
   - `audience.icp` / `audience.segments` (pains, goals) — the hook angle.
   - `offers[]` (name, description, cta) — what the ad promotes and the CTA to drive.
   If the brand isn't set up in Great Ads AI yet, say so and ask for industry/offer/audience
   directly instead of guessing — never fabricate a voice.

3. **Ask what's missing:** the `offer` (what's being promoted), the `audience` (who sees it),
   and optionally a `tone` override and whether they want primary text, headlines,
   descriptions, or the full set.

4. **Write the copy** using the frameworks and rules below, then present it in the exact
   copy-paste format in §5 so it drops straight into Meta Ads Manager.

## Meta Ad Copy Structure

| Element | Max Length | Purpose |
|---|---|---|
| **Primary Text** | 125 chars visible (up to 2000 total) | The main body copy above the image/video |
| **Headline** | 40 chars | Below the image, bold — first thing read after the creative |
| **Description** | 30 chars | Below the headline, smaller text |
| **CTA Button** | Fixed dropdown options | Learn More, Sign Up, Get Quote, etc. |

## Angle tag

Every variant set should declare ONE of these canonical angles, so the set can be named
and organized cleanly in Ads Manager:

- `FOMO` — urgency / scarcity
- `UGC` — testimonial / raw authentic
- `PAIN` — problem-first / agitation
- `PROOF` — social proof / case study / result
- `BENEFIT` — benefit-first / dream outcome
- `EDU` — education / authority / teach something

Print `Angle: <TAG>` before the variants. If the user wants a mixed batch, produce a
separate block per angle — don't blend angles inside one variant set (it weakens the hook).

## 2. Write the copy

Every variant must do three things — non-negotiable:

- **Name the ONE persuasion lever it pulls.** Pick a single lever and label the variant
  with it: loss aversion, social proof, scarcity/urgency, authority, specificity/anchoring,
  curiosity gap, identity/belonging, or framing. One lever, named explicitly — not a pile
  of tactics stacked in one line.
- **Land the hook in the first 125 visible characters of primary text.** Meta hides
  everything after ~125 chars behind "...more" — the hook and the core promise must sit
  above that fold. Never bury the offer below it.
- **Count characters and show the count.** Print `used/limit` (e.g. `21/40`) next to every
  headline and description so the hard limits are visibly respected, never guessed.

### Primary Text formulas (pick 3-5 variants)

- **PAS** — Problem (state the pain), Agitate (make the consequence vivid), Solve (the
  offer as relief).
- **AIDA** — Attention (hook with a number/question/bold claim), Interest (relevant detail),
  Desire (the outcome), Action (clear CTA).
- **Social proof + CTA** — lead with a result or testimonial angle, follow with the offer,
  close with urgency.
- **Question hook** — open with a question the audience can't ignore, answer with the offer.

### Headline formulas (generate 5-10, ≤ 40 chars)

- **Question / pain callout** — "Injured in a Car Crash?"
- **Specificity** — a real number or concrete detail beats a vague claim
- **Social proof** — "500+ Families Helped This Year"
- **Outcome-first** — the dream result stated plainly
- **Differentiation** — what makes this brand's offer different from the obvious alternative

### Description formulas (generate 3-5, ≤ 30 chars)

Reinforce the CTA and remove friction — e.g. "100% Free Consultation", "No Win, No Fee",
"Call Now. 24/7". Match the brand's real offer terms, not invented ones.

## 3. Output format

**One fenced code block = one Ads Manager field.** The user pastes each piece straight into
Meta Ads Manager, so the copy has to come out clean:

- Put every pasteable field in its own ` ```text ` code block — each primary text, each
  headline, each description. Never a blockquote, never a numbered list, never wrapping
  quotes.
- **Inside the fence is ONLY the clean copy** — no label, no number, no surrounding quotes,
  no markdown. The reader copies the block and pastes it as-is.
- **Every annotation goes on the line ABOVE the fence:** the slot label (`V1`/`H1`/`D1`),
  the framework, the persuasion lever, and the `used/limit` char count, separated by `·`.
- **Bilingual brands (e.g. Spanish-speaking audiences):** emit each language as its own
  block (`V1-EN` / `V1-ES`, `H1-EN` / `H1-ES`) — they run as separate ads.

Emit it in this shape (shown with a four-backtick outer fence so the inner ` ```text `
blocks are literal):

````
## Meta Ad Copy: <Brand> (<niche>)
Angle: PAIN | Offer: <offer> | Audience: <audience> | CTA: <cta>

PRIMARY TEXT  (≥3 variants; hook in the first 125 chars)

V1 · PAS · Loss aversion · 134 chars
```text
<primary text copy>
```

HEADLINES  (max 40 chars; generate 5-10)

H1 · Question · Curiosity · 21/40
```text
<headline copy>
```

DESCRIPTIONS  (max 30 chars; generate 3-5)

D1 · 20/30
```text
<description copy>
```

CTA: <fixed dropdown option>   (nothing to paste)

A/B Testing Plan
- Test the top 2 primary texts against the same headline.
- Test the top 3 headlines against the winning primary text.
- Run each variant 3-5 days or 1000+ impressions before judging.
````

## Rules

- **Honor the brand profile.** Never use a banned word, never make a banned claim, never
  ship a headline matching an `avoid` entry — even if the copy would read as higher-CTR.
  Lead on proven `ad_headlines.winning` and `creative_winners.winners` patterns.
- **Generate multiple variants.** At least 3 primary texts and 5 headlines.
- **Character limits are hard constraints.** Headline ≤ 40 chars, Description ≤ 30 chars.
  Count carefully and show the count.
- **Plain words, 4th-5th grade reading level.** Write so a casual reader — including a
  non-native English speaker — gets it on the first read. The common everyday word beats
  the fancy one ("use" not "utilize"). Avoid clever metaphors or wordplay that need a
  second read. Same standard applies to any other language: plain, everyday, no literary
  turns of phrase.
- **No em or en dashes in any generated copy.** Use a comma, period, or colon for the
  pause instead. Plain hyphens in compound words (`cost-per-case`) are fine.
- **No compliance violations.** Don't promise specific settlement/outcome amounts. Don't
  make medical or legal guarantees a regulated brand can't make.
- **Include an A/B testing plan.** Copy without a test plan is just guessing.
- **This skill never creates or publishes ads.** It only generates copy for the user to
  review and paste into Ads Manager themselves.
- **No local keys.** If `brand.py` reports a missing key, the user generates one in the
  dashboard → Settings → Integrations → **Connect to Claude**, then pastes the ready-made
  env block into `~/.config/great-marketing-ai/great-marketing-ai.env`.
